"""
Knowledge Graph Builder — query-time subgraph (top-k patents)
=============================================================
Takes a list of patent_ids returned by FAISS retrieval and writes a
Neo4j subgraph covering all five node types and six edge types.

Node types : Patent, Company, Inventor, CPCCode, Paper
Edge types : OWNS, INVENTED, HAS_CPC,
             SIMPLE_FAMILY_MEMBER, EXTENDED_FAMILY_MEMBER, CITES_PAPER

Family members that are not in the top-k are written as stub Patent
nodes (is_stub=true, no metadata properties) so that structural edges
are preserved without polluting the graph with unrelated full records.

Usage (as a library):
    from src.kg.builder import build_kg_for_query
    build_kg_for_query(["patent_id_1", "patent_id_2", ...])

Usage (CLI smoke-test):
    cd patent-kg/backend
    python -m src.kg.builder
"""

import logging
import os
from pathlib import Path
from typing import List, Set

import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)

# ── Paths ──────────────────────────────────────────────────────────────────────
# builder.py lives at: patent-kg/backend/src/kg/builder.py
# parents[0] → kg/
# parents[1] → src/
# parents[2] → backend/
# parents[3] → patent-kg/   ← CSVs live here
_DATA_DIR = Path(__file__).resolve().parents[3]   # → patent-kg/

# Required: patents_deduped.csv  (canonical deduplicated corpus)
# Optional: all others — KG build skips gracefully if they are absent
_CSV = {
    "patents":         _DATA_DIR / "patents_deduped.csv",
    "assignees":       _DATA_DIR / "assignees.csv",
    "inventors":       _DATA_DIR / "inventors.csv",
    "classifications": _DATA_DIR / "classifications.csv",
    "families":        _DATA_DIR / "patent_families.csv",
    "citations":       _DATA_DIR / "citations_metadata.csv",
    "npl":             _DATA_DIR / "npl_metadata.csv",
}

# CSVs that are truly optional — missing files produce a warning, not a crash.
_OPTIONAL_CSVS = {"assignees", "inventors", "classifications", "citations", "npl"}

# ── Neo4j connection ───────────────────────────────────────────────────────────
_NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
_NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
_NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")


# ══════════════════════════════════════════════════════════════════════════════
# KGBuilder
# ══════════════════════════════════════════════════════════════════════════════

class KGBuilder:
    """Builds and populates a Neo4j knowledge graph for a set of patent IDs."""

    def __init__(self):
        self.driver = GraphDatabase.driver(
            _NEO4J_URI, auth=(_NEO4J_USER, _NEO4J_PASSWORD)
        )

    def close(self):
        self.driver.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    # ── Public entry point ─────────────────────────────────────────────────────

    def build_subgraph(self, patent_ids: List[str]) -> None:
        """
        Main entry point. Loads CSV data for the given patent_ids and
        writes all nodes + edges into Neo4j.
        """
        ids: Set[str] = set(patent_ids)
        logger.info("Building KG subgraph for %d patent IDs ...", len(ids))

        self._create_constraints()

        # ── Load and filter CSVs ───────────────────────────────────────────────
        patents         = self._load("patents",         ids)
        assignees       = self._load("assignees",       ids)
        inventors       = self._load("inventors",       ids)
        classifications = self._load("classifications", ids)
        families        = self._load("families",        ids)
        citations       = self._load("citations",       ids)
        npl             = self._load("npl",             ids)

        # Enrich Patent nodes with npl citation counts only when citations loaded.
        if not citations.empty and "npl_citation_count" in citations.columns:
            npl_counts = citations[["patent_id", "npl_citation_count", "npl_resolved_citation_count"]]
            patents = patents.merge(npl_counts, on="patent_id", how="left").fillna("")

        # ── Write nodes then edges ─────────────────────────────────────────────
        with self.driver.session() as session:
            self._write_patent_nodes(session, patents)
            if not families.empty:
                self._write_stub_nodes(session, families, ids)
            if not assignees.empty:
                self._write_company_nodes(session, assignees)
            if not inventors.empty:
                self._write_inventor_nodes(session, inventors)
            if not classifications.empty:
                self._write_cpc_nodes(session, classifications)
            if not npl.empty:
                self._write_paper_nodes(session, npl)

            if not assignees.empty:
                self._write_owns_edges(session, assignees)
            if not inventors.empty:
                self._write_invented_edges(session, inventors)
            if not classifications.empty:
                self._write_hascpc_edges(session, classifications)
            if not families.empty:
                self._write_family_edges(session, families)
            if not npl.empty:
                self._write_cites_paper_edges(session, npl)

        logger.info("KG subgraph complete.")

    # ── Constraints ────────────────────────────────────────────────────────────

    def _create_constraints(self) -> None:
        """Uniqueness constraints — idempotent, safe to run on every call."""
        statements = [
            "CREATE CONSTRAINT patent_id IF NOT EXISTS FOR (n:Patent)   REQUIRE n.patent_id   IS UNIQUE",
            "CREATE CONSTRAINT company_id IF NOT EXISTS FOR (n:Company)  REQUIRE n.company_id  IS UNIQUE",
            "CREATE CONSTRAINT inventor_id IF NOT EXISTS FOR (n:Inventor) REQUIRE n.inventor_id IS UNIQUE",
            "CREATE CONSTRAINT cpc_code IF NOT EXISTS FOR (n:CPCCode)   REQUIRE n.code        IS UNIQUE",
            "CREATE CONSTRAINT paper_lens_id IF NOT EXISTS FOR (n:Paper) REQUIRE n.npl_lens_id IS UNIQUE",
        ]
        with self.driver.session() as session:
            for stmt in statements:
                session.run(stmt)
        logger.info("Constraints verified.")

    # ── CSV loader ─────────────────────────────────────────────────────────────

    def _load(self, name: str, ids: Set[str]) -> pd.DataFrame:
        path = _CSV[name]
        if not path.exists():
            if name in _OPTIONAL_CSVS:
                logger.warning(
                    "Optional CSV '%s' not found at '%s' — skipping.",
                    name, path,
                )
                return pd.DataFrame()   # empty — callers must handle this
            raise FileNotFoundError(f"Required CSV not found: {path}")
        df = pd.read_csv(path, dtype=str).fillna("")
        # Some CSVs may not have a patent_id column (they'll be handled separately)
        if "patent_id" in df.columns:
            filtered = df[df["patent_id"].isin(ids)]
        else:
            filtered = df
        logger.info("%-16s → %d rows (filtered from %d)", name, len(filtered), len(df))
        return filtered

    # ══════════════════════════════════════════════════════════════════════════
    # Node writers
    # ══════════════════════════════════════════════════════════════════════════

    def _write_patent_nodes(self, session, df: pd.DataFrame) -> None:
        cols = [
            "patent_id", "title", "abstract", "domain", "legal_status",
            "publication_year", "jurisdiction", "document_type",
            "family_size", "cited_by_patent_count", "cites_patent_count",
            "npl_citation_count", "npl_resolved_citation_count", "url",
        ]
        # Keep only columns that actually exist after the merge
        cols = [c for c in cols if c in df.columns]
        records = df[cols].to_dict("records")

        session.run(
            """
            UNWIND $rows AS r
            MERGE (p:Patent {patent_id: r.patent_id})
            SET p.title                      = r.title,
                p.abstract                   = r.abstract,
                p.domain                     = r.domain,
                p.legal_status               = r.legal_status,
                p.publication_year           = r.publication_year,
                p.jurisdiction               = r.jurisdiction,
                p.document_type              = r.document_type,
                p.family_size                = r.family_size,
                p.cited_by_patent_count      = r.cited_by_patent_count,
                p.cites_patent_count         = r.cites_patent_count,
                p.npl_citation_count         = r.npl_citation_count,
                p.npl_resolved_citation_count= r.npl_resolved_citation_count,
                p.url                        = r.url,
                p.is_stub                    = false
            """,
            rows=records,
        )
        logger.info("Patent nodes: %d written.", len(records))

    def _write_stub_nodes(self, session, families_df: pd.DataFrame, known_ids: Set[str]) -> None:
        """
        Create minimal Patent nodes for family members not in the top-k.
        ON CREATE ensures we never overwrite a full node that was already written.
        """
        stub_ids = set(families_df["family_member"].tolist()) - known_ids
        if not stub_ids:
            logger.info("Stub Patent nodes: 0 (all family members already in top-k).")
            return

        session.run(
            """
            UNWIND $ids AS pid
            MERGE (p:Patent {patent_id: pid})
            ON CREATE SET p.is_stub = true
            """,
            ids=list(stub_ids),
        )
        logger.info("Stub Patent nodes: %d written.", len(stub_ids))

    def _write_company_nodes(self, session, df: pd.DataFrame) -> None:
        records = (
            df[["company_id", "company_name"]]
            .drop_duplicates(subset=["company_id"])
            .to_dict("records")
        )
        session.run(
            """
            UNWIND $rows AS r
            MERGE (c:Company {company_id: r.company_id})
            SET c.company_name = r.company_name
            """,
            rows=records,
        )
        logger.info("Company nodes: %d written.", len(records))

    def _write_inventor_nodes(self, session, df: pd.DataFrame) -> None:
        records = (
            df[["inventor_id", "inventor_name"]]
            .drop_duplicates(subset=["inventor_id"])
            .to_dict("records")
        )
        session.run(
            """
            UNWIND $rows AS r
            MERGE (i:Inventor {inventor_id: r.inventor_id})
            SET i.inventor_name = r.inventor_name
            """,
            rows=records,
        )
        logger.info("Inventor nodes: %d written.", len(records))

    def _write_cpc_nodes(self, session, df: pd.DataFrame) -> None:
        records = (
            df[["classification_code", "classification_type"]]
            .drop_duplicates(subset=["classification_code"])
            .to_dict("records")
        )
        session.run(
            """
            UNWIND $rows AS r
            MERGE (c:CPCCode {code: r.classification_code})
            SET c.classification_type = r.classification_type
            """,
            rows=records,
        )
        logger.info("CPCCode nodes: %d written.", len(records))

    def _write_paper_nodes(self, session, df: pd.DataFrame) -> None:
        # Only write papers that have a Lens ID to MERGE on
        valid = (
            df[df["npl_lens_id"] != ""][["npl_lens_id", "npl_external_id", "npl_text"]]
            .drop_duplicates(subset=["npl_lens_id"])
        )
        if valid.empty:
            logger.info("Paper nodes: 0 (no resolved NPL citations in this result set).")
            return

        session.run(
            """
            UNWIND $rows AS r
            MERGE (p:Paper {npl_lens_id: r.npl_lens_id})
            SET p.doi      = r.npl_external_id,
                p.npl_text = r.npl_text
            """,
            rows=valid.to_dict("records"),
        )
        logger.info("Paper nodes: %d written.", len(valid))

    # ══════════════════════════════════════════════════════════════════════════
    # Edge writers
    # ══════════════════════════════════════════════════════════════════════════

    def _write_owns_edges(self, session, df: pd.DataFrame) -> None:
        records = df[["company_id", "patent_id"]].to_dict("records")
        session.run(
            """
            UNWIND $rows AS r
            MATCH (c:Company {company_id: r.company_id})
            MATCH (p:Patent  {patent_id:  r.patent_id})
            MERGE (c)-[:OWNS]->(p)
            """,
            rows=records,
        )
        logger.info("OWNS edges: %d written.", len(records))

    def _write_invented_edges(self, session, df: pd.DataFrame) -> None:
        records = df[["inventor_id", "patent_id"]].to_dict("records")
        session.run(
            """
            UNWIND $rows AS r
            MATCH (i:Inventor {inventor_id: r.inventor_id})
            MATCH (p:Patent   {patent_id:   r.patent_id})
            MERGE (i)-[:INVENTED]->(p)
            """,
            rows=records,
        )
        logger.info("INVENTED edges: %d written.", len(records))

    def _write_hascpc_edges(self, session, df: pd.DataFrame) -> None:
        records = df[["patent_id", "classification_code"]].to_dict("records")
        session.run(
            """
            UNWIND $rows AS r
            MATCH (p:Patent {patent_id:          r.patent_id})
            MATCH (c:CPCCode {code: r.classification_code})
            MERGE (p)-[:HAS_CPC]->(c)
            """,
            rows=records,
        )
        logger.info("HAS_CPC edges: %d written.", len(records))

    def _write_family_edges(self, session, df: pd.DataFrame) -> None:
        simple   = df[df["family_type"] == "SIMPLE"][["patent_id", "family_member"]].to_dict("records")
        extended = df[df["family_type"] == "EXTENDED"][["patent_id", "family_member"]].to_dict("records")

        if simple:
            session.run(
                """
                UNWIND $rows AS r
                MATCH (a:Patent {patent_id: r.patent_id})
                MATCH (b:Patent {patent_id: r.family_member})
                MERGE (a)-[:SIMPLE_FAMILY_MEMBER]->(b)
                """,
                rows=simple,
            )

        if extended:
            session.run(
                """
                UNWIND $rows AS r
                MATCH (a:Patent {patent_id: r.patent_id})
                MATCH (b:Patent {patent_id: r.family_member})
                MERGE (a)-[:EXTENDED_FAMILY_MEMBER]->(b)
                """,
                rows=extended,
            )

        logger.info(
            "FAMILY edges: %d SIMPLE + %d EXTENDED written.",
            len(simple), len(extended),
        )

    def _write_cites_paper_edges(self, session, df: pd.DataFrame) -> None:
        valid = df[df["npl_lens_id"] != ""][["patent_id", "npl_lens_id"]].to_dict("records")
        if not valid:
            logger.info("CITES_PAPER edges: 0.")
            return

        session.run(
            """
            UNWIND $rows AS r
            MATCH (p:Patent {patent_id:   r.patent_id})
            MATCH (paper:Paper {npl_lens_id: r.npl_lens_id})
            MERGE (p)-[:CITES_PAPER]->(paper)
            """,
            rows=valid,
        )
        logger.info("CITES_PAPER edges: %d written.", len(valid))


# ══════════════════════════════════════════════════════════════════════════════
# Full corpus builder
# ══════════════════════════════════════════════════════════════════════════════

    def build_full_graph(self, batch_size: int = 2000) -> None:
        """
        Build the complete KG from all 7 CSVs — no patent_id filtering.
        Designed for a one-time offline run over the full ~58K patent corpus.

        Large files (classifications 1M rows, families 1.4M rows) are processed
        in chunks so memory usage stays bounded regardless of corpus size.
        """
        logger.info("=== FULL KG BUILD START ===")
        self._create_constraints()

        # ── Load core tables fully (all fit comfortably in memory) ─────────────
        logger.info("Loading patents_deduped.csv ...")
        patents = pd.read_csv(_CSV["patents"], dtype=str).fillna("")
        patent_ids: Set[str] = set(patents["patent_id"].tolist())
        logger.info("  %d patents loaded.", len(patents))

        logger.info("Loading citations_metadata.csv ...")
        citations = pd.read_csv(_CSV["citations"], dtype=str).fillna("")

        logger.info("Loading assignees.csv ...")
        assignees = pd.read_csv(_CSV["assignees"], dtype=str).fillna("")

        logger.info("Loading inventors.csv ...")
        inventors = pd.read_csv(_CSV["inventors"], dtype=str).fillna("")

        logger.info("Loading npl_metadata.csv ...")
        npl = pd.read_csv(_CSV["npl"], dtype=str).fillna("")

        # Enrich patents with npl citation counts
        npl_counts = citations[["patent_id", "npl_citation_count", "npl_resolved_citation_count"]]
        patents = patents.merge(npl_counts, on="patent_id", how="left").fillna("")

        # ── Collect stub IDs from families before processing edges ─────────────
        logger.info("Scanning patent_families.csv for stub IDs ...")
        stub_ids: Set[str] = set()
        for chunk in pd.read_csv(_CSV["families"], dtype=str, usecols=["family_member"], chunksize=50_000):
            stub_ids.update(chunk["family_member"].tolist())
        stub_ids -= patent_ids
        logger.info("  %d stub Patent nodes needed.", len(stub_ids))

        # ── Write all nodes ────────────────────────────────────────────────────
        with self.driver.session() as session:
            logger.info("Writing Patent nodes (%d) ...", len(patents))
            self._write_in_batches(
                session, patents.to_dict("records"),
                """
                UNWIND $rows AS r
                MERGE (p:Patent {patent_id: r.patent_id})
                SET p.title                       = r.title,
                    p.abstract                    = r.abstract,
                    p.domain                      = r.domain,
                    p.legal_status                = r.legal_status,
                    p.publication_year            = r.publication_year,
                    p.jurisdiction                = r.jurisdiction,
                    p.document_type               = r.document_type,
                    p.family_size                 = r.family_size,
                    p.cited_by_patent_count       = r.cited_by_patent_count,
                    p.cites_patent_count          = r.cites_patent_count,
                    p.npl_citation_count          = r.npl_citation_count,
                    p.npl_resolved_citation_count = r.npl_resolved_citation_count,
                    p.url                         = r.url,
                    p.is_stub                     = false
                """,
                batch_size=batch_size, label="Patent nodes",
            )

            logger.info("Writing stub Patent nodes (%d) ...", len(stub_ids))
            self._write_in_batches(
                session, [{"pid": pid} for pid in stub_ids],
                """
                UNWIND $rows AS r
                MERGE (p:Patent {patent_id: r.pid})
                ON CREATE SET p.is_stub = true
                """,
                batch_size=batch_size, label="Stub nodes",
            )

            logger.info("Writing Company nodes ...")
            companies = assignees[["company_id", "company_name"]].drop_duplicates("company_id")
            self._write_in_batches(
                session, companies.to_dict("records"),
                """
                UNWIND $rows AS r
                MERGE (c:Company {company_id: r.company_id})
                SET c.company_name = r.company_name
                """,
                batch_size=batch_size, label="Company nodes",
            )

            logger.info("Writing Inventor nodes ...")
            invs = inventors[["inventor_id", "inventor_name"]].drop_duplicates("inventor_id")
            self._write_in_batches(
                session, invs.to_dict("records"),
                """
                UNWIND $rows AS r
                MERGE (i:Inventor {inventor_id: r.inventor_id})
                SET i.inventor_name = r.inventor_name
                """,
                batch_size=batch_size, label="Inventor nodes",
            )

            logger.info("Writing CPCCode nodes (chunked from classifications.csv) ...")
            seen_codes: Set[str] = set()
            for chunk in pd.read_csv(_CSV["classifications"], dtype=str, chunksize=50_000):
                chunk = chunk.fillna("")
                new_codes = chunk[~chunk["classification_code"].isin(seen_codes)]
                unique = new_codes[["classification_code", "classification_type"]].drop_duplicates("classification_code")
                if not unique.empty:
                    self._write_in_batches(
                        session, unique.to_dict("records"),
                        """
                        UNWIND $rows AS r
                        MERGE (c:CPCCode {code: r.classification_code})
                        SET c.classification_type = r.classification_type
                        """,
                        batch_size=batch_size, label="CPCCode nodes",
                    )
                    seen_codes.update(unique["classification_code"].tolist())

            logger.info("Writing Paper nodes ...")
            papers = npl[npl["npl_lens_id"] != ""][["npl_lens_id", "npl_external_id", "npl_text"]].drop_duplicates("npl_lens_id")
            self._write_in_batches(
                session, papers.to_dict("records"),
                """
                UNWIND $rows AS r
                MERGE (p:Paper {npl_lens_id: r.npl_lens_id})
                SET p.doi = r.npl_external_id, p.npl_text = r.npl_text
                """,
                batch_size=batch_size, label="Paper nodes",
            )

            # ── Write all edges ────────────────────────────────────────────────
            logger.info("Writing OWNS edges ...")
            self._write_in_batches(
                session, assignees[["company_id", "patent_id"]].to_dict("records"),
                """
                UNWIND $rows AS r
                MATCH (c:Company {company_id: r.company_id})
                MATCH (p:Patent  {patent_id:  r.patent_id})
                MERGE (c)-[:OWNS]->(p)
                """,
                batch_size=batch_size, label="OWNS edges",
            )

            logger.info("Writing INVENTED edges ...")
            self._write_in_batches(
                session, inventors[["inventor_id", "patent_id"]].to_dict("records"),
                """
                UNWIND $rows AS r
                MATCH (i:Inventor {inventor_id: r.inventor_id})
                MATCH (p:Patent   {patent_id:   r.patent_id})
                MERGE (i)-[:INVENTED]->(p)
                """,
                batch_size=batch_size, label="INVENTED edges",
            )

            logger.info("Writing HAS_CPC edges (chunked from classifications.csv) ...")
            total_cpc_edges = 0
            for chunk in pd.read_csv(_CSV["classifications"], dtype=str, chunksize=50_000):
                chunk = chunk.fillna("")
                records = chunk[["patent_id", "classification_code"]].to_dict("records")
                self._write_in_batches(
                    session, records,
                    """
                    UNWIND $rows AS r
                    MATCH (p:Patent  {patent_id: r.patent_id})
                    MATCH (c:CPCCode {code:       r.classification_code})
                    MERGE (p)-[:HAS_CPC]->(c)
                    """,
                    batch_size=batch_size, label="HAS_CPC edges",
                )
                total_cpc_edges += len(records)
            logger.info("  HAS_CPC total: %d edges.", total_cpc_edges)

            logger.info("Writing FAMILY edges (chunked from patent_families.csv) ...")
            total_family_edges = 0
            for chunk in pd.read_csv(_CSV["families"], dtype=str, chunksize=50_000):
                chunk = chunk.fillna("")
                simple   = chunk[chunk["family_type"] == "SIMPLE"][["patent_id", "family_member"]].to_dict("records")
                extended = chunk[chunk["family_type"] == "EXTENDED"][["patent_id", "family_member"]].to_dict("records")
                if simple:
                    self._write_in_batches(
                        session, simple,
                        """
                        UNWIND $rows AS r
                        MATCH (a:Patent {patent_id: r.patent_id})
                        MATCH (b:Patent {patent_id: r.family_member})
                        MERGE (a)-[:SIMPLE_FAMILY_MEMBER]->(b)
                        """,
                        batch_size=batch_size, label="SIMPLE_FAMILY edges",
                    )
                if extended:
                    self._write_in_batches(
                        session, extended,
                        """
                        UNWIND $rows AS r
                        MATCH (a:Patent {patent_id: r.patent_id})
                        MATCH (b:Patent {patent_id: r.family_member})
                        MERGE (a)-[:EXTENDED_FAMILY_MEMBER]->(b)
                        """,
                        batch_size=batch_size, label="EXTENDED_FAMILY edges",
                    )
                total_family_edges += len(simple) + len(extended)
            logger.info("  FAMILY total: %d edges.", total_family_edges)

            logger.info("Writing CITES_PAPER edges ...")
            valid_npl = npl[npl["npl_lens_id"] != ""][["patent_id", "npl_lens_id"]]
            self._write_in_batches(
                session, valid_npl.to_dict("records"),
                """
                UNWIND $rows AS r
                MATCH (p:Patent {patent_id:      r.patent_id})
                MATCH (paper:Paper {npl_lens_id: r.npl_lens_id})
                MERGE (p)-[:CITES_PAPER]->(paper)
                """,
                batch_size=batch_size, label="CITES_PAPER edges",
            )

        logger.info("=== FULL KG BUILD COMPLETE ===")

    # ── Batch write helper ─────────────────────────────────────────────────────

    def _write_in_batches(
        self,
        session,
        records: list,
        cypher: str,
        batch_size: int = 2000,
        label: str = "records",
    ) -> None:
        """Run a parameterised Cypher statement in batches to avoid memory spikes."""
        total = len(records)
        for start in range(0, total, batch_size):
            batch = records[start : start + batch_size]
            session.run(cypher, rows=batch)
            end = min(start + batch_size, total)
            logger.info("  [%s] %d / %d", label, end, total)


# ══════════════════════════════════════════════════════════════════════════════
# Public helper
# ══════════════════════════════════════════════════════════════════════════════

def build_kg_for_query(patent_ids: List[str]) -> None:
    """
    Convenience wrapper called after FAISS retrieval.

        from src.integration.pipeline import run_end_to_end
        from src.kg.builder import build_kg_for_query

        response = run_end_to_end("my idea", top_k=100)
        ids = [hit["patent_id"] for hit in response["results"]]
        build_kg_for_query(ids)
    """
    with KGBuilder() as builder:
        builder.build_subgraph(patent_ids)


# ══════════════════════════════════════════════════════════════════════════════
# CLI smoke-test
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    import json

    # Pull real IDs from the pipeline if available, otherwise use a tiny hardcoded set
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from integration.pipeline import run_end_to_end

        idea = "neural implant for seizure detection using EEG and machine learning"
        print(f"\nRunning FAISS retrieval for: '{idea}'")
        response = run_end_to_end(idea, top_k=100)
        ids = [hit["patent_id"] for hit in response["results"]]
        print(f"Retrieved {len(ids)} patent IDs from FAISS.\n")
    except Exception as e:
        print(f"[WARN] Could not run FAISS pipeline ({e}). Using stub IDs for smoke-test.")
        ids = ["171-148-280-142-283", "079-908-471-909-613", "185-773-313-791-389"]

    print(f"Building KG for {len(ids)} patents ...")
    build_kg_for_query(ids)
    print("\nDone. Open Neo4j Browser at http://localhost:7474 and run:")
    print("  MATCH (n) RETURN n LIMIT 100")
