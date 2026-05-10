import torch
from neo4j import GraphDatabase
from torch_geometric.data import Data
import os
from dotenv import load_dotenv

load_dotenv()

class PatentDataLoader:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"), 
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )

    def get_pyg_data(self):
        with self.driver.session() as session:
            print("Fetching nodes and checking dimensions...")
            nodes_query = "MATCH (p:Patent) RETURN p.patent_id as pid, p.embedding as emb"
            nodes_res = session.run(nodes_query)
            
            node_map = {}
            features = []
            
            for i, record in enumerate(nodes_res):
                p_id = record['pid']
                emb = record['emb']
                
                # If embedding is missing or wrong size, we'll handle it
                if emb is None:
                    emb = [0.0] * 768 # Default to 768
                
                # CRITICAL FIX: Ensure every embedding is exactly 768
                # If it's 384, we'll pad it with zeros so PyTorch is happy
                if len(emb) < 768:
                    emb = emb + [0.0] * (768 - len(emb))
                elif len(emb) > 768:
                    emb = emb[:768] # Truncate if too long
                
                node_map[p_id] = i
                features.append(emb)
            
            x = torch.tensor(features, dtype=torch.float)
            print(f"Verified feature matrix shape: {x.shape}") # Should be [Total, 768]

            # ... (rest of your edge code stays the same)
    
            # 2. Get all Citation/Family Edges
            # We are using the family relationships found in your db.relationshipTypes()
            edges_query = """MATCH (p1:Patent)-[:SIMPLE_FAMILY_MEMBER|EXTENDED_FAMILY_MEMBER]->(p2:Patent) 
            RETURN p1.patent_id as source, p2.patent_id as target
            """
            edges_res = session.run(edges_query)
            
            edge_sources = []
            edge_targets = []
            for record in edges_res:
                if record['source'] in node_map and record['target'] in node_map:
                    edge_sources.append(node_map[record['source']])
                    edge_targets.append(node_map[record['target']])
            
            edge_index = torch.tensor([edge_sources, edge_targets], dtype=torch.long)

            return Data(x=x, edge_index=edge_index)

    def close(self):
        self.driver.close()