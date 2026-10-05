"""Add missing metadata/run snapshots without repeating the full patent import."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import inspect, text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend" / "src"))
load_dotenv(ROOT / ".env")

from persistence.database import get_engine  # noqa: E402


def nullable_int(value, minimum=0):
    if value is None or str(value).strip() == "":
        return None
    number = int(value)
    return number if number >= minimum else None


def ensure_schema(engine):
    # MySQL DDL commits implicitly; keep it outside data-import transactions.
    with engine.connect() as connection:
        for table, additions in {
            "patents": {"jurisdiction": "VARCHAR(10) NULL", "cites_patent_count": "INT NULL", "family_size": "INT NULL"},
            "analysis_runs": {"idea_text": "TEXT NULL", "improvement_payload": "JSON NULL"},
        }.items():
            columns = {column["name"] for column in inspect(connection).get_columns(table)}
            for name, definition in additions.items():
                if name not in columns:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))
        for index in inspect(connection).get_indexes("analysis_runs"):
            if index["unique"] and index["column_names"] == ["query_id"]:
                name = connection.dialect.identifier_preparer.quote(index["name"])
                connection.execute(text(f"ALTER TABLE analysis_runs DROP INDEX {name}"))
        if not any(index["column_names"] == ["query_id"] for index in inspect(connection).get_indexes("analysis_runs")):
            connection.execute(text("CREATE INDEX ix_run_query ON analysis_runs(query_id)"))
        connection.execute(text("""
            CREATE OR REPLACE VIEW vw_patent_retrieval AS
            SELECT p.patent_id, p.title, p.abstract, d.name AS domain,
                   p.publication_year, p.legal_status, p.cited_by_patent_count,
                   p.url, p.jurisdiction, p.cites_patent_count, p.family_size
            FROM patents p LEFT JOIN domains d ON d.domain_id=p.domain_id
        """))
        connection.commit()


def backfill_metadata(engine, source: Path, batch_size=5000):
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    total = 0
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TEMPORARY TABLE integration_metadata (
                patent_id VARCHAR(80) PRIMARY KEY,
                jurisdiction VARCHAR(10) NULL,
                cites_patent_count INT NULL,
                family_size INT NULL
            ) ENGINE=InnoDB
        """))
        try:
            for frame in pd.read_csv(source, usecols=["patent_id", "jurisdiction", "cites_patent_count", "family_size"], dtype=str, keep_default_na=False, chunksize=batch_size):
                rows = [{"patent_id": row["patent_id"], "jurisdiction": row["jurisdiction"].strip() or None,
                         "cites_patent_count": nullable_int(row["cites_patent_count"]),
                         "family_size": nullable_int(row["family_size"], minimum=1)} for row in frame.to_dict("records")]
                connection.execute(text("""
                    INSERT INTO integration_metadata VALUES
                    (:patent_id, :jurisdiction, :cites_patent_count, :family_size)
                """), rows)
                total += len(rows)
            connection.execute(text("""
                UPDATE patents p JOIN integration_metadata m ON m.patent_id=p.patent_id
                SET p.jurisdiction=m.jurisdiction, p.cites_patent_count=m.cites_patent_count,
                    p.family_size=m.family_size
            """))
        finally:
            connection.execute(text("DROP TEMPORARY TABLE integration_metadata"))
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema-only", action="store_true")
    args = parser.parse_args()
    ensure_schema(get_engine())
    print("Integration schema is ready", flush=True)
    if not args.schema_only:
        print(f"Backfilled {backfill_metadata(get_engine(), ROOT / 'data/processed/patents.csv'):,} source metadata rows")
