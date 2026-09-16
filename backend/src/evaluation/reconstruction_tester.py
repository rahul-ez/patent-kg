"""Test whether an LLM can reconstruct an idea from retrieved prior art."""
from __future__ import annotations

import logging
from typing import List

import numpy as np

from .per_concept_search import ConceptSearchResult

logger = logging.getLogger(__name__)


def _prior_art_summary(results: List[ConceptSearchResult]) -> str:
    return "\n".join(
        f"{result.concept.label}: " + "; ".join(hit.title for hit in result.hits[:2] if hit.title)
        for result in results
    )


def _semantic_similarity(generated: str, invention: str) -> float:
    if not generated or not invention:
        return 0.0
    try:
        import faiss
        from integration.pipeline import _get_model

        vectors = _get_model().encode([generated, invention], convert_to_numpy=True).astype("float32")
        faiss.normalize_L2(vectors)
        return float(np.dot(vectors[0], vectors[1]))
    except Exception as exc:
        logger.warning("Reconstruction similarity unavailable: %s", exc)
        return 0.0


def score_reconstruction_difficulty(
    results: List[ConceptSearchResult], user_idea: str, n_samples: int = 10, threshold: float = 0.75,
) -> dict:
    try:
        from .gemini_client import get_gemini_client

        client = get_gemini_client()
        if client is None:
            return _default()
        prior_art = _prior_art_summary(results)
        problem = " AND ".join(result.concept.description for result in results[:3])
        similarities = []
        for _ in range(n_samples):
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Using only this prior art, propose a technical solution.\nPrior art:\n{prior_art}\nProblem: {problem}",
            )
            similarities.append(_semantic_similarity(response.text or "", user_idea))
    except Exception as exc:
        logger.warning("Reconstruction test unavailable: %s", exc)
        return _default()

    reconstructed = sum(score >= threshold for score in similarities)
    rate = reconstructed / n_samples
    score = 1.0 - rate
    return {
        "score": round(score, 4), "reconstruction_rate": round(rate, 4),
        "n_samples": n_samples, "n_reconstructed": reconstructed,
        "avg_similarity": round(float(np.mean(similarities)), 4), "threshold": threshold,
        "interpretation": "Rarely reconstructed" if score >= 0.85 else "Moderately difficult to reconstruct" if score >= 0.60 else "Frequently reconstructed",
    }


def _default() -> dict:
    return {"score": 0.5, "reconstruction_rate": None, "n_samples": 0, "n_reconstructed": 0,
            "avg_similarity": None, "threshold": 0.75, "interpretation": "Reconstruction test unavailable"}
