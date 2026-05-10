import json
import os
import faiss
from neo4j import GraphDatabase
from dotenv import load_dotenv
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent.parent
load_dotenv(_BACKEND.parent / ".env")

VECTOR_STORE_DIR = _BACKEND.parent / "data" / "vector_store"
METADATA_PATH = VECTOR_STORE_DIR / "metadata_mapping.json"
INDEX_PATH = VECTOR_STORE_DIR / "patents.index"

class FinalSyncer:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
        )

    def sync(self):
        print("Loading FAISS index and metadata...")
        index = faiss.read_index(str(INDEX_PATH))
        with open(METADATA_PATH, 'r') as f:
            metadata = json.load(f)
        
        # Based on your error:
        # Key = '0', '1', '2' (The FAISS Row)
        # Value = '171-148-280-142-283' (The Patent ID)

        with self.driver.session() as session:
            # We match on 'patent_id' because that's what your Neo4j nodes use
            query = """
            UNWIND $data as row
            MATCH (p:Patent {patent_id: row.p_id})
            SET p.embedding = row.emb
            RETURN count(p) as updated
            """
            
            batch = []
            total_updated = 0
            
            for row_idx, patent_id in metadata.items():
                # Pull vector using the key (row index)
                vector = index.reconstruct(int(row_idx)).tolist()
                
                batch.append({
                    "p_id": str(patent_id),
                    "emb": vector
                })
                
                if len(batch) >= 500:
                    result = session.run(query, data=batch)
                    total_updated += result.single()["updated"]
                    batch = []
                    print(f"  [Verified Sync] Updated {total_updated} nodes...")

            if batch:
                result = session.run(query, data=batch)
                total_updated += result.single()["updated"]

        print(f"DONE! {total_updated} patents now have embeddings in Neo4j.")

    def close(self):
        self.driver.close()

if __name__ == "__main__":
    syncer = FinalSyncer()
    syncer.sync()