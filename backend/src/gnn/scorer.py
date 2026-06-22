"""
backend/src/gnn/scorer.py
==========================
Unified interface for GNN-powered patent scoring.
Restores real live GraphSAGE forward pass inference instead of offline score loading.

Supports two GNN scoring modes:
1. "novelty"   - Live prediction of novelty score via the GNN model's MLP head.
2. "graph_sim" - Live structural cosine similarity against the graph neighborhood centroid.
"""
from __future__ import annotations
import logging
from typing import Callable

logger = logging.getLogger(__name__)

def load_novelty_scorer(novelty_scores_path: str) -> Callable:
    """Wrapper for backward compatibility."""
    return get_scorer("novelty")

def get_scorer(mode: str = "novelty") -> Callable:
    """
    Return the GNN score_hits() callable.
    
    The returned callable matches the original interface:
    score_hits(hits, semantic_weight=0.6, novelty_weight=0.4)
    """
    if mode not in ("novelty", "graph_sim"):
        raise ValueError(f"Unknown GNN mode: '{mode}'. Valid options: 'novelty', 'graph_sim'.")
        
    def score_hits(
        hits: list[dict],
        semantic_weight: float = 0.7,
        novelty_weight: float = 0.3,
    ) -> list[dict]:
        """
        Execute the live GNN pipeline:
        Graph construction -> Model forward pass -> Hybrid re-ranking.
        """
        if not hits:
            return hits
            
        try:
            # Local imports to prevent circular dependencies with integration.pipeline
            from integration.pipeline import _load_resources, _get_model
            from gnn.graph_builder import build_subgraph_data
            from gnn.inference import run_gnn_inference
            from gnn.reranker import rerank_hits
            
            # Retrieve cached global resources (FAISS index, metadata, SentenceTransformer)
            faiss_index, metadata_mapping, patents_df = _load_resources()
            st_model = _get_model()
            
            # Step 1: Build the query-time PyTorch Geometric subgraph
            logger.info("Step 5.1 — Building query-time graph object...")
            data, pid_to_idx = build_subgraph_data(hits, patents_df, metadata_mapping, faiss_index, st_model)
            
            # Step 2: Run live GraphSAGE forward pass
            logger.info("Step 5.2 — Loading GraphSAGE and running live forward pass...")
            embeddings, preds = run_gnn_inference(data)
            
            # Step 3: Compute structural similarity and rerank
            logger.info("Step 5.3 — Executing hybrid re-ranking...")
            return rerank_hits(
                hits=hits,
                embeddings=embeddings,
                preds=preds,
                pid_to_idx=pid_to_idx,
                mode=mode,
                semantic_weight=semantic_weight,
                novelty_weight=novelty_weight
            )
            
        except Exception as exc:
            # Critical constraint 7: Pipeline must degrade gracefully and never crash
            logger.exception("GNN scoring failed due to an error. Degrading to semantic scores only: %s", exc)
            
            # Fall back to semantic scores only
            for i, hit in enumerate(hits):
                hit["rank"] = i + 1
                hit["graph_score"] = None
                hit["combined_score"] = None
                hit["gnn_mode"] = mode
                hit["rank_change"] = 0
                
            hits.sort(key=lambda h: h.get("semantic_score") or 0.0, reverse=True)
            for i, hit in enumerate(hits):
                hit["rank"] = i + 1
                
            return hits
            
    return score_hits
