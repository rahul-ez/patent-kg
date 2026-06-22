"""
Indian Patent Act Eligibility Checker (Section 3)
===================================================
Rule-based classifier that flags inventions likely excluded under Section 3
of the Patents Act 1970 (India).

Returns a list of flags — NOT a numeric score. Each flag is a warning that
an Indian examiner may raise. The patentability engine shows these flags
alongside the numeric scores; the inventor must then consult a patent attorney.

Sections checked:
  3(k) — Mathematical methods, business methods, computer programs per se,
          algorithms. The word "per se" is critical — a technical effect
          anchored to specific hardware is generally allowable.
  3(d) — New form of known substance that does not result in enhanced efficacy.
          Mainly pharmaceutical but also applies to materials science.
  3(c) — Discovery of natural law, natural phenomenon, or abstract theory.

We also surface a 3(k) SAFE_HARBOR note when the idea describes hardware-
anchored technical effects — giving the attorney ammunition to overcome the
examiner's objection.

Methodology: keyword pattern matching on idea text + concept labels + domains.
No Gemini calls — this stays deterministic and fast.
"""

import logging
import re
from typing import List

logger = logging.getLogger(__name__)

from .per_concept_search import ConceptSearchResult


# ── 3(k) signals ────────────────────────────────────────────────────────────

_SEC3K_SOFTWARE_KW = re.compile(
    r"\b(algorithm|software|app(?:lication)?|mobile app|computer program|"
    r"machine learning model|neural network|deep learning|ai model|llm|"
    r"business method|business process|financial method|data processing|"
    r"mathematical method|mathematical formula|calculation method)\b",
    re.IGNORECASE,
)

_SEC3K_HARDWARE_KW = re.compile(
    r"\b(device|apparatus|system|circuit|chip|sensor|processor|hardware|"
    r"embedded|robot|machine|physical|mechanism|component|module|"
    r"implant|instrument|tool)\b",
    re.IGNORECASE,
)

# ── 3(d) signals ─────────────────────────────────────────────────────────────

_SEC3D_SUBSTANCE_KW = re.compile(
    r"\b(drug|molecule|compound|salt|ester|polymorph|crystal|dosage form|"
    r"pharmaceutical|therapeutic|medicine|formulation|pro-drug|prodrug|"
    r"coating|nanoparticle|excipient|active ingredient)\b",
    re.IGNORECASE,
)

_SEC3D_EFFICACY_KW = re.compile(
    r"\b(efficacy|bioavailability|therapeutic effect|pharmacological|"
    r"improved solubility|enhanced activity|in vivo|clinical)\b",
    re.IGNORECASE,
)

# ── 3(c) signals ──────────────────────────────────────────────────────────────

_SEC3C_KW = re.compile(
    r"\b(law of nature|natural phenomenon|abstract idea|discovery of|"
    r"theory of|principle of|naturally occurring|naturally found|"
    r"fundamental theorem|physical law)\b",
    re.IGNORECASE,
)

# ── CPC sections with predominantly software/algorithm content ────────────────
_SOFTWARE_CPC_SECTIONS = {"G06", "G16"}   # Computer science, data processing


def check_india_eligibility(
    user_idea: str,
    results: List[ConceptSearchResult],
) -> dict:
    """
    Parameters
    ----------
    user_idea : str
        Original idea text.
    results : List[ConceptSearchResult]
        Output of search_per_concept() — used for CPC codes and domain names.

    Returns
    -------
    dict:
        flags       — list of flag dicts {section, title, severity, explanation}
        safe_harbors— list of notes that may overcome an examiner's objection
        is_flagged  — bool, True if any HIGH or MEDIUM severity flags raised
        summary     — plain-English one-liner
    """
    flags = []
    safe_harbors = []
    text = (user_idea or "").strip()

    # Gather extra context from results
    all_domains    = list({h.domain for r in results for h in r.hits if h.domain})
    all_cpc        = list({c for r in results for c in r.all_cpc_codes})
    concept_labels = " ".join(r.concept.label for r in results)
    full_text      = f"{text} {concept_labels}"

    # ── Check 3(k) ────────────────────────────────────────────────────────────
    sw_matches = _SEC3K_SOFTWARE_KW.findall(full_text)
    hw_matches = _SEC3K_HARDWARE_KW.findall(full_text)

    # CPC signal: G06 = Computing, G16 = Information and Communication Technology
    sw_cpc = any(c.upper().startswith(tuple(_SOFTWARE_CPC_SECTIONS)) for c in all_cpc)

    if sw_matches or sw_cpc:
        has_hardware_anchor = bool(hw_matches)

        if has_hardware_anchor:
            severity = "MEDIUM"
            explanation = (
                f"The idea contains software/algorithm elements "
                f"({', '.join(set(sw_matches[:3]))}) but also mentions physical "
                f"hardware ({', '.join(set(hw_matches[:3]))}). Under Section 3(k), "
                f"a computer program 'per se' is not patentable, but a technical "
                f"invention that uses software to produce a concrete technical effect "
                f"on specific hardware IS allowable. Claims must be hardware-anchored."
            )
            safe_harbors.append({
                "note": "Hardware-anchored claim strategy",
                "detail": (
                    f"Draft claims to recite the specific hardware "
                    f"({', '.join(set(hw_matches[:2]))}) as a mandatory structural "
                    f"element. The software must be described as achieving a technical "
                    f"effect on that hardware, not just performing a process in the abstract."
                ),
            })
        else:
            severity = "HIGH"
            explanation = (
                f"The idea appears to be primarily a software/algorithm method "
                f"({', '.join(set(sw_matches[:3]))}) with no clear physical hardware "
                f"substrate described. Section 3(k) of the Indian Patents Act excludes "
                f"computer programs, algorithms, and mathematical methods 'per se'. "
                f"Without a concrete hardware-anchored technical effect, this is likely "
                f"not patentable in India as-is."
            )
            safe_harbors.append({
                "note": "Add a hardware substrate to overcome 3(k)",
                "detail": (
                    "Consider describing the invention as a physical device or system "
                    "rather than a standalone method. If the algorithm runs on specific "
                    "hardware (e.g., an ASIC, sensor, or embedded system) and produces "
                    "a measurable technical effect, claims can be drafted to survive 3(k)."
                ),
            })

        flags.append({
            "section":     "3(k)",
            "title":       "Computer Program / Algorithm Exclusion",
            "severity":    severity,
            "explanation": explanation,
            "matched_kw":  list(set(sw_matches[:5])),
        })

    # ── Check 3(d) ────────────────────────────────────────────────────────────
    substance_matches = _SEC3D_SUBSTANCE_KW.findall(full_text)
    if substance_matches:
        has_efficacy = bool(_SEC3D_EFFICACY_KW.search(full_text))

        if has_efficacy:
            severity = "LOW"
            explanation = (
                f"The idea involves a substance/formulation "
                f"({', '.join(set(substance_matches[:3]))}) and claims enhanced efficacy. "
                f"Section 3(d) requires demonstrating that the new form results in "
                f"significantly enhanced therapeutic efficacy over the known substance. "
                f"Comparative data will be essential at prosecution."
            )
        else:
            severity = "MEDIUM"
            explanation = (
                f"The idea involves a substance/formulation "
                f"({', '.join(set(substance_matches[:3]))}) but does not clearly claim "
                f"enhanced therapeutic efficacy. Section 3(d) excludes new forms of "
                f"known substances that do not produce enhanced efficacy. Ensure claims "
                f"are accompanied by comparative efficacy data."
            )

        flags.append({
            "section":     "3(d)",
            "title":       "New Form of Known Substance",
            "severity":    severity,
            "explanation": explanation,
            "matched_kw":  list(set(substance_matches[:5])),
        })

    # ── Check 3(c) ────────────────────────────────────────────────────────────
    nature_matches = _SEC3C_KW.findall(full_text)
    if nature_matches:
        flags.append({
            "section":     "3(c)",
            "title":       "Discovery / Natural Phenomenon",
            "severity":    "HIGH",
            "explanation": (
                f"The idea description matches language associated with discoveries "
                f"of natural laws or phenomena ({', '.join(set(nature_matches[:3]))}). "
                f"Section 3(c) excludes the discovery of any living or non-living "
                f"natural occurring substance, natural phenomenon, and abstract theory. "
                f"To be patentable, the invention must describe a practical application "
                f"or specific utility, not just the underlying discovery."
            ),
            "matched_kw":  list(set(nature_matches[:5])),
        })

    # ── Compute is_flagged and summary ───────────────────────────────────────
    severities = [f["severity"] for f in flags]
    is_flagged  = "HIGH" in severities or "MEDIUM" in severities

    if not flags:
        summary = "No Indian Patent Act Section 3 exclusion flags raised"
    elif "HIGH" in severities:
        flagged_sections = [f["section"] for f in flags if f["severity"] == "HIGH"]
        summary = f"HIGH risk under Indian Patent Act Section {', '.join(flagged_sections)} — consult a patent attorney before proceeding"
    else:
        flagged_sections = [f["section"] for f in flags]
        summary = f"Medium/low risk flags under Section {', '.join(flagged_sections)} — may need claim strategy adjustment"

    logger.info(
        "India eligibility: %d flags (is_flagged=%s): %s",
        len(flags), is_flagged, [f["section"] for f in flags],
    )

    return {
        "flags":        flags,
        "safe_harbors": safe_harbors,
        "is_flagged":   is_flagged,
        "summary":      summary,
    }
