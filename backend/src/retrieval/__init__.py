"""
Semantic Retrieval Module for Graph-Enhanced Patent Intelligence Platform.

This module provides:
- Patent text embedding via SentenceTransformers
- NumPy-based vector storage (save/load)
- Cosine-similarity-based semantic search
- Evaluation metrics (Precision@K, Recall@K)
- Explainability layer (keyword-overlap explanations)

Usage:
    from retrieval.embed import get_embeddings
    from retrieval.vector_store import save_embeddings, load_embeddings
    from retrieval.search import search
    from retrieval.evaluate import precision_at_k, recall_at_k, evaluate_search
    from retrieval.explain import generate_explanation, get_overlap
"""

from retrieval.embed import get_embeddings
from retrieval.vector_store import save_embeddings, load_embeddings
from retrieval.search import search
from retrieval.evaluate import precision_at_k, recall_at_k, evaluate_search
from retrieval.explain import generate_explanation, get_overlap

__all__ = [
    "get_embeddings",
    "save_embeddings",
    "load_embeddings",
    "search",
    "precision_at_k",
    "recall_at_k",
    "evaluate_search",
    "generate_explanation",
    "get_overlap",
]
