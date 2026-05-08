"""
Integration layer: bridges NLP preprocessing and semantic retrieval.

Exports:
    run_end_to_end      - Full pipeline: idea text → top-k patents
    faiss_search        - Direct FAISS search with an already-embedded query
    prepare_retrieval_query - Extract symmetric embedding query from NLPResult
"""

from .pipeline import run_end_to_end, faiss_search, prepare_retrieval_query

__all__ = ["run_end_to_end", "faiss_search", "prepare_retrieval_query"]
