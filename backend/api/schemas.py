from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class PipelineRequest(BaseModel):
    idea: str
    top_k: int = Field(default=10, ge=1, le=100)
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
    top_k: int = Field(default=10, ge=1, le=100)
    gnn_mode: str = "novelty"
    run_fast: bool = False
    n_reconstruction_samples: int = Field(default=5, ge=1, le=10)
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
    patent_ids: List[str] = Field(min_length=1, max_length=100)


class KGBuildResponse(BaseModel):
    nodes: Dict[str, int]
    edges: Dict[str, int]


class KGExpandRequest(BaseModel):
    patent_ids: List[str] = Field(min_length=1, max_length=100)
    cpc_cap: int = Field(default=10, ge=1, le=100)


class KGExpandResponse(BaseModel):
    family: List[Dict[str, Any]]
    cpc_siblings: List[Dict[str, Any]]
    total_added: int


class KGGraphResponse(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
