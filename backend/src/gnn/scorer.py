"""
backend/src/gnn/scorer.py
==========================
Two GNN-powered scoring modes for post-retrieval re-ranking:

Mode 1 — "novelty"
    Loads pre-computed novelty_scores.json (produced by the Colab notebook)
    and blends each patent's novelty score with its FAISS semantic score.
    Fast O(1) lookup per hit.

Mode 2 — "graph_sim"
    Loads node_embeddings.npy (64-dim GNN embeddings produced by model.encode()).
    Computes structural uniqueness for each hit: how different this patent is
    from all other retrieved hits in GNN graph-embedding space.

    graph_uniqueness_i = 1 - mean_cosine_sim(emb_i, {emb_j | j ≠ i})

    Patents sitting in dense graph neighbourhoods (well-explored technology
    clusters) score LOW; patents in sparse, isolated neighbourhoods score HIGH.
    This gives a signal grounded in the actual graph topology rather than a
    hand-crafted heuristic.

Singleton accessors:
    get_scorer(mode="novelty")   → Callable
    get_scorer(mode="graph_sim") → Callable
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Default paths ──────────────────────────────────────────────────────────────
# scorer.py lives at: backend/src/gnn/scorer.py
# parents[0] → gnn/
# parents[1] → src/
# parents[2] → backend/
_VECTOR_DIR = Path(__file__).resolve().parents[2] / "data" / "vector_store"

# Module-level singletons — initialised on first call, reused thereafter
_novelty_scorer: Optional[Callable] = None
_graph_sim_scorer: Optional[Callable] = None


# ══════════════════════════════════════════════════════════════════════════════
# Mode 1 — Novelty Score (pre-computed lookup)
# ══════════════════════════════════════════════════════════════════════════════

def load_novelty_scorer(novelty_scores_path: str | Path) -> Callable:
    """
    Load pre-computed novelty scores and return a score_hits() callable.

    Args:
        novelty_scores_path: Path to novelty_scores.json from the Colab notebook.

    Returns:
        score_hits callable.

    Raises:
        FileNotFoundError: if the file does not exist.
    """
    path = Path(novelty_scores_path)
    if not path.exists():
        raise FileNotFoundError(
            f"novelty_scores.json not found at {path}. "
            "Run the Colab training notebook first and place the output in "
            "backend/data/vector_store/."
        )

    with open(path) as f:
        novelty_map: Dict[str, float] = json.load(f)

    logger.info("Loaded novelty scores for %d patents from %s", len(novelty_map), path)

    def score_hits(
        hits: List[dict],
        semantic_weight: float = 0.6,
        novelty_weight: float = 0.4,
    ) -> List[dict]:
        """
        Re-rank FAISS hits by blending semantic similarity with GNN novelty.

        Adds three keys to every hit dict:
            novelty_score  (float 0-1): GNN-predicted novelty.
            combined_score (float 0-1): weighted blend for re-ranking.
            gnn_mode       (str):       "novelty" — identifies scoring mode.

        Patents not seen during training receive novelty_score=0.5 (neutral).
        """
        if not hits:
            return hits

        unseen = 0
        for hit in hits:
            pid     = hit.get("patent_id", "")
            novelty = novelty_map.get(pid, 0.5)
            if pid not in novelty_map:
                unseen += 1
            combined = semantic_weight * hit["score"] + novelty_weight * novelty
            hit["novelty_score"]  = round(novelty,  4)
            hit["combined_score"] = round(combined, 4)
            hit["gnn_mode"]       = "novelty"

        if unseen:
            logger.debug("%d/%d hits used fallback novelty=0.5", unseen, len(hits))

        hits.sort(key=lambda h: h["combined_score"], reverse=True)
        for i, hit in enumerate(hits):
            hit["rank"] = i + 1

        return hits

    return score_hits


# ══════════════════════════════════════════════════════════════════════════════
# Mode 2 — Graph Similarity (structural neighbourhood uniqueness)
# ══════════════════════════════════════════════════════════════════════════════

def load_graph_sim_scorer(
    node_embeddings_path: str | Path,
    metadata_path: str | Path,
) -> Callable:
    """
    Load GNN node embeddings and return a score_hits() callable that uses
    structural neighbourhood uniqueness as the GNN signal.

    For a retrieved set of M patents, the uniqueness of patent i is:

        graph_uniqueness_i = 1 - (1/(M-1)) * Σ_{j≠i} cos_sim(emb_i, emb_j)

    where emb_i is the 64-dim GNN node embedding from model.encode().

    Rationale:
        Patents that are structurally similar to many others in the retrieved
        set sit in a dense, well-explored technology cluster → low uniqueness.
        Patents that are structurally isolated represent underexplored niches
        → high uniqueness (high novelty signal).

    This is grounded in actual graph topology (family links + CPC sibling
    edges) rather than a hand-crafted heuristic formula.

    Args:
        node_embeddings_path: Path to node_embeddings.npy (shape N×64).
        metadata_path: Path to metadata_mapping.json ({faiss_row: patent_id}).
    """
    emb_path  = Path(node_embeddings_path)
    meta_path = Path(metadata_path)

    if not emb_path.exists():
        raise FileNotFoundError(
            f"node_embeddings.npy not found at {emb_path}. "
            "Run the Colab training notebook and copy node_embeddings.npy to "
            "backend/data/vector_store/."
        )

    # Load and L2-normalise so cosine similarity == dot product (fast)
    node_embs: np.ndarray = np.load(str(emb_path)).astype(np.float32)   # (N, 64)
    norms = np.linalg.norm(node_embs, axis=1, keepdims=True) + 1e-8
    node_embs = node_embs / norms

    # Build patent_id → FAISS row index lookup
    if meta_path.exists():
        with open(meta_path) as f:
            raw = json.load(f)
        pid_to_row: Dict[str, int] = {v: int(k) for k, v in raw.items()}
        logger.info(
            "Loaded node embeddings %s + metadata (%d entries) for graph_sim scoring.",
            node_embs.shape, len(pid_to_row),
        )
    else:
        pid_to_row = {}
        logger.warning(
            "metadata_mapping.json not found at '%s'. "
            "Graph similarity will fall back to novelty=0.5 for all hits. "
            "Re-run build_faiss_index.py to generate proper metadata.",
            meta_path,
        )

    def score_hits(
        hits: List[dict],
        semantic_weight: float = 0.6,
        novelty_weight: float = 0.4,
    ) -> List[dict]:
        """
        Re-rank hits using graph-neighbourhood structural uniqueness.

        Adds three keys to every hit dict:
            novelty_score  (float 0-1): structural uniqueness in GNN space.
                1.0 = maximally isolated (novel niche).
                0.0 = perfectly clustered with all other hits.
            combined_score (float 0-1): weighted blend for re-ranking.
            gnn_mode       (str):       "graph_sim" — identifies scoring mode.
        """
        if not hits:
            return hits

        # Gather GNN embeddings for each hit
        hit_embs: List[Optional[np.ndarray]] = []
        for hit in hits:
            row = pid_to_row.get(hit.get("patent_id", ""))
            hit_embs.append(node_embs[row] if row is not None else None)

        # Need at least 2 known embeddings to compute pairwise similarity
        known_indices = [i for i, e in enumerate(hit_embs) if e is not None]

        if len(known_indices) < 2:
            # Graceful fallback: neutral uniqueness for all
            for hit in hits:
                hit["novelty_score"]  = 0.5
                hit["combined_score"] = round(
                    semantic_weight * hit["score"] + novelty_weight * 0.5, 4
                )
                hit["gnn_mode"] = "graph_sim"
            hits.sort(key=lambda h: h["combined_score"], reverse=True)
            for i, hit in enumerate(hits):
                hit["rank"] = i + 1
            return hits

        # Stack known embeddings into matrix (M × 64), already L2-normed
        emb_matrix = np.stack([hit_embs[i] for i in known_indices])   # (M, 64)

        # Pairwise cosine sim matrix via matrix multiplication (fast)
        sim_matrix = emb_matrix @ emb_matrix.T   # (M, M)
        M = len(known_indices)

        # Mean cosine similarity to all OTHER hits (exclude diagonal = self-sim of 1.0)
        mean_sim_to_others = (sim_matrix.sum(axis=1) - 1.0) / max(M - 1, 1)

        # Uniqueness = 1 - mean similarity, clipped to [0, 1]
        uniqueness = (1.0 - mean_sim_to_others).clip(0.0, 1.0)

        # Map known hit indices back to uniqueness values
        uniqueness_by_hit_idx: Dict[int, float] = {
            known_indices[j]: float(uniqueness[j]) for j in range(M)
        }

        # Apply scores to all hits
        for i, hit in enumerate(hits):
            u = uniqueness_by_hit_idx.get(i, 0.5)   # 0.5 neutral for unseen
            combined = semantic_weight * hit["score"] + novelty_weight * u
            hit["novelty_score"]  = round(u,        4)
            hit["combined_score"] = round(combined, 4)
            hit["gnn_mode"]       = "graph_sim"

        hits.sort(key=lambda h: h["combined_score"], reverse=True)
        for i, hit in enumerate(hits):
            hit["rank"] = i + 1

        return hits

    return score_hits


# ══════════════════════════════════════════════════════════════════════════════
# Public singleton accessor
# ══════════════════════════════════════════════════════════════════════════════

def get_scorer(mode: str = "novelty") -> Callable:
    """
    Return the module-level singleton scorer for the given mode.

    Singletons are initialised on first call and cached for the process lifetime
    (safe for Streamlit's @st.cache_resource pattern).

    Modes:
        "novelty"   — Pre-computed novelty lookup from novelty_scores.json.
                      Fast O(1) per hit. Requires re-training in Colab when
                      the corpus changes.

        "graph_sim" — Structural uniqueness from node_embeddings.npy.
                      Computed at query time from the retrieved hit set.
                      Works with any subset of the corpus; no retraining needed
                      to support a new query.

    Raises:
        FileNotFoundError: If the required artefacts for the chosen mode are
            missing from backend/data/vector_store/.
        ValueError: If an unknown mode string is supplied.
    """
    global _novelty_scorer, _graph_sim_scorer

    if mode == "novelty":
        if _novelty_scorer is None:
            _novelty_scorer = load_novelty_scorer(
                _VECTOR_DIR / "novelty_scores.json"
            )
        return _novelty_scorer

    elif mode == "graph_sim":
        if _graph_sim_scorer is None:
            _graph_sim_scorer = load_graph_sim_scorer(
                _VECTOR_DIR / "node_embeddings.npy",
                _VECTOR_DIR / "metadata_mapping.json",
            )
        return _graph_sim_scorer

    else:
        raise ValueError(
            f"Unknown GNN mode: '{mode}'. Valid options: 'novelty', 'graph_sim'."
        )
