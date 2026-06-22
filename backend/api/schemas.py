from __future__ import annotations
from pydantic import BaseModel
from typing import Any, Dict, List, Optional


class PipelineRequest(BaseModel):
    idea: str
    top_k: int = 10
    gnn_mode: str = "novelty"


class PipelineResponse(BaseModel):
    query_id: str
    query_text: str
    nlp_result: Dict[str, Any]
    model: str
    top_k: int
    results: List[Dict[str, Any]]
    gnn_status: Optional[str] = None
    kg_status: Optional[str] = None


class EvaluateRequest(BaseModel):
    idea: str
    top_k: int = 10
    gnn_mode: str = "novelty"
    run_fast: bool = False
    n_reconstruction_samples: int = 5
    pipeline_result: Optional[Dict[str, Any]] = None  # pass existing hits to skip re-running pipeline


class EvaluateResponse(BaseModel):
    patentability_score: float
    patentability_raw: float
    verdict: str
    risk: str
    confidence: float
    novelty: Dict[str, Any]
    non_obviousness: Dict[str, Any]
    landscape: Dict[str, Any]
    claim_breadth: Dict[str, Any]
    timing: Dict[str, Any]
    india_eligibility: Dict[str, Any]
    technical_depth: Dict[str, Any]
    weights: Dict[str, float]
    contributions: Dict[str, float]
    concept_count: int
    concepts: List[Dict[str, Any]]
    elapsed_seconds: float
    fast_mode: bool


class KGBuildRequest(BaseModel):
    patent_ids: List[str]


class KGBuildResponse(BaseModel):
    nodes: Dict[str, int]
    edges: Dict[str, int]


class KGExpandRequest(BaseModel):
    patent_ids: List[str]
    cpc_cap: int = 10


class KGExpandResponse(BaseModel):
    family: List[Dict[str, Any]]
    cpc_siblings: List[Dict[str, Any]]
    total_added: int


class KGGraphResponse(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
