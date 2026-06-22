"""
Combination Difficulty Scorer
==============================
Measures how hard it would be for a skilled engineer to combine the extracted
concepts. Higher difficulty = more non-obvious.

Three signals:
1. CPC tree distance   — how far apart concepts are in the patent classification tree
2. KG path distance    — shortest Neo4j path between concept patent clusters
3. Embedding distance  — cosine distance between concept embeddings

Score: 0 (trivial combination) → 1 (very difficult to combine)
"""

import logging
import os
import re
from typing import List, Tuple

import numpy as np
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

from .per_concept_search import ConceptSearchResult


# ── CPC Tree Distance ──────────────────────────────────────────────────────────

def _parse_cpc(code: str) -> Tuple[str, ...]:
    """
    Parse CPC code into hierarchical components.
    G06N3/0454 → ('G', '06', 'N', '3', '0454')
    A61B5/369  → ('A', '61', 'B', '5', '369')
    """
    code = code.strip().upper()
    m = re.match(r'^([A-H])(\d{2})([A-Z])(?:(\d+)(?:/(\w+))?)?', code)
    if not m:
        return (code[0],) if code else ()
    return tuple(g for g in m.groups() if g is not None)


def _cpc_pair_distance(code_a: str, code_b: str) -> float:
    """Normalised tree distance between two CPC codes. 0 = identical, 1 = no overlap."""
    a = _parse_cpc(code_a)
    b = _parse_cpc(code_b)
    if not a or not b:
        return 1.0
    max_depth = max(len(a), len(b))
    shared = 0
    for x, y in zip(a, b):
        if x != y:
            break
        shared += 1
    return 1.0 - (shared / max_depth)


def _concept_cpc_distance(codes_a: List[str], codes_b: List[str]) -> float:
    """Mean pairwise CPC distance between two concept clusters."""
    if not codes_a or not codes_b:
        return 0.5
    dists = [
        _cpc_pair_distance(ca, cb)
        for ca in codes_a[:10]
        for cb in codes_b[:10]
    ]
    return float(np.mean(dists)) if dists else 0.5


def cpc_tree_distance(results: List[ConceptSearchResult]) -> float:
    """Average pairwise CPC distance across all concept pairs. 0–1."""
    if len(results) < 2:
        return 0.0
    scores = []
    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            scores.append(_concept_cpc_distance(
                results[i].all_cpc_codes,
                results[j].all_cpc_codes,
            ))
    return float(np.mean(scores)) if scores else 0.5


# ── KG Path Distance ───────────────────────────────────────────────────────────

def kg_path_distance(results: List[ConceptSearchResult], max_hops: int = 6) -> float:
    """
    Shortest-path length between top patent nodes of each concept pair in Neo4j.
    Longer path = more isolated = higher difficulty. Returns 0.5 if Neo4j offline.
    """
    if len(results) < 2:
        return 0.0

    top_ids = [r.hits[0].patent_id for r in results if r.hits]
    if len(top_ids) < 2:
        return 0.5

    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "")),
        )
        path_lengths = []
        with driver.session() as session:
            for i in range(len(top_ids)):
                for j in range(i + 1, len(top_ids)):
                    row = session.run(
                        f"""
                        MATCH (a:Patent {{patent_id: $id_a}}), (b:Patent {{patent_id: $id_b}})
                        MATCH p = shortestPath((a)-[*..{max_hops}]-(b))
                        RETURN length(p) AS dist LIMIT 1
                        """,
                        id_a=top_ids[i], id_b=top_ids[j],
                    ).single()
                    path_lengths.append(row["dist"] if row else max_hops)
        driver.close()
        return min(float(np.mean(path_lengths)) / max_hops, 1.0)
    except Exception as exc:
        logger.warning("KG path distance skipped (%s) — neutral 0.5.", exc)
        return 0.5


# ── Embedding Distance ─────────────────────────────────────────────────────────

def embedding_distance(results: List[ConceptSearchResult]) -> float:
    """
    Average pairwise cosine distance between concept label embeddings.
    Score 0–1: higher = concepts live in more distant embedding regions.
    """
    if len(results) < 2:
        return 0.0
    try:
        import faiss as faiss_lib
        from integration.pipeline import _get_model
        model = _get_model()
        texts = [f"{r.concept.label}. {r.concept.description}" for r in results]
        vecs = model.encode(texts, convert_to_numpy=True).astype("float32")
        faiss_lib.normalize_L2(vecs)
        dists = []
        for i in range(len(vecs)):
            for j in range(i + 1, len(vecs)):
                cos_sim  = float(np.dot(vecs[i], vecs[j]))
                cos_dist = (1.0 - cos_sim) / 2.0   # [-1,1] → [0,1]
                dists.append(cos_dist)
        return float(np.mean(dists)) if dists else 0.5
    except Exception as exc:
        logger.warning("Embedding distance failed (%s) — neutral 0.5.", exc)
        return 0.5


# ── Combined Scorer ────────────────────────────────────────────────────────────

def score_combination_difficulty(
    results: List[ConceptSearchResult],
    w_cpc: float = 0.40,
    w_kg:  float = 0.30,
    w_emb: float = 0.30,
) -> dict:
    """
    Compute combined combination difficulty from three signals.

    Returns
    -------
    dict: score (0–1), sub-scores, interpretation
    """
    cpc_dist = cpc_tree_distance(results)
    kg_dist  = kg_path_distance(results)
    emb_dist = embedding_distance(results)

    score = w_cpc * cpc_dist + w_kg * kg_dist + w_emb * emb_dist

    if score >= 0.75:
        interp = "Very hard to combine — concepts span distant technology domains"
    elif score >= 0.55:
        interp = "Moderately difficult — requires cross-domain expertise"
    elif score >= 0.35:
        interp = "Somewhat difficult — field overlap exists but connection is non-trivial"
    else:
        interp = "Easy to combine — concepts are closely related in the prior art"

    logger.info(
        "Combination difficulty: %.3f (CPC=%.3f, KG=%.3f, Emb=%.3f)",
        score, cpc_dist, kg_dist, emb_dist,
    )
    return {
        "score":          round(score, 4),
        "cpc_distance":   round(cpc_dist, 4),
        "kg_path_dist":   round(kg_dist, 4),
        "embedding_dist": round(emb_dist, 4),
        "interpretation": interp,
    }
