"""
Competitive Landscape Scorer
=============================
How crowded and actively contested is the patent space?

Signals:
1. Prior art density        — FAISS hits above similarity threshold
2. Active legal status ratio — % of top hits that are still ACTIVE (live barriers)
3. Assignee concentration   — fraction of hits owned by top-2 companies (Neo4j)
4. CPC sibling volume       — optional: total siblings from KG expansion

Score: 0 (saturated, hostile to new filings) → 1 (open field, favorable)
"""

import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

from .per_concept_search import ConceptSearchResult


def score_landscape(
    results: List[ConceptSearchResult],
    similarity_threshold: float = 0.50,
    cpc_sibling_count: Optional[int] = None,
) -> dict:
    """
    Returns
    -------
    dict: score, density, active_ratio, assignee_concentration,
          cpc_sibling_count, interpretation
    """
    all_hits = [h for r in results for h in r.hits]
    if not all_hits:
        return _default()

    # ── Prior art density ─────────────────────────────────────────────────────
    dense_hits  = [h for h in all_hits if h.score >= similarity_threshold]
    density     = len(dense_hits)
    density_score = 1.0 - min(density / 20.0, 1.0)   # more hits = lower score

    # ── Active legal status ───────────────────────────────────────────────────
    active_ratio  = _get_active_ratio([h.patent_id for h in all_hits])
    active_score  = 1.0 - active_ratio

    # ── Assignee concentration ────────────────────────────────────────────────
    concentration       = _get_assignee_concentration([h.patent_id for h in dense_hits])
    concentration_score = 1.0 - concentration

    # ── CPC sibling volume (optional) ─────────────────────────────────────────
    if cpc_sibling_count is not None:
        sibling_score = 1.0 - min(cpc_sibling_count / 100.0, 1.0)
        score = (
            0.30 * density_score +
            0.25 * active_score +
            0.25 * concentration_score +
            0.20 * sibling_score
        )
    else:
        score = (
            0.35 * density_score +
            0.35 * active_score +
            0.30 * concentration_score
        )

    if score >= 0.70:
        interp = "Open landscape — relatively few active barriers to filing"
    elif score >= 0.45:
        interp = "Moderate competition — some active prior art, room to differentiate"
    else:
        interp = "Crowded landscape — dense prior art with dominant players"

    logger.info(
        "Landscape: %.3f (density=%d, active=%.2f, concentration=%.2f)",
        score, density, active_ratio, concentration,
    )

    return {
        "score":                  round(score, 4),
        "density":                density,
        "active_ratio":           round(active_ratio, 3),
        "assignee_concentration": round(concentration, 3),
        "cpc_sibling_count":      cpc_sibling_count,
        "interpretation":         interp,
    }


def _get_active_ratio(patent_ids: List[str]) -> float:
    if not patent_ids:
        return 0.5
    try:
        import pandas as pd
        from config.paths import VECTOR_STORE, ROOT
        for csv_path in [VECTOR_STORE / "patents_deduped.csv", ROOT / "patents.csv"]:
            if csv_path.exists():
                df = pd.read_csv(csv_path, usecols=["patent_id", "legal_status"], dtype=str).fillna("")
                sub = df[df["patent_id"].isin(patent_ids)]
                if sub.empty:
                    return 0.5
                active = sub["legal_status"].str.upper().str.contains("ACTIVE", na=False)
                return float(active.sum() / len(sub))
        return 0.5
    except Exception as exc:
        logger.warning("Active ratio fetch failed (%s).", exc)
        return 0.5


def _get_assignee_concentration(patent_ids: List[str]) -> float:
    if not patent_ids:
        return 0.0
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
        )
        with driver.session() as session:
            rows = session.run(
                """
                MATCH (c:Company)-[:OWNS]->(p:Patent)
                WHERE p.patent_id IN $ids
                RETURN c.company_name AS company, count(p) AS cnt
                ORDER BY cnt DESC LIMIT 5
                """,
                ids=patent_ids,
            ).data()
        driver.close()
        if not rows:
            return 0.0
        total = sum(r["cnt"] for r in rows)
        top2  = sum(r["cnt"] for r in rows[:2])
        return top2 / max(total, 1)
    except Exception as exc:
        logger.warning("Assignee concentration fetch failed (%s).", exc)
        return 0.0


def _default() -> dict:
    return {
        "score":                  0.5,
        "density":                0,
        "active_ratio":           0.5,
        "assignee_concentration": 0.0,
        "cpc_sibling_count":      None,
        "interpretation":         "Insufficient data to compute landscape score",
    }
