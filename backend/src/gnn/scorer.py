"""Single authoritative entry point for live GNN patent re-ranking."""
from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger(__name__)


def run_live_gnn_rerank(
    hits: list[dict],
    mode: str = "novelty",
    semantic_weight: float = 0.7,
    novelty_weight: float = 0.3,
) -> list[dict]:
    """Build the query graph, execute GraphSAGE, and return reranked hits.

    Errors intentionally propagate so the caller can report an accurate GNN
    status and select its own semantic-only fallback.
    """
    if mode not in ("novelty", "graph_sim"):
        raise ValueError(f"Unknown GNN mode: '{mode}'.")
    if not hits:
        return hits

    # Local imports avoid the integration/scoring import cycle.
    from integration.pipeline import _get_model, _load_resources
    from gnn.graph_builder import build_subgraph_data
    from gnn.inference import run_gnn_inference
    from gnn.reranker import rerank_hits

    faiss_index, metadata_mapping, patents_df = _load_resources()
    graph_data, pid_to_idx = build_subgraph_data(
        hits, patents_df, metadata_mapping, faiss_index, _get_model()
    )
    embeddings, predictions = run_gnn_inference(graph_data)
    return rerank_hits(
        hits=hits,
        embeddings=embeddings,
        preds=predictions,
        pid_to_idx=pid_to_idx,
        mode=mode,
        semantic_weight=semantic_weight,
        novelty_weight=novelty_weight,
    )


def load_novelty_scorer(novelty_scores_path: str) -> Callable:
    """Backward-compatible alias; ``novelty_scores_path`` is no longer used."""
    return get_scorer("novelty")


def get_scorer(mode: str = "novelty") -> Callable:
    """Return the legacy scorer callable with semantic-only graceful fallback."""
    if mode not in ("novelty", "graph_sim"):
        raise ValueError(f"Unknown GNN mode: '{mode}'. Valid options: 'novelty', 'graph_sim'.")

    def score_hits(
        hits: list[dict],
        semantic_weight: float = 0.7,
        novelty_weight: float = 0.3,
    ) -> list[dict]:
        try:
            return run_live_gnn_rerank(
                hits,
                mode=mode,
                semantic_weight=semantic_weight,
                novelty_weight=novelty_weight,
            )
        except Exception as exc:
            logger.exception("GNN scoring failed; using semantic order: %s", exc)
            hits.sort(key=lambda hit: hit.get("semantic_score") or 0.0, reverse=True)
            for rank, hit in enumerate(hits, start=1):
                hit.update(
                    rank=rank,
                    graph_score=None,
                    combined_score=None,
                    gnn_mode=mode,
                    rank_change=0,
                )
            return hits

    return score_hits
