"""
Teaching Away Detector
=======================
Prior art that explicitly discourages combining techniques is strong evidence
of non-obviousness — if the field said "don't do X with Y" and the invention
does exactly that and achieves a breakthrough, the combination wasn't obvious.

Searches npl_text of Paper nodes in Neo4j for negative language near concept terms.

Score: bonus modifier 0–0.30 (0 = no signal found, ≥ 0.10 = meaningful signal).
"""

import logging
import os
import re
from typing import List, Dict

logger = logging.getLogger(__name__)

from .per_concept_search import ConceptSearchResult

_NEGATIVE_PHRASES = [
    "ineffective", "not suitable", "not effective", "poor performance",
    "should not be used", "cannot be used", "disadvantage", "limitation of",
    "fails to", "limited by", "not recommended", "not feasible",
    "impractical", "inferior", "unreliable", "not applicable",
]

_PATTERN = re.compile(
    "|".join(re.escape(p) for p in _NEGATIVE_PHRASES),
    re.IGNORECASE,
)


def score_teaching_away(results: List[ConceptSearchResult]) -> dict:
    """
    Returns
    -------
    dict: score (0–0.30 bonus), signals, signal_count, interpretation
    """
    all_patent_ids = list({
        h.patent_id
        for r in results for h in r.hits
        if not h.patent_id.startswith("UNKNOWN")
    })
    concept_terms = [r.concept.label.lower() for r in results]

    if not all_patent_ids:
        return _default()

    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
        )

        with driver.session() as session:
            rows = session.run(
                """
                MATCH (p:Patent)-[:CITES_PAPER]->(paper:Paper)
                WHERE p.patent_id IN $ids
                  AND paper.npl_text IS NOT NULL AND paper.npl_text <> ''
                RETURN paper.npl_text AS text LIMIT 200
                """,
                ids=all_patent_ids,
            ).data()
        driver.close()

        signals: List[Dict] = []

        for row in rows:
            text = (row.get("text") or "").strip()
            if not text:
                continue
            for term in concept_terms:
                if term not in text.lower():
                    continue
                for m in re.finditer(re.escape(term), text.lower()):
                    window = text[max(0, m.start() - 150): m.start() + 150]
                    neg = _PATTERN.search(window)
                    if neg:
                        signals.append({
                            "concept":       term,
                            "phrase_matched": neg.group(0),
                            "excerpt":       window[:200].strip(),
                        })
                        if len(signals) >= 10:
                            break
                if len(signals) >= 10:
                    break

        bonus = min(len(signals) / 5.0 * 0.30, 0.30)

        if len(signals) >= 3:
            interp = "Teaching-away detected — prior art discourages this combination"
        elif len(signals) >= 1:
            interp = "Weak teaching-away signal — some discouragement in prior art"
        else:
            interp = "No teaching-away detected"

        logger.info("Teaching away: bonus=%.3f (%d signals)", bonus, len(signals))

        return {
            "score":         round(bonus, 4),
            "signals":       signals[:5],
            "signal_count":  len(signals),
            "interpretation": interp,
        }

    except Exception as exc:
        logger.warning("Teaching away skipped (%s).", exc)
        return _default()


def _default() -> dict:
    return {
        "score":          0.0,
        "signals":        [],
        "signal_count":   0,
        "interpretation": "Teaching-away analysis unavailable (Neo4j offline or no NPL data)",
    }
