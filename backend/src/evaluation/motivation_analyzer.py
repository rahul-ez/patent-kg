"""Estimate whether prior-art clusters suggest an obvious motivation to combine."""
from __future__ import annotations

import json
import logging
import os
from typing import List

from .per_concept_search import ConceptSearchResult

logger = logging.getLogger(__name__)


def _cross_citation_density(results: List[ConceptSearchResult]) -> float:
    clusters = [[hit.patent_id for hit in result.hits if not hit.patent_id.startswith("UNKNOWN")] for result in results]
    clusters = [cluster for cluster in clusters if cluster]
    if len(clusters) < 2:
        return 0.0
    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
        )
        try:
            with driver.session() as session:
                shared = 0
                for left, right in zip(clusters, clusters[1:]):
                    row = session.run(
                        """MATCH (a:Patent)-[:CITES_PAPER]->(p:Paper)<-[:CITES_PAPER]-(b:Patent)
                           WHERE a.patent_id IN $left AND b.patent_id IN $right
                           RETURN count(DISTINCT p) AS shared""",
                        left=left,
                        right=right,
                    ).single()
                    shared += row["shared"] if row else 0
                return min(shared / 10.0, 1.0)
        finally:
            driver.close()
    except Exception as exc:
        logger.warning("Cross-citation density skipped: %s", exc)
        return 0.0


def _gemini_motivation(concepts_text: str) -> dict:
    try:
        from .gemini_client import get_gemini_client

        client = get_gemini_client()
        if client is None:
            raise RuntimeError("Gemini client unavailable")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=("Assess whether a skilled engineer would have an obvious motivation to combine these concepts. "
                      "Return only JSON with has_obvious_motivation, reason, confidence.\n\n" + concepts_text),
            config={"response_mime_type": "application/json"},
        )
        return json.loads(response.text or "{}")
    except Exception as exc:
        logger.warning("Gemini motivation analysis unavailable: %s", exc)
        return {"has_obvious_motivation": None, "reason": "unavailable", "confidence": 0.0}


def score_motivation_to_combine(results: List[ConceptSearchResult]) -> dict:
    concepts_text = "\n".join(f"- {result.concept.label}: {result.concept.description}" for result in results)
    citation_density = _cross_citation_density(results)
    gemini = _gemini_motivation(concepts_text)
    confidence = float(gemini.get("confidence", 0.0) or 0.0)
    has_motivation = gemini.get("has_obvious_motivation")
    gemini_signal = confidence if has_motivation is True else 1.0 - confidence if has_motivation is False else 0.5
    score = 1.0 - (0.4 * citation_density + 0.6 * gemini_signal)
    interpretation = (
        "Weak motivation to combine" if score >= 0.70 else
        "Moderate motivation to combine" if score >= 0.45 else
        "Strong motivation to combine"
    )
    return {
        "score": round(score, 4),
        "cross_citation_density": round(citation_density, 4),
        "gemini_has_motivation": has_motivation,
        "gemini_reason": gemini.get("reason", ""),
        "interpretation": interpretation,
    }
