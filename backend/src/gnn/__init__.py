# backend/src/gnn/__init__.py
from .scorer import get_scorer, load_novelty_scorer

__all__ = ["get_scorer", "load_novelty_scorer"]
