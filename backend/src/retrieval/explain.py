"""
Explainability layer for the Semantic Retrieval pipeline.

Provides lightweight, keyword-overlap-based explanations for WHY
a particular patent was retrieved for a given query.  No heavy NLP
libraries are required -- tokenisation and stop-word filtering are
done with pure Python.

Usage:
    from retrieval.explain import generate_explanation, get_overlap
"""

import logging
import re
from typing import List, Set

logger = logging.getLogger(__name__)

# -- Stopwords -----------------------------------------------------
# A compact English stop-word list sufficient for keyword-overlap
# explanations.  Intentionally kept small so domain terms like
# "system", "method", "device" are NOT filtered (they carry meaning
# in patent text).

_STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "if", "in", "on", "at",
    "to", "for", "of", "with", "by", "from", "as", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "shall", "should", "may",
    "might", "can", "could", "not", "no", "nor", "so", "yet",
    "both", "each", "few", "more", "most", "other", "some", "such",
    "than", "too", "very", "just", "also", "into", "over", "under",
    "about", "up", "out", "off", "then", "once", "here", "there",
    "when", "where", "why", "how", "all", "any", "its", "it",
    "this", "that", "these", "those", "their", "our", "your",
    "which", "what", "who", "whom", "while", "during", "before",
    "after", "between", "through", "above", "below", "using",
}


# -- Helpers -------------------------------------------------------


def _tokenize(text: str) -> List[str]:
    """Lowercase and split text into alpha-numeric tokens.

    Parameters
    ----------
    text : str
        Raw input text.

    Returns
    -------
    List[str]
        Cleaned token list (lowercase, non-empty, len > 1).
    """
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if len(t) > 1]


def extract_keywords(text: str) -> Set[str]:
    """Extract meaningful keywords from *text*.

    Steps:
        1. Tokenise (lowercase, alphanumeric only)
        2. Remove stop-words
        3. Return unique keyword set

    Parameters
    ----------
    text : str
        Input text (query or patent abstract).

    Returns
    -------
    Set[str]
        Set of lowercase keywords.
    """
    tokens = _tokenize(text)
    keywords = {t for t in tokens if t not in _STOPWORDS}
    return keywords


# -- Core Functions ------------------------------------------------


def get_overlap(query: str, text: str) -> Set[str]:
    """Compute the keyword overlap between *query* and *text*.

    Parameters
    ----------
    query : str
        User query or idea description.
    text : str
        Patent text (title + abstract).

    Returns
    -------
    Set[str]
        Common keywords appearing in both inputs.
    """
    query_kw = extract_keywords(query)
    text_kw = extract_keywords(text)
    common = query_kw & text_kw

    logger.debug(
        "Overlap: %d query kw, %d text kw, %d common",
        len(query_kw), len(text_kw), len(common),
    )
    return common


def generate_explanation(query: str, text: str) -> str:
    """Produce a human-readable explanation for a search match.

    Parameters
    ----------
    query : str
        User query or idea description.
    text : str
        Patent text that was retrieved.

    Returns
    -------
    str
        Explanation string, e.g.
        `"Matched based on terms: drone, navigation, AI"`
        or a fallback if no keyword overlap exists.
    """
    common = get_overlap(query, text)

    if not common:
        return "Matched based on overall semantic similarity (no direct keyword overlap)."

    # Sort for deterministic output
    sorted_terms = sorted(common)
    terms_str = ", ".join(sorted_terms)
    return f"Matched based on terms: {terms_str}"
