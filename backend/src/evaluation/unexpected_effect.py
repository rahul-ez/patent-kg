"""Score optional, quantitative unexpected-effect evidence with Gemini."""
from __future__ import annotations

import json
import logging
from typing import List

from .per_concept_search import ConceptSearchResult

logger = logging.getLogger(__name__)


def score_unexpected_effect(user_idea: str, results: List[ConceptSearchResult]) -> dict:
    if not user_idea or not user_idea.strip():
        return _default("No idea text provided")
    prior_art = "\n".join(f"- {hit.title}" for result in results for hit in result.hits[:2] if hit.title) or "Not available"
    try:
        from .gemini_client import get_gemini_client

        client = get_gemini_client()
        if client is None:
            return _default("Gemini unavailable")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=("Identify a quantitative performance claim in this invention and whether it is surprising against the prior art. "
                      "Return only JSON: has_quantitative_claim, claimed_metric, is_surprising, reason.\n"
                      f"Invention: {user_idea}\nPrior art:\n{prior_art}"),
            config={"response_mime_type": "application/json"},
        )
        data = json.loads(response.text or "{}")
    except Exception as exc:
        logger.warning("Unexpected-effect analysis unavailable: %s", exc)
        return _default(str(exc))

    has_claim = bool(data.get("has_quantitative_claim", False))
    surprising = data.get("is_surprising")
    score = 0.15 if has_claim and surprising is True else 0.05 if has_claim else 0.0
    return {
        "score": score, "has_quantitative_claim": has_claim,
        "claimed_metric": data.get("claimed_metric"), "is_surprising": surprising,
        "reason": data.get("reason", ""),
        "interpretation": "Unexpected effect detected" if score == 0.15 else "Quantitative claim requires evidence" if has_claim else "No quantitative performance claim found",
    }


def _default(reason: str = "") -> dict:
    return {"score": 0.0, "has_quantitative_claim": False, "claimed_metric": None,
            "is_surprising": None, "reason": reason, "interpretation": "Unexpected-effect analysis unavailable"}
