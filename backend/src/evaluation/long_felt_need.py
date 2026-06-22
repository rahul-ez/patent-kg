"""
Long-Felt Need Scorer
======================
A problem unsolved for many years despite many attempts strengthens
the case for non-obviousness.

Three signals from hit metadata:
1. Year spread          — how long patents in this space have existed
2. Citation activity    — average cited_by_patent_count (proxy for research volume)
3. No dominant solution — absence of a single landmark patent (cited_by > 500)

Score: 0 (recent / already solved) → 1 (old, heavily studied, still unsolved)
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

from .per_concept_search import ConceptSearchResult


def score_long_felt_need(results: List[ConceptSearchResult]) -> dict:
    """
    Returns
    -------
    dict: score, year_spread, min_year, max_year, avg_citations,
          dominant_solution, interpretation
    """
    all_hits = [h for r in results for h in r.hits]
    if not all_hits:
        return _default()

    # ── Year spread ───────────────────────────────────────────────────────────
    years = []
    for h in all_hits:
        try:
            y = int(h.publication_year)
            if 1970 <= y <= 2030:
                years.append(y)
        except (ValueError, TypeError):
            pass

    year_spread = (max(years) - min(years)) if len(years) >= 2 else 0
    year_score  = min(year_spread / 20.0, 1.0)   # 20+ year spread → 1.0

    # ── Citation activity ─────────────────────────────────────────────────────
    counts = []
    for h in all_hits:
        try:
            counts.append(int(h.cited_by_patent_count))
        except (ValueError, TypeError):
            pass

    avg_citations = sum(counts) / len(counts) if counts else 0.0
    citation_score = min(avg_citations / 100.0, 1.0)   # avg > 100 → 1.0

    # ── No dominant solution ──────────────────────────────────────────────────
    max_citations = max(counts, default=0)
    has_dominant  = max_citations > 500
    no_dominant_score = 0.0 if has_dominant else 1.0

    # ── Combined ──────────────────────────────────────────────────────────────
    score = 0.40 * year_score + 0.35 * citation_score + 0.25 * no_dominant_score

    if score >= 0.70:
        interp = "Long-felt need — old, heavily studied problem with no definitive solution"
    elif score >= 0.45:
        interp = "Moderate long-felt need — active research area over several years"
    else:
        interp = "Recent problem — newly emerged area or already well solved"

    logger.info(
        "Long-felt need: %.3f (spread=%d yrs, avg_cites=%.1f, dominant=%s)",
        score, year_spread, avg_citations, has_dominant,
    )

    return {
        "score":              round(score, 4),
        "year_spread":        year_spread,
        "min_year":           min(years, default=None),
        "max_year":           max(years, default=None),
        "avg_citations":      round(avg_citations, 1),
        "dominant_solution":  has_dominant,
        "dominant_threshold": 500,
        "interpretation":     interp,
    }


def _default() -> dict:
    return {
        "score":              0.5,
        "year_spread":        0,
        "min_year":           None,
        "max_year":           None,
        "avg_citations":      0.0,
        "dominant_solution":  False,
        "dominant_threshold": 500,
        "interpretation":     "Insufficient data to compute long-felt need signal",
    }
