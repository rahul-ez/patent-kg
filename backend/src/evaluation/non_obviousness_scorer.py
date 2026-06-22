"""
Non-Obviousness Scorer
=======================
Orchestrates all eight sub-scorers into a single weighted Non-Obviousness Score (0–100).

Formula
-------
base (90 pts max):
    25% Combination Difficulty
    20% Motivation-to-Combine
    15% Cross-Domain Novelty
    15% Reconstruction Difficulty
    10% Citation Isolation
    10% Long-Felt Need

bonus (up to 10 pts):
    Teaching Away    (0–0.30 raw → contributes up to 5 pts)
    Unexpected Effect (0–0.15 raw → contributes up to 5 pts)

Gemini-heavy scorers (motivation, reconstruction) are skipped when
run_fast=True so the endpoint can return quickly without making extra LLM calls.
"""

import logging
import time
from typing import List, Optional

logger = logging.getLogger(__name__)

from .per_concept_search    import ConceptSearchResult
from .combination_difficulty import score_combination_difficulty
from .cross_domain_novelty  import score_cross_domain_novelty
from .citation_isolation    import score_citation_isolation
from .long_felt_need        import score_long_felt_need
from .landscape_scorer      import score_landscape
from .motivation_analyzer   import score_motivation_to_combine
from .teaching_away         import score_teaching_away
from .reconstruction_tester import score_reconstruction_difficulty
from .unexpected_effect     import score_unexpected_effect


def score_non_obviousness(
    user_idea: str,
    results: List[ConceptSearchResult],
    run_fast: bool = False,
    n_reconstruction_samples: int = 10,
    cpc_sibling_count: Optional[int] = None,
) -> dict:
    """
    Compute the full Non-Obviousness Score.

    Parameters
    ----------
    user_idea : str
        Original user idea text.
    results : List[ConceptSearchResult]
        Output of search_per_concept().
    run_fast : bool
        If True, skip Gemini-heavy scorers (motivation, reconstruction).
        Those slots fall back to neutral 0.5. Use for quick previews.
    n_reconstruction_samples : int
        Number of Gemini sampling attempts for the reconstruction test.
    cpc_sibling_count : int, optional
        From KG expansion — used by the landscape scorer.

    Returns
    -------
    dict
        score            — 0–100 final Non-Obviousness Score
        breakdown        — per-sub-scorer dict with score + interpretation
        weighted_contributions — how much each sub-scorer added to the total
        interpretation   — plain-English verdict
        elapsed_seconds  — wall-clock time
    """
    t0 = time.perf_counter()
    logger.info("=== Non-Obviousness Scoring START (fast=%s) ===", run_fast)

    # ── Run all sub-scorers ──────────────────────────────────────────────────
    comb   = score_combination_difficulty(results)
    cdnov  = score_cross_domain_novelty(results)
    citiso = score_citation_isolation(results)
    lfn    = score_long_felt_need(results)
    land   = score_landscape(results, cpc_sibling_count=cpc_sibling_count)

    if run_fast:
        motiv = {"score": 0.5, "cross_citation_density": 0.0,
                 "gemini_has_motivation": None, "gemini_reason": "skipped (fast mode)",
                 "interpretation": "Skipped in fast mode"}
        recon = {"score": 0.5, "reconstruction_rate": None, "n_samples": 0,
                 "n_reconstructed": 0, "avg_similarity": None, "threshold": 0.75,
                 "interpretation": "Skipped in fast mode"}
    else:
        motiv = score_motivation_to_combine(results)
        recon = score_reconstruction_difficulty(
            results, user_idea, n_samples=n_reconstruction_samples
        )

    teach = score_teaching_away(results)
    unexp = score_unexpected_effect(user_idea, results)

    # ── Weighted base (0–1) ──────────────────────────────────────────────────
    weights = {
        "combination_difficulty": 0.25,
        "motivation_to_combine":  0.20,
        "cross_domain_novelty":   0.15,
        "reconstruction":         0.15,
        "citation_isolation":     0.10,
        "long_felt_need":         0.10,
    }
    sub_scores = {
        "combination_difficulty": comb["score"],
        "motivation_to_combine":  motiv["score"],
        "cross_domain_novelty":   cdnov["score"],
        "reconstruction":         recon["score"],
        "citation_isolation":     citiso["score"],
        "long_felt_need":         lfn["score"],
    }

    base = sum(weights[k] * sub_scores[k] for k in weights)

    # ── Bonus (0–0.10) ───────────────────────────────────────────────────────
    # teaching_away raw is 0–0.30 → normalise to 0–0.05 contribution
    # unexpected_effect raw is 0–0.15 → normalise to 0–0.05 contribution
    teach_contrib = min(teach["score"] / 0.30 * 0.05, 0.05)
    unexp_contrib = min(unexp["score"] / 0.15 * 0.05, 0.05) if unexp["score"] > 0 else 0.0
    bonus = teach_contrib + unexp_contrib

    final_raw = min(base + bonus, 1.0)
    score_100 = round(final_raw * 100, 1)

    # ── Weighted contributions for the UI breakdown ──────────────────────────
    weighted_contributions = {k: round(weights[k] * sub_scores[k] * 100, 2) for k in weights}
    weighted_contributions["teaching_away_bonus"]   = round(teach_contrib * 100, 2)
    weighted_contributions["unexpected_effect_bonus"] = round(unexp_contrib * 100, 2)

    # ── Verdict ───────────────────────────────────────────────────────────────
    if score_100 >= 75:
        verdict = "Strong non-obviousness — this invention has significant inventive step"
    elif score_100 >= 55:
        verdict = "Moderate non-obviousness — some inventive step present, claims need careful drafting"
    elif score_100 >= 35:
        verdict = "Weak non-obviousness — combination may be argued as obvious by an examiner"
    else:
        verdict = "Low non-obviousness — prior art closely anticipates this combination"

    elapsed = round(time.perf_counter() - t0, 2)
    logger.info("=== Non-Obviousness Score: %.1f/100 (%.2fs) ===", score_100, elapsed)

    return {
        "score":          score_100,
        "score_raw":      round(final_raw, 4),
        "breakdown": {
            "combination_difficulty": {**comb,   "weight": weights["combination_difficulty"]},
            "motivation_to_combine":  {**motiv,  "weight": weights["motivation_to_combine"]},
            "cross_domain_novelty":   {**cdnov,  "weight": weights["cross_domain_novelty"]},
            "reconstruction":         {**recon,  "weight": weights["reconstruction"]},
            "citation_isolation":     {**citiso, "weight": weights["citation_isolation"]},
            "long_felt_need":         {**lfn,    "weight": weights["long_felt_need"]},
            "teaching_away":          {**teach,  "weight": 0.05, "type": "bonus"},
            "unexpected_effect":      {**unexp,  "weight": 0.05, "type": "bonus"},
            "landscape":              {**land,   "weight": 0.0,  "type": "context_only"},
        },
        "weighted_contributions": weighted_contributions,
        "interpretation":  verdict,
        "elapsed_seconds": elapsed,
        "fast_mode":       run_fast,
    }
