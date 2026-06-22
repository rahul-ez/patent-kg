"""
Timing Scorer
==============
Estimates whether the invention arrives at the right market moment.

Three signals:
  1. Filing velocity trend — are patents in this area being filed more quickly
     in recent years? Accelerating trend → closing window → lower timing score.

  2. Recency of closest prior art — if the newest patent is very recent (< 2y),
     the space is actively contested. If the newest is old (> 10y), it may be
     cleared by expiry.

  3. Technology cycle position — measured by the spread of publication years.
     Very tight cluster → nascent or saturated field. Wide spread → established
     field with room for incremental improvement.

Scoring formula (all sub-scores 0–1):
    velocity_score  = 1 - acceleration_ratio   (higher velocity → lower score)
    recency_score   = inverse of how recent the newest patent is
    spread_score    = year_spread normalised to [0,1] capped at 20 years

    score_raw = 0.40 * recency_score + 0.35 * velocity_score + 0.25 * spread_score
"""

import logging
import math
from typing import List, Optional

CURRENT_YEAR = 2026
logger = logging.getLogger(__name__)

from .per_concept_search import ConceptSearchResult


def score_timing(results: List[ConceptSearchResult]) -> dict:
    """
    Returns
    -------
    dict:
        score           — 0–100 timing score (higher = better window)
        newest_year     — most recent publication year seen
        oldest_year     — oldest publication year seen
        year_spread     — newest - oldest
        velocity_score  — 0–1 (lower velocity = higher score)
        recency_score   — 0–1 (older most-recent = higher score)
        spread_score    — 0–1
        interpretation  — plain-English verdict
        recency_flag    — "ACTIVE" | "CLEARING" | "LEGACY"
    """
    years: List[int] = []
    for r in results:
        for h in r.hits:
            try:
                y = int(h.publication_year)
                if 1900 < y <= CURRENT_YEAR:
                    years.append(y)
            except (ValueError, TypeError):
                pass

    if not years:
        return _default("No publication years available")

    newest = max(years)
    oldest = min(years)
    spread = newest - oldest

    # ── Recency signal ───────────────────────────────────────────────────────
    years_since_newest = CURRENT_YEAR - newest
    if years_since_newest <= 2:
        recency_score = 0.20   # very active — hard to patent around
        recency_flag  = "ACTIVE"
    elif years_since_newest <= 6:
        recency_score = 0.55   # moderately recent
        recency_flag  = "ACTIVE"
    elif years_since_newest <= 12:
        recency_score = 0.75   # cooling down, some room opening
        recency_flag  = "CLEARING"
    else:
        recency_score = 0.90   # likely expired or ignored — open space
        recency_flag  = "LEGACY"

    # ── Velocity signal ──────────────────────────────────────────────────────
    # Compare filing density in recent half vs old half of the timeline.
    if spread >= 4:
        midpoint   = oldest + spread // 2
        old_half   = [y for y in years if y < midpoint]
        new_half   = [y for y in years if y >= midpoint]
        old_rate   = len(old_half) / max(spread / 2, 1)
        new_rate   = len(new_half) / max(spread / 2, 1)
        accel      = new_rate / old_rate if old_rate > 0 else 1.0
        # accel > 1 means accelerating → lower score
        velocity_score = max(0.0, min(1.0, 1.0 - math.log1p(max(accel - 1.0, 0.0)) / math.log1p(3)))
    else:
        accel          = None
        velocity_score = 0.50   # not enough data

    # ── Spread signal ────────────────────────────────────────────────────────
    spread_score = min(spread / 20.0, 1.0)

    # ── Combine ───────────────────────────────────────────────────────────────
    score_raw = (
        0.40 * recency_score +
        0.35 * velocity_score +
        0.25 * spread_score
    )
    score_100 = round(min(score_raw, 1.0) * 100, 1)

    if score_100 >= 70:
        verdict = "Favourable timing — prior art is maturing and the window is opening"
    elif score_100 >= 50:
        verdict = "Neutral timing — moderate competition, filing now is reasonable"
    elif score_100 >= 30:
        verdict = "Challenging timing — field is active and competition is intensifying"
    else:
        verdict = "Poor timing — very active filing area or severely saturated space"

    logger.info(
        "Timing: score=%.1f, newest=%d, spread=%d, accel=%s, flag=%s",
        score_100, newest, spread,
        f"{accel:.2f}" if accel is not None else "n/a",
        recency_flag,
    )

    return {
        "score":          score_100,
        "score_raw":      round(score_raw, 4),
        "newest_year":    newest,
        "oldest_year":    oldest,
        "year_spread":    spread,
        "velocity_score": round(velocity_score, 4),
        "recency_score":  round(recency_score, 4),
        "spread_score":   round(spread_score, 4),
        "acceleration":   round(accel, 3) if accel is not None else None,
        "recency_flag":   recency_flag,
        "n_years_used":   len(years),
        "interpretation": verdict,
    }


def _default(reason: str = "") -> dict:
    return {
        "score":          50.0,
        "score_raw":      0.5,
        "newest_year":    None,
        "oldest_year":    None,
        "year_spread":    None,
        "velocity_score": None,
        "recency_score":  None,
        "spread_score":   None,
        "acceleration":   None,
        "recency_flag":   "UNKNOWN",
        "n_years_used":   0,
        "interpretation": f"Timing analysis unavailable: {reason}",
    }
