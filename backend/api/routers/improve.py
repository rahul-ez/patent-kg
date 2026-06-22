from __future__ import annotations

import logging
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from improvement.schemas import ImprovementRequest, ImprovementResponse
from improvement.agent import ImprovementAgent

logger = logging.getLogger("api.routers.improve")
router = APIRouter(tags=["improvement"])

@router.post("/improve", response_model=ImprovementResponse)
async def improve_idea(req: ImprovementRequest):
    """
    Generate structured patent improvement recommendations.
    
    If pipeline_result or evaluation_result are not provided, they are dynamically computed on the fly.
    """
    idea_stripped = req.idea.strip()
    if not idea_stripped:
        raise HTTPException(status_code=400, detail="User idea cannot be empty or whitespace.")

    pipeline_res = req.pipeline_result
    eval_res = req.evaluation_result

    # 1. Run pipeline if missing
    if not pipeline_res:
        logger.info("Pipeline result not provided. Executing end-to-end retrieval and GNN inference...")
        try:
            from integration.pipeline import run_end_to_end
            pipeline_res = run_end_to_end(idea_stripped, top_k=10)
        except Exception as exc:
            logger.error("End-to-end pipeline execution failed during improvement processing: %s", exc)
            raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(exc)}")

    # 2. Run evaluation engine if missing
    if not eval_res:
        logger.info("Evaluation result not provided. Running patentability scoring engine...")
        try:
            from evaluation.patentability_engine import run_evaluation
            hits = pipeline_res.get("results", [])
            eval_res = run_evaluation(
                user_idea=idea_stripped,
                hits=hits,
                top_k_concepts=5,
                run_fast=True  # Fast mode for API response latency
            )
        except Exception as exc:
            logger.error("Evaluation engine execution failed during improvement processing: %s", exc)
            raise HTTPException(status_code=500, detail=f"Evaluation scoring failed: {str(exc)}")

    # 3. Run orchestrator agent
    try:
        agent = ImprovementAgent()
        output = agent.run_improvement_pipeline(
            user_idea=idea_stripped,
            pipeline_result=pipeline_res,
            evaluation_result=eval_res
        )
        return output
    except Exception as exc:
        logger.error("Improvement agent orchestration failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Improvement generation failed: {str(exc)}")
