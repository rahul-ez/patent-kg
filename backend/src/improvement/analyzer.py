import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from .config import (
    SEMANTIC_THRESHOLD,
    GRAPH_THRESHOLD,
    LANDSCAPE_THRESHOLD,
    DENSITY_THRESHOLD,
    NOVELTY_SCORE_THRESHOLD,
    NON_OBVIOUSNESS_SCORE_THRESHOLD,
    PATENTABILITY_SCORE_THRESHOLD
)

def analyze_overlap(
    pipeline_result: Optional[Dict[str, Any]],
    evaluation_result: Optional[Dict[str, Any]]
) -> List[str]:
    """
    Deterministic rule-based overlap and problem analyzer.
    Consumes pipeline and evaluation results and identifies key problems.
    """
    problems = []

    # 1. Semantic Overlap Check
    max_semantic = 0.0
    if pipeline_result and "results" in pipeline_result:
        semantic_scores = [
            h["semantic_score"] for h in pipeline_result["results"]
            if isinstance(h.get("semantic_score"), (int, float))
        ]
        if semantic_scores:
            max_semantic = max(semantic_scores)
    
    if evaluation_result and "novelty" in evaluation_result:
        top_sem = evaluation_result["novelty"].get("top_semantic_score")
        if isinstance(top_sem, (int, float)):
            max_semantic = max(max_semantic, top_sem)

    if max_semantic > SEMANTIC_THRESHOLD:
        problems.append("high_semantic_overlap")

    # 2. Graph Overlap Check
    max_graph = 0.0
    if pipeline_result and "results" in pipeline_result:
        graph_scores = [
            h["graph_score"] for h in pipeline_result["results"]
            if isinstance(h.get("graph_score"), (int, float))
        ]
        if graph_scores:
            max_graph = max(graph_scores)

    if max_graph > GRAPH_THRESHOLD:
        problems.append("high_graph_overlap")

    # 3. Crowded Patent Space Check
    density = 0
    landscape_score = 1.0  # Favorable by default

    if evaluation_result and "landscape" in evaluation_result:
        land = evaluation_result["landscape"]
        if isinstance(land.get("score"), (int, float)):
            landscape_score = land["score"]
        if isinstance(land.get("density"), int):
            density = land["density"]
    elif pipeline_result and "results" in pipeline_result:
        # Fallback to computing density from pipeline results
        semantic_scores = [
            h["semantic_score"] for h in pipeline_result["results"]
            if isinstance(h.get("semantic_score"), (int, float))
        ]
        density = sum(1 for s in semantic_scores if s >= 0.50)

    if landscape_score < LANDSCAPE_THRESHOLD or density > DENSITY_THRESHOLD:
        problems.append("crowded_domain")

    # 4. Low Novelty Check
    novelty_score = 100.0
    non_obviousness_score = 100.0
    patentability_score = 100.0

    if evaluation_result:
        if "novelty" in evaluation_result and isinstance(evaluation_result["novelty"].get("score"), (int, float)):
            novelty_score = evaluation_result["novelty"]["score"]
        if "non_obviousness" in evaluation_result and isinstance(evaluation_result["non_obviousness"].get("score"), (int, float)):
            non_obviousness_score = evaluation_result["non_obviousness"]["score"]
        if isinstance(evaluation_result.get("patentability_score"), (int, float)):
            patentability_score = evaluation_result["patentability_score"]
    
    if (
        novelty_score < NOVELTY_SCORE_THRESHOLD or 
        non_obviousness_score < NON_OBVIOUSNESS_SCORE_THRESHOLD or 
        patentability_score < PATENTABILITY_SCORE_THRESHOLD
    ):
        problems.append("low_novelty")

    logger.info(
        "Overlap analysis: max_sem=%.3f, max_graph=%.3f, landscape=%.3f, density=%d, novelty_score=%.1f, non_obv=%.1f, pat_score=%.1f -> problems=%s",
        max_semantic, max_graph, landscape_score, density, novelty_score, non_obviousness_score, patentability_score, problems
    )

    return problems

def detect_weaknesses(
    pipeline_result: Optional[Dict[str, Any]],
    evaluation_result: Optional[Dict[str, Any]],
    problems: List[str]
) -> List[str]:
    """
    Deterministic translator of metrics into human-readable technical weaknesses.
    """
    weaknesses = []

    # Gather metrics for reporting in strings
    max_semantic = 0.0
    max_graph = 0.0
    density = 0
    landscape_score = 1.0
    novelty_score = 100.0
    non_obviousness_score = 100.0
    patentability_score = 100.0

    if pipeline_result and "results" in pipeline_result:
        sem_scores = [h["semantic_score"] for h in pipeline_result["results"] if isinstance(h.get("semantic_score"), (int, float))]
        if sem_scores:
            max_semantic = max(sem_scores)
        g_scores = [h["graph_score"] for h in pipeline_result["results"] if isinstance(h.get("graph_score"), (int, float))]
        if g_scores:
            max_graph = max(g_scores)
            
    if evaluation_result:
        if "novelty" in evaluation_result:
            top_sem = evaluation_result["novelty"].get("top_semantic_score")
            if isinstance(top_sem, (int, float)):
                max_semantic = max(max_semantic, top_sem)
            if isinstance(evaluation_result["novelty"].get("score"), (int, float)):
                novelty_score = evaluation_result["novelty"]["score"]
        if "landscape" in evaluation_result:
            land = evaluation_result["landscape"]
            if isinstance(land.get("score"), (int, float)):
                landscape_score = land["score"]
            if isinstance(land.get("density"), int):
                density = land["density"]
        if "non_obviousness" in evaluation_result and isinstance(evaluation_result["non_obviousness"].get("score"), (int, float)):
            non_obviousness_score = evaluation_result["non_obviousness"]["score"]
        if isinstance(evaluation_result.get("patentability_score"), (int, float)):
            patentability_score = evaluation_result["patentability_score"]

    if "high_semantic_overlap" in problems:
        weaknesses.append(
            f"High semantic overlap: The user idea closely matches existing patent text (maximum similarity score: {max_semantic:.3f} exceeds threshold of {SEMANTIC_THRESHOLD})."
        )
    if "high_graph_overlap" in problems:
        weaknesses.append(
            f"Strong graph association: The user idea shows high structural similarity (maximum graph score: {max_graph:.3f} exceeds threshold of {GRAPH_THRESHOLD}) to an established patent family or CPC code group."
        )
    if "crowded_domain" in problems:
        weaknesses.append(
            f"Crowded innovation space: There is a high density of active prior art ({density} active patents) and the competitive landscape room to maneuver is limited (landscape score: {landscape_score:.3f} < {LANDSCAPE_THRESHOLD})."
        )
    if "low_novelty" in problems:
        weaknesses.append(
            f"Low novelty/patentability potential: The evaluation metrics are weak (overall patentability: {patentability_score}/100, novelty score: {novelty_score}/100, non-obviousness: {non_obviousness_score}/100)."
        )

    # Fallback if no problems detected
    if not weaknesses:
        weaknesses.append("No critical patentability or overlap weaknesses detected based on system metrics.")

    return weaknesses
