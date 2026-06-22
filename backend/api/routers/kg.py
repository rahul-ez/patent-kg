"""
Knowledge Graph router.
  POST /api/kg/build   — write patent subgraph to Neo4j
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


# ── Helper: build KG and return node/edge counts ──────────────────────────────

def _build_kg_and_count(patent_ids: List[str]) -> dict:
    """Build Neo4j subgraph and return node + edge type counts."""
    from neo4j import GraphDatabase
    from kg.builder import KGBuilder

    with KGBuilder() as builder:
        builder.build_subgraph(patent_ids)

    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
    )
    try:
        with driver.session() as session:
            node_rows = session.run(
                "MATCH (n) WITH labels(n)[0] AS lbl, count(n) AS cnt "
                "RETURN lbl, cnt ORDER BY lbl"
            ).data()
            edge_rows = session.run(
                "MATCH ()-[r]->() WITH type(r) AS t, count(r) AS cnt "
                "RETURN t, cnt ORDER BY t"
            ).data()
    finally:
        driver.close()

    nodes = {row["lbl"]: row["cnt"] for row in node_rows if row["lbl"]}
    edges = {row["t"]: row["cnt"] for row in edge_rows if row["t"]}
    return {"nodes": nodes, "edges": edges}


# ── POST /api/kg/build ────────────────────────────────────────────────────────

@router.post("/kg/build", response_model=KGBuildResponse)
async def build_kg(req: KGBuildRequest) -> KGBuildResponse:
    """Write a patent subgraph to Neo4j and return node/edge statistics."""
    if not req.patent_ids:
        raise HTTPException(status_code=422, detail="patent_ids cannot be empty.")
    try:
        stats = _build_kg_and_count(req.patent_ids)
        return KGBuildResponse(**stats)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"KG build failed: {exc}") from exc


# ── POST /api/kg/expand ───────────────────────────────────────────────────────

@router.post("/kg/expand", response_model=KGExpandResponse)
async def expand_kg(req: KGExpandRequest) -> KGExpandResponse:
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
async def get_kg_graph(
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
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
        )
        try:
            with driver.session() as session:
                result = session.run(
                    """
                    MATCH (n)-[r]->(m)
                    RETURN n, r, m
                    LIMIT 200
                    """
                )
                rows = list(result)
        finally:
            driver.close()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Neo4j query failed: {exc}") from exc

    # Build node + edge sets
    node_map: dict = {}  # node_key -> node properties
    rf_edges = []

    NODE_TYPE_MAP = {
        "Patent": "patent",
        "Assignee": "company",
        "CPC": "cpc",
        "Inventor": "inventor",
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
                    "_label": props.get("patent_id") or props.get("name") or props.get("code") or nid[:8],
                    "_title": props.get("title", ""),
                    **props,
                }

        src_id = str(n.element_id)
        tgt_id = str(m.element_id)
        rel_type = r.type
        rf_edges.append({
            "id": f"e-{src_id}-{tgt_id}-{rel_type}",
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
