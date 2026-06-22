"""
Concept Extractor
=================
Decomposes a user's invention idea into atomic technical concepts using Gemini.

Each concept is the smallest independently searchable technical unit of the idea.
The output drives all non-obviousness sub-scorers: each concept is searched
separately in FAISS, and the relationships between concept clusters are what
the combination difficulty, motivation, and isolation scorers measure.

Usage:
    from evaluation.concept_extractor import extract_concepts

    concepts = extract_concepts("Use an LLM to generate SQL and validate against a schema graph")
    # [
    #   Concept(label="LLM query generation", description="...", domain_hint="AI"),
    #   Concept(label="schema graph representation", description="...", domain_hint="AI"),
    #   Concept(label="pre-execution validation layer", description="...", domain_hint="AI"),
    # ]
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Gemini client ──────────────────────────────────────────────────────────────
# Uses google-generativeai (legacy SDK) which is what the project has installed.
_gemini_model = None

def _get_gemini_model():
    global _gemini_model
    if _gemini_model is not None:
        return _gemini_model
    try:
        import google.generativeai as genai
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY not set — concept extraction will use fallback.")
            return None
        genai.configure(api_key=api_key)
        _gemini_model = genai.GenerativeModel("gemini-2.5-flash")
        logger.info("Gemini model initialised for concept extractor.")
        return _gemini_model
    except ImportError:
        logger.warning("google-generativeai not installed — concept extraction will use fallback.")
        return None


# ── Data model ─────────────────────────────────────────────────────────────────

@dataclass
class Concept:
    """A single atomic technical concept extracted from an invention idea."""
    label: str          # short phrase: "EEG signal processing"
    description: str    # one sentence explaining the concept
    domain_hint: str    # AI | Medical | IoT | Automotive | Energy | Mechanical | General


# ── Prompts ────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a patent analysis expert who decomposes invention ideas into
their smallest independently patentable technical concepts.

Rules for decomposition:
- Extract between 3 and 7 concepts. Never fewer than 3, never more than 7.
- Each concept must be a standalone technical contribution — something that could
  appear as its own claim in a patent application.
- Do not include business goals, user outcomes, or market applications as concepts.
  Focus only on technical mechanisms.
- If a concept is a well-known existing technology used as-is (e.g. "HTTPS"), still
  include it — downstream steps need it to measure combination difficulty.
- The label must be a 2-6 word noun phrase (no verbs, no articles at the start).
- The domain_hint must be one of: AI, Medical, IoT, Automotive, Energy, Mechanical, General.

Return ONLY valid JSON — no markdown, no explanation."""

_USER_PROMPT_TEMPLATE = """Decompose this invention idea into atomic technical concepts:

IDEA: "{idea}"

Return this exact JSON structure:
{{
  "concepts": [
    {{
      "label": "short noun phrase",
      "description": "one sentence explaining the technical mechanism",
      "domain_hint": "one of AI | Medical | IoT | Automotive | Energy | Mechanical | General"
    }}
  ]
}}"""


# ── Main function ──────────────────────────────────────────────────────────────

def extract_concepts(idea: str) -> List[Concept]:
    """
    Decompose a user's invention idea into atomic technical concepts.

    Parameters
    ----------
    idea : str
        The raw invention idea in plain English.

    Returns
    -------
    List[Concept]
        3–7 Concept objects. Falls back to keyword-based extraction if Gemini
        is unavailable, so this function never raises.
    """
    if not idea or not idea.strip():
        raise ValueError("Idea string is empty.")

    model = _get_gemini_model()
    if model is None:
        logger.warning("Gemini unavailable — using keyword fallback for concept extraction.")
        return _keyword_fallback(idea)

    try:
        import google.generativeai as genai

        prompt = f"{_SYSTEM_PROMPT}\n\n{_USER_PROMPT_TEMPLATE.format(idea=idea.strip())}"
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
            ),
        )

        raw = response.text.strip()
        data = json.loads(raw)
        raw_concepts = data.get("concepts", [])

        if not raw_concepts:
            logger.warning("Gemini returned empty concept list — using keyword fallback.")
            return _keyword_fallback(idea)

        concepts = []
        for item in raw_concepts:
            label = str(item.get("label", "")).strip()
            desc  = str(item.get("description", "")).strip()
            hint  = str(item.get("domain_hint", "General")).strip()
            if label:
                concepts.append(Concept(label=label, description=desc, domain_hint=hint))

        logger.info("Extracted %d concepts from idea.", len(concepts))
        for c in concepts:
            logger.info("  [%s] %s — %s", c.domain_hint, c.label, c.description[:60])

        return concepts

    except Exception as exc:
        logger.error("Gemini concept extraction failed (%s) — using keyword fallback.", exc)
        return _keyword_fallback(idea)


# ── Keyword fallback ───────────────────────────────────────────────────────────

def _keyword_fallback(idea: str) -> List[Concept]:
    """
    Lightweight fallback when Gemini is unavailable.
    Uses the existing spaCy NLP pipeline to extract noun chunks and wraps
    them as Concept objects. Lower quality than Gemini but never crashes.
    """
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(idea)

        # Collect noun chunks, deduplicate, filter short ones
        seen = set()
        concepts = []
        for chunk in doc.noun_chunks:
            text = chunk.text.lower().strip()
            if len(text.split()) < 2 or text in seen:
                continue
            seen.add(text)
            concepts.append(Concept(
                label=text,
                description=f"Technical concept derived from noun chunk: '{text}'",
                domain_hint="General",
            ))
            if len(concepts) >= 6:
                break

        if len(concepts) < 3:
            # Last resort: split into 3-word windows
            words = idea.lower().split()
            for i in range(0, min(len(words) - 2, 9), 3):
                label = " ".join(words[i:i+3])
                concepts.append(Concept(
                    label=label,
                    description=f"Concept fragment: '{label}'",
                    domain_hint="General",
                ))
                if len(concepts) >= 4:
                    break

        logger.info("Keyword fallback produced %d concepts.", len(concepts))
        return concepts[:7]

    except Exception as exc:
        logger.error("Keyword fallback also failed (%s). Returning single whole-idea concept.", exc)
        return [Concept(
            label=idea[:60],
            description=idea,
            domain_hint="General",
        )]
