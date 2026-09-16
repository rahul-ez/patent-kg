"""Extract independently searchable technical concepts from an invention idea."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You decompose invention ideas into independently searchable technical concepts.
Return 3 to 7 concepts only. Each label is a 2-6 word noun phrase and each domain_hint is one of AI, Medical, IoT, Automotive, Energy, Mechanical, or General.
Return only JSON."""
_USER_PROMPT_TEMPLATE = """Decompose this invention idea into atomic technical concepts:

IDEA: "{idea}"

Return this JSON structure:
{{"concepts": [{{"label": "noun phrase", "description": "technical mechanism", "domain_hint": "General"}}]}}"""


@dataclass
class Concept:
    """One atomic technical contribution used by evaluation search/scorers."""

    label: str
    description: str
    domain_hint: str


def extract_concepts(idea: str) -> List[Concept]:
    """Use Gemini structured output when available, otherwise a local fallback."""
    if not idea or not idea.strip():
        raise ValueError("Idea string is empty.")

    try:
        from .gemini_client import get_gemini_client

        client = get_gemini_client()
        if client is None:
            return _keyword_fallback(idea)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{_SYSTEM_PROMPT}\n\n{_USER_PROMPT_TEMPLATE.format(idea=idea.strip())}",
            config={"response_mime_type": "application/json"},
        )
        payload = json.loads(response.text or "{}")
        concepts = [
            Concept(
                label=str(item.get("label", "")).strip(),
                description=str(item.get("description", "")).strip(),
                domain_hint=str(item.get("domain_hint", "General")).strip() or "General",
            )
            for item in payload.get("concepts", [])
            if str(item.get("label", "")).strip()
        ]
        if concepts:
            return concepts[:7]
    except Exception as exc:
        logger.warning("Gemini concept extraction failed (%s); using fallback.", exc)
    return _keyword_fallback(idea)


def _keyword_fallback(idea: str) -> List[Concept]:
    """Return stable local concepts when Gemini or spaCy is unavailable."""
    try:
        import spacy

        doc = spacy.load("en_core_web_sm")(idea)
        seen: set[str] = set()
        concepts: List[Concept] = []
        for chunk in doc.noun_chunks:
            label = chunk.text.lower().strip()
            if len(label.split()) < 2 or label in seen:
                continue
            seen.add(label)
            concepts.append(Concept(label, f"Technical concept: {label}", "General"))
            if len(concepts) == 6:
                break
        if concepts:
            return concepts
    except Exception as exc:
        logger.warning("spaCy concept fallback failed: %s", exc)

    words = idea.lower().split()
    fragments = [" ".join(words[i:i + 3]) for i in range(0, min(len(words), 12), 3)]
    return [
        Concept(label=fragment or idea[:60], description=fragment or idea, domain_hint="General")
        for fragment in fragments[:4]
        if fragment
    ] or [Concept(label=idea[:60], description=idea, domain_hint="General")]
