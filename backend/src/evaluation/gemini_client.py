"""Shared, optional Gemini client for evaluation sub-scorers."""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)
_client: Any | None = None
_initialised = False


def get_gemini_client() -> Any | None:
    """Return a cached current-SDK client, or ``None`` when Gemini is unavailable."""
    global _client, _initialised
    if _initialised:
        return _client

    _initialised = True
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("GOOGLE_API_KEY is not configured; evaluation will use fallbacks.")
        return None
    try:
        from google import genai

        _client = genai.Client(api_key=api_key)
    except ImportError:
        logger.warning("google-genai is not installed; evaluation will use fallbacks.")
    except Exception as exc:
        logger.warning("Gemini client initialisation failed: %s", exc)
    return _client
