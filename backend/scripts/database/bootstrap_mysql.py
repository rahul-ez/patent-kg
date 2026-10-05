"""Idempotently import normalized CSV data into MySQL in bounded batches.

Run from ``backend`` after starting Docker Compose:
    python scripts/database/bootstrap_mysql.py
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

_BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_BACKEND / "src"))
load_dotenv(_BACKEND.parent / ".env")

from persistence.database import DatabaseUnavailable, get_engine, verify_database  # noqa: E402
from retrieval.classifications import cpc_rows  # noqa: E402

_PROCESSED = _BACKEND.parent / "data" / "processed"


def _records(frame: pd.DataFrame, columns: list[str]) -> list[dict]:
    clean = frame.reindex(columns=columns).fillna("")
    return clean.to_dict(orient="records")


def _upsert_domains(connection, patents: pd.DataFrame) -> dict[str, int]:
    from sqlalchemy import text

    names = sorted({str(value).strip() for value in patents.get("domain", []) if str(value).strip()})
    if names:
        connection.execute(text("INSERT IGNORE INTO domains(name) VALUES (:name)"), [{"name": name} for name in names])
    rows = connection.execute(text("SELECT domain_id, name FROM domains")).mappings()
    return {row["name"]: row["domain_id"] for row in rows}


def _import_patents(connection, path: Path, batch_size: int) -> int:
    from sqlalchemy import text

    total = 0
    statement = text("""
        INSERT INTO patents(patent_id, title, abstract, publication_year, legal_status,
                            cited_by_patent_count, url, domain_id, jurisdiction, cites_patent_count, family_size)
        VALUES (:patent_id, :title, :abstract, :publication_year, :legal_status,
                :cited_by_patent_count, :url, :domain_id, :jurisdiction, :cites_patent_count, :family_size)
        ON DUPLICATE KEY UPDATE
            title=VALUES(title), abstract=VALUES(abstract), publication_year=VALUES(publication_year),
            legal_status=VALUES(legal_status), cited_by_patent_count=VALUES(cited_by_patent_count),
            url=VALUES(url), domain_id=VALUES(domain_id), jurisdiction=VALUES(jurisdiction),
            cites_patent_count=VALUES(cites_patent_count), family_size=VALUES(family_size)
    """)
    for frame in pd.read_csv(path, dtype=str, chunksize=batch_size):
        frame = frame.fillna("")
        domain_ids = _upsert_domains(connection, frame)
        rows = []
        for row in frame.to_dict(orient="records"):
            year = row.get("publication_year", "")
            citations = row.get("cited_by_patent_count", "")
            rows.append({
                "patent_id": row["patent_id"], "title": row.get("title", ""), "abstract": row.get("abstract", ""),
                "publication_year": int(float(year)) if year else None,
                "legal_status": row.get("legal_status") or None,
                "cited_by_patent_count": int(float(citations)) if citations else 0,
                "url": row.get("url") or None, "domain_id": domain_ids.get(row.get("domain", "")),
                "jurisdiction": row.get("jurisdiction") or None,
                "cites_patent_count": int(row["cites_patent_count"]) if row.get("cites_patent_count") else None,
                "family_size": int(row["family_size"]) if row.get("family_size") and int(row["family_size"]) > 0 else None,
            })
        connection.execute(statement, rows)
        total += len(rows)
    return total


def _import_patent_domains(connection, path: Path, batch_size: int) -> int:
    """Replace the all-domain membership projection from its authoritative CSV."""
    from sqlalchemy import text

    # CREATE IF NOT EXISTS also migrates databases created before this junction
    # was added to 01_schema.sql.
    connection.execute(text("""
        CREATE TABLE IF NOT EXISTS patent_domains (
            patent_id VARCHAR(80) NOT NULL,
            domain_id INT NOT NULL,
            PRIMARY KEY (patent_id, domain_id),
            FOREIGN KEY (patent_id) REFERENCES patents(patent_id) ON DELETE CASCADE,
            FOREIGN KEY (domain_id) REFERENCES domains(domain_id)
        ) ENGINE=InnoDB
    """))
    connection.execute(text("DELETE FROM patent_domains"))

    total = 0
    for frame in pd.read_csv(path, dtype=str, chunksize=batch_size):
        frame = frame.fillna("")
        domain_ids = _upsert_domains(connection, frame)
        rows = [
            {"patent_id": row["patent_id"], "domain_id": domain_ids[row["domain"]]}
            for row in frame.to_dict(orient="records")
            if row.get("patent_id") and row.get("domain") in domain_ids
        ]
        if rows:
            connection.execute(text("""
                INSERT IGNORE INTO patent_domains(patent_id, domain_id)
                SELECT :patent_id, :domain_id
                WHERE EXISTS (SELECT 1 FROM patents p WHERE p.patent_id=:patent_id)
            """), rows)
        total += len(rows)
    return total


def _import_named_relationship(connection, path: Path, entity_table: str, entity_column: str, batch_size: int) -> int:
    """Load assignee/inventor entities plus their M:N junction rows."""
    from sqlalchemy import text

    junction = "patent_assignees" if entity_table == "assignees" else "patent_inventors"
    entity_pk = "assignee_id" if entity_table == "assignees" else "inventor_id"
    total = 0
    for frame in pd.read_csv(path, dtype=str, chunksize=batch_size):
        frame = frame.fillna("")
        names = [{"name": value.strip()} for value in frame[entity_column].astype(str) if value.strip()]
        if names:
            connection.execute(text(f"INSERT IGNORE INTO {entity_table}(name) VALUES (:name)"), names)
        name_map = {
            row["name"]: row[entity_pk]
            for row in connection.execute(text(f"SELECT {entity_pk}, name FROM {entity_table}")).mappings()
        }
        rows = [
            {"patent_id": row["patent_id"], entity_pk: name_map[row[entity_column].strip()]}
            for row in frame.to_dict(orient="records") if row.get(entity_column, "").strip() in name_map
        ]
        if rows:
            connection.execute(text(f"INSERT IGNORE INTO {junction}(patent_id, {entity_pk}) VALUES (:patent_id, :{entity_pk})"), rows)
        total += len(rows)
    return total


def _import_cpc(connection, path: Path, batch_size: int) -> int:
    from sqlalchemy import text

    # Reconcile old imports as well as new ones: previous versions inserted
    # IPCR/US links into the CPC-only tables. The processed CSV is authoritative.
    connection.execute(text("DROP TEMPORARY TABLE IF EXISTS valid_cpc_links"))
    connection.execute(text("""
        CREATE TEMPORARY TABLE valid_cpc_links (
            patent_id VARCHAR(80) NOT NULL,
            cpc_code VARCHAR(32) NOT NULL,
            PRIMARY KEY (patent_id, cpc_code)
        ) ENGINE=InnoDB
    """))
    total = 0
    try:
        for frame in pd.read_csv(path, dtype=str, chunksize=batch_size):
            frame = cpc_rows(frame.fillna(""))
            if frame.empty:
                continue
            links = [
                {"patent_id": row["patent_id"], "cpc_code": row["classification_code"]}
                for row in frame.to_dict(orient="records")
            ]
            connection.execute(
                text("INSERT IGNORE INTO cpc_codes(cpc_code, section) VALUES (:cpc_code, :section)"),
                [{"cpc_code": link["cpc_code"], "section": link["cpc_code"][0]} for link in links],
            )
            connection.execute(text("""
                INSERT IGNORE INTO valid_cpc_links(patent_id, cpc_code)
                VALUES (:patent_id, :cpc_code)
            """), links)
            connection.execute(text("""
                INSERT IGNORE INTO patent_cpc_codes(patent_id, cpc_code)
                VALUES (:patent_id, :cpc_code)
            """), links)
            total += len(links)

        connection.execute(text("""
            DELETE linked FROM patent_cpc_codes AS linked
            LEFT JOIN valid_cpc_links AS valid
              ON valid.patent_id = linked.patent_id AND valid.cpc_code = linked.cpc_code
            WHERE valid.patent_id IS NULL
        """))
        # Only discard unreferenced codes without curated descriptions.
        connection.execute(text("""
            DELETE codes FROM cpc_codes AS codes
            LEFT JOIN patent_cpc_codes AS linked ON linked.cpc_code = codes.cpc_code
            WHERE linked.cpc_code IS NULL AND codes.description IS NULL
        """))
    finally:
        connection.execute(text("DROP TEMPORARY TABLE IF EXISTS valid_cpc_links"))
    return total


def _import_families(connection, path: Path, batch_size: int) -> int:
    from sqlalchemy import text

    # Stage the authoritative edge set once, then reconcile it with two joins.
    # This avoids two correlated patent-existence checks for every source row.
    connection.execute(text("DROP TEMPORARY TABLE IF EXISTS valid_family_links"))
    connection.execute(text("""
        CREATE TEMPORARY TABLE valid_family_links (
            patent_id VARCHAR(80) NOT NULL,
            related_patent_id VARCHAR(80) NOT NULL,
            relation_type VARCHAR(32) NOT NULL,
            PRIMARY KEY (patent_id, related_patent_id, relation_type)
        ) ENGINE=InnoDB
    """))
    total = 0
    try:
        for frame in pd.read_csv(path, dtype=str, chunksize=batch_size):
            frame = frame.fillna("")
            rows = [
                {
                    "patent_id": row["patent_id"],
                    "related_patent_id": row["family_member"],
                    "relation_type": row.get("family_type") or "SIMPLE",
                }
                for row in frame.to_dict(orient="records")
                if row.get("patent_id") and row.get("family_member")
                and row["patent_id"] != row["family_member"]
            ]
            if rows:
                connection.execute(text("""
                    INSERT IGNORE INTO valid_family_links(
                        patent_id, related_patent_id, relation_type
                    ) VALUES (:patent_id, :related_patent_id, :relation_type)
                """), rows)
            total += len(rows)

        connection.execute(text("DELETE FROM patent_families"))
        connection.execute(text("""
            INSERT INTO patent_families(patent_id, related_patent_id, relation_type)
            SELECT candidate.patent_id, candidate.related_patent_id, candidate.relation_type
            FROM valid_family_links candidate
            JOIN patents source ON source.patent_id = candidate.patent_id
            JOIN patents related ON related.patent_id = candidate.related_patent_id
        """))
    finally:
        connection.execute(text("DROP TEMPORARY TABLE IF EXISTS valid_family_links"))
    return total


def _import_citation_snapshots(connection, path: Path, batch_size: int) -> int:
    from sqlalchemy import text

    total = 0
    for frame in pd.read_csv(path, dtype=str, chunksize=batch_size):
        frame = frame.fillna("")
        rows = [
            {"patent_id": row["patent_id"], "cited_by_count": int(float(row.get("cited_by_patent_count", "0") or 0))}
            for row in frame.to_dict(orient="records") if row.get("patent_id")
        ]
        if rows:
            connection.execute(text("""
                INSERT INTO citation_snapshots(patent_id, cited_by_count, observed_on)
                SELECT :patent_id, :cited_by_count, CURRENT_DATE
                WHERE EXISTS (SELECT 1 FROM patents p WHERE p.patent_id=:patent_id)
                ON DUPLICATE KEY UPDATE cited_by_count=VALUES(cited_by_count)
            """), rows)
        total += len(rows)
    return total


def _import_npl(connection, path: Path, batch_size: int) -> int:
    from sqlalchemy import text

    total = 0
    for frame in pd.read_csv(path, dtype=str, chunksize=batch_size):
        frame = frame.fillna("")
        source_rows = []
        for row in frame.to_dict(orient="records"):
            citation = row.get("npl_text", "").strip()
            if citation and row.get("patent_id"):
                source_rows.append({"patent_id": row["patent_id"], "citation": citation,
                                    "normalized_key": hashlib.sha256(citation.lower().encode("utf-8")).hexdigest()})
        if not source_rows:
            continue
        connection.execute(text("INSERT IGNORE INTO npl_references(citation, normalized_key) VALUES (:citation, :normalized_key)"), source_rows)
        id_map = {row["normalized_key"]: row["npl_id"] for row in connection.execute(text("SELECT npl_id, normalized_key FROM npl_references")).mappings()}
        connection.execute(text("INSERT IGNORE INTO patent_npl_references(patent_id, npl_id) VALUES (:patent_id, :npl_id)"), [
            {"patent_id": row["patent_id"], "npl_id": id_map[row["normalized_key"]]} for row in source_rows if row["normalized_key"] in id_map
        ])
        total += len(source_rows)
    return total


def bootstrap(batch_size: int) -> None:
    required = ["patents.csv", "patent_domains.csv", "assignees.csv", "inventors.csv", "classifications.csv", "patent_families.csv", "citations_metadata.csv", "npl_metadata.csv"]
    missing = [name for name in required if not (_PROCESSED / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing processed CSVs: {', '.join(missing)}")

    verify_database()
    with get_engine().begin() as connection:
        print(f"Imported/upserted { _import_patents(connection, _PROCESSED / 'patents.csv', batch_size):,} patents")
        print(f"Imported { _import_patent_domains(connection, _PROCESSED / 'patent_domains.csv', batch_size):,} patent-domain rows")
        print(f"Imported { _import_named_relationship(connection, _PROCESSED / 'assignees.csv', 'assignees', 'company_name', batch_size):,} patent-assignee rows")
        print(f"Imported { _import_named_relationship(connection, _PROCESSED / 'inventors.csv', 'inventors', 'inventor_name', batch_size):,} patent-inventor rows")
        print(f"Imported { _import_cpc(connection, _PROCESSED / 'classifications.csv', batch_size):,} patent-CPC rows")
        print(f"Processed { _import_families(connection, _PROCESSED / 'patent_families.csv', batch_size):,} patent-family rows")
        print(f"Imported { _import_citation_snapshots(connection, _PROCESSED / 'citations_metadata.csv', batch_size):,} citation snapshots")
        print(f"Imported { _import_npl(connection, _PROCESSED / 'npl_metadata.csv', batch_size):,} patent-NPL rows")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Idempotently bootstrap MySQL from data/processed CSVs.")
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()
    try:
        bootstrap(args.batch_size)
    except (DatabaseUnavailable, FileNotFoundError, ValueError) as exc:
        raise SystemExit(f"Bootstrap failed: {exc}") from exc
