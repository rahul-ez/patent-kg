"""
End-to-End Integration Pipeline
=================================
Graph-Enhanced Patent Intelligence Platform

Bridges the NLP preprocessing layer and the semantic retrieval module.

Pipeline:
    raw user idea
        → NLP (process_user_query)       — extract clean_text, keywords, entities
        → prepare_retrieval_query()       — symmetric embedding format
        → FAISS index search              — top-k similar patents
        → metadata enrichment             — attach patent_id, title, abstract
        → RetrievalResponse               — structured JSON output

Usage:
    cd patent-kg/backend/
    python -m src.integration.pipeline

    Or as a library:
        from src.integration.pipeline import run_end_to_end
        response = run_end_to_end("neural implant for memory restoration", top_k=5)
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

# ── Import path setup ──────────────────────────────────────────────────────────
# Ensures `nlp` and `retrieval` packages are importable regardless of CWD.
_SRC_DIR = Path(__file__).resolve().parents[1]   # → backend/src/
sys.path.insert(0, str(_SRC_DIR))

from nlp.pipeline import process_user_query       # NLP layer (your code)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("integration.pipeline")

# ── Configuration ─────────────────────────────────────────────────────────────
_BACKEND_DIR   = Path(__file__).resolve().parents[2]          # → patent-kg/backend/
_PATENT_KG_DIR = _BACKEND_DIR.parent                          # → patent-kg/
_PROJECT_ROOT  = _PATENT_KG_DIR.parent                        # → project root
_VECTOR_DIR    = _PATENT_KG_DIR / "data" / "vector_store"     # → patent-kg/data/vector_store/
_PATENTS_CSV   = _PROJECT_ROOT / "patents.csv"
_FAISS_INDEX   = _VECTOR_DIR / "patents.index"
_METADATA_FILE = _VECTOR_DIR / "metadata_mapping.json"

_MODEL_NAME    = "all-MiniLM-L6-v2"   # Must match build_faiss_index.py

# ── Shared Types ──────────────────────────────────────────────────────────────
NLPResult = Dict[str, Any]
RetrievalHit = Dict[str, Any]
RetrievalResponse = Dict[str, Any]


# ══════════════════════════════════════════════════════════════════════════════
# 1. Query Preparation — ensures embedding symmetry with corpus
# ══════════════════════════════════════════════════════════════════════════════

def prepare_retrieval_query(nlp_result: NLPResult) -> str:
    """
    Extract the embedding-ready query string from an NLPResult.

    CRITICAL DESIGN DECISION:
    The corpus was indexed as `title + ". " + abstract` (raw, no boilerplate
    removal, no keyword appending).  To maintain query-corpus symmetry, we
    use ONLY `clean_text` here — not the keyword-augmented string that
    `prepare_embedding_input()` in pipeline.py produces.

    If you change the corpus indexing strategy, update this function to match.

    Args:
        nlp_result: Output dict from process_user_query() or process_patent().

    Returns:
        str: The query string to be embedded and searched.
    """
    clean_text = nlp_result.get("clean_text", "").strip()
    if not clean_text:
        raise ValueError(
            "NLPResult has empty 'clean_text'. "
            "Check that process_user_query() ran successfully."
        )
    return clean_text


# ══════════════════════════════════════════════════════════════════════════════
# 2. FAISS Index Loader (cached)
# ══════════════════════════════════════════════════════════════════════════════

_cached_index: Optional[faiss.Index] = None
_cached_metadata: Optional[Dict[str, str]] = None
_cached_patents_df: Optional[pd.DataFrame] = None


def _load_resources() -> tuple:
    """
    Load and cache the FAISS index, patent_id metadata mapping, and patents DataFrame.

    Returns:
        (faiss.Index, dict[str, str], pd.DataFrame)

    Raises:
        FileNotFoundError: If the FAISS index or metadata file is missing.
            Run `python scripts/build_faiss_index.py` first.
    """
    global _cached_index, _cached_metadata, _cached_patents_df

    if _cached_index is None:
        if not _FAISS_INDEX.exists():
            raise FileNotFoundError(
                f"FAISS index not found at '{_FAISS_INDEX}'.\n"
                "Run: python patent-kg/backend/scripts/build_faiss_index.py"
            )
        logger.info("Loading FAISS index from '%s' ...", _FAISS_INDEX)
        _cached_index = faiss.read_index(str(_FAISS_INDEX))
        logger.info(
            "FAISS index loaded: %d vectors, dim=%d",
            _cached_index.ntotal,
            _cached_index.d,
        )

    if _cached_metadata is None:
        if not _METADATA_FILE.exists():
            raise FileNotFoundError(
                f"Metadata mapping not found at '{_METADATA_FILE}'.\n"
                "Run: python patent-kg/backend/scripts/build_faiss_index.py"
            )
        with open(_METADATA_FILE, "r", encoding="utf-8") as f:
            _cached_metadata = json.load(f)   # {"0": "US-12345-B2", ...}

    if _cached_patents_df is None:
        if not _PATENTS_CSV.exists():
            raise FileNotFoundError(
                f"patents.csv not found at '{_PATENTS_CSV}'.\n"
                "Run: python src/processing/process_patents.py"
            )
        logger.info("Loading patents metadata from '%s' ...", _PATENTS_CSV)
        _cached_patents_df = pd.read_csv(
            _PATENTS_CSV,
            usecols=["patent_id", "title", "abstract", "domain", "url"],
            dtype=str,
        ).fillna("")
        logger.info("Loaded %d patent records.", len(_cached_patents_df))

    return _cached_index, _cached_metadata, _cached_patents_df


# ══════════════════════════════════════════════════════════════════════════════
# 3. Embedding + FAISS Search
# ══════════════════════════════════════════════════════════════════════════════

_st_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    """Return cached SentenceTransformer model."""
    global _st_model
    if _st_model is None:
        logger.info("Loading SentenceTransformer '%s' ...", _MODEL_NAME)
        _st_model = SentenceTransformer(_MODEL_NAME)
    return _st_model


def faiss_search(query_text: str, top_k: int = 10) -> List[RetrievalHit]:
    """
    Embed query_text and retrieve top-k similar patents from the FAISS index.

    Args:
        query_text: Embedding-ready query string (from prepare_retrieval_query).
        top_k:      Number of results to return.

    Returns:
        List of RetrievalHit dicts with keys:
            rank, patent_id, score, title, abstract, domain, url
    """
    index, metadata, patents_df = _load_resources()
    model = _get_model()

    # Embed query — must match normalization used during indexing
    query_vec: np.ndarray = model.encode([query_text], convert_to_numpy=True)
    faiss.normalize_L2(query_vec)   # Matches faiss.normalize_L2 in build_faiss_index.py

    distances, indices = index.search(query_vec, top_k)   # shape (1, top_k)
    distances = distances[0]   # (top_k,) — inner product = cosine sim after L2 norm
    indices   = indices[0]     # (top_k,)

    # Build result list
    hits: List[RetrievalHit] = []
    for rank, (idx, score) in enumerate(zip(indices, distances), start=1):
        if idx == -1:   # FAISS returns -1 for unfilled slots
            continue

        patent_id = metadata.get(str(idx), f"UNKNOWN_{idx}")

        # Enrich with metadata from patents.csv
        row = patents_df[patents_df["patent_id"] == patent_id]
        if not row.empty:
            title    = row.iloc[0]["title"]
            abstract = row.iloc[0]["abstract"]
            domain   = row.iloc[0]["domain"]
            url      = row.iloc[0]["url"]
        else:
            title = abstract = domain = url = ""

        hits.append({
            "rank":       rank,
            "patent_id":  patent_id,
            "score":      round(float(score), 6),   # raw cosine sim (L2-normed)
            "title":      title,
            "abstract":   abstract[:300] + "..." if len(abstract) > 300 else abstract,
            "domain":     domain,
            "url":        url,
        })

    logger.info(
        "FAISS search complete: query='%s...' → %d hits",
        query_text[:60], len(hits),
    )
    return hits


# ══════════════════════════════════════════════════════════════════════════════
# 4. Main Integration Entrypoint
# ══════════════════════════════════════════════════════════════════════════════

def run_end_to_end(
    user_idea: str,
    top_k: int = 10,
) -> RetrievalResponse:
    """
    Full pipeline: raw user idea → NLP → retrieval → structured response.

    Args:
        user_idea: Free-text innovation idea from the user.
        top_k:     Number of patents to retrieve.

    Returns:
        RetrievalResponse dict conforming to the RetrievalResult/v1 schema:
        {
            "query_id":     str,
            "query_text":   str,
            "nlp_result":   NLPResult,
            "model":        str,
            "top_k":        int,
            "results":      List[RetrievalHit],
        }
    """
    logger.info("=== End-to-End Pipeline START ===")
    logger.info("User idea: '%s'", user_idea[:80])

    # ── Step 1: NLP Preprocessing ──────────────────────────────────────────
    logger.info("Step 1/3 — Running NLP pipeline ...")
    nlp_result: NLPResult = process_user_query(user_idea)
    logger.info(
        "NLP result: %d keywords, %d entities, clean_text_len=%d",
        len(nlp_result.get("keywords", [])),
        len(nlp_result.get("entities", [])),
        len(nlp_result.get("clean_text", "")),
    )

    # ── Step 2: Prepare symmetric embedding query ──────────────────────────
    logger.info("Step 2/3 — Preparing retrieval query ...")
    query_text = prepare_retrieval_query(nlp_result)
    logger.info("Query text: '%s...'", query_text[:80])

    # ── Step 3: FAISS Retrieval ────────────────────────────────────────────
    logger.info("Step 3/3 — Running FAISS search (top_k=%d) ...", top_k)
    hits = faiss_search(query_text, top_k=top_k)

    response: RetrievalResponse = {
        "query_id":   nlp_result.get("patent_id", "user_query"),
        "query_text": query_text,
        "nlp_result": nlp_result,
        "model":      _MODEL_NAME,
        "top_k":      top_k,
        "results":    hits,
    }

    logger.info("=== End-to-End Pipeline COMPLETE: %d results ===", len(hits))
    return response


# ══════════════════════════════════════════════════════════════════════════════
# 5. CLI Demo
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json

    demo_idea = (
        "I want to build a wearable device that uses EEG signals "
        "and machine learning to detect early signs of epileptic seizures "
        "and automatically alert caregivers via a mobile app."
    )

    print("\n" + "=" * 70)
    print("  INTEGRATION PIPELINE DEMO")
    print("=" * 70)
    print(f"\n  Input idea:\n  {demo_idea}\n")

    try:
        result = run_end_to_end(demo_idea, top_k=5)
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        print("\nSetup steps required:")
        print("  1. python src/processing/process_patents.py")
        print("  2. python patent-kg/backend/scripts/build_faiss_index.py")
        print("  3. python -m src.integration.pipeline")
        sys.exit(1)

    print(f"\n  NLP Output:")
    print(f"    clean_text : {result['nlp_result']['clean_text'][:100]}...")
    print(f"    keywords   : {result['nlp_result']['keywords']}")
    print(f"    entities   : {result['nlp_result']['entities']}")
    print(f"\n  Query sent to FAISS: '{result['query_text'][:80]}...'")
    print(f"\n  Top-{result['top_k']} Retrieved Patents:")
    print("-" * 70)

    for hit in result["results"]:
        print(
            f"  [{hit['rank']}] Score: {hit['score']:.4f}  |  {hit['domain']}\n"
            f"      ID: {hit['patent_id']}\n"
            f"      {hit['title'][:80]}\n"
        )

    print("=" * 70)
    print("\n  Full JSON response:")
    # Truncate abstract in output for readability
    display = dict(result)
    for r in display["results"]:
        r["abstract"] = r["abstract"][:120] + "..."
    print(json.dumps(display, indent=2, default=str))
