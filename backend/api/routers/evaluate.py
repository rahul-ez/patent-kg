"""
Evaluation router
==================
POST /api/evaluate        — nested result (used by the React dashboard)
POST /api/evaluate/full   — flat single-level JSON (easy for teammates/scripts)
GET  /api/evaluate/fields — field reference: name, type, range, description
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from api.schemas import EvaluateRequest, EvaluateResponse  # noqa: E402

router = APIRouter(tags=["evaluation"])


# ── Shared helper ─────────────────────────────────────────────────────────────

def _run(req: EvaluateRequest) -> dict:
    """Run evaluation engine, reusing pre-existing pipeline hits when available."""
    # If the caller already ran the pipeline, reuse those hits — no double search.
    if req.pipeline_result and req.pipeline_result.get("results"):
        hits = req.pipeline_result["results"]
    else:
        from integration.pipeline import run_end_to_end
        raw = run_end_to_end(req.idea.strip(), top_k=req.top_k, gnn_mode=req.gnn_mode)
        hits = raw.get("results", [])

    from evaluation.patentability_engine import run_evaluation
    return run_evaluation(
        user_idea=req.idea.strip(),
        hits=hits,
        top_k_concepts=min(req.top_k, 5),
        run_fast=req.run_fast,
        n_reconstruction_samples=req.n_reconstruction_samples,
    )


def _flatten(r: dict) -> Dict[str, Any]:
    """
    Flatten the nested engine result into a single-level dict.
    Every key is prefixed by its dimension so the namespace is unambiguous.
    All scores are in their native units (0-1 or 0-100 as noted in /fields).
    """
    nov = r["novelty"]
    nob = r["non_obviousness"]
    nob_bd = nob["breakdown"]
    land = r["landscape"]
    cb   = r["claim_breadth"]
    tim  = r["timing"]
    ind  = r["india_eligibility"]
    dep  = r["technical_depth"]
    cont = r["contributions"]

    return {
        # ── Overall ──────────────────────────────────────────────────────────
        "patentability_score":           r["patentability_score"],       # 0-100
        "patentability_score_undamped":  r["patentability_raw"],         # 0-100, before confidence dampening
        "verdict":                       r["verdict"],
        "risk":                          r["risk"],                      # "Low" | "Medium" | "High"
        "confidence":                    r["confidence"],                # 0-1 (from technical depth)

        # ── Novelty ──────────────────────────────────────────────────────────
        "novelty_score":                 nov["score"],                   # 0-100
        "novelty_semantic":              nov["semantic_novelty"],        # 0-1
        "novelty_gnn":                   nov["gnn_novelty"],             # 0-1 or null
        "novelty_gnn_mode":              nov["gnn_mode"],                # "novelty" | "graph_sim" | null
        "novelty_blend_semantic":        nov["blend"]["semantic"],       # 0-1 weight used
        "novelty_blend_gnn":             nov["blend"]["gnn"],            # 0-1 weight used
        "novelty_top_faiss_score":       nov["top_semantic_score"],      # 0-1 (highest cosine similarity seen)
        "novelty_n_hits":                nov["n_hits_used"],
        "novelty_interpretation":        nov["interpretation"],

        # ── Non-Obviousness (top-level) ───────────────────────────────────────
        "non_obviousness_score":         nob["score"],                   # 0-100
        "non_obviousness_fast_mode":     nob["fast_mode"],

        # sub-scorer raw scores (0-1 each)
        "no_combination_difficulty":     nob_bd["combination_difficulty"]["score"],
        "no_motivation_to_combine":      nob_bd["motivation_to_combine"]["score"],
        "no_cross_domain_novelty":       nob_bd["cross_domain_novelty"]["score"],
        "no_reconstruction_difficulty":  nob_bd["reconstruction"]["score"],
        "no_citation_isolation":         nob_bd["citation_isolation"]["score"],
        "no_long_felt_need":             nob_bd["long_felt_need"]["score"],
        "no_teaching_away_bonus":        nob_bd["teaching_away"]["score"],        # 0-0.30
        "no_unexpected_effect_bonus":    nob_bd["unexpected_effect"]["score"],    # 0-0.15

        # weighted contributions to the 0-100 non-obviousness score
        "no_contrib_combination_difficulty":   nob["weighted_contributions"].get("combination_difficulty", 0),
        "no_contrib_motivation_to_combine":    nob["weighted_contributions"].get("motivation_to_combine", 0),
        "no_contrib_cross_domain_novelty":     nob["weighted_contributions"].get("cross_domain_novelty", 0),
        "no_contrib_reconstruction":           nob["weighted_contributions"].get("reconstruction", 0),
        "no_contrib_citation_isolation":       nob["weighted_contributions"].get("citation_isolation", 0),
        "no_contrib_long_felt_need":           nob["weighted_contributions"].get("long_felt_need", 0),
        "no_contrib_teaching_away_bonus":      nob["weighted_contributions"].get("teaching_away_bonus", 0),
        "no_contrib_unexpected_effect_bonus":  nob["weighted_contributions"].get("unexpected_effect_bonus", 0),

        # sub-scorer detail fields
        "comb_cpc_distance":             nob_bd["combination_difficulty"].get("cpc_distance"),
        "comb_kg_path_dist":             nob_bd["combination_difficulty"].get("kg_path_dist"),
        "comb_embedding_dist":           nob_bd["combination_difficulty"].get("embedding_dist"),

        "cdnov_cpc_sections":            nob_bd["cross_domain_novelty"].get("cpc_sections"),
        "cdnov_isolated_concept_count":  nob_bd["cross_domain_novelty"].get("isolated_concept_count"),

        "citiso_connected_pairs":        nob_bd["citation_isolation"].get("connected_pairs"),
        "citiso_isolated_pairs":         nob_bd["citation_isolation"].get("isolated_pairs"),
        "citiso_shared_papers":          nob_bd["citation_isolation"].get("shared_papers"),

        "lfn_year_spread":               nob_bd["long_felt_need"].get("year_spread"),
        "lfn_min_year":                  nob_bd["long_felt_need"].get("min_year"),
        "lfn_max_year":                  nob_bd["long_felt_need"].get("max_year"),
        "lfn_avg_citations":             nob_bd["long_felt_need"].get("avg_citations"),
        "lfn_dominant_solution":         nob_bd["long_felt_need"].get("dominant_solution"),

        "teach_signal_count":            nob_bd["teaching_away"].get("signal_count"),
        "teach_signals":                 nob_bd["teaching_away"].get("signals"),

        "motiv_cross_citation_density":  nob_bd["motivation_to_combine"].get("cross_citation_density"),
        "motiv_gemini_has_motivation":   nob_bd["motivation_to_combine"].get("gemini_has_motivation"),
        "motiv_gemini_reason":           nob_bd["motivation_to_combine"].get("gemini_reason"),

        "recon_rate":                    nob_bd["reconstruction"].get("reconstruction_rate"),
        "recon_n_samples":               nob_bd["reconstruction"].get("n_samples"),
        "recon_n_reconstructed":         nob_bd["reconstruction"].get("n_reconstructed"),
        "recon_avg_similarity":          nob_bd["reconstruction"].get("avg_similarity"),
        "recon_threshold":               nob_bd["reconstruction"].get("threshold"),

        "unexp_has_quantitative_claim":  nob_bd["unexpected_effect"].get("has_quantitative_claim"),
        "unexp_claimed_metric":          nob_bd["unexpected_effect"].get("claimed_metric"),
        "unexp_is_surprising":           nob_bd["unexpected_effect"].get("is_surprising"),
        "unexp_reason":                  nob_bd["unexpected_effect"].get("reason"),

        # ── Competitive Landscape ─────────────────────────────────────────────
        "landscape_score":               land["score"],                  # 0-1
        "landscape_score_100":           land["score_100"],              # 0-100 (for display)
        "landscape_density":             land.get("density"),            # 0-1, fraction of space occupied
        "landscape_active_ratio":        land.get("active_ratio"),       # 0-1, active/granted patents
        "landscape_assignee_concentration": land.get("assignee_concentration"),  # 0-1, HHI-like
        "landscape_cpc_sibling_count":   land.get("cpc_sibling_count"),
        "landscape_interpretation":      land["interpretation"],

        # ── Claim Breadth ─────────────────────────────────────────────────────
        "claim_breadth_score":           cb["score"],                    # 0-100
        "claim_breadth_avg_cpc_depth":   cb["avg_cpc_depth"],            # 1-5 (lower = broader)
        "claim_breadth_unique_section_ratio": cb["unique_section_ratio"],# 0-1
        "claim_breadth_total_cpc_codes": cb["total_cpc_codes"],
        "claim_breadth_depth_score":     cb["depth_score"],              # 0-1 sub-score
        "claim_breadth_uniqueness_score":cb["uniqueness_score"],         # 0-1 sub-score
        "claim_breadth_per_concept_depth": cb["per_concept_depth"],      # {label: avg_depth}
        "claim_breadth_interpretation":  cb["interpretation"],

        # ── Timing ────────────────────────────────────────────────────────────
        "timing_score":                  tim["score"],                   # 0-100
        "timing_newest_year":            tim["newest_year"],
        "timing_oldest_year":            tim["oldest_year"],
        "timing_year_spread":            tim["year_spread"],
        "timing_recency_flag":           tim["recency_flag"],            # "ACTIVE"|"CLEARING"|"LEGACY"
        "timing_acceleration":           tim["acceleration"],            # >1 = filing rate growing
        "timing_velocity_score":         tim["velocity_score"],          # 0-1 sub-score
        "timing_recency_score":          tim["recency_score"],           # 0-1 sub-score
        "timing_spread_score":           tim["spread_score"],            # 0-1 sub-score
        "timing_interpretation":         tim["interpretation"],

        # ── India Patent Act Section 3 ────────────────────────────────────────
        "india_is_flagged":              ind["is_flagged"],
        "india_flag_count":              len(ind["flags"]),
        "india_high_severity_count":     sum(1 for f in ind["flags"] if f["severity"] == "HIGH"),
        "india_medium_severity_count":   sum(1 for f in ind["flags"] if f["severity"] == "MEDIUM"),
        "india_flagged_sections":        [f["section"] for f in ind["flags"]],
        "india_flags":                   ind["flags"],                   # full flag objects
        "india_safe_harbors":            ind["safe_harbors"],
        "india_summary":                 ind["summary"],

        # ── Technical Depth ───────────────────────────────────────────────────
        "depth_level":                   dep["level"],                   # "Low"|"Medium"|"High"
        "depth_confidence":              dep["confidence"],              # 0-1
        "depth_entity_count":            dep["entity_count"],
        "depth_entity_density":          dep["entity_density"],          # per 100 words
        "depth_quantitative_hits":       dep["quantitative_hits"],
        "depth_quantitative_density":    dep["quantitative_density"],    # per 100 words
        "depth_term_richness":           dep["term_richness"],
        "depth_word_count":              dep["word_count"],
        "depth_interpretation":          dep["interpretation"],

        # ── Final score weights ───────────────────────────────────────────────
        "weight_novelty":                r["weights"]["novelty"],
        "weight_non_obviousness":        r["weights"]["non_obvious"],
        "weight_landscape":              r["weights"]["landscape"],
        "weight_claim_breadth":          r["weights"]["claim_breadth"],
        "weight_timing":                 r["weights"]["timing"],

        # ── Weighted contributions to patentability_score ─────────────────────
        "contrib_novelty":               cont["novelty"],
        "contrib_non_obviousness":       cont["non_obvious"],
        "contrib_landscape":             cont["landscape"],
        "contrib_claim_breadth":         cont["claim_breadth"],
        "contrib_timing":                cont["timing"],

        # ── Metadata ──────────────────────────────────────────────────────────
        "concept_count":                 r["concept_count"],
        "concepts":                      r["concepts"],
        "elapsed_seconds":               r["elapsed_seconds"],
        "fast_mode":                     r["fast_mode"],
    }


# ── Field reference ───────────────────────────────────────────────────────────

_FIELDS = [
    # Overall
    {"name": "patentability_score",          "type": "float",    "range": "0–100",    "group": "overall",     "description": "Final weighted patentability score after confidence dampening."},
    {"name": "patentability_score_undamped", "type": "float",    "range": "0–100",    "group": "overall",     "description": "Raw weighted blend before confidence dampening (higher means more certain score is trustworthy)."},
    {"name": "verdict",                      "type": "string",   "range": "—",        "group": "overall",     "description": "Plain-English summary verdict with optional India eligibility caveat."},
    {"name": "risk",                         "type": "string",   "range": "Low|Medium|High", "group": "overall", "description": "Patent risk level derived from patentability_score."},
    {"name": "confidence",                   "type": "float",    "range": "0–1",      "group": "overall",     "description": "Confidence multiplier from technical_depth (Low=0.40, Medium=0.65, High=0.90)."},
    # Novelty
    {"name": "novelty_score",               "type": "float",    "range": "0–100",    "group": "novelty",     "description": "Blended novelty score (60% semantic FAISS + 40% GNN)."},
    {"name": "novelty_semantic",            "type": "float",    "range": "0–1",      "group": "novelty",     "description": "1 minus the weighted average cosine similarity from FAISS retrieval."},
    {"name": "novelty_gnn",                 "type": "float|null","range": "0–1",     "group": "novelty",     "description": "Average GNN novelty score across retrieved hits. Null if GNN was not run."},
    {"name": "novelty_gnn_mode",            "type": "string|null","range": "novelty|graph_sim", "group": "novelty", "description": "Which GNN scoring mode was active."},
    {"name": "novelty_blend_semantic",      "type": "float",    "range": "0–1",      "group": "novelty",     "description": "Weight given to semantic novelty in the blend (0.60 when GNN available, 1.00 otherwise)."},
    {"name": "novelty_blend_gnn",           "type": "float",    "range": "0–1",      "group": "novelty",     "description": "Weight given to GNN novelty in the blend (0.40 when GNN available, 0.00 otherwise)."},
    {"name": "novelty_top_faiss_score",     "type": "float",    "range": "0–1",      "group": "novelty",     "description": "Highest cosine similarity score from FAISS (= closest prior art distance)."},
    # Non-Obviousness top-level
    {"name": "non_obviousness_score",       "type": "float",    "range": "0–100",    "group": "non_obviousness", "description": "Final weighted non-obviousness score (base sub-scorers + bonus modifiers)."},
    {"name": "non_obviousness_fast_mode",   "type": "bool",     "range": "—",        "group": "non_obviousness", "description": "If true, motivation and reconstruction scores are neutral placeholders (Gemini skipped)."},
    # Non-Obviousness sub-scores (0-1)
    {"name": "no_combination_difficulty",   "type": "float",    "range": "0–1",      "group": "non_obviousness", "description": "How structurally distant the concept combination is (CPC distance + KG path + embedding). Weight: 25%."},
    {"name": "no_motivation_to_combine",    "type": "float",    "range": "0–1",      "group": "non_obviousness", "description": "INVERTED — 1=no motivation found (non-obvious), 0=obvious motivation exists. Weight: 20%."},
    {"name": "no_cross_domain_novelty",     "type": "float",    "range": "0–1",      "group": "non_obviousness", "description": "Degree to which concepts span different CPC technology domains. Weight: 15%."},
    {"name": "no_reconstruction_difficulty","type": "float",    "range": "0–1",      "group": "non_obviousness", "description": "1 minus the rate at which Gemini reconstructs the invention from only prior art. Weight: 15%."},
    {"name": "no_citation_isolation",       "type": "float",    "range": "0–1",      "group": "non_obviousness", "description": "Fraction of concept-pairs not connected by shared paper citations or family edges. Weight: 10%."},
    {"name": "no_long_felt_need",           "type": "float",    "range": "0–1",      "group": "non_obviousness", "description": "Evidence that the problem was unsolved for a long time (year spread + citations). Weight: 10%."},
    {"name": "no_teaching_away_bonus",      "type": "float",    "range": "0–0.30",   "group": "non_obviousness", "description": "Bonus: prior art literature actively discourages this combination. Contributes up to 5 pts."},
    {"name": "no_unexpected_effect_bonus",  "type": "float",    "range": "0–0.15",   "group": "non_obviousness", "description": "Bonus: invention claims a quantitative effect that surprises given the prior art. Contributes up to 5 pts."},
    # Sub-scorer detail fields
    {"name": "comb_cpc_distance",           "type": "float|null","range": "0–1",     "group": "combination_difficulty", "description": "CPC taxonomy distance between concept clusters (0=same leaf, 1=different sections)."},
    {"name": "comb_kg_path_dist",           "type": "float|null","range": "0–1",     "group": "combination_difficulty", "description": "Normalised shortest KG path length between representative patents."},
    {"name": "comb_embedding_dist",         "type": "float|null","range": "0–1",     "group": "combination_difficulty", "description": "Cosine distance between mean concept embeddings."},
    {"name": "cdnov_cpc_sections",          "type": "list[str]|null","range": "—",   "group": "cross_domain", "description": "Unique CPC sections (A–H) seen across all concept clusters."},
    {"name": "cdnov_isolated_concept_count","type": "int|null", "range": "0–N",      "group": "cross_domain", "description": "Number of concepts whose CPC sections have no overlap with other concepts."},
    {"name": "citiso_connected_pairs",      "type": "int|null", "range": "0–N",      "group": "citation_isolation", "description": "Concept-pairs connected by shared NPL papers or patent family edges."},
    {"name": "citiso_isolated_pairs",       "type": "int|null", "range": "0–N",      "group": "citation_isolation", "description": "Concept-pairs with no shared citation or family connection."},
    {"name": "citiso_shared_papers",        "type": "int|null", "range": "0–N",      "group": "citation_isolation", "description": "Total shared NPL papers between all concept clusters."},
    {"name": "lfn_year_spread",             "type": "int|null", "range": "0–N",      "group": "long_felt_need", "description": "Difference (years) between earliest and latest patent in the concept clusters."},
    {"name": "lfn_min_year",               "type": "int|null", "range": "—",        "group": "long_felt_need", "description": "Earliest publication year seen across all retrieved hits."},
    {"name": "lfn_max_year",               "type": "int|null", "range": "—",        "group": "long_felt_need", "description": "Latest publication year seen across all retrieved hits."},
    {"name": "lfn_avg_citations",          "type": "float|null","range": "0–N",      "group": "long_felt_need", "description": "Average cited_by count across all retrieved patents."},
    {"name": "lfn_dominant_solution",      "type": "bool|null","range": "—",        "group": "long_felt_need", "description": "True if one patent has >500 citations (dominant incumbent solution exists)."},
    {"name": "teach_signal_count",         "type": "int",      "range": "0–N",      "group": "teaching_away", "description": "Number of teaching-away signal matches found in NPL texts."},
    {"name": "teach_signals",              "type": "list",     "range": "—",        "group": "teaching_away", "description": "Up to 5 teaching-away evidence objects {concept, phrase_matched, excerpt}."},
    {"name": "motiv_cross_citation_density","type": "float",   "range": "0–1",      "group": "motivation",  "description": "Fraction of concept-pairs that cite each other's patents (high = obvious combination)."},
    {"name": "motiv_gemini_has_motivation","type": "bool|null","range": "—",        "group": "motivation",  "description": "Gemini judgment: does prior art explicitly suggest combining these concepts?"},
    {"name": "motiv_gemini_reason",        "type": "string",   "range": "—",        "group": "motivation",  "description": "Gemini's one-sentence justification for the motivation judgment."},
    {"name": "recon_rate",                 "type": "float|null","range": "0–1",     "group": "reconstruction","description": "Fraction of Gemini attempts that reproduced the invention (high = obvious)."},
    {"name": "recon_n_samples",            "type": "int",      "range": "0–N",      "group": "reconstruction","description": "Number of independent Gemini generation attempts used."},
    {"name": "recon_n_reconstructed",      "type": "int",      "range": "0–N",      "group": "reconstruction","description": "How many attempts scored above the similarity threshold."},
    {"name": "recon_avg_similarity",       "type": "float|null","range": "0–1",     "group": "reconstruction","description": "Average cosine similarity of Gemini-generated solutions vs the user's idea."},
    {"name": "recon_threshold",            "type": "float",    "range": "0–1",      "group": "reconstruction","description": "Similarity threshold above which a generation counts as reconstructed (default 0.75)."},
    {"name": "unexp_has_quantitative_claim","type": "bool",    "range": "—",        "group": "unexpected_effect","description": "Whether the idea text contains a specific quantitative performance claim."},
    {"name": "unexp_claimed_metric",       "type": "string|null","range": "—",      "group": "unexpected_effect","description": "Description of the claimed metric (e.g. '40% accuracy improvement')."},
    {"name": "unexp_is_surprising",        "type": "bool|null","range": "—",        "group": "unexpected_effect","description": "Gemini judgment: would this magnitude of improvement surprise a skilled engineer?"},
    {"name": "unexp_reason",               "type": "string",   "range": "—",        "group": "unexpected_effect","description": "Gemini's one-sentence justification for the surprise judgment."},
    # Landscape
    {"name": "landscape_score",            "type": "float",    "range": "0–1",      "group": "landscape",   "description": "Overall competitive landscape score (higher = less competitive = more room to patent)."},
    {"name": "landscape_score_100",        "type": "float",    "range": "0–100",    "group": "landscape",   "description": "Same as landscape_score scaled to 0–100 for display."},
    {"name": "landscape_density",          "type": "float|null","range": "0–1",     "group": "landscape",   "description": "Fraction of retrieved hits above similarity_threshold (proxy for space crowdedness)."},
    {"name": "landscape_active_ratio",     "type": "float|null","range": "0–1",     "group": "landscape",   "description": "Fraction of retrieved patents with active/granted legal status."},
    {"name": "landscape_assignee_concentration","type": "float|null","range":"0–1", "group": "landscape",   "description": "HHI-like concentration of patent ownership (1 = single dominant assignee)."},
    {"name": "landscape_cpc_sibling_count","type": "int|null", "range": "0–N",      "group": "landscape",   "description": "Number of patents sharing the same CPC subclass in the KG (from KG expansion)."},
    # Claim Breadth
    {"name": "claim_breadth_score",        "type": "float",    "range": "0–100",    "group": "claim_breadth","description": "Estimate of how broadly claims can be drafted given the CPC landscape."},
    {"name": "claim_breadth_avg_cpc_depth","type": "float|null","range": "1–5",     "group": "claim_breadth","description": "Average CPC hierarchy depth across all retrieved codes (lower = broader technology territory)."},
    {"name": "claim_breadth_unique_section_ratio","type":"float|null","range":"0–1","group": "claim_breadth","description": "Fraction of concepts whose CPC section has no overlap with other concepts."},
    {"name": "claim_breadth_total_cpc_codes","type":"int",     "range": "0–N",      "group": "claim_breadth","description": "Total CPC codes observed across all concept clusters."},
    {"name": "claim_breadth_depth_score",  "type": "float|null","range": "0–1",     "group": "claim_breadth","description": "Sub-score from CPC depth analysis alone."},
    {"name": "claim_breadth_uniqueness_score","type":"float|null","range":"0–1",    "group": "claim_breadth","description": "Sub-score from cross-domain uniqueness analysis alone."},
    {"name": "claim_breadth_per_concept_depth","type":"dict",  "range": "—",        "group": "claim_breadth","description": "Average CPC depth per concept label."},
    # Timing
    {"name": "timing_score",               "type": "float",    "range": "0–100",    "group": "timing",      "description": "How favourable the filing timing is (higher = better window)."},
    {"name": "timing_newest_year",         "type": "int|null", "range": "—",        "group": "timing",      "description": "Most recent publication year in the retrieved prior art."},
    {"name": "timing_oldest_year",         "type": "int|null", "range": "—",        "group": "timing",      "description": "Oldest publication year in the retrieved prior art."},
    {"name": "timing_year_spread",         "type": "int|null", "range": "0–N",      "group": "timing",      "description": "Number of years between oldest and newest prior art (wider = more mature field)."},
    {"name": "timing_recency_flag",        "type": "string",   "range": "ACTIVE|CLEARING|LEGACY", "group": "timing", "description": "ACTIVE: newest prior art ≤6y old. CLEARING: 6–12y. LEGACY: >12y (likely expired space)."},
    {"name": "timing_acceleration",        "type": "float|null","range": "0–N",     "group": "timing",      "description": "Filing rate in the recent half of the timeline divided by the older half (>1 = accelerating)."},
    # India
    {"name": "india_is_flagged",           "type": "bool",     "range": "—",        "group": "india",       "description": "True if any HIGH or MEDIUM severity Section 3 exclusion flags were raised."},
    {"name": "india_flag_count",           "type": "int",      "range": "0–3",      "group": "india",       "description": "Total number of Section 3 flags raised."},
    {"name": "india_high_severity_count",  "type": "int",      "range": "0–3",      "group": "india",       "description": "Number of HIGH severity flags (likely ineligible without claim restructuring)."},
    {"name": "india_flagged_sections",     "type": "list[str]","range": "—",        "group": "india",       "description": "List of flagged sections e.g. ['3(k)', '3(d)']."},
    {"name": "india_flags",                "type": "list",     "range": "—",        "group": "india",       "description": "Full flag objects: {section, title, severity, explanation, matched_kw}."},
    {"name": "india_safe_harbors",         "type": "list",     "range": "—",        "group": "india",       "description": "Claim strategy notes to help overcome each flag: {note, detail}."},
    # Technical Depth
    {"name": "depth_level",               "type": "string",   "range": "Low|Medium|High", "group": "technical_depth", "description": "Qualitative assessment of how technically detailed the idea description is."},
    {"name": "depth_confidence",          "type": "float",    "range": "0–1",      "group": "technical_depth", "description": "Confidence multiplier applied to final score (Low=0.40, Medium=0.65, High=0.90)."},
    {"name": "depth_entity_count",        "type": "int",      "range": "0–N",      "group": "technical_depth", "description": "Number of technical named entities found in idea text."},
    {"name": "depth_quantitative_hits",   "type": "int",      "range": "0–N",      "group": "technical_depth", "description": "Number of numeric/unit/range patterns found in idea text."},
    {"name": "depth_word_count",          "type": "int",      "range": "0–N",      "group": "technical_depth", "description": "Total word count of the idea text."},
    # Weights + Contributions
    {"name": "weight_novelty",            "type": "float",    "range": "0–1",      "group": "weights",     "description": "Weight of Novelty in final patentability blend (0.30)."},
    {"name": "weight_non_obviousness",    "type": "float",    "range": "0–1",      "group": "weights",     "description": "Weight of Non-Obviousness in final blend (0.35)."},
    {"name": "weight_landscape",          "type": "float",    "range": "0–1",      "group": "weights",     "description": "Weight of Competitive Landscape in final blend (0.15)."},
    {"name": "weight_claim_breadth",      "type": "float",    "range": "0–1",      "group": "weights",     "description": "Weight of Claim Breadth in final blend (0.10)."},
    {"name": "weight_timing",             "type": "float",    "range": "0–1",      "group": "weights",     "description": "Weight of Timing in final blend (0.10)."},
    {"name": "contrib_novelty",           "type": "float",    "range": "0–30",     "group": "contributions","description": "Points contributed by Novelty to patentability_score_undamped."},
    {"name": "contrib_non_obviousness",   "type": "float",    "range": "0–35",     "group": "contributions","description": "Points contributed by Non-Obviousness."},
    {"name": "contrib_landscape",         "type": "float",    "range": "0–15",     "group": "contributions","description": "Points contributed by Competitive Landscape."},
    {"name": "contrib_claim_breadth",     "type": "float",    "range": "0–10",     "group": "contributions","description": "Points contributed by Claim Breadth."},
    {"name": "contrib_timing",            "type": "float",    "range": "0–10",     "group": "contributions","description": "Points contributed by Timing."},
    # Metadata
    {"name": "concept_count",             "type": "int",      "range": "0–N",      "group": "meta",        "description": "Number of concepts extracted from the idea by Gemini."},
    {"name": "concepts",                  "type": "list",     "range": "—",        "group": "meta",        "description": "Extracted concepts: [{label, description}]."},
    {"name": "elapsed_seconds",           "type": "float",    "range": "0–N",      "group": "meta",        "description": "Total wall-clock time for the full evaluation run."},
    {"name": "fast_mode",                 "type": "bool",     "range": "—",        "group": "meta",        "description": "If true, Gemini-heavy sub-scorers were skipped."},
]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_idea(req: EvaluateRequest) -> EvaluateResponse:
    """
    Full patentability evaluation — nested JSON used by the React dashboard.

    Returns a hierarchical result with all dimension scores and sub-scorer breakdowns.
    For a flat, machine-readable format use **POST /api/evaluate/full**.

    Expected runtime: 30–120 s (full mode) or ~15 s (run_fast=true).
    """
    if not req.idea.strip():
        raise HTTPException(status_code=422, detail="Idea text cannot be empty.")
    if req.gnn_mode not in ("novelty", "graph_sim"):
        raise HTTPException(status_code=422, detail="gnn_mode must be 'novelty' or 'graph_sim'.")
    try:
        return EvaluateResponse(**_run(req))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=f"Pipeline resource not found: {exc}.") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/evaluate/full")
async def evaluate_idea_flat(req: EvaluateRequest) -> Dict[str, Any]:
    """
    Full patentability evaluation — **flat single-level JSON**.

    Every computed value is exposed as a top-level key.  No nesting.
    Designed for teammates who want to iterate over fields programmatically,
    pipe results into a spreadsheet, or feed into an external ML model.

    Use **GET /api/evaluate/fields** to get a description of every field.

    Same request body and runtime as POST /api/evaluate.
    """
    if not req.idea.strip():
        raise HTTPException(status_code=422, detail="Idea text cannot be empty.")
    if req.gnn_mode not in ("novelty", "graph_sim"):
        raise HTTPException(status_code=422, detail="gnn_mode must be 'novelty' or 'graph_sim'.")
    try:
        raw = _run(req)
        return _flatten(raw)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=f"Pipeline resource not found: {exc}.") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/evaluate/fields")
async def list_evaluation_fields():
    """
    Returns a description of every field produced by **POST /api/evaluate/full**.

    Each entry contains:
    - `name`        — exact key in the flat JSON response
    - `type`        — Python/JSON type
    - `range`       — value range or enum options
    - `group`       — which dimension this field belongs to
    - `description` — plain-English explanation

    Use this as living documentation for the evaluation API.
    """
    groups = {}
    for f in _FIELDS:
        groups.setdefault(f["group"], []).append(f)

    return {
        "total_fields": len(_FIELDS),
        "groups":       list(groups.keys()),
        "fields":       _FIELDS,
        "fields_by_group": groups,
    }
