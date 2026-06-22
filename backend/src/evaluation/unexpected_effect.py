"""
Unexpected Effect Scorer
=========================
If the invention claims a quantitative performance improvement that would
surprise a skilled engineer given the prior art, this is strong secondary
consideration evidence of non-obviousness (Graham v. John Deere).

Score: 0.0 if no quantitative claim found (neutral), up to 0.15 bonus.
"""

import json
import logging
import os
from typing import List

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

from .per_concept_search import ConceptSearchResult


def score_unexpected_effect(
    user_idea: str,
    results: List[ConceptSearchResult],
) -> dict:
    """
    Returns
    -------
    dict: score (0–0.15 bonus), has_quantitative_claim, claimed_metric,
          is_surprising, reason, interpretation
    """
    if not user_idea or not user_idea.strip():
        return _default("No idea text provided")

    try:
        import google.generativeai as genai
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
    except Exception as exc:
        logger.warning("Gemini unavailable for unexpected effect (%s).", exc)
        return _default("Gemini unavailable")

    prior_art_titles = [
        h.title for r in results for h in r.hits[:2] if h.title
    ][:6]
    prior_art_ctx = "\n".join(f"- {t}" for t in prior_art_titles) or "Not available"

    prompt = f"""You are a patent examiner assessing unexpected technical effects.

Invention idea:
"{user_idea}"

Relevant prior art:
{prior_art_ctx}

1. Does the idea contain a specific quantitative performance claim?
   (e.g. "improves accuracy by 40%", "reduces latency by 3×", "2× energy savings")
2. If yes, would this magnitude of improvement be SURPRISING to a skilled engineer?

Return ONLY this JSON:
{{
  "has_quantitative_claim": true or false,
  "claimed_metric": "description of the metric or null",
  "is_surprising": true or false or null,
  "reason": "one sentence explanation"
}}"""

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
            ),
        )
        data         = json.loads(response.text)
        has_claim    = data.get("has_quantitative_claim", False)
        claimed      = data.get("claimed_metric")
        surprising   = data.get("is_surprising")
        reason       = data.get("reason", "")

        if has_claim and surprising is True:
            score  = 0.15
            interp = f"Unexpected effect detected: {claimed}"
        elif has_claim and surprising is False:
            score  = 0.0
            interp = f"Quantitative claim found but expected given prior art: {claimed}"
        elif has_claim:
            score  = 0.05
            interp = f"Quantitative claim present, surprise level uncertain: {claimed}"
        else:
            score  = 0.0
            interp = "No quantitative performance claim found — neutral"

        logger.info("Unexpected effect: score=%.3f, claim=%s, surprising=%s", score, claimed, surprising)

        return {
            "score":                  round(score, 4),
            "has_quantitative_claim": has_claim,
            "claimed_metric":         claimed,
            "is_surprising":          surprising,
            "reason":                 reason,
            "interpretation":         interp,
        }

    except Exception as exc:
        logger.warning("Unexpected effect analysis failed (%s).", exc)
        return _default(str(exc))


def _default(reason: str = "") -> dict:
    return {
        "score":                  0.0,
        "has_quantitative_claim": False,
        "claimed_metric":         None,
        "is_surprising":          None,
        "reason":                 reason,
        "interpretation":         "Unexpected effect analysis not available",
    }
