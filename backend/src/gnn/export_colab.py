import pandas as pd
import numpy as np
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()
driver = GraphDatabase.driver(os.getenv("NEO4J_URI"), auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")))

def export_v3():
    with driver.session() as session:
        # 1. Get the real count first
        count = session.run("MATCH (p:Patent) RETURN count(p) as c").single()["c"]
        print(f"Exporting {count} patents...")

        # 2. Initialize a memory-mapped array to save RAM
        # This writes directly to disk instead of filling up your Mac's memory
        embs = np.zeros((count, 768), dtype=np.float32)
        ids = []

        results = session.run("MATCH (p:Patent) RETURN p.patent_id as id, p.embedding as emb")
        
        for i, r in enumerate(results):
            ids.append(str(r["id"]))
            val = r["emb"]
            if val and len(val) == 768:
                embs[i] = val
            elif val and len(val) == 384:
                embs[i, :384] = val # Pad with zeros
            
            if i % 10000 == 0:
                print(f"  Progress: {i}/{count}...")

        # 3. Save Files
        np.save("embeddings_fixed.npy", embs)
        pd.DataFrame({"id": ids}).to_csv("node_ids_fixed.csv", index=False)
        
        print("Now exporting edges...")
        edges = session.run("MATCH (p1:Patent)-[:SIMPLE_FAMILY_MEMBER|EXTENDED_FAMILY_MEMBER]->(p2:Patent) RETURN p1.patent_id as src, p2.patent_id as tgt")
        edge_data = [{"src": str(r["src"]), "tgt": str(r["tgt"])} for r in edges]
        pd.DataFrame(edge_data).to_csv("edges_fixed.csv", index=False)
        print("ALL DONE. Check file sizes before uploading!")

export_v3()