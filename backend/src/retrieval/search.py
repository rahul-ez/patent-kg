"""
Semantic search module for the Retrieval pipeline.

Given a natural-language query, encodes it into an embedding and
ranks stored patent texts by cosine similarity.
"""

import logging
from typing import List, TypedDict

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from retrieval.embed import get_embeddings
from retrieval.explain import generate_explanation

logger = logging.getLogger(__name__)


class SearchResult(TypedDict):
    """Schema for a single search hit."""

    rank: int
    text: str
    semantic_score: float  # normalised cosine similarity ∈ [0, 1]
    explanation: str    # human-readable reason for the match


def search(
    query: str,
    embeddings: np.ndarray,
    texts: List[str],
    top_k: int = 5,
) -> List[SearchResult]:
    """Return the *top_k* most semantically similar patents.

    Parameters
    ----------
    query : str
        User query or idea description.
    embeddings : np.ndarray
        Pre-computed patent embeddings of shape ``(n, dim)``.
    texts : List[str]
        Patent texts aligned with *embeddings*.
    top_k : int, optional
        Number of results to return (default ``5``).

    Returns
    -------
    List[SearchResult]
        Ranked list of dicts with keys ``rank``, ``text``, ``score``,
        and ``explanation``.  Scores are normalised to the ``[0, 1]``
        range.

    Raises
    ------
    ValueError
        If *query* is empty or *embeddings* / *texts* are mismatched.
    """
    # ── Input validation ──────────────────────────────────────────
    if not query or not query.strip():
        raise ValueError("Query must be a non-empty string.")

    if len(embeddings) == 0 or len(texts) == 0:
        logger.warning("Empty corpus – returning no results.")
        return []

    if len(embeddings) != len(texts):
        raise ValueError(
            f"Length mismatch: embeddings ({len(embeddings)}) "
            f"vs texts ({len(texts)})."
        )

    # ── Encode query ──────────────────────────────────────────────
    query_embedding: np.ndarray = get_embeddings([query])  # shape (1, dim)

    # ── Compute cosine similarity ─────────────────────────────────
    similarities: np.ndarray = cosine_similarity(
        query_embedding, embeddings
    ).flatten()  # shape (n,)

    # Normalise scores to [0, 1]  (cosine similarity is already in
    # [-1, 1] for unit-normed vectors, but sentence-transformers
    # outputs are not always perfectly normed).
    min_score = similarities.min()
    max_score = similarities.max()
    if max_score - min_score > 0:
        normalised = (similarities - min_score) / (max_score - min_score)
    else:
        normalised = np.ones_like(similarities)

    # ── Rank and collect top-k ────────────────────────────────────
    effective_k = min(top_k, len(texts))
    top_indices = np.argsort(normalised)[::-1][:effective_k]

    results: List[SearchResult] = []
    for rank, idx in enumerate(top_indices, start=1):
        explanation = generate_explanation(query, texts[idx])
        results.append(
            SearchResult(
                rank=rank,
                text=texts[idx],
                semantic_score=round(float(normalised[idx]), 4),
                explanation=explanation,
            )
        )

    logger.info(
        "Search complete - query='%s...' -> %d result(s)",
        query[:60],
        len(results),
    )
    return results
