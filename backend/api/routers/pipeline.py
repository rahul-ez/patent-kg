"""
Pipeline router — POST /api/pipeline/run
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

# Ensure backend/src/ is importable
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from api.schemas import PipelineRequest, PipelineResponse  # noqa: E402

router = APIRouter(tags=["pipeline"])


@router.post("/pipeline/run", response_model=PipelineResponse)
async def run_pipeline(req: PipelineRequest) -> PipelineResponse:
    """
    Execute the full end-to-end patent analysis pipeline.
    NLP → Embedding → FAISS retrieval → GNN re-ranking.
    This is a blocking call; it may take 30-90 seconds on first load.
    """
    if not req.idea.strip():
        raise HTTPException(status_code=422, detail="Idea text cannot be empty.")
    if req.gnn_mode not in ("novelty", "graph_sim"):
        raise HTTPException(status_code=422, detail="gnn_mode must be 'novelty' or 'graph_sim'.")

    try:
        from integration.pipeline import run_end_to_end
        result = run_end_to_end(req.idea.strip(), top_k=req.top_k, gnn_mode=req.gnn_mode)
        return PipelineResponse(**result)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Pipeline resource not found: {exc}. Run build scripts first.",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
