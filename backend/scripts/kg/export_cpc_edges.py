import os
from pathlib import Path

import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[3]
_OUTPUT_DIR = _REPO_ROOT / "data" / "exports"
load_dotenv(_REPO_ROOT / ".env")

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

_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
cpc_df.to_csv(_OUTPUT_DIR / "patent_cpc_map.csv", index=False)
cpc_edges_df.to_csv(_OUTPUT_DIR / "cpc_sibling_edges.csv", index=False)
print(f"CPC map: {len(cpc_df)} rows")
print(f"CPC sibling edges: {len(cpc_edges_df)} rows")
