from __future__ import annotations
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

class ImprovementRequest(BaseModel):
    idea: str
    pipeline_result: Optional[Dict[str, Any]] = None
    evaluation_result: Optional[Dict[str, Any]] = None

class StrategyItem(BaseModel):
    strategy: str
    impact: str
    reason: str

class OverlappingPatentItem(BaseModel):
    patent_id: str
    title: str
    similarity: float

class ImprovementResponse(BaseModel):
    diagnosis: List[str]
    weaknesses: List[str]
    strategies: List[StrategyItem]
    alternative_directions: List[str]
    recommendations: str
    overlapping_patents: List[OverlappingPatentItem]
