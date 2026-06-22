"""
Claim Breadth Potential Scorer
================================
Estimates how broadly an inventor could draft patent claims given the CPC
landscape around the idea.

Two signals:
  1. CPC code depth  — shallower average CPC depth → broader territory available
     CPC hierarchy: Section (1) → Class (2) → Subclass (3) → Group (4) → Subgroup (5)
     A short code like "G06N" (depth 3) covers more than "G06N 3/04" (depth 5).

  2. CPC uniqueness  — fraction of concepts that have UNIQUE CPC sections (no overlap)
     If each concept maps to a different CPC area, the claims can be drafted broadly
     across domains. If all concepts map to the same few codes, the space is crowded.

Scoring formula:
    depth_score    = 1 - (avg_depth - 1) / 4   (depth 1→score 1, depth 5→score 0)
    unique_score   = unique_concepts / total_concepts
    score_raw      = 0.55 * depth_score + 0.45 * unique_score
"""

import logging
import re
from typing import List, Dict, Tuple, Set

logger = logging.getLogger(__name__)

from .per_concept_search import ConceptSearchResult

_CPC_RE = re.compile(r"^([A-H])(\d{2})([A-Z])(\d+)(?:[/\\](\S+))?$", re.IGNORECASE)


def _parse_cpc_depth(code: str) -> int:
    """Return hierarchy depth of a CPC code string (1–5)."""
    code = code.strip().upper()
    m = _CPC_RE.match(code)
    if not m:
        # Single letter = section only
        if len(code) == 1 and code in "ABCDEFGH":
            return 1
        return 3  # safe default if parse fails
    _, cls, subcls, group, subgroup = m.groups()
    if subgroup:
        return 5
    if group:
        return 4
    if subcls:
        return 3
    if cls:
        return 2
    return 1


def _cpc_section(code: str) -> str:
    c = code.strip().upper()
    return c[0] if c and c[0] in "ABCDEFGH" else ""


def score_claim_breadth(results: List[ConceptSearchResult]) -> dict:
    """
    Parameters
    ----------
    results : List[ConceptSearchResult]
        Output of search_per_concept().

    Returns
    -------
    dict:
        score               — 0–100 claim breadth potential
        avg_cpc_depth       — average hierarchy depth of all CPC codes seen
        unique_section_ratio — fraction of concepts with unique CPC sections
        total_cpc_codes     — total codes observed
        depth_score         — sub-score from depth analysis (0–1)
        uniqueness_score    — sub-score from section uniqueness (0–1)
        per_concept_depth   — {concept_label: avg_depth}
        interpretation      — plain-English verdict
    """
    if not results:
        return _default("No concept results provided")

    per_concept_sections: Dict[str, Set[str]] = {}
    all_depths: List[int] = []
    total_codes = 0

    for r in results:
        sections: Set[str] = set()
        for code in r.all_cpc_codes:
            depth = _parse_cpc_depth(code)
            all_depths.append(depth)
            total_codes += 1
            sec = _cpc_section(code)
            if sec:
                sections.add(sec)
        per_concept_sections[r.concept.label] = sections

    per_concept_avg: Dict[str, float] = {}
    for r in results:
        depths = [_parse_cpc_depth(c) for c in r.all_cpc_codes] if r.all_cpc_codes else []
        per_concept_avg[r.concept.label] = round(sum(depths) / len(depths), 2) if depths else 3.0

    if not all_depths:
        return _default("No CPC codes found in results")

    avg_depth = sum(all_depths) / len(all_depths)
    # Normalise: depth 1 → 1.0, depth 5 → 0.0
    depth_score = max(0.0, min(1.0, 1.0 - (avg_depth - 1.0) / 4.0))

    # Uniqueness: concepts whose sections don't overlap with ALL others
    n_concepts = len(results)
    if n_concepts <= 1:
        unique_score = 0.5
    else:
        unique_count = 0
        labels = list(per_concept_sections.keys())
        for label in labels:
            secs = per_concept_sections[label]
            others = set().union(*(per_concept_sections[l] for l in labels if l != label))
            if not secs or not secs.intersection(others):
                unique_count += 1
        unique_score = unique_count / n_concepts

    score_raw = 0.55 * depth_score + 0.45 * unique_score
    score_100 = round(min(score_raw, 1.0) * 100, 1)

    if score_100 >= 70:
        verdict = "High claim breadth potential — broad claims possible across multiple CPC domains"
    elif score_100 >= 50:
        verdict = "Moderate claim breadth — some domain overlap limits scope"
    elif score_100 >= 30:
        verdict = "Limited claim breadth — crowded CPC space, narrower claims likely needed"
    else:
        verdict = "Low claim breadth potential — dense prior art, very specific claims required"

    logger.info(
        "Claim breadth: score=%.1f, avg_depth=%.2f, unique_ratio=%.2f",
        score_100, avg_depth, unique_score,
    )

    return {
        "score":                score_100,
        "score_raw":            round(score_raw, 4),
        "avg_cpc_depth":        round(avg_depth, 2),
        "unique_section_ratio": round(unique_score, 4),
        "total_cpc_codes":      total_codes,
        "depth_score":          round(depth_score, 4),
        "uniqueness_score":     round(unique_score, 4),
        "per_concept_depth":    per_concept_avg,
        "interpretation":       verdict,
    }


def _default(reason: str = "") -> dict:
    return {
        "score":                50.0,
        "score_raw":            0.5,
        "avg_cpc_depth":        None,
        "unique_section_ratio": None,
        "total_cpc_codes":      0,
        "depth_score":          None,
        "uniqueness_score":     None,
        "per_concept_depth":    {},
        "interpretation":       f"Claim breadth unavailable: {reason}",
    }
