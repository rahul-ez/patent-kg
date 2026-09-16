"""Manual Neo4j connectivity probe; it is not part of the automated test suite."""
import os

from dotenv import load_dotenv
from neo4j import GraphDatabase


def main() -> int:
    load_dotenv()
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        print("NEO4J_PASSWORD is not configured; skipping connectivity probe.")
        return 0

    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), password),
    )
    try:
        driver.verify_connectivity()
        print("Neo4j is connected.")
        return 0
    except Exception as exc:
        print(f"Neo4j connectivity failed: {exc}")
        return 1
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
