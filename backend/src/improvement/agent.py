import logging
from typing import Any, Dict, List, Optional

from .analyzer import analyze_overlap, detect_weaknesses
from .strategies import choose_improvement_strategies, identify_primary_domain
from .opportunity_finder import find_low_density_opportunities
from .generator import generate_llm_explanation
from .config import TOP_N_OVERLAPPING

logger = logging.getLogger(__name__)

# Clean diagnosis name mapping for client display
DIAGNOSIS_MAP = {
    "high_semantic_overlap": "high semantic overlap",
    "high_graph_overlap": "strong graph similarity",
    "crowded_domain": "crowded patent domain",
    "low_novelty": "low novelty"
}

class ImprovementAgent:
    """
    Orchestrator for the Improvement Agent pipeline.
    
    Coordinates the steps:
    1. Overlap Analyzer & Weakness Detector (analyzer.py)
    2. Domain Classifier & Strategy Selection Engine (strategies.py)
    3. Low-Density Opportunity Finder (opportunity_finder.py)
    4. Explanation Generator (generator.py)
    """

    def run_improvement_pipeline(
        self,
        user_idea: str,
        pipeline_result: Optional[Dict[str, Any]] = None,
        evaluation_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Orchestrate the overlap analyzer, strategy selector, low density opportunity finder,
        and Gemini explanation generator into the final structured output dictionary.
        """
        logger.info("=== Improvement Agent Pipeline START ===")
        
        # 1. Extract candidate patents
        retrieved_patents = []
        if pipeline_result and "results" in pipeline_result:
            retrieved_patents = pipeline_result["results"]

        # 2. Identify primary domain
        domain = identify_primary_domain(user_idea, retrieved_patents)
        logger.info("Improvement Orchestrator: identified primary domain '%s'", domain)

        # 3. Run Overlap Analyzer
        problem_keys = analyze_overlap(pipeline_result, evaluation_result)
        
        # Convert internal keys to client-friendly names
        diagnosis = [DIAGNOSIS_MAP.get(k, k) for k in problem_keys]
        
        # 4. Detect Weaknesses
        weaknesses = detect_weaknesses(pipeline_result, evaluation_result, problem_keys)
        
        # 5. Domain-Aware Strategy Selection
        strategies = choose_improvement_strategies(problem_keys, domain)
        
        # 6. Opportunity Finder
        alternative_directions = find_low_density_opportunities(user_idea, retrieved_patents)
        
        # 7. Extract Top Overlapping Patents
        overlapping_patents = []
        if retrieved_patents:
            # Sort retrieved patents by semantic score descending to find closest prior art
            sorted_hits = sorted(
                retrieved_patents,
                key=lambda h: h.get("semantic_score") or 0.0,
                reverse=True
            )
            for hit in sorted_hits[:TOP_N_OVERLAPPING]:
                overlapping_patents.append({
                    "patent_id": hit.get("patent_id", "Unknown"),
                    "title": hit.get("title", "Unknown"),
                    "similarity": round(float(hit.get("semantic_score") or 0.0), 4)
                })
        
        # 8. LLM Explanation Generator
        recommendations = generate_llm_explanation(
            idea=user_idea,
            diagnosis=diagnosis,
            weaknesses=weaknesses,
            strategies=strategies,
            alternative_directions=alternative_directions
        )
        
        logger.info("=== Improvement Agent Pipeline COMPLETE ===")
        
        return {
            "diagnosis": diagnosis,
            "weaknesses": weaknesses,
            "strategies": strategies,
            "alternative_directions": alternative_directions,
            "recommendations": recommendations,
            "overlapping_patents": overlapping_patents
        }
