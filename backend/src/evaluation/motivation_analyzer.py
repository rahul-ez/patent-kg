"""
Motivation-to-Combine Analyzer
================================
Estimates whether there is an obvious engineering reason to combine the concepts.

Two signals:
1. Cross-citation density — concepts whose patents co-cite the same papers
   were already linked in the prior art (motivation exists)
2. Gemini judgment        — direct LLM assessment of combination motivation

Score: 0 (obvious motivation exists) → 1 (no apparent motivation = more non-obvious)
"""

import json
import logging
import os
from typing import List

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

from .per_concept_search import ConceptSearchResult


def _cross_citation_density(results: List[ConceptSearchResult]) -> float:
    """
    Fraction of concept pairs that share cited papers in Neo4j.
    0 = no shared citations, 1 = 10+ shared papers across all pairs.
    """
    if len(results) < 2:
        return 0.0

    clusters = [
        [h.patent_id for h in r.hits if not h.patent_id.startswith("UNKNOWN")]
        for r in results
    ]
    clusters = [c for c in clusters if c]
    if len(clusters) < 2:
        return 0.0

    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
        )
        total_shared = 0
        with driver.session() as session:
            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    row = session.run(
                        """
                        MATCH (a:Patent)-[:CITES_PAPER]->(p:Paper)<-[:CITES_PAPER]-(b:Patent)
                        WHERE a.patent_id IN $ids_a AND b.patent_id IN $ids_b
                        RETURN count(DISTINCT p) AS shared
                        """,
                        ids_a=clusters[i], ids_b=clusters[j],
                    ).single()
                    total_shared += row["shared"] if row else 0
        driver.close()
        return min(total_shared / 10.0, 1.0)
    except Exception as exc:
        logger.warning("Cross-citation density skipped (%s).", exc)
        return 0.0


def _gemini_motivation(concepts_text: str) -> dict:
    """Ask Gemini whether there is an obvious motivation to combine the concepts."""
    try:
        import google.generativeai as genai
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = f"""You are a patent examiner assessing non-obviousness.

Given these technical concepts that form an invention:
{concepts_text}

Would a skilled engineer in this field have an OBVIOUS motivation to combine these concepts?
Consider: common engineering practice, whether one concept naturally requires the other,
well-known reasons to pair these technologies.

Return ONLY this JSON:
{{
  "has_obvious_motivation": true or false,
  "reason": "one sentence explaining why or why not",
  "confidence": 0.0 to 1.0
}}"""

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
            ),
        )
        return json.loads(response.text)

    except Exception as exc:
        logger.warning("Gemini motivation analysis failed (%s).", exc)
        return {"has_obvious_motivation": None, "reason": "unavailable", "confidence": 0.0}


def score_motivation_to_combine(results: List[ConceptSearchResult]) -> dict:
    """
    Returns
    -------
    dict: score (0–1, higher = less motivation = more non-obvious),
          cross_citation_density, gemini_has_motivation, gemini_reason, interpretation
    """
    concepts_text = "\n".join(
        f"- {r.concept.label}: {r.concept.description}" for r in results
    )

    citation_density = _cross_citation_density(results)
    gemini           = _gemini_motivation(concepts_text)
    has_motivation   = gemini.get("has_obvious_motivation")
    gemini_reason    = gemini.get("reason", "")
    confidence       = float(gemini.get("confidence", 0.0))

    # Convert to a 0–1 motivation signal (high = obvious motivation exists)
    citation_motivation = citation_density

    if has_motivation is True:
        gemini_motivation = confidence
    elif has_motivation is False:
        gemini_motivation = 1.0 - confidence
    else:
        gemini_motivation = 0.5

    motivation = 0.40 * citation_motivation + 0.60 * gemini_motivation
    score = 1.0 - motivation   # invert: less motivation = higher non-obviousness score

    if score >= 0.70:
        interp = "Weak motivation to combine — no clear engineering reason exists"
    elif score >= 0.45:
        interp = "Moderate motivation — some connection but not immediately obvious"
    else:
        interp = "Strong motivation to combine — obvious engineering reason exists"

    logger.info(
        "Motivation-to-combine: %.3f (citation=%.3f, gemini=%s)",
        score, citation_density, has_motivation,
    )

    return {
        "score":                  round(score, 4),
        "cross_citation_density": round(citation_density, 4),
        "gemini_has_motivation":  has_motivation,
        "gemini_reason":          gemini_reason,
        "interpretation":         interp,
    }
