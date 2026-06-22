import os
import logging
import numpy as np
import torch
import pandas as pd
from torch_geometric.data import Data
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

# Neo4j configuration
_NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
_NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
_NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

def fetch_subgraph_neighbors(patent_ids: list, limit_fam=150, limit_cpc=250, limit_cite=150) -> list:
    """
    Query Neo4j for structural neighbors of the target patents to expand the graph context.
    Returns a unique list of neighbor patent IDs.
    """
    query = """
    MATCH (p:Patent)-[:SIMPLE_FAMILY_MEMBER|EXTENDED_FAMILY_MEMBER]-(neigh:Patent)
    WHERE p.patent_id IN $ids AND NOT neigh.patent_id IN $ids
    RETURN DISTINCT neigh.patent_id AS id
    LIMIT $limit_fam

    UNION

    MATCH (p:Patent)-[:HAS_CPC]->(c:CPCCode)<-[:HAS_CPC]-(neigh:Patent)
    WHERE p.patent_id IN $ids AND NOT neigh.patent_id IN $ids
    RETURN DISTINCT neigh.patent_id AS id
    LIMIT $limit_cpc

    UNION

    MATCH (p:Patent)-[:CITES_PAPER]->(paper:Paper)<-[:CITES_PAPER]-(neigh:Patent)
    WHERE p.patent_id IN $ids AND NOT neigh.patent_id IN $ids
    RETURN DISTINCT neigh.patent_id AS id
    LIMIT $limit_cite
    """
    neighbor_ids = []
    driver = None
    try:
        driver = GraphDatabase.driver(_NEO4J_URI, auth=(_NEO4J_USER, _NEO4J_PASSWORD))
        with driver.session() as session:
            result = session.run(
                query, 
                ids=patent_ids, 
                limit_fam=limit_fam, 
                limit_cpc=limit_cpc, 
                limit_cite=limit_cite
            )
            for record in result:
                if record["id"]:
                    neighbor_ids.append(record["id"])
    except Exception as exc:
        logger.warning("Failed to fetch GNN graph neighbors from Neo4j: %s. Using candidate nodes only.", exc)
    finally:
        if driver:
            driver.close()
    return list(set(neighbor_ids))

def fetch_subgraph_edges(patent_ids: list) -> list:
    """
    Query Neo4j for all connections among the expanded set of patents.
    Returns a list of tuples representing edges (source_id, target_id).
    """
    query = """
    MATCH (a:Patent)-[:SIMPLE_FAMILY_MEMBER|EXTENDED_FAMILY_MEMBER]->(b:Patent)
    WHERE a.patent_id IN $ids AND b.patent_id IN $ids
    RETURN a.patent_id AS source, b.patent_id AS target

    UNION

    MATCH (a:Patent)-[:HAS_CPC]->(c:CPCCode)<-[:HAS_CPC]-(b:Patent)
    WHERE a.patent_id IN $ids AND b.patent_id IN $ids AND a.patent_id < b.patent_id
    RETURN a.patent_id AS source, b.patent_id AS target

    UNION

    MATCH (a:Patent)-[:CITES_PAPER]->(paper:Paper)<-[:CITES_PAPER]-(b:Patent)
    WHERE a.patent_id IN $ids AND b.patent_id IN $ids AND a.patent_id < b.patent_id
    RETURN a.patent_id AS source, b.patent_id AS target
    """
    edges = []
    driver = None
    try:
        driver = GraphDatabase.driver(_NEO4J_URI, auth=(_NEO4J_USER, _NEO4J_PASSWORD))
        with driver.session() as session:
            result = session.run(query, ids=patent_ids)
            for record in result:
                edges.append((record["source"], record["target"]))
    except Exception as exc:
        logger.warning("Failed to fetch GNN graph edges from Neo4j: %s. Graph will run with empty edge set.", exc)
    finally:
        if driver:
            driver.close()
    return edges

def build_subgraph_data(hits: list, patents_df: pd.DataFrame, metadata_mapping: dict, faiss_index, st_model) -> tuple:
    """
    Main entry point to assemble retrieved and expanded patents into a PyTorch Geometric Data graph object.
    
    Returns:
        (Data, dict): The constructed Data object, and a mapping of patent_id -> node_index.
    """
    # 1. Gather seed candidate patent IDs from retrieval and KG expansion
    candidate_ids = [hit["patent_id"] for hit in hits if hit.get("patent_id")]
    
    # 2. Fetch structural neighbors to target 500-800 total nodes
    neighbor_ids = fetch_subgraph_neighbors(candidate_ids)
    
    # Combined deduplicated set of nodes
    all_pids = list(candidate_ids)
    candidate_set = set(candidate_ids)
    for pid in neighbor_ids:
        if pid not in candidate_set:
            all_pids.append(pid)
            
    N = len(all_pids)
    logger.info("Building GNN subgraph: %d candidates + %d structural neighbors = %d total nodes", 
                len(candidate_ids), len(all_pids) - len(candidate_ids), N)
    
    # Index mapping: patent_id -> index in node feature matrix
    pid_to_idx = {pid: i for i, pid in enumerate(all_pids)}
    
    # 3. Build node features matrix x of shape [N, 780]
    # We will build features in parallel
    x_features = []
    
    # Pre-index patents_df for fast O(1) lookups
    # (Checking if 'patent_id' index exists or indexing temporarily)
    if not isinstance(patents_df.index, pd.Index) or patents_df.index.name != 'patent_id':
        patents_lookup = patents_df.set_index('patent_id')
    else:
        patents_lookup = patents_df
        
    for pid in all_pids:
        # A. SBERTa embedding (768-dim) lookup with SentenceTransformer fallback
        emb = None
        row_idx_str = None
        
        # Check metadata mapping first to find its row index in the FAISS index
        for k, v in metadata_mapping.items():
            if v == pid:
                row_idx_str = k
                break
                
        if row_idx_str is not None:
            try:
                emb = faiss_index.reconstruct(int(row_idx_str))
            except Exception:
                pass
                
        if emb is None:
            # Fallback to SentenceTransformer encoding
            title = ""
            abstract = ""
            if pid in patents_lookup.index:
                row = patents_lookup.loc[pid]
                if isinstance(row, pd.Series):
                    title = str(row.get("title", ""))
                    abstract = str(row.get("abstract", ""))
                elif isinstance(row, pd.DataFrame):
                    # Multi-match safety
                    title = str(row.iloc[0].get("title", ""))
                    abstract = str(row.iloc[0].get("abstract", ""))
            
            # If still empty, check hits list as a backup
            if not title and not abstract:
                for hit in hits:
                    if hit.get("patent_id") == pid:
                        title = hit.get("title", "")
                        abstract = hit.get("abstract", "")
                        break
                        
            text = f"{title}. {abstract}".strip()
            if text and text != ".":
                emb = st_model.encode(text)
            else:
                # Absolute baseline zero embedding
                emb = np.zeros(768, dtype=np.float32)
                
        # B. Load structural and categorical metadata from patents_deduped.csv
        cites = 0.0
        cited = 0.0
        fam = 1.0
        jurisdiction = ""
        domain = ""
        
        if pid in patents_lookup.index:
            row = patents_lookup.loc[pid]
            if isinstance(row, pd.Series):
                cites = float(row.get("cites_patent_count", 0) or 0)
                cited = float(row.get("cited_by_patent_count", 0) or 0)
                fam = float(row.get("family_size", 1) or 1)
                jurisdiction = str(row.get("jurisdiction", ""))
                domain = str(row.get("domain", ""))
            elif isinstance(row, pd.DataFrame):
                cites = float(row.iloc[0].get("cites_patent_count", 0) or 0)
                cited = float(row.iloc[0].get("cited_by_patent_count", 0) or 0)
                fam = float(row.iloc[0].get("family_size", 1) or 1)
                jurisdiction = str(row.iloc[0].get("jurisdiction", ""))
                domain = str(row.iloc[0].get("domain", ""))
                
        # Log-transform scalar properties (log1p damping)
        cites_val = np.log1p(cites)
        cited_val = np.log1p(cited)
        fam_val = np.log1p(fam)
        
        # One-hot encoding for jurisdiction (jur_EP, jur_US, jur_WO)
        jur_EP = 1.0 if jurisdiction == "EP" else 0.0
        jur_US = 1.0 if jurisdiction == "US" else 0.0
        jur_WO = 1.0 if jurisdiction == "WO" else 0.0
        
        # One-hot encoding for domain (6 classes)
        dom_AI = 1.0 if domain == "AI" else 0.0
        dom_Automotive = 1.0 if domain == "Automotive" else 0.0
        dom_Energy = 1.0 if domain == "Energy" else 0.0
        dom_IoT = 1.0 if domain == "IoT" else 0.0
        dom_Mechanical = 1.0 if domain == "Mechanical" else 0.0
        dom_Medical = 1.0 if domain == "Medical" else 0.0
        
        node_feat = np.concatenate([
            emb, 
            [cites_val, cited_val, fam_val],
            [jur_EP, jur_US, jur_WO],
            [dom_AI, dom_Automotive, dom_Energy, dom_IoT, dom_Mechanical, dom_Medical]
        ])
        x_features.append(node_feat)
        
    x_tensor = torch.tensor(np.array(x_features), dtype=torch.float)
    
    # 4. Fetch subgraph edges and convert to PyG edge_index format
    edges = fetch_subgraph_edges(all_pids)
    
    sources = []
    targets = []
    for src_id, tgt_id in edges:
        if src_id in pid_to_idx and tgt_id in pid_to_idx:
            s = pid_to_idx[src_id]
            t = pid_to_idx[tgt_id]
            # SAGE is undirected; add both directions
            sources.extend([s, t])
            targets.extend([t, s])
            
    # Deduplicate edges
    edge_set = set(zip(sources, targets))
    if edge_set:
        sources, targets = zip(*edge_set)
        edge_index = torch.tensor([sources, targets], dtype=torch.long)
    else:
        edge_index = torch.empty((2, 0), dtype=torch.long)
        
    data = Data(x=x_tensor, edge_index=edge_index)
    return data, pid_to_idx
