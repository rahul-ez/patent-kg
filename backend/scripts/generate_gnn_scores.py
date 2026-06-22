"""
generate_gnn_scores.py
======================
Generates novelty_scores.json and node_embeddings.npy locally — no Colab or
trained GNN required. Results are a good approximation; a proper GNN trained
on the citation graph will be more accurate but this unblocks the GNN scoring
pathway immediately.

novelty_scores.json
-------------------
Maps patent_id -> novelty float (0-1).
Derived from: embedding isolation (how different each patent is from its
nearest neighbours in FAISS space) blended with recency and inverse citation
count. Patents in sparse, underexplored embedding regions score HIGH.

node_embeddings.npy
-------------------
Shape (N, D) float32 — the same embeddings already stored in the FAISS index,
reconstructed into a NumPy array. This enables graph_sim scoring mode, which
computes structural uniqueness live at query time.

Usage
-----
    cd patent-kg/backend
    python scripts/generate_gnn_scores.py

Output files land in:  patent-kg/data/vector_store/
Runtime:               5–20 min depending on corpus size (215K patents, 384-dim)
"""

import json
import logging
import os
import sys
from pathlib import Path

import numpy as np
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── Path setup ────────────────────────────────────────────────────────────────
_SCRIPTS_DIR  = Path(__file__).resolve().parent
_BACKEND_DIR  = _SCRIPTS_DIR.parent
_SRC_DIR      = _BACKEND_DIR / "src"
sys.path.insert(0, str(_SRC_DIR))

from config.paths import VECTOR_STORE, ROOT  # noqa: E402
import faiss                                  # noqa: E402
import pandas as pd                           # noqa: E402

_INDEX_FILE    = VECTOR_STORE / "patents.index"
_METADATA_FILE = VECTOR_STORE / "metadata_mapping.json"
_OUT_EMBEDDINGS = VECTOR_STORE / "node_embeddings.npy"
_OUT_NOVELTY    = VECTOR_STORE / "novelty_scores.json"

# Batch size for nearest-neighbour queries (tune down if you run out of RAM)
_NN_BATCH = 512
# How many nearest neighbours to use for isolation score
_K_NEIGHBOURS = 10


def load_index_and_metadata():
    logger.info("Loading FAISS index from %s …", _INDEX_FILE)
    index = faiss.read_index(str(_INDEX_FILE))
    logger.info("  %d vectors, dim=%d", index.ntotal, index.d)

    with open(_METADATA_FILE) as f:
        meta = json.load(f)  # {str(row): patent_id}
    row_to_pid = {int(k): v for k, v in meta.items()}
    return index, row_to_pid


def reconstruct_embeddings(index) -> np.ndarray:
    """
    Pull all stored vectors out of the FAISS index.
    Works for IndexFlatIP / IndexFlatL2 directly.
    For IVF indices, calls make_direct_map() first.
    """
    n, d = index.ntotal, index.d
    logger.info("Reconstructing %d × %d embeddings from FAISS index …", n, d)

    try:
        # Try bulk reconstruction first (fast path for flat indices)
        embeddings = np.empty((n, d), dtype=np.float32)
        index.reconstruct_n(0, n, embeddings)
        logger.info("  Bulk reconstruct_n succeeded.")
        return embeddings
    except Exception:
        pass

    # IVF indices need a direct map
    try:
        logger.info("  Bulk failed — building direct map for IVF index …")
        index.make_direct_map()
        embeddings = np.empty((n, d), dtype=np.float32)
        index.reconstruct_n(0, n, embeddings)
        logger.info("  IVF reconstruct succeeded.")
        return embeddings
    except Exception:
        pass

    # Last resort: reconstruct row by row (slow but always works)
    logger.info("  Falling back to row-by-row reconstruction (slow) …")
    embeddings = np.empty((n, d), dtype=np.float32)
    for i in tqdm(range(n), desc="Reconstructing"):
        embeddings[i] = index.reconstruct(i)
    return embeddings


def compute_isolation_scores(index, embeddings: np.ndarray) -> np.ndarray:
    """
    For every patent, compute its average cosine similarity to its K nearest
    neighbours (excluding itself). Isolation = 1 - mean_sim.

    Patents in dense clusters (many close neighbours) score LOW isolation.
    Patents in sparse regions score HIGH isolation → high novelty.
    """
    n = embeddings.shape[0]
    # L2-normalise so inner product = cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8
    normed = (embeddings / norms).astype(np.float32)

    # Build a temporary flat index for batch search
    tmp_index = faiss.IndexFlatIP(embeddings.shape[1])
    tmp_index.add(normed)

    isolation = np.zeros(n, dtype=np.float32)
    k = _K_NEIGHBOURS + 1  # +1 because result includes self (sim=1.0)

    logger.info("Computing nearest-neighbour isolation scores (batch=%d, k=%d) …",
                _NN_BATCH, _K_NEIGHBOURS)

    for start in tqdm(range(0, n, _NN_BATCH), desc="NN batches"):
        end   = min(start + _NN_BATCH, n)
        batch = normed[start:end]
        sims, _   = tmp_index.search(batch, k)
        # sims shape: (batch, k) — first column is self (1.0), exclude it
        mean_nn_sim = sims[:, 1:].mean(axis=1)   # (batch,)
        isolation[start:end] = 1.0 - mean_nn_sim

    return isolation


def load_metadata_signals(row_to_pid: dict) -> dict:
    """
    Load citation counts and years from patents.csv.
    Returns {patent_id: {"citations": int, "year": int}}.
    """
    csv_candidates = [
        VECTOR_STORE / "patents_deduped.csv",
        ROOT / "patents.csv",
    ]
    df = None
    for p in csv_candidates:
        if p.exists():
            try:
                cols = pd.read_csv(p, nrows=0).columns.tolist()
                usecols = [c for c in ["patent_id", "cited_by_patent_count", "publication_year"]
                           if c in cols]
                df = pd.read_csv(p, usecols=usecols, dtype=str).fillna("0")
                logger.info("Loaded metadata from %s (%d rows)", p, len(df))
                break
            except Exception as exc:
                logger.warning("  Could not load %s: %s", p, exc)

    if df is None or df.empty:
        logger.warning("No patents CSV found — metadata signals unavailable.")
        return {}

    result = {}
    for _, row in df.iterrows():
        pid = row.get("patent_id", "")
        if not pid:
            continue
        try:
            citations = int(float(row.get("cited_by_patent_count", "0") or "0"))
        except ValueError:
            citations = 0
        try:
            year = int(float(row.get("publication_year", "0") or "0"))
        except ValueError:
            year = 0
        result[pid] = {"citations": citations, "year": year}
    return result


def blend_novelty(
    isolation: np.ndarray,
    row_to_pid: dict,
    meta: dict,
) -> dict:
    """
    Blend embedding isolation with recency and inverse citation count.

    Weights:
        60%  Embedding isolation   (structural sparsity in vector space)
        25%  Inverse citation rank (highly cited = well explored = less novel)
        15%  Recency rank          (newer = less explored relative to older art)
    """
    n = len(isolation)
    pids = [row_to_pid.get(i, f"UNKNOWN_{i}") for i in range(n)]

    citations_arr = np.array([meta.get(p, {}).get("citations", 0) for p in pids], dtype=float)
    years_arr     = np.array([meta.get(p, {}).get("year", 0)      for p in pids], dtype=float)

    def percentile_rank(arr: np.ndarray) -> np.ndarray:
        """Return 0-1 rank (0 = lowest value, 1 = highest)."""
        valid = arr[arr > 0]
        if len(valid) == 0:
            return np.full_like(arr, 0.5, dtype=float)
        ranks = np.zeros(len(arr), dtype=float)
        for i, v in enumerate(arr):
            if v <= 0:
                ranks[i] = 0.5
            else:
                ranks[i] = float((valid < v).sum()) / len(valid)
        return ranks

    citation_rank = percentile_rank(citations_arr)  # high citation → high rank
    year_rank     = percentile_rank(years_arr)       # newer → high rank

    inv_citation = 1.0 - citation_rank   # less cited → higher novelty
    recency      = year_rank             # newer → slightly higher novelty

    blended = (
        0.60 * isolation.astype(float) +
        0.25 * inv_citation +
        0.15 * recency
    )

    # Clip and normalise to [0, 1]
    blended = np.clip(blended, 0.0, 1.0)
    lo, hi  = blended.min(), blended.max()
    if hi > lo:
        blended = (blended - lo) / (hi - lo)

    return {pid: round(float(blended[i]), 6) for i, pid in enumerate(pids)}


def main():
    if not _INDEX_FILE.exists():
        logger.error("FAISS index not found at %s. Run build_faiss_index.py first.", _INDEX_FILE)
        sys.exit(1)
    if not _METADATA_FILE.exists():
        logger.error("metadata_mapping.json not found at %s.", _METADATA_FILE)
        sys.exit(1)

    index, row_to_pid = load_index_and_metadata()

    # ── Step 1: Reconstruct embeddings ────────────────────────────────────────
    embeddings = reconstruct_embeddings(index)
    logger.info("Saving node_embeddings.npy → %s", _OUT_EMBEDDINGS)
    np.save(str(_OUT_EMBEDDINGS), embeddings)
    logger.info("  Saved. Shape: %s", embeddings.shape)

    # ── Step 2: Compute isolation novelty scores ───────────────────────────────
    isolation = compute_isolation_scores(index, embeddings)

    # ── Step 3: Blend with metadata signals ───────────────────────────────────
    meta = load_metadata_signals(row_to_pid)
    novelty_scores = blend_novelty(isolation, row_to_pid, meta)

    logger.info("Saving novelty_scores.json → %s", _OUT_NOVELTY)
    with open(_OUT_NOVELTY, "w") as f:
        json.dump(novelty_scores, f)

    vals = list(novelty_scores.values())
    logger.info(
        "  Saved %d scores. Stats: min=%.3f, max=%.3f, mean=%.3f",
        len(vals), min(vals), max(vals), sum(vals) / len(vals),
    )
    logger.info("Done. Restart the API server to pick up the new files.")


if __name__ == "__main__":
    main()
