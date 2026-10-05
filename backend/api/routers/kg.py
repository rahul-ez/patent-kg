"""
Knowledge Graph router.
  GET  /api/kg/stats   — read statistics for the displayed graph slice
  POST /api/kg/build   — deprecated, read-only statistics compatibility alias
  POST /api/kg/expand  — find family + CPC sibling patents
  GET  /api/kg/graph   — return React Flow compatible node/edge JSON
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from api.schemas import (
    KGBuildRequest, KGBuildResponse,
    KGExpandRequest, KGExpandResponse,
    KGGraphResponse,
)

router = APIRouter(tags=["kg"])

_GRAPH_EDGE_LIMIT = 200
_SCOPED_GRAPH_QUERY = """
MATCH (seed:Patent)
WHERE seed.patent_id IN $ids
MATCH (seed)-[r]-(related)
WHERE related:Patent OR related:Company OR related:Inventor OR related:CPCCode OR related:Paper
RETURN seed AS n, r, related AS m
ORDER BY seed.patent_id, type(r)
LIMIT $limit
"""


def _scoped_graph_rows(patent_ids: List[str]) -> list:
    """Return only edges adjacent to the patents requested by this client."""
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
    )
    try:
        with driver.session() as session:
            return list(session.run(_SCOPED_GRAPH_QUERY, ids=patent_ids, limit=_GRAPH_EDGE_LIMIT))
    finally:
        driver.close()


def _counts_from_rows(rows: list) -> dict:
    """Count the graph slice that will actually be rendered, not the whole database."""
    nodes: dict[str, set[str]] = {}
    edges: dict[str, set[str]] = {}
    for row in rows:
        for node in (row["n"], row["m"]):
            label = next(iter(node.labels), "Unknown")
            nodes.setdefault(label, set()).add(str(node.element_id))
        edge_type = row["r"].type
        edges.setdefault(edge_type, set()).add(str(row["r"].element_id))
    return {"nodes": {label: len(ids) for label, ids in nodes.items()}, "edges": {label: len(ids) for label, ids in edges.items()}}


# ── Helper: read the rendered graph slice ───────────────────────────────────

def _graph_stats(patent_ids: List[str]) -> dict:
    """Viewing a graph must never write CSV facts into the MySQL projection."""
    return _counts_from_rows(_scoped_graph_rows(patent_ids))


# ── POST /api/kg/build ────────────────────────────────────────────────────────

@router.post("/kg/build", response_model=KGBuildResponse, deprecated=True)
def build_kg(req: KGBuildRequest) -> KGBuildResponse:
    """Compatibility endpoint: read statistics without rebuilding the graph."""
    if not req.patent_ids:
        raise HTTPException(status_code=422, detail="patent_ids cannot be empty.")
    try:
        stats = _graph_stats(req.patent_ids)
        return KGBuildResponse(**stats)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Graph statistics unavailable.") from exc


@router.get("/kg/stats", response_model=KGBuildResponse)
def read_graph_stats(patent_ids: str = Query(..., description="Comma-separated patent IDs")):
    ids = [value.strip() for value in patent_ids.split(",") if value.strip()]
    if not ids or len(ids) > 100:
        raise HTTPException(status_code=422, detail="Provide 1 to 100 patent IDs.")
    return KGBuildResponse(**_graph_stats(ids))


# ── POST /api/kg/expand ───────────────────────────────────────────────────────

@router.post("/kg/expand", response_model=KGExpandResponse)
def expand_kg(req: KGExpandRequest) -> KGExpandResponse:
    """Find family members and CPC siblings via Neo4j expansion."""
    if not req.patent_ids:
        raise HTTPException(status_code=422, detail="patent_ids cannot be empty.")
    try:
        from kg.expander import expand_via_kg
        result = expand_via_kg(req.patent_ids, cpc_cap=req.cpc_cap)
        return KGExpandResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"KG expand failed: {exc}") from exc


# ── GET /api/kg/graph ─────────────────────────────────────────────────────────

@router.get("/kg/graph", response_model=KGGraphResponse)
def get_kg_graph(
    patent_ids: str = Query(..., description="Comma-separated patent IDs"),
) -> KGGraphResponse:
    """
    Query Neo4j for nodes + relationships and return React Flow compatible JSON.
    Uses a circular layout to position nodes.
    """
    ids = [pid.strip() for pid in patent_ids.split(",") if pid.strip()]
    if not ids:
        raise HTTPException(status_code=422, detail="No valid patent_ids provided.")

    try:
        rows = _scoped_graph_rows(ids)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Neo4j query failed: {exc}") from exc

    # Build node + edge sets
    node_map: dict = {}  # node_key -> node properties
    rf_edges = []
    seen_relationships = set()

    NODE_TYPE_MAP = {
        "Patent": "patent",
        "Company": "company",
        "CPCCode": "cpc",
        "Inventor": "inventor",
        "Paper": "paper",
    }

    for row in rows:
        n, r, m = row["n"], row["r"], row["m"]

        for node in (n, m):
            # Neo4j node element_id as key
            nid = str(node.element_id)
            if nid not in node_map:
                labels = list(node.labels)
                node_type = labels[0] if labels else "Unknown"
                props = dict(node)
                node_map[nid] = {
                    "_element_id": nid,
                    "_type": node_type,
                    "_label": props.get("patent_id") or props.get("name") or props.get("company_name") or props.get("inventor_name") or props.get("code") or props.get("title") or nid[:8],
                    "_title": props.get("title", ""),
                    **props,
                }

        relationship_id = str(r.element_id)
        if relationship_id in seen_relationships:
            continue
        seen_relationships.add(relationship_id)
        # An undirected MATCH may return either seed first. Preserve the actual
        # stored relationship direction and allow distinct parallel edges.
        src_id = str(r.start_node.element_id)
        tgt_id = str(r.end_node.element_id)
        rel_type = r.type
        rf_edges.append({
            "id": f"e-{relationship_id}",
            "source": src_id,
            "target": tgt_id,
            "label": rel_type,
            "type": "smoothstep",
        })

    # Circular layout for nodes
    node_list = list(node_map.values())
    n_nodes = len(node_list)
    cx, cy, radius = 600, 400, min(350, max(150, n_nodes * 30))

    rf_nodes = []
    for i, node in enumerate(node_list):
        angle = (2 * math.pi * i) / max(n_nodes, 1)
        x = cx + radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        node_type_css = NODE_TYPE_MAP.get(node["_type"], "default")
        rf_nodes.append({
            "id": node["_element_id"],
            "type": node_type_css,
            "position": {"x": round(x, 1), "y": round(y, 1)},
            "data": {
                "label": str(node["_label"])[:30],
                "title": str(node["_title"])[:80],
                "nodeType": node["_type"],
            },
        })

    return KGGraphResponse(nodes=rf_nodes, edges=rf_edges)
