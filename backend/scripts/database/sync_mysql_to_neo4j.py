"""Project normalized MySQL facts into Neo4j for graph traversal.

MySQL remains the authority. This script performs idempotent Cypher ``MERGE``
operations and never reads or writes business facts directly in Neo4j first.
"""
from __future__ import annotations

import argparse
import os
import sys
from itertools import islice
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

_BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_BACKEND / "src"))
load_dotenv(_BACKEND.parent / ".env")

from persistence.database import get_engine, verify_database  # noqa: E402


def _batches(iterable, size: int):
    iterator = iter(iterable)
    while batch := list(islice(iterator, size)):
        yield batch


def _read_rows(sql: str):
    from sqlalchemy import text
    with get_engine().connect() as connection:
        return [dict(row) for row in connection.execute(text(sql)).mappings()]


def sync(batch_size: int) -> None:
    verify_database()
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
    )
    queries = [
        ("patents", """
            SELECT p.patent_id, p.title, p.abstract, p.publication_year, p.legal_status,
                   p.cited_by_patent_count, p.url, d.name AS domain
            FROM patents p LEFT JOIN domains d ON d.domain_id=p.domain_id
        """, """
            UNWIND $rows AS row MERGE (p:Patent {patent_id: row.patent_id})
            SET p.title=row.title, p.abstract=row.abstract, p.publication_year=row.publication_year,
                p.legal_status=row.legal_status, p.cited_by_patent_count=row.cited_by_patent_count,
                p.url=row.url, p.domain=row.domain
        """),
        ("assignees", """
            SELECT p.patent_id, a.name AS company_name FROM patent_assignees pa
            JOIN patents p ON p.patent_id=pa.patent_id JOIN assignees a ON a.assignee_id=pa.assignee_id
        """, """
            UNWIND $rows AS row MATCH (p:Patent {patent_id: row.patent_id})
            MERGE (c:Company {company_name: row.company_name}) MERGE (c)-[:OWNS]->(p)
        """),
        ("inventors", """
            SELECT p.patent_id, i.name AS inventor_name FROM patent_inventors pi
            JOIN patents p ON p.patent_id=pi.patent_id JOIN inventors i ON i.inventor_id=pi.inventor_id
        """, """
            UNWIND $rows AS row MATCH (p:Patent {patent_id: row.patent_id})
            MERGE (i:Inventor {inventor_name: row.inventor_name}) MERGE (i)-[:INVENTED]->(p)
        """),
        ("cpc", "SELECT patent_id, cpc_code FROM patent_cpc_codes", """
            UNWIND $rows AS row MATCH (p:Patent {patent_id: row.patent_id})
            MERGE (c:CPCCode {code: row.cpc_code}) MERGE (p)-[:HAS_CPC]->(c)
        """),
        ("npl", """
            SELECT pn.patent_id, n.npl_id, n.citation FROM patent_npl_references pn
            JOIN npl_references n ON n.npl_id=pn.npl_id
        """, """
            UNWIND $rows AS row MATCH (p:Patent {patent_id: row.patent_id})
            MERGE (paper:Paper {npl_id: toString(row.npl_id)}) SET paper.title=row.citation
            MERGE (p)-[:CITES_PAPER]->(paper)
        """),
        ("families", "SELECT patent_id, related_patent_id, relation_type FROM patent_families", """
            UNWIND $rows AS row MATCH (a:Patent {patent_id: row.patent_id})
            MATCH (b:Patent {patent_id: row.related_patent_id})
            FOREACH (_ IN CASE WHEN row.relation_type='EXTENDED' THEN [1] ELSE [] END |
                MERGE (a)-[:EXTENDED_FAMILY_MEMBER]->(b))
            FOREACH (_ IN CASE WHEN row.relation_type<>'EXTENDED' THEN [1] ELSE [] END |
                MERGE (a)-[:SIMPLE_FAMILY_MEMBER]->(b))
        """),
    ]
    try:
        with driver.session() as session:
            for label, source_sql, cypher in queries:
                rows = _read_rows(source_sql)
                for batch in _batches(rows, batch_size):
                    session.run(cypher, rows=batch).consume()
                print(f"Projected {len(rows):,} {label} rows")
    finally:
        driver.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Project MySQL patent facts into Neo4j.")
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()
    sync(args.batch_size)
