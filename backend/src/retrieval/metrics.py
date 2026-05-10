"""
Reusable metrics for Information Retrieval (IR) evaluation.
"""

from typing import List, Set, Any

def precision_at_k(relevant_ids: Set[Any], retrieved_ids: List[Any], k: int) -> float:
    """Compute Precision@K."""
    if k <= 0:
        return 0.0
    top_k = set(retrieved_ids[:k])
    hits = top_k & relevant_ids
    return len(hits) / k

def recall_at_k(relevant_ids: Set[Any], retrieved_ids: List[Any], k: int) -> float:
    """Compute Recall@K."""
    if not relevant_ids or k <= 0:
        return 0.0
    top_k = set(retrieved_ids[:k])
    hits = top_k & relevant_ids
    return len(hits) / len(relevant_ids)

def hit_at_k(relevant_ids: Set[Any], retrieved_ids: List[Any], k: int) -> int:
    """Compute Hit@K (1 if any relevant item is in top K, else 0)."""
    if k <= 0:
        return 0
    top_k = set(retrieved_ids[:k])
    return 1 if top_k & relevant_ids else 0

def mrr_at_k(relevant_ids: Set[Any], retrieved_ids: List[Any], k: int) -> float:
    """Compute Mean Reciprocal Rank (MRR) at K."""
    if k <= 0:
        return 0.0
    
    for rank, ret_id in enumerate(retrieved_ids[:k], start=1):
        if ret_id in relevant_ids:
            return 1.0 / rank
    return 0.0

def average_similarity_of_relevant(relevant_ids: Set[Any], retrieved_ids: List[Any], scores: List[float], k: int) -> float:
    """Compute average similarity score of relevant items found in top K."""
    relevant_scores = []
    for ret_id, score in zip(retrieved_ids[:k], scores[:k]):
        if ret_id in relevant_ids:
            relevant_scores.append(score)
            
    if not relevant_scores:
        return 0.0
    return sum(relevant_scores) / len(relevant_scores)
