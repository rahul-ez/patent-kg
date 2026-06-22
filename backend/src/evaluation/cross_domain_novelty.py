"""
Cross-Domain Novelty Scorer
============================
Cross-domain inventions are statistically less obvious — they require knowledge
from disparate fields that would not typically be combined.

Two signals:
1. CPC section diversity  — distinct top-level CPC groups (A–H) across all concepts
2. Patent domain diversity — distinct domain tags across all concept hit sets

Score: 0 (single-domain) → 1 (spans maximum distinct domains)
"""

import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

from .per_concept_search import ConceptSearchResult

_CPC_SECTION_LABELS = {
    "A": "Human Necessities",
    "B": "Performing Operations / Transporting",
    "C": "Chemistry / Metallurgy",
    "D": "Textiles / Paper",
    "E": "Fixed Constructions",
    "F": "Mechanical Engineering",
    "G": "Physics",
    "H": "Electricity",
}


def score_cross_domain_novelty(results: List[ConceptSearchResult]) -> dict:
    """
    Score the cross-domain novelty of the invention.

    Returns
    -------
    dict: score (0–1), cpc_sections, patent_domains, per_concept_sections, interpretation
    """
    # ── CPC section diversity ─────────────────────────────────────────────────
    per_concept_sections: Dict[str, set] = {}
    global_sections: set = set()

    for r in results:
        secs = set()
        for code in r.all_cpc_codes:
            if code:
                s = code[0].upper()
                if s in _CPC_SECTION_LABELS:
                    secs.add(s)
                    global_sections.add(s)
        per_concept_sections[r.concept.label] = secs

    n_cpc = len(global_sections)
    cpc_score = min(n_cpc / 8.0, 1.0)   # 8 possible sections

    # ── Patent domain diversity ───────────────────────────────────────────────
    global_domains: set = set()
    for r in results:
        for h in r.hits:
            if h.domain:
                global_domains.add(h.domain.strip())

    n_domains = len(global_domains)
    domain_score = min(n_domains / 6.0, 1.0)   # 6 corpus domains

    # ── Isolation bonus ───────────────────────────────────────────────────────
    # Count concepts whose CPC sections don't overlap with any other concept
    labels = list(per_concept_sections.keys())
    isolated = 0
    for i, lbl in enumerate(labels):
        secs_i = per_concept_sections[lbl]
        if not secs_i:
            continue
        overlaps = any(
            secs_i & per_concept_sections[labels[j]]
            for j in range(len(labels)) if j != i
        )
        if not overlaps:
            isolated += 1

    # Combined
    score = 0.65 * cpc_score + 0.35 * domain_score
    if isolated >= 2:
        score = min(score + 0.10, 1.0)

    if score >= 0.70:
        interp = "Strong cross-domain invention — bridges multiple technology areas"
    elif score >= 0.45:
        interp = "Moderate cross-domain overlap — spans two or more fields"
    else:
        interp = "Single-domain invention — prior art exists in one main technology area"

    logger.info(
        "Cross-domain novelty: %.3f (CPC sections=%d, domains=%d, isolated_concepts=%d)",
        score, n_cpc, n_domains, isolated,
    )

    return {
        "score":                round(score, 4),
        "cpc_sections":         [
            {"section": s, "label": _CPC_SECTION_LABELS[s]}
            for s in sorted(global_sections)
        ],
        "patent_domains":       sorted(global_domains),
        "per_concept_sections": {k: sorted(v) for k, v in per_concept_sections.items()},
        "isolated_concept_count": isolated,
        "interpretation":       interp,
    }
