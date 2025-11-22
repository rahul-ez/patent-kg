# 1. Test Neo4j
from neo4j import GraphDatabase

uri = "bolt://localhost:7687"
driver = GraphDatabase.driver(uri, auth=("neo4j", "password123"))

try:
    driver.verify_connectivity()
    print("Neo4j is connected!")
except Exception as e:
    print(f"Neo4j failed: {e}")

# 2. Test Chroma
import chromadb

try:
    # Connect to the Docker container, not a local file
    chroma_client = chromadb.HttpClient(host='localhost', port=8000)
    chroma_client.heartbeat()
    print("ChromaDB is connected!")
except Exception as e:
    print(f"Chroma failed: {e}")