"""
Citation Network Isolation Scorer
===================================
If concept patent clusters share no cited papers and no family edges, the
prior art never connected them — strong evidence of non-obviousness.

Score: 0 (concepts well-connected in citation graph) → 1 (fully isolated)
"""

import logging
import os
from typing import List

logger = logging.getLogger(__name__)

from .per_concept_search import ConceptSearchResult


def score_citation_isolation(results: List[ConceptSearchResult]) -> dict:
    """
    Query Neo4j for citation connections between concept patent clusters.

    Returns
    -------
    dict: score (0–1), connected_pairs, isolated_pairs, shared_papers, interpretation
    """
    if len(results) < 2:
        return _default()

    clusters = {
        r.concept.label: [
            h.patent_id for h in r.hits
            if not h.patent_id.startswith("UNKNOWN")
        ]
        for r in results
    }
    clusters = {k: v for k, v in clusters.items() if v}

    if len(clusters) < 2:
        return _default()

    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
        )

        labels = list(clusters.keys())
        connected_pairs, isolated_pairs = [], []
        total_shared_papers = 0

        with driver.session() as session:
            for i in range(len(labels)):
                for j in range(i + 1, len(labels)):
                    ids_a, ids_b = clusters[labels[i]], clusters[labels[j]]

                    # Shared cited papers (co-citation)
                    row = session.run(
                        """
                        MATCH (a:Patent)-[:CITES_PAPER]->(p:Paper)<-[:CITES_PAPER]-(b:Patent)
                        WHERE a.patent_id IN $ids_a AND b.patent_id IN $ids_b
                        RETURN count(DISTINCT p) AS shared
                        """,
                        ids_a=ids_a, ids_b=ids_b,
                    ).single()
                    shared = row["shared"] if row else 0
                    total_shared_papers += shared

                    # Shared family membership
                    fam = session.run(
                        """
                        MATCH (a:Patent)-[:SIMPLE_FAMILY_MEMBER|EXTENDED_FAMILY_MEMBER]-(b:Patent)
                        WHERE a.patent_id IN $ids_a AND b.patent_id IN $ids_b
                        RETURN count(*) AS links
                        """,
                        ids_a=ids_a, ids_b=ids_b,
                    ).single()
                    family_links = fam["links"] if fam else 0

                    pair = (labels[i], labels[j])
                    if shared > 0 or family_links > 0:
                        connected_pairs.append({
                            "concepts":      pair,
                            "shared_papers": shared,
                            "family_links":  family_links,
                        })
                    else:
                        isolated_pairs.append({"concepts": pair})

        driver.close()

        total = len(connected_pairs) + len(isolated_pairs)
        isolation_ratio = len(isolated_pairs) / max(total, 1)
        paper_penalty   = min(total_shared_papers / 20.0, 0.3)
        score = max(isolation_ratio - paper_penalty, 0.0)

        if score >= 0.80:
            interp = "Concepts are citation-isolated — prior art never connected them"
        elif score >= 0.50:
            interp = "Partial citation isolation — weak connections in the prior art"
        else:
            interp = "Concepts are citation-connected — prior art already linked these areas"

        logger.info(
            "Citation isolation: %.3f (isolated=%d/%d pairs, shared_papers=%d)",
            score, len(isolated_pairs), total, total_shared_papers,
        )

        return {
            "score":           round(score, 4),
            "connected_pairs": connected_pairs,
            "isolated_pairs":  isolated_pairs,
            "shared_papers":   total_shared_papers,
            "interpretation":  interp,
        }

    except Exception as exc:
        logger.warning("Citation isolation skipped (%s) — neutral.", exc)
        return _default()


def _default() -> dict:
    return {
        "score":           0.5,
        "connected_pairs": [],
        "isolated_pairs":  [],
        "shared_papers":   0,
        "interpretation":  "Citation isolation unavailable (Neo4j offline or insufficient data)",
    }
