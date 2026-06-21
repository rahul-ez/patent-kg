"""
KG Expander — query-time graph expansion
=========================================
Given the top-k patent IDs from FAISS retrieval, queries the full Neo4j
KG to find two categories of related patents that FAISS may have missed:

  1. Family members  — same invention filed in other jurisdictions
                       (SIMPLE_FAMILY_MEMBER + EXTENDED_FAMILY_MEMBER edges)

  2. CPC siblings    — patents sharing the same technology classification code
                       capped at top-N per code, ranked by cited_by_patent_count

Only full (non-stub) Patent nodes are returned. Patents already in the
retrieved set are excluded from both expansion groups.

Usage:
    from kg.expander import expand_via_kg

    result = expand_via_kg(patent_ids, cpc_cap=10)
    # result = {
    #     "family":       [{"patent_id": ..., "title": ..., ...}, ...],
    #     "cpc_siblings": [{"patent_id": ..., "title": ..., ...}, ...],
    #     "total_added":  int,
    # }
"""

import logging
import os
from typing import Dict, List

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

logger = logging.getLogger(__name__)

_NEO4J_URI      = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
_NEO4J_USER     = os.getenv("NEO4J_USER",     "neo4j")
_NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

# Cypher — family members reachable via either family edge type,
# excluding stubs and already-retrieved patents.
_FAMILY_QUERY = """
MATCH (p:Patent)-[:SIMPLE_FAMILY_MEMBER|EXTENDED_FAMILY_MEMBER]->(fam:Patent)
WHERE p.patent_id IN $ids
  AND NOT fam.patent_id IN $ids
  AND coalesce(fam.is_stub, false) = false
RETURN DISTINCT
    fam.patent_id            AS patent_id,
    fam.title                AS title,
    fam.abstract             AS abstract,
    fam.domain               AS domain,
    fam.legal_status         AS legal_status,
    fam.publication_year     AS publication_year,
    fam.cited_by_patent_count AS cited_by_patent_count,
    fam.jurisdiction         AS jurisdiction,
    fam.url                  AS url
"""

_CPC_SIBLING_QUERY = """
MATCH (p:Patent)-[:HAS_CPC]->(code:CPCCode)
WHERE p.patent_id IN $ids
MATCH (code)<-[:HAS_CPC]-(sibling:Patent)
WHERE NOT sibling.patent_id IN $ids
  AND coalesce(sibling.is_stub, false) = false
WITH code, sibling
ORDER BY code.code, toInteger(coalesce(sibling.cited_by_patent_count, 0)) DESC
WITH code, collect(sibling)[..$cpc_cap] AS siblings
UNWIND siblings AS sibling
RETURN DISTINCT
    code.code                        AS cpc_code,
    sibling.patent_id                AS patent_id,
    sibling.title                    AS title,
    sibling.abstract                 AS abstract,
    sibling.domain                   AS domain,
    sibling.legal_status             AS legal_status,
    sibling.publication_year         AS publication_year,
    sibling.cited_by_patent_count    AS cited_by_patent_count,
    sibling.jurisdiction             AS jurisdiction,
    sibling.url                      AS url
"""


def _safe_int(value) -> int:
    """Convert a Neo4j string/None property to int safely."""
    try:
        return int(value or 0)
    except (ValueError, TypeError):
        return 0


def _row_to_dict(record, expansion_type: str) -> Dict:
    return {
        "patent_id":             record["patent_id"],
        "title":                 record["title"]            or "",
        "abstract":              record["abstract"]         or "",
        "domain":                record["domain"]           or "",
        "legal_status":          record["legal_status"]     or "",
        "publication_year":      record["publication_year"] or "",
        "cited_by_patent_count": record["cited_by_patent_count"] or "0",
        "jurisdiction":          record["jurisdiction"]     or "",
        "url":                   record["url"]              or "",
        "expansion_type":        expansion_type,
    }


def expand_via_kg(
    patent_ids: List[str],
    cpc_cap: int = 10,
) -> Dict:
    """
    Expand a set of retrieved patent IDs using the full KG in Neo4j.

    Parameters
    ----------
    patent_ids : list of str
        Patent IDs from FAISS retrieval (the top-k set).
    cpc_cap : int
        Maximum number of CPC siblings to include per classification code.
        Ranked by cited_by_patent_count descending.

    Returns
    -------
    dict with keys:
        "family"       – list of family-member patent dicts
        "cpc_siblings" – list of CPC-sibling patent dicts (deduplicated)
        "total_added"  – total unique patents added by expansion
    """
    driver = GraphDatabase.driver(_NEO4J_URI, auth=(_NEO4J_USER, _NEO4J_PASSWORD))
    retrieved_set = set(patent_ids)

    try:
        with driver.session() as session:

            # ── Family expansion ───────────────────────────────────────────────
            logger.info("Querying family members for %d patents ...", len(patent_ids))
            family_rows = session.run(_FAMILY_QUERY, ids=patent_ids).data()
            family = [_row_to_dict(r, "family") for r in family_rows]
            logger.info("  Family members found: %d", len(family))

            # ── CPC sibling expansion ──────────────────────────────────────────
            logger.info("Querying CPC siblings (cap=%d per code) ...", cpc_cap)
            sibling_rows = session.run(_CPC_SIBLING_QUERY, ids=patent_ids, cpc_cap=cpc_cap).data()

            # Group by CPC code, keep top-N per code
            from collections import defaultdict
            by_code: Dict[str, list] = defaultdict(list)
            for row in sibling_rows:
                by_code[row["cpc_code"]].append(row)

            # Keep existing logic: up to cpc_cap patents per CPC code
            all_cpc_candidates = []
            for code, rows in by_code.items():
                rows.sort(key=lambda r: _safe_int(r["cited_by_patent_count"]), reverse=True)
                for row in rows[:cpc_cap]:
                    all_cpc_candidates.append(row)

            # Sort globally by cited_by_patent_count descending
            all_cpc_candidates.sort(key=lambda r: _safe_int(r["cited_by_patent_count"]), reverse=True)

            # Deduplicate and apply global cap of 100 patents max
            seen_ids = retrieved_set | {p["patent_id"] for p in family}
            cpc_siblings: List[Dict] = []
            for row in all_cpc_candidates:
                pid = row["patent_id"]
                if pid not in seen_ids:
                    cpc_siblings.append(_row_to_dict(row, "cpc_sibling"))
                    seen_ids.add(pid)
                    if len(cpc_siblings) >= 100:
                        break

            logger.info("  CPC siblings after dedup: %d", len(cpc_siblings))

    finally:
        driver.close()

    total_added = len(family) + len(cpc_siblings)
    logger.info("KG expansion complete: +%d patents (%d family + %d CPC siblings)",
                total_added, len(family), len(cpc_siblings))

    return {
        "family":       family,
        "cpc_siblings": cpc_siblings,
        "total_added":  total_added,
    }
