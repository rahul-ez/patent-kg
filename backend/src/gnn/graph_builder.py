import os
import logging
import numpy as np
import torch
import pandas as pd
from torch_geometric.data import Data
from neo4j import GraphDatabase
from time import perf_counter
from retrieval.patent_embeddings import PatentEmbeddings

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

def build_subgraph_data(hits: list, patents_df: pd.DataFrame, metadata_mapping: dict, faiss_index, st_model,
                        *, embedding_store=None, timings=None) -> tuple:
    """
    Main entry point to assemble retrieved and expanded patents into a PyTorch Geometric Data graph object.
    
    Returns:
        (Data, dict): The constructed Data object, and a mapping of patent_id -> node_index.
    """
    # 1. Gather seed candidate patent IDs from retrieval and KG expansion
    candidate_ids = list(dict.fromkeys(hit["patent_id"] for hit in hits if hit.get("patent_id")))
    
    # 2. Fetch structural neighbors to target 500-800 total nodes
    started = perf_counter()
    neighbor_ids = fetch_subgraph_neighbors(candidate_ids)
    if timings is not None:
        timings["gnn_neighbors"] = perf_counter() - started
    
    # Combined deduplicated set of nodes
    all_pids = list(candidate_ids)
    candidate_set = set(candidate_ids)
    for pid in neighbor_ids:
        if pid not in candidate_set:
            all_pids.append(pid)
            candidate_set.add(pid)
            
    N = len(all_pids)
    logger.info("Building GNN subgraph: %d candidates + %d structural neighbors = %d total nodes", 
                len(candidate_ids), len(all_pids) - len(candidate_ids), N)
    
    # Index mapping: patent_id -> index in node feature matrix
    pid_to_idx = {pid: i for i, pid in enumerate(all_pids)}
    
    # 3. Build node features matrix x of shape [N, 780]
    x_features = []
    started = perf_counter()
    if embedding_store is None:
        # Legacy/offline callers still get batching, without a shared disk cache.
        rows = (patents_df.drop_duplicates(subset="patent_id").set_index("patent_id").to_dict("index")
                if patents_df.index.name != "patent_id" else patents_df.to_dict("index"))
        embedding_store = PatentEmbeddings(faiss_index, metadata_mapping, rows, st_model)
    rows = embedding_store.patent_rows
    hits_by_id = {hit["patent_id"]: hit for hit in hits if hit.get("patent_id")}
    vectors = embedding_store.get_many([hits_by_id.get(pid, {"patent_id": pid}) for pid in all_pids])
    if timings is not None:
        timings["gnn_embeddings"] = perf_counter() - started

    for pid, emb in zip(all_pids, vectors):
        # B. Load structural and categorical metadata from canonical public rows.
        row = rows.get(pid, {})
        cites = float(row.get("cites_patent_count", 0) or 0)
        cited = float(row.get("cited_by_patent_count", 0) or 0)
        fam = float(row.get("family_size", 1) or 1)
        jurisdiction = str(row.get("jurisdiction", ""))
        domain = str(row.get("domain", ""))
                
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
        
    x_tensor = torch.tensor(np.array(x_features).reshape(N, faiss_index.d + 12), dtype=torch.float)
    
    # 4. Fetch subgraph edges and convert to PyG edge_index format
    started = perf_counter()
    edges = fetch_subgraph_edges(all_pids)
    if timings is not None:
        timings["gnn_edges"] = perf_counter() - started
    
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
