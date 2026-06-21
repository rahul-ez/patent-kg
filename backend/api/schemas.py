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
