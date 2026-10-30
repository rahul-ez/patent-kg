"""
Pipeline router — POST /api/pipeline/run
"""
from __future__ import annotations

import sys
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

# Ensure backend/src/ is importable
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from api.schemas import PipelineRequest, PipelineResponse  # noqa: E402
from api.persistence import attach_saving_status
from api.auth import Principal, require_user

router = APIRouter(tags=["pipeline"])


@router.post("/pipeline/run", response_model=PipelineResponse)
def run_pipeline(req: PipelineRequest, user: Principal = Depends(require_user)) -> PipelineResponse:
    """
    Execute the full end-to-end patent analysis pipeline.
    NLP → Embedding → FAISS retrieval → GNN re-ranking.
    This synchronous handler is run in FastAPI's thread pool, so model and
    database work do not block the async event loop.
    """
    if not req.idea.strip():
        raise HTTPException(status_code=422, detail="Idea text cannot be empty.")
    if req.gnn_mode not in ("novelty", "graph_sim"):
        raise HTTPException(status_code=422, detail="gnn_mode must be 'novelty' or 'graph_sim'.")

    try:
        from persistence.analysis_store import get_case
        if req.case_id and get_case(req.case_id, owner_user_id=user.user_id) is None:
            raise HTTPException(404, "Analysis case not found.")
        from integration.pipeline import run_end_to_end
        result = run_end_to_end(req.idea.strip(), top_k=req.top_k, gnn_mode=req.gnn_mode)
        from persistence.analysis_store import persist_pipeline_result
        result = attach_saving_status(result, lambda: persist_pipeline_result(
                idea=req.idea.strip(), top_k=req.top_k, gnn_mode=req.gnn_mode,
                pipeline_result=result, case_id=req.case_id, case_title=req.case_title, owner_user_id=user.user_id,
        ))
        if req.case_id and not result.get("case_id"):
            result["case_id"] = req.case_id
        return PipelineResponse(**result)
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Pipeline resource not found: {exc}. Run build scripts first.",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
