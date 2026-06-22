"""
Reconstruction Difficulty Tester
==================================
Given only the prior art, how often does an AI independently arrive at the
user's invention?

High reconstruction rate → predictable from prior art → obvious.
Low reconstruction rate → requires insight beyond prior art → non-obvious.

Gemini generates N independent solutions; each is compared to the user's idea
using PatentSBERTa cosine similarity. Reconstruction rate = fraction above threshold.

N defaults to 10 to keep API costs low. Increase for higher confidence.
"""

import logging
import os
from typing import List

import numpy as np
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

from .per_concept_search import ConceptSearchResult


def _prior_art_summary(results: List[ConceptSearchResult]) -> str:
    lines = []
    for r in results:
        lines.append(f"Area: {r.concept.label}")
        for h in r.hits[:2]:
            if h.title:
                lines.append(f"  - {h.title} ({h.publication_year})")
    return "\n".join(lines)


def _generate_solution(model, prior_art: str, problem: str) -> str:
    try:
        prompt = (
            f"You are a skilled engineer with access ONLY to this prior art:\n\n"
            f"{prior_art}\n\n"
            f"Problem: {problem}\n\n"
            f"Propose a specific technical solution using ONLY the above prior art. "
            f"One paragraph, be specific about the mechanism."
        )
        return model.generate_content(prompt).text.strip()
    except Exception:
        return ""


def _semantic_similarity(generated: str, invention: str) -> float:
    if not generated or not invention:
        return 0.0
    try:
        import faiss as faiss_lib
        from integration.pipeline import _get_model
        model = _get_model()
        vecs = model.encode([generated, invention], convert_to_numpy=True).astype("float32")
        faiss_lib.normalize_L2(vecs)
        return float(np.dot(vecs[0], vecs[1]))
    except Exception:
        return 0.0


def score_reconstruction_difficulty(
    results: List[ConceptSearchResult],
    user_idea: str,
    n_samples: int = 10,
    threshold: float = 0.75,
) -> dict:
    """
    Parameters
    ----------
    results    : concept search results (provides prior art context)
    user_idea  : original user idea (used only for similarity comparison)
    n_samples  : number of Gemini generation attempts (default 10)
    threshold  : cosine similarity above which generation counts as "reconstructed"

    Returns
    -------
    dict: score (0–1), reconstruction_rate, n_samples, n_reconstructed,
          avg_similarity, interpretation
    """
    try:
        import google.generativeai as genai
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
    except Exception as exc:
        logger.warning("Gemini unavailable for reconstruction test (%s).", exc)
        return _default()

    prior_art = _prior_art_summary(results)
    problem   = "Solve: " + " AND ".join(r.concept.description for r in results[:3])

    logger.info("Reconstruction test: %d samples ...", n_samples)

    sims: List[float] = []
    reconstructed = 0

    for i in range(n_samples):
        generated = _generate_solution(model, prior_art, problem)
        sim = _semantic_similarity(generated, user_idea)
        sims.append(sim)
        if sim >= threshold:
            reconstructed += 1
        logger.debug("  Sample %d: sim=%.4f", i + 1, sim)

    rate        = reconstructed / n_samples
    avg_sim     = float(np.mean(sims)) if sims else 0.0
    score       = 1.0 - rate   # low reconstruction = high non-obviousness

    if score >= 0.85:
        interp = f"Rarely reconstructed ({reconstructed}/{n_samples}) — strongly non-obvious"
    elif score >= 0.60:
        interp = f"Moderately difficult to reconstruct ({reconstructed}/{n_samples})"
    else:
        interp = f"Frequently reconstructed ({reconstructed}/{n_samples}) — likely obvious from prior art"

    logger.info(
        "Reconstruction: score=%.3f, rate=%.2f (%d/%d), avg_sim=%.4f",
        score, rate, reconstructed, n_samples, avg_sim,
    )

    return {
        "score":               round(score, 4),
        "reconstruction_rate": round(rate, 4),
        "n_samples":           n_samples,
        "n_reconstructed":     reconstructed,
        "avg_similarity":      round(avg_sim, 4),
        "threshold":           threshold,
        "interpretation":      interp,
    }


def _default() -> dict:
    return {
        "score":               0.5,
        "reconstruction_rate": None,
        "n_samples":           0,
        "n_reconstructed":     0,
        "avg_similarity":      None,
        "threshold":           0.75,
        "interpretation":      "Reconstruction test unavailable (Gemini offline)",
    }
