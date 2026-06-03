"""
Embedding module for the Semantic Retrieval pipeline.

Uses SentenceTransformers (AI-Growth-Lab/PatentSBERTa) to convert patent texts
into dense vector embeddings suitable for cosine-similarity search.
"""

import logging
import os
from typing import List

# Suppress TF/Keras import in transformers (Keras 3 is incompatible).
# Must be set before sentence_transformers is imported.
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_TORCH", "1")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level model cache – avoids reloading on every call
# ---------------------------------------------------------------------------
_MODEL_NAME: str = "AI-Growth-Lab/PatentSBERTa"
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Return a cached SentenceTransformer model instance."""
    global _model
    if _model is None:
        logger.info("Loading SentenceTransformer model '%s' …", _MODEL_NAME)
        _model = SentenceTransformer(_MODEL_NAME)
        logger.info("Model loaded successfully.")
    return _model


def get_embeddings(texts: List[str]) -> np.ndarray:
    """Encode a list of texts into dense embeddings.

    Parameters
    ----------
    texts : List[str]
        Patent texts to embed.  Each element is typically
        ``title + " " + abstract``.

    Returns
    -------
    np.ndarray
        2-D array of shape ``(len(texts), embedding_dim)`` with
        float32 embeddings.  Returns an empty array of shape
        ``(0, 768)`` when *texts* is empty.

    Raises
    ------
    ValueError
        If *texts* is ``None``.
    """
    if texts is None:
        raise ValueError("'texts' must be a list of strings, got None.")

    if len(texts) == 0:
        logger.warning("Empty text list received – returning empty embeddings.")
        return np.empty((0, 768), dtype=np.float32)

    # Filter out blank / whitespace-only entries while keeping indices
    cleaned: List[str] = [t if t.strip() else "" for t in texts]
    blank_count = sum(1 for t in cleaned if t == "")
    if blank_count:
        logger.warning(
            "%d blank text(s) detected – they will produce near-zero embeddings.",
            blank_count,
        )

    model = _get_model()
    embeddings: np.ndarray = model.encode(cleaned, show_progress_bar=False)
    logger.info(
        "Generated embeddings for %d text(s). Shape: %s",
        len(cleaned),
        embeddings.shape,
    )
    return embeddings
