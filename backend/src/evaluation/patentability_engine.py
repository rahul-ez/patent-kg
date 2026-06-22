"""
Patentability Engine
=====================
Master orchestrator — runs all evaluation modules and blends them into a
single patentability assessment.

Final score weights (0–100):
    30%  Novelty            — FAISS + GNN semantic distance
    35%  Non-Obviousness    — 8-factor KSR analysis
    15%  Competitive Landscape — prior art density + assignee concentration
    10%  Claim Breadth      — CPC depth + cross-domain uniqueness
    10%  Timing             — filing velocity + recency of prior art

Qualitative outputs (not blended):
    India Eligibility  — Section 3 flags (rule-based, no score)
    Technical Depth    — Low/Medium/High confidence indicator
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional

logger = logging.getLogger(__name__)

from .concept_extractor     import extract_concepts
from .per_concept_search    import search_per_concept
from .novelty_scorer        import score_novelty
from .non_obviousness_scorer import score_non_obviousness
from .landscape_scorer      import score_landscape
from .claim_breadth_scorer  import score_claim_breadth
from .timing_scorer         import score_timing
from .india_eligibility     import check_india_eligibility
from .technical_depth       import assess_technical_depth

_WEIGHTS = {
    "novelty":     0.30,
    "non_obvious": 0.35,
    "landscape":   0.15,
    "claim_breadth": 0.10,
    "timing":      0.10,
}


def run_evaluation(
    user_idea: str,
    hits: List[dict],
    top_k_concepts: int = 5,
    run_fast: bool = False,
    n_reconstruction_samples: int = 5,
) -> dict:
    """
    Parameters
    ----------
    user_idea : str
        Raw inventor idea text (same as what was passed to the pipeline).
    hits : List[dict]
        Pipeline results as returned by run_end_to_end() — used for novelty scoring
        and as additional prior-art context.
    top_k_concepts : int
        Number of prior-art hits to retrieve per concept (default 5).
    run_fast : bool
        Skip Gemini-heavy scorers (reconstruction, motivation). Faster but less thorough.
    n_reconstruction_samples : int
        Number of Gemini reconstruction attempts (default 5, increase for rigour).

    Returns
    -------
    dict  — see inline comments for field descriptions.
    """
    t0 = time.perf_counter()
    logger.info("=== Patentability Engine START (fast=%s) ===", run_fast)

    # ── Step 1: Concept extraction ────────────────────────────────────────────
    concepts = extract_concepts(user_idea)
    logger.info("Extracted %d concepts: %s", len(concepts), [c.label for c in concepts])

    # ── Step 2: Per-concept FAISS search ─────────────────────────────────────
    results = search_per_concept(concepts, top_k=top_k_concepts, enrich_cpc=True)
    logger.info("Per-concept search: %d concept clusters", len(results))

    # ── Step 3: Run all dimension scorers ─────────────────────────────────────
    # 3a. Novelty uses raw pipeline hits (already GNN-scored)
    novelty_r = score_novelty(hits)

    # 3b. Non-Obviousness (most complex — internally calls 8 sub-scorers)
    non_obvs_r = score_non_obviousness(
        user_idea, results,
        run_fast=run_fast,
        n_reconstruction_samples=n_reconstruction_samples,
    )

    # 3c. Landscape (also computed inside non_obviousness as context_only;
    #     calling again here is cheap and keeps the engine self-contained)
    landscape_r = score_landscape(results)

    # 3d. Claim Breadth
    breadth_r = score_claim_breadth(results)

    # 3e. Timing
    timing_r = score_timing(results)

    # 3f. India Section 3 eligibility (rule-based, no numeric score)
    india_r = check_india_eligibility(user_idea, results)

    # 3g. Technical depth (confidence indicator, not blended)
    depth_r = assess_technical_depth(user_idea, results)

    # ── Step 4: Final weighted blend ──────────────────────────────────────────
    # All dimension scores are 0–100. Landscape score is 0–1 — convert it.
    landscape_score_100 = landscape_r["score"] * 100

    raw_blend = (
        _WEIGHTS["novelty"]      * novelty_r["score"] +
        _WEIGHTS["non_obvious"]  * non_obvs_r["score"] +
        _WEIGHTS["landscape"]    * landscape_score_100 +
        _WEIGHTS["claim_breadth"] * breadth_r["score"] +
        _WEIGHTS["timing"]       * timing_r["score"]
    )

    # Confidence dampening: Low depth → pull score toward 50 (uncertain territory)
    confidence = depth_r["confidence"]
    dampened = raw_blend * confidence + 50.0 * (1.0 - confidence)
    patentability_score = round(min(max(dampened, 0.0), 100.0), 1)

    # ── Step 5: Verdict ───────────────────────────────────────────────────────
    if india_r["is_flagged"] and any(f["severity"] == "HIGH" for f in india_r["flags"]):
        eligibility_caveat = " Note: Indian Patent Act eligibility concerns flagged."
    else:
        eligibility_caveat = ""

    if patentability_score >= 75:
        verdict = f"Strong patentability potential.{eligibility_caveat}"
        risk    = "Low"
    elif patentability_score >= 55:
        verdict = f"Moderate patentability — careful claim drafting needed.{eligibility_caveat}"
        risk    = "Medium"
    elif patentability_score >= 35:
        verdict = f"Weak patentability — significant prior art overlap exists.{eligibility_caveat}"
        risk    = "High"
    else:
        verdict = f"Low patentability — invention closely anticipated by prior art.{eligibility_caveat}"
        risk    = "High"

    elapsed = round(time.perf_counter() - t0, 2)
    logger.info(
        "=== Patentability Engine DONE: %.1f/100 (%s risk) in %.2fs ===",
        patentability_score, risk, elapsed,
    )

    return {
        # ── Top-level result ──────────────────────────────────────────────────
        "patentability_score": patentability_score,
        "patentability_raw":   round(raw_blend, 2),
        "verdict":             verdict,
        "risk":                risk,
        "confidence":          confidence,

        # ── Dimension scores ──────────────────────────────────────────────────
        "novelty":         novelty_r,
        "non_obviousness": non_obvs_r,
        "landscape":       {**landscape_r, "score_100": round(landscape_score_100, 1)},
        "claim_breadth":   breadth_r,
        "timing":          timing_r,

        # ── Qualitative assessors ─────────────────────────────────────────────
        "india_eligibility": india_r,
        "technical_depth":   depth_r,

        # ── Weight breakdown (for transparency UI) ────────────────────────────
        "weights":    _WEIGHTS,
        "contributions": {
            "novelty":      round(_WEIGHTS["novelty"]       * novelty_r["score"], 2),
            "non_obvious":  round(_WEIGHTS["non_obvious"]   * non_obvs_r["score"], 2),
            "landscape":    round(_WEIGHTS["landscape"]     * landscape_score_100, 2),
            "claim_breadth": round(_WEIGHTS["claim_breadth"] * breadth_r["score"], 2),
            "timing":       round(_WEIGHTS["timing"]        * timing_r["score"], 2),
        },

        # ── Metadata ──────────────────────────────────────────────────────────
        "concept_count":  len(concepts),
        "concepts":       [{"label": c.label, "description": c.description} for c in concepts],
        "elapsed_seconds": elapsed,
        "fast_mode":       run_fast,
    }
