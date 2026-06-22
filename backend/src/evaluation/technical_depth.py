"""
Technical Depth Assessor
=========================
Estimates how technically detailed and precise the inventor's description is.

This is NOT a patentability sub-score — it is a confidence indicator.
High technical depth → other scorers (especially novelty and reconstruction)
can be trusted more. Low technical depth → scores should be treated cautiously
because the idea description is too vague to accurately match prior art.

Three signals:
  1. Entity density — technical named entities per 100 words.
     More entities (measurements, compounds, parameters) = more depth.
  2. Quantitative density — presence of numbers, units, percentages, ranges.
     Specific numbers anchor the invention and raise confidence.
  3. Technical term richness — number of domain-specific multi-word terms
     relative to total words.

Output:
  level         — "Low" | "Medium" | "High"
  confidence    — 0.0–1.0 numeric confidence in the evaluation scores
  entity_density, quantitative_density, term_richness — raw sub-signals
  interpretation — note for the UI
"""

import logging
import re
from typing import List

logger = logging.getLogger(__name__)

from .per_concept_search import ConceptSearchResult

# Numbers, percentages, units, ranges
_NUMBER_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?(?:\s*(?:%|percent|ppm|Hz|MHz|GHz|kHz|ms|ns|μs|us|"
    r"nm|μm|mm|cm|m|km|kg|g|mg|μg|ug|mL|L|mW|W|kW|MW|V|mV|A|mA|°C|K|"
    r"Pa|kPa|MPa|dB|bps|Gbps|Mbps|kbps|Tbps|rpm|fps|psi|mol|kJ|J|eV)s?)?\b",
    re.IGNORECASE,
)

# Range patterns: "10-20", "between X and Y", "at least N"
_RANGE_RE = re.compile(
    r"\b(?:between\s+\d+\s+and\s+\d+|\d+\s*[-–]\s*\d+|at\s+least\s+\d+|"
    r"up\s+to\s+\d+|less\s+than\s+\d+|more\s+than\s+\d+)\b",
    re.IGNORECASE,
)

# Technical multi-word terms commonly found in patents
_TECHNICAL_TERM_RE = re.compile(
    r"\b(?:[a-z]+(?:\s+[a-z]+){1,3})\b",
    re.IGNORECASE,
)

# spaCy entity types that indicate technical content
_TECHNICAL_ENT_TYPES = {
    "ORG", "PRODUCT", "WORK_OF_ART", "LAW", "NORP",
    # custom types from patent NLP models if present
    "CHEM", "MATERIAL", "PROCESS", "DEVICE",
}


def assess_technical_depth(
    user_idea: str,
    results: List[ConceptSearchResult],
) -> dict:
    """
    Parameters
    ----------
    user_idea : str
        Original idea text.
    results : List[ConceptSearchResult]
        Provides concept labels and descriptions as additional text.

    Returns
    -------
    dict:
        level              — "Low" | "Medium" | "High"
        confidence         — 0.0–1.0 numeric confidence multiplier
        entity_density     — entities per 100 words
        quantitative_hits  — count of number/unit patterns found
        quantitative_density — quantitative_hits per 100 words
        word_count         — total words in idea text
        interpretation     — short explanation
    """
    text = (user_idea or "").strip()
    if not text:
        return _default("Idea text is empty")

    words = re.findall(r"\b\w+\b", text)
    word_count = len(words)
    if word_count < 5:
        return _default("Idea text too short to assess")

    per_100 = 100.0 / word_count

    # ── Signal 1: spaCy entity density ───────────────────────────────────────
    entity_count = 0
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)
        entity_count = sum(
            1 for ent in doc.ents if ent.label_ in _TECHNICAL_ENT_TYPES
        )
    except Exception:
        # Fallback: count capitalised non-sentence-start tokens as entities
        entity_count = sum(
            1 for i, w in enumerate(words)
            if i > 0 and w[0].isupper() and len(w) > 3
        )

    entity_density = round(entity_count * per_100, 2)

    # ── Signal 2: Quantitative density ───────────────────────────────────────
    number_hits = len(_NUMBER_RE.findall(text))
    range_hits  = len(_RANGE_RE.findall(text))
    quant_hits  = number_hits + range_hits
    quant_density = round(quant_hits * per_100, 2)

    # ── Signal 3: Technical term richness ────────────────────────────────────
    # Proxy: count multi-word noun phrases (2-4 words) that appear in concept labels
    concept_words = set()
    for r in results:
        concept_words.update(r.concept.label.lower().split())
        concept_words.update(r.concept.description.lower().split())

    text_lower = text.lower()
    richness_hits = sum(
        1 for w in concept_words if len(w) > 5 and w in text_lower
    )
    term_richness = round(richness_hits * per_100, 2)

    # ── Scoring ───────────────────────────────────────────────────────────────
    # Thresholds calibrated on typical inventor idea descriptions:
    #   Low:    entity_density<2, quant_density<1
    #   Medium: entity_density 2-5, quant_density 1-3
    #   High:   entity_density>5 or quant_density>3

    entity_score = min(entity_density / 10.0, 1.0)
    quant_score  = min(quant_density  / 5.0,  1.0)
    rich_score   = min(term_richness  / 5.0,  1.0)

    composite = 0.40 * entity_score + 0.40 * quant_score + 0.20 * rich_score

    if composite >= 0.55 or (entity_density >= 4 and quant_density >= 2):
        level      = "High"
        confidence = 0.90
        interp     = (
            "Technically detailed description — evaluation scores are reliable. "
            f"Found {quant_hits} quantitative data points, {entity_count} technical entities."
        )
    elif composite >= 0.25 or (entity_density >= 1.5 or quant_density >= 0.8):
        level      = "Medium"
        confidence = 0.65
        interp     = (
            "Moderately detailed description — evaluation scores should be treated "
            "as indicative. Adding more specific numbers and technical parameters "
            "would improve accuracy."
        )
    else:
        level      = "Low"
        confidence = 0.40
        interp     = (
            "Vague description — evaluation scores have low confidence. "
            "Provide specific technical parameters, measurements, and mechanisms "
            "for a more accurate patentability assessment."
        )

    logger.info(
        "Technical depth: %s (confidence=%.2f, entities=%d, quant=%d, words=%d)",
        level, confidence, entity_count, quant_hits, word_count,
    )

    return {
        "level":                level,
        "confidence":           confidence,
        "entity_count":         entity_count,
        "entity_density":       entity_density,
        "quantitative_hits":    quant_hits,
        "quantitative_density": quant_density,
        "term_richness":        term_richness,
        "word_count":           word_count,
        "interpretation":       interp,
    }


def _default(reason: str = "") -> dict:
    return {
        "level":                "Low",
        "confidence":           0.40,
        "entity_count":         0,
        "entity_density":       0.0,
        "quantitative_hits":    0,
        "quantitative_density": 0.0,
        "term_richness":        0.0,
        "word_count":           0,
        "interpretation":       f"Technical depth assessment unavailable: {reason}",
    }
