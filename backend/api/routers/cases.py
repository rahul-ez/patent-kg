"""CRUD endpoints for persisted DBMS-lab analysis cases and SQL reports."""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from api.schemas import AnalysisCaseCreate, AnalysisCaseResponse, AnalysisCaseUpdate, ReportResponse  # noqa: E402

router = APIRouter(tags=["analysis-cases", "reports"])


def _store():
    from persistence import analysis_store
    from persistence.database import DatabaseUnavailable
    return analysis_store, DatabaseUnavailable


@router.post("/cases", response_model=AnalysisCaseResponse, status_code=201)
def create_analysis_case(payload: AnalysisCaseCreate):
    store, unavailable = _store()
    try:
        return store.create_case(payload.title, payload.idea_text)
    except unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/cases", response_model=list[AnalysisCaseResponse])
def list_analysis_cases(limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0)):
    store, unavailable = _store()
    try:
        return store.list_cases(limit, offset)
    except unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/cases/{case_id}", response_model=AnalysisCaseResponse)
def read_analysis_case(case_id: str):
    store, unavailable = _store()
    try:
        result = store.get_case(case_id)
    except unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis case not found.")
    return result


@router.patch("/cases/{case_id}", response_model=AnalysisCaseResponse)
def update_analysis_case(case_id: str, payload: AnalysisCaseUpdate):
    if payload.status is not None and payload.status not in {"draft", "active", "archived"}:
        raise HTTPException(status_code=422, detail="status must be draft, active, or archived.")
    store, unavailable = _store()
    try:
        result = store.update_case(case_id, payload.title, payload.idea_text, payload.status)
    except unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis case not found.")
    return result


@router.delete("/cases/{case_id}", status_code=204)
def remove_analysis_case(case_id: str):
    store, unavailable = _store()
    try:
        deleted = store.delete_case(case_id)
    except unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Analysis case not found.")
    return Response(status_code=204)


@router.get("/reports/{report}", response_model=ReportResponse)
def read_report(report: str, limit: int = Query(default=20, ge=1, le=100)):
    store, unavailable = _store()
    try:
        return {"report": report, "rows": store.report_rows(report, limit)}
    except unavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
