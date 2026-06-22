"""
Per-Concept FAISS Search
========================
Given a list of extracted Concept objects, embeds each one with PatentSBERTa
and runs an independent FAISS search against the full 58K patent index.

Returns a ConceptSearchResult per concept, each holding its top-k patent hits
enriched with metadata (title, abstract, domain, citation count, publication year,
CPC codes). The CPC codes are fetched from Neo4j so downstream scorers
(combination_difficulty, cross_domain_novelty, citation_isolation) can work
directly with concept → patent → CPC mappings without additional DB calls.

Usage:
    from evaluation.concept_extractor import extract_concepts
    from evaluation.per_concept_search import search_per_concept

    concepts = extract_concepts(idea)
    results  = search_per_concept(concepts, top_k=5)
    for r in results:
        print(r.concept.label, "→", [h.patent_id for h in r.hits])
"""

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

from .concept_extractor import Concept


# ── Data models ────────────────────────────────────────────────────────────────

@dataclass
class ConceptHit:
    """A single patent returned for one concept."""
    patent_id: str
    title: str
    abstract: str
    domain: str
    score: float                        # cosine similarity (0–1)
    cited_by_patent_count: str          # kept as string — matches CSV dtype
    publication_year: str
    url: str
    cpc_codes: List[str] = field(default_factory=list)   # populated from Neo4j


@dataclass
class ConceptSearchResult:
    """All search results for a single extracted concept."""
    concept: Concept
    hits: List[ConceptHit]

    @property
    def top_score(self) -> float:
        return self.hits[0].score if self.hits else 0.0

    @property
    def all_cpc_codes(self) -> List[str]:
        codes = []
        for h in self.hits:
            codes.extend(h.cpc_codes)
        return list(dict.fromkeys(codes))   # preserve order, deduplicate


# ── Shared resource loader ─────────────────────────────────────────────────────
# Reuses the cached index, metadata, and DataFrame already loaded by the pipeline.
# Importing from integration.pipeline avoids double-loading the 768-dim index.

def _load_faiss_resources():
    """
    Returns (faiss_index, metadata_dict, patents_df) from the pipeline cache.
    If the pipeline's DataFrame is empty (patents_deduped.csv missing), falls
    back to loading the original patents.csv independently.
    """
    try:
        from integration.pipeline import _load_resources
        index, metadata, df = _load_resources()
        if df.empty:
            logger.info("Pipeline DataFrame is empty — loading CSV independently.")
            _, _, df = _load_resources_direct(index_only=False)
        return index, metadata, df
    except Exception as exc:
        logger.warning("Could not reuse pipeline cache (%s) — loading independently.", exc)
        return _load_resources_direct()


def _load_resources_direct(index_only: bool = False):
    """
    Independent FAISS + metadata loader for cases where pipeline isn't cached.
    Mirrors the logic in integration/pipeline.py.
    """
    import json
    import faiss
    import pandas as pd
    from config.paths import VECTOR_STORE

    index_path    = VECTOR_STORE / "patents.index"
    metadata_path = VECTOR_STORE / "metadata_mapping.json"
    csv_path      = VECTOR_STORE / "patents_deduped.csv"

    if not index_path.exists():
        raise FileNotFoundError(
            f"FAISS index not found at '{index_path}'. "
            "Run: python scripts/build_faiss_index.py"
        )

    index = faiss.read_index(str(index_path))
    logger.info("FAISS index loaded directly: %d vectors, dim=%d", index.ntotal, index.d)

    if metadata_path.exists():
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        metadata = {str(i): f"UNKNOWN_{i}" for i in range(index.ntotal)}
        logger.warning("metadata_mapping.json missing — patent IDs will be UNKNOWN_*")

    _USECOLS = ["patent_id", "title", "abstract", "domain",
                "cited_by_patent_count", "publication_year", "url"]

    if csv_path.exists():
        df = pd.read_csv(csv_path, usecols=_USECOLS, dtype=str).fillna("")
    else:
        # Fallback: try the original patents.csv at the project data root
        from config.paths import PROCESSED_DATA, ROOT
        fallbacks = [
            PROCESSED_DATA / "patents.csv",
            ROOT / "data" / "processed" / "patents.csv",
            ROOT / "patents.csv",
            ROOT.parent / "patents.csv",   # C:\PantentsAI\patents.csv
        ]
        fallback_df = None
        for fb in fallbacks:
            if fb.exists():
                available = pd.read_csv(fb, nrows=0).columns.tolist()
                cols = [c for c in _USECOLS if c in available]
                fallback_df = pd.read_csv(fb, usecols=cols, dtype=str).fillna("")
                logger.info("Using fallback CSV: %s (%d rows)", fb, len(fallback_df))
                break
        if fallback_df is not None:
            df = fallback_df
        else:
            df = pd.DataFrame(columns=_USECOLS)
            logger.warning("No patents CSV found — patent metadata will be empty.")

    return index, metadata, df


# ── Model loader — auto-detects the FAISS index dimension ─────────────────────
# dim=384 → all-MiniLM-L6-v2  (original index)
# dim=768 → AI-Growth-Lab/PatentSBERTa  (rebuilt index)
_DIM_TO_MODEL = {
    384: "all-MiniLM-L6-v2",
    768: "AI-Growth-Lab/PatentSBERTa",
}

_st_model = None

def _get_model(index_dim: int = 384):
    global _st_model
    if _st_model is not None:
        return _st_model

    model_name = _DIM_TO_MODEL.get(index_dim)
    if model_name is None:
        raise ValueError(
            f"Unknown FAISS index dimension {index_dim}. "
            f"Expected one of {list(_DIM_TO_MODEL.keys())}."
        )

    # Try to reuse the already-loaded pipeline model (same dim = same model)
    try:
        from integration.pipeline import _get_model as _pipeline_model, _st_model as _pm
        if _pm is not None:
            _st_model = _pm
            logger.info("Reusing pipeline SentenceTransformer (%s).", model_name)
            return _st_model
    except Exception:
        pass

    from sentence_transformers import SentenceTransformer
    logger.info("Loading SentenceTransformer '%s' ...", model_name)
    _st_model = SentenceTransformer(model_name)
    return _st_model


# ── CPC enrichment from Neo4j ──────────────────────────────────────────────────

def _fetch_cpc_codes(patent_ids: List[str]) -> dict:
    """
    Query Neo4j for CPC codes of the given patent IDs.
    Returns {patent_id: [code, code, ...]} dict.
    Silently returns empty dict if Neo4j is offline — CPC data is optional here.
    """
    if not patent_ids:
        return {}

    try:
        from neo4j import GraphDatabase
        uri  = os.getenv("NEO4J_URI",      "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER",     "neo4j")
        pwd  = os.getenv("NEO4J_PASSWORD", "")

        driver = GraphDatabase.driver(uri, auth=(user, pwd))
        with driver.session() as session:
            rows = session.run(
                """
                MATCH (p:Patent)-[:HAS_CPC]->(c:CPCCode)
                WHERE p.patent_id IN $ids
                RETURN p.patent_id AS patent_id, collect(c.code) AS codes
                """,
                ids=patent_ids,
            ).data()
        driver.close()

        return {row["patent_id"]: row["codes"] for row in rows}

    except Exception as exc:
        logger.warning("Neo4j CPC fetch skipped (%s) — CPC codes will be empty.", exc)
        return {}


# ── Core search function ───────────────────────────────────────────────────────

def search_per_concept(
    concepts: List[Concept],
    top_k: int = 5,
    enrich_cpc: bool = True,
) -> List[ConceptSearchResult]:
    """
    Embed each concept and retrieve its closest patents from the FAISS index.

    Parameters
    ----------
    concepts : List[Concept]
        Concepts from extract_concepts().
    top_k : int
        Number of patent hits per concept (default 5).
    enrich_cpc : bool
        Whether to fetch CPC codes from Neo4j for each hit (default True).
        Set False for faster execution when CPC data is not yet needed.

    Returns
    -------
    List[ConceptSearchResult]
        One result per concept, each with up to top_k ConceptHit objects.
    """
    if not concepts:
        return []

    import faiss as faiss_lib

    index, metadata, patents_df = _load_faiss_resources()
    model = _get_model(index_dim=index.d)

    # Build a lookup for fast metadata access
    patent_lookup = (
        patents_df.set_index("patent_id").to_dict("index")
        if not patents_df.empty
        else {}
    )

    results: List[ConceptSearchResult] = []

    for concept in concepts:
        query_text = f"{concept.label}. {concept.description}"
        logger.info("Searching FAISS for concept: '%s'", concept.label)

        # Embed and L2-normalise (must match how the index was built)
        vec = model.encode([query_text], convert_to_numpy=True).astype("float32")
        faiss_lib.normalize_L2(vec)

        distances, indices = index.search(vec, top_k)
        distances = distances[0]
        indices   = indices[0]

        hits: List[ConceptHit] = []
        for idx, score in zip(indices, distances):
            if idx == -1:
                continue

            patent_id = metadata.get(str(idx), f"UNKNOWN_{idx}")
            row = patent_lookup.get(patent_id, {})

            hits.append(ConceptHit(
                patent_id            = patent_id,
                title                = row.get("title", ""),
                abstract             = (row.get("abstract", "")[:300] + "..."
                                        if len(row.get("abstract", "")) > 300
                                        else row.get("abstract", "")),
                domain               = row.get("domain", ""),
                score                = round(float(score), 6),
                cited_by_patent_count= row.get("cited_by_patent_count", "0"),
                publication_year     = row.get("publication_year", ""),
                url                  = row.get("url", ""),
                cpc_codes            = [],   # populated below
            ))

        logger.info(
            "  Concept '%s' → %d hits (top score: %.4f)",
            concept.label, len(hits), hits[0].score if hits else 0.0,
        )

        results.append(ConceptSearchResult(concept=concept, hits=hits))

    # ── CPC enrichment (single batch Neo4j call across all concepts) ──────────
    if enrich_cpc and results:
        all_patent_ids = list({
            h.patent_id
            for r in results
            for h in r.hits
            if not h.patent_id.startswith("UNKNOWN")
        })
        cpc_map = _fetch_cpc_codes(all_patent_ids)

        for result in results:
            for hit in result.hits:
                hit.cpc_codes = cpc_map.get(hit.patent_id, [])

        logger.info("CPC enrichment complete: %d patents enriched.", len(cpc_map))

    return results


# ── Convenience summary ────────────────────────────────────────────────────────

def summarise_concept_map(results: List[ConceptSearchResult]) -> dict:
    """
    Returns a JSON-serialisable summary of the concept map suitable for API
    responses and the frontend concept map UI component.
    """
    return {
        "concepts": [
            {
                "label":       r.concept.label,
                "description": r.concept.description,
                "domain_hint": r.concept.domain_hint,
                "top_score":   r.top_score,
                "hits": [
                    {
                        "patent_id":             h.patent_id,
                        "title":                 h.title,
                        "domain":                h.domain,
                        "score":                 h.score,
                        "cited_by_patent_count": h.cited_by_patent_count,
                        "publication_year":      h.publication_year,
                        "cpc_codes":             h.cpc_codes[:5],   # top 5 per hit
                        "url":                   h.url,
                    }
                    for h in r.hits
                ],
                "all_cpc_codes": r.all_cpc_codes[:20],
            }
            for r in results
        ]
    }
