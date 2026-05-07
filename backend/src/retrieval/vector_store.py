"""
Vector storage module for the Semantic Retrieval pipeline.

Provides simple NumPy-based persistence so embeddings can be
computed once and reused across sessions without a database.
"""

import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Default directory used when the caller doesn't specify a path.
_DEFAULT_DIR: str = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "embeddings"
)
_EMBEDDINGS_FILE: str = "patent_embeddings.npy"
_TEXTS_FILE: str = "patent_texts.npy"


def save_embeddings(
    embeddings: np.ndarray,
    texts: list[str],
    directory: Optional[str] = None,
) -> str:
    """Persist embeddings and their source texts to disk.

    Parameters
    ----------
    embeddings : np.ndarray
        2-D float array of shape ``(n, dim)``.
    texts : list[str]
        The original texts corresponding to each row in *embeddings*.
    directory : str, optional
        Folder to save into.  Defaults to
        ``backend/data/embeddings/``.

    Returns
    -------
    str
        Absolute path of the directory where files were saved.

    Raises
    ------
    ValueError
        If *embeddings* and *texts* lengths do not match.
    """
    if len(embeddings) != len(texts):
        raise ValueError(
            f"Length mismatch: embeddings ({len(embeddings)}) vs texts ({len(texts)})."
        )

    save_dir = Path(directory or _DEFAULT_DIR).resolve()
    save_dir.mkdir(parents=True, exist_ok=True)

    emb_path = save_dir / _EMBEDDINGS_FILE
    txt_path = save_dir / _TEXTS_FILE

    np.save(str(emb_path), embeddings)
    np.save(str(txt_path), np.array(texts, dtype=object))

    logger.info(
        "Saved %d embeddings (%s) to %s",
        len(embeddings),
        embeddings.shape,
        save_dir,
    )
    return str(save_dir)


def load_embeddings(
    directory: Optional[str] = None,
) -> tuple[np.ndarray, list[str]]:
    """Load previously saved embeddings and texts from disk.

    Parameters
    ----------
    directory : str, optional
        Folder to load from.  Defaults to
        ``backend/data/embeddings/``.

    Returns
    -------
    tuple[np.ndarray, list[str]]
        ``(embeddings, texts)`` where *embeddings* has shape
        ``(n, dim)`` and *texts* is a list of *n* strings.

    Raises
    ------
    FileNotFoundError
        If the expected files do not exist in *directory*.
    """
    load_dir = Path(directory or _DEFAULT_DIR).resolve()

    emb_path = load_dir / _EMBEDDINGS_FILE
    txt_path = load_dir / _TEXTS_FILE

    if not emb_path.exists() or not txt_path.exists():
        raise FileNotFoundError(
            f"Embedding files not found in '{load_dir}'. "
            "Run embedding generation first."
        )

    embeddings: np.ndarray = np.load(str(emb_path))
    texts: list[str] = np.load(str(txt_path), allow_pickle=True).tolist()

    logger.info(
        "Loaded %d embeddings (%s) from %s",
        len(embeddings),
        embeddings.shape,
        load_dir,
    )
    return embeddings, texts
