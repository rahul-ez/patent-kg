"""
Novelty Scorer
==============
Combines semantic FAISS similarity with GNN novelty to produce a 0–100 Novelty Score.

Two signals:
  1. Semantic novelty  = 1 - (weighted average of top FAISS semantic scores)
     → Low FAISS score means the idea is far from existing patents → high novelty
  2. GNN novelty score = already computed by scorer.py (pre-built or structural)
     → Reflects graph-structural originality, not just text similarity

Blend: 60% semantic, 40% GNN (mirrors the pipeline's combined_score weights).
If GNN novelty is unavailable, falls back to 100% semantic.
"""

import logging
import math
from typing import List

logger = logging.getLogger(__name__)


def score_novelty(hits: List[dict]) -> dict:
    """
    Parameters
    ----------
    hits : list of hit dicts as returned by the pipeline
        Required fields: semantic_score
        Optional fields: novelty_score (GNN), gnn_mode

    Returns
    -------
    dict:
        score             — 0–100 novelty score
        semantic_novelty  — 0–1 semantic component
        gnn_novelty       — 0–1 GNN component (None if unavailable)
        gnn_mode          — "novelty" | "graph_sim" | None
        blend             — actual weights used {"semantic": x, "gnn": y}
        top_semantic_score — highest semantic_score seen (= closest prior art)
        interpretation    — plain-English verdict
    """
    if not hits:
        return _default("No hits provided")

    # ── Semantic novelty ─────────────────────────────────────────────────────
    # Only FAISS hits carry a real semantic_score; KG-expanded hits have None.
    # Use only hits where semantic_score is an actual float.
    faiss_hits = [h for h in hits if isinstance(h.get("semantic_score"), float)]
    if not faiss_hits:
        return _default("No FAISS hits with semantic scores")

    # Weight by inverse rank so the closest prior art matters most.
    semantic_scores = [h["semantic_score"] for h in faiss_hits]
    top_semantic    = max(semantic_scores)

    weights      = [1.0 / (i + 1) for i in range(len(faiss_hits))]
    w_sum        = sum(weights)
    weighted_avg = sum(s * w for s, w in zip(semantic_scores, weights)) / w_sum

    # Novelty is the COMPLEMENT of similarity
    semantic_novelty = max(0.0, 1.0 - weighted_avg)

    # ── GNN novelty ──────────────────────────────────────────────────────────
    gnn_scores = [h.get("novelty_score") for h in hits
                  if isinstance(h.get("novelty_score"), float)]
    gnn_mode   = hits[0].get("gnn_mode") if hits else None

    if gnn_scores:
        avg_gnn_novelty = sum(gnn_scores) / len(gnn_scores)
        w_sem, w_gnn    = 0.60, 0.40
        final_raw       = w_sem * semantic_novelty + w_gnn * avg_gnn_novelty
    else:
        avg_gnn_novelty = None
        w_sem, w_gnn    = 1.00, 0.00
        final_raw       = semantic_novelty

    final_raw = min(max(final_raw, 0.0), 1.0)
    score_100 = round(final_raw * 100, 1)

    # ── Interpretation ───────────────────────────────────────────────────────
    if score_100 >= 80:
        verdict = "High novelty — idea is far from existing prior art"
    elif score_100 >= 60:
        verdict = "Moderate novelty — some prior art overlap, but meaningful differentiation"
    elif score_100 >= 40:
        verdict = "Low-moderate novelty — prior art closely covers core concepts"
    else:
        verdict = "Low novelty — closely anticipated by existing patents"

    logger.info(
        "Novelty: score=%.1f, sem=%.3f, gnn=%s, blend=(%.0f%%/%.0f%%)",
        score_100, semantic_novelty,
        f"{avg_gnn_novelty:.3f}" if avg_gnn_novelty is not None else "n/a",
        w_sem * 100, w_gnn * 100,
    )

    return {
        "score":               score_100,
        "score_raw":           round(final_raw, 4),
        "semantic_novelty":    round(semantic_novelty, 4),
        "gnn_novelty":         round(avg_gnn_novelty, 4) if avg_gnn_novelty is not None else None,
        "gnn_mode":            gnn_mode,
        "blend": {
            "semantic": round(w_sem, 2),
            "gnn":      round(w_gnn, 2),
        },
        "top_semantic_score":  round(top_semantic, 4),
        "n_hits_used":         len(hits),
        "interpretation":      verdict,
    }


def _default(reason: str = "") -> dict:
    return {
        "score":              50.0,
        "score_raw":          0.5,
        "semantic_novelty":   None,
        "gnn_novelty":        None,
        "gnn_mode":           None,
        "blend":              {"semantic": 1.0, "gnn": 0.0},
        "top_semantic_score": None,
        "n_hits_used":        0,
        "interpretation":     f"Novelty scoring unavailable: {reason}",
    }
