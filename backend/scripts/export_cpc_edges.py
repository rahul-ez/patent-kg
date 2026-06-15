# Run locally: patent-kg/scripts/export_cpc_edges.py
from neo4j import GraphDatabase
import pandas as pd
import os
from dotenv import load_dotenv
load_dotenv()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", ""))
)

with driver.session() as session:
    # Patent → CPC edges
    result = session.run("""
        MATCH (p:Patent)-[:HAS_CPC]->(c:CPCCode)
        RETURN p.patent_id AS patent_id, c.code AS cpc_code
    """)
    cpc_df = pd.DataFrame([r.data() for r in result])

    # CPC siblings: patents sharing a CPC code = implicit edges
    result2 = session.run("""
        MATCH (p1:Patent)-[:HAS_CPC]->(c:CPCCode)<-[:HAS_CPC]-(p2:Patent)
        WHERE p1.patent_id < p2.patent_id
        RETURN p1.patent_id AS src, p2.patent_id AS dst, c.code AS via_cpc
        LIMIT 500000
    """)
    cpc_edges_df = pd.DataFrame([r.data() for r in result2])

driver.close()

cpc_df.to_csv("patent_cpc_map.csv", index=False)
cpc_edges_df.to_csv("cpc_sibling_edges.csv", index=False)
print(f"CPC map: {len(cpc_df)} rows")
print(f"CPC sibling edges: {len(cpc_edges_df)} rows")