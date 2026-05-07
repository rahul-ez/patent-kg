"""
Evaluation metrics for the Semantic Retrieval pipeline.

Provides Precision@K, Recall@K, and a convenience runner that
computes average metrics over a set of test queries with known
ground-truth relevant documents.

Usage:
    from retrieval.evaluate import precision_at_k, recall_at_k, evaluate_search
"""

import logging
from typing import Dict, List, Set

import numpy as np

from retrieval.search import search

logger = logging.getLogger(__name__)


# -- Core Metrics --------------------------------------------------


def precision_at_k(
    relevant_indices: Set[int],
    retrieved_indices: List[int],
    k: int,
) -> float:
    """Compute Precision@K.

    Precision@K = |relevant intersection retrieved_top_k| / k

    Parameters
    ----------
    relevant_indices : Set[int]
        Set of corpus indices that are truly relevant.
    retrieved_indices : List[int]
        Ordered list of corpus indices returned by the search
        (best match first).
    k : int
        Cut-off rank.

    Returns
    -------
    float
        Precision score in [0.0, 1.0].
    """
    if k <= 0:
        logger.warning("k must be > 0 for precision_at_k; returning 0.0")
        return 0.0

    top_k = set(retrieved_indices[:k])
    hits = top_k & relevant_indices
    score = len(hits) / k

    logger.debug(
        "Precision@%d: %d hit(s) out of %d retrieved -> %.4f",
        k, len(hits), k, score,
    )
    return score


def recall_at_k(
    relevant_indices: Set[int],
    retrieved_indices: List[int],
    k: int,
) -> float:
    """Compute Recall@K.

    Recall@K = |relevant intersection retrieved_top_k| / |relevant|

    Parameters
    ----------
    relevant_indices : Set[int]
        Set of corpus indices that are truly relevant.
    retrieved_indices : List[int]
        Ordered list of corpus indices returned by the search.
    k : int
        Cut-off rank.

    Returns
    -------
    float
        Recall score in [0.0, 1.0].  Returns 0.0 when
        *relevant_indices* is empty.
    """
    if not relevant_indices:
        logger.warning("No relevant items defined; recall is 0.0")
        return 0.0

    if k <= 0:
        logger.warning("k must be > 0 for recall_at_k; returning 0.0")
        return 0.0

    top_k = set(retrieved_indices[:k])
    hits = top_k & relevant_indices
    score = len(hits) / len(relevant_indices)

    logger.debug(
        "Recall@%d: %d hit(s) out of %d relevant -> %.4f",
        k, len(hits), len(relevant_indices), score,
    )
    return score


# -- Evaluation Runner ---------------------------------------------


def evaluate_search(
    test_queries: List[str],
    ground_truth: Dict[str, List[int]],
    embeddings: np.ndarray,
    texts: List[str],
    k: int = 5,
) -> Dict[str, float]:
    """Run evaluation across multiple queries and return average metrics.

    Parameters
    ----------
    test_queries : List[str]
        Queries to evaluate.
    ground_truth : Dict[str, List[int]]
        Mapping of each query string to a list of relevant corpus
        indices (0-based).
    embeddings : np.ndarray
        Pre-computed patent embeddings of shape `(n, dim)`.
    texts : List[str]
        Patent texts aligned with *embeddings*.
    k : int, optional
        Cut-off rank used for both Precision and Recall (default 5).

    Returns
    -------
    Dict[str, float]
        Dictionary with keys `avg_precision_at_k`, `avg_recall_at_k`,
        and per-query breakdowns under `details`.
    """
    precisions: List[float] = []
    recalls: List[float] = []
    details: List[Dict] = []

    for query in test_queries:
        if query not in ground_truth:
            logger.warning(
                "No ground truth for query '%s' -- skipping.", query[:60]
            )
            continue

        relevant = set(ground_truth[query])

        # Run semantic search
        results = search(
            query=query,
            embeddings=embeddings,
            texts=texts,
            top_k=k,
        )

        # Map results back to corpus indices
        retrieved_indices: List[int] = []
        for r in results:
            try:
                idx = texts.index(r["text"])
                retrieved_indices.append(idx)
            except ValueError:
                pass  # text not in corpus (shouldn't happen)

        p = precision_at_k(relevant, retrieved_indices, k)
        r_val = recall_at_k(relevant, retrieved_indices, k)

        precisions.append(p)
        recalls.append(r_val)
        details.append({
            "query": query,
            "precision_at_k": round(p, 4),
            "recall_at_k": round(r_val, 4),
            "retrieved_indices": retrieved_indices,
            "relevant_indices": sorted(relevant),
        })

        logger.info(
            "Query='%s...'  P@%d=%.4f  R@%d=%.4f",
            query[:40], k, p, k, r_val,
        )

    avg_p = round(sum(precisions) / len(precisions), 4) if precisions else 0.0
    avg_r = round(sum(recalls) / len(recalls), 4) if recalls else 0.0

    logger.info(
        "Evaluation complete -- Avg P@%d=%.4f  Avg R@%d=%.4f",
        k, avg_p, k, avg_r,
    )

    return {
        "k": k,
        "avg_precision_at_k": avg_p,
        "avg_recall_at_k": avg_r,
        "num_queries": len(precisions),
        "details": details,
    }
