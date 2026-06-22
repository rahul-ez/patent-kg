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

# ── Import path setup ──────────────────────────────────────────────────────────
# Ensures `nlp`, `retrieval`, and `gnn` packages are importable regardless of CWD.
# MUST be done before any local package imports.
_SRC_DIR = Path(__file__).resolve().parents[1]   # → backend/src/
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# pyrefly: ignore [missing-import]
import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from gnn.scorer import get_scorer

from nlp.pipeline import process_user_query       # NLP layer (your code)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("integration.pipeline")

# ── Configuration ─────────────────────────────────────────────────────────────
from config.paths import VECTOR_STORE, PROCESSED_DATA

# All runtime artefacts (index, metadata, csv) live in patent-kg/data/vector_store/
# — this is where build_faiss_index.py writes them.
_VECTOR_DIR    = VECTOR_STORE
_PATENTS_CSV   = _VECTOR_DIR / "patents_deduped.csv"
_FAISS_INDEX   = _VECTOR_DIR / "patents.index"
_METADATA_FILE = _VECTOR_DIR / "metadata_mapping.json"
_gnn_scorer = None   # lazy-loaded on first query

# Model is selected at runtime based on the FAISS index dimension so this file
# works regardless of which model was used when build_faiss_index.py was run.
_DIM_TO_MODEL: Dict[int, str] = {
    384: "all-MiniLM-L6-v2",
    768: "AI-Growth-Lab/PatentSBERTa",
}
_MODEL_NAME: str = "all-MiniLM-L6-v2"   # updated in _load_resources() after index is read
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
        # Auto-select embedding model to match the index dimension
        global _MODEL_NAME
        detected = _DIM_TO_MODEL.get(_cached_index.d)
        if detected:
            _MODEL_NAME = detected
            logger.info("Auto-selected embedding model '%s' (index dim=%d)", _MODEL_NAME, _cached_index.d)
        else:
            logger.warning(
                "Unknown index dimension %d — keeping default model '%s'. "
                "Queries may fail if dimensions do not match.",
                _cached_index.d, _MODEL_NAME,
            )

    if _cached_metadata is None:
        if not _METADATA_FILE.exists():
            # Graceful fallback: synthesise sequential integer keys that mirror
            # the FAISS row order.  Hits will show UNKNOWN_<idx> patent IDs
            # until a proper metadata_mapping.json is generated by
            # build_faiss_index.py, but the pipeline will not crash.
            logger.warning(
                "metadata_mapping.json not found at '%s'. "
                "Patent IDs will show as UNKNOWN_<idx>. "
                "Re-run build_faiss_index.py to generate proper metadata.",
                _METADATA_FILE,
            )
            n = _cached_index.ntotal if _cached_index is not None else 0
            _cached_metadata = {str(i): f"UNKNOWN_{i}" for i in range(n)}
        else:
            with open(_METADATA_FILE, "r", encoding="utf-8") as f:
                _cached_metadata = json.load(f)   # {"0": "US-12345-B2", ...}

    if _cached_patents_df is None:
        from config.paths import ROOT
        _CSV_CANDIDATES = [
            _PATENTS_CSV,
            ROOT / "patents.csv",
            PROCESSED_DATA / "patents.csv",
        ]
        csv_path = next((p for p in _CSV_CANDIDATES if p.exists()), None)

        expected_cols = [
            "patent_id", "title", "abstract", "domain", "url", 
            "jurisdiction", "cites_patent_count", "cited_by_patent_count", "family_size"
        ]

        if csv_path is None:
            logger.warning(
                "No patents CSV found (tried %s). "
                "Title/abstract/domain/url will be empty in results.",
                ", ".join(str(p) for p in _CSV_CANDIDATES),
            )
            _cached_patents_df = pd.DataFrame(columns=expected_cols)
        else:
            logger.info("Loading patents metadata from '%s' ...", csv_path)
            # Load only the columns we need — tolerate CSVs that lack domain/url
            available = pd.read_csv(csv_path, nrows=0).columns.tolist()
            usecols = [c for c in expected_cols if c in available]
            _cached_patents_df = pd.read_csv(csv_path, usecols=usecols, dtype=str).fillna("")
            # Ensure all expected columns exist even if not in CSV
            for col in expected_cols:
                if col not in _cached_patents_df.columns:
                    if col in ["cites_patent_count", "cited_by_patent_count"]:
                        _cached_patents_df[col] = "0"
                    elif col == "family_size":
                        _cached_patents_df[col] = "1"
                    else:
                        _cached_patents_df[col] = ""
            logger.info("Loaded %d patent records from '%s'.", len(_cached_patents_df), csv_path)

    return _cached_index, _cached_metadata, _cached_patents_df


# ══════════════════════════════════════════════════════════════════════════════
# 3. Embedding + FAISS Search
# ══════════════════════════════════════════════════════════════════════════════

_st_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    """Return cached SentenceTransformer model. Reloads if _MODEL_NAME changed after index detection."""
    global _st_model
    if _st_model is None or getattr(_st_model, "_loaded_name", None) != _MODEL_NAME:
        logger.info("Loading SentenceTransformer '%s' ...", _MODEL_NAME)
        _st_model = SentenceTransformer(_MODEL_NAME)
        _st_model._loaded_name = _MODEL_NAME  # type: ignore[attr-defined]
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
            "rank":           rank,
            "patent_id":      patent_id,
            "semantic_score": round(float(score), 6),   # raw cosine sim (L2-normed)
            "title":          title,
            "abstract":       abstract[:300] + "..." if len(abstract) > 300 else abstract,
            "domain":         domain,
            "url":            url,
        })

    logger.info(
        "FAISS search complete: query='%s...' → %d hits",
        query_text[:60], len(hits),
    )
    return hits


# ══════════════════════════════════════════════════════════════════════════════
# 4. Main Integration Entrypoint
# ══════════════════════════════════════════════════════════════════════════════

def build_subgraph(expanded_hits: list) -> tuple:
    """Helper to convert candidate patents into a PyG Data object."""
    from gnn.graph_builder import build_subgraph_data
    index, metadata, patents_df = _load_resources()
    model = _get_model()
    return build_subgraph_data(expanded_hits, patents_df, metadata, index, model)

def run_gnn(graph_data) -> tuple:
    """Helper to run live GraphSAGE forward pass."""
    from gnn.inference import run_gnn_inference
    return run_gnn_inference(graph_data)

def hybrid_rerank(hits: list, semantic_scores, graph_embeddings, preds, pid_to_idx, gnn_mode) -> list:
    """Helper to blend semantic scores and GNN scores."""
    from gnn.reranker import rerank_hits
    return rerank_hits(
        hits=hits,
        embeddings=graph_embeddings,
        preds=preds,
        pid_to_idx=pid_to_idx,
        mode=gnn_mode,
        semantic_weight=0.7,
        novelty_weight=0.3
    )

def run_end_to_end(
    user_idea: str,
    top_k: int = 10,
    gnn_mode: str = "novelty",
) -> RetrievalResponse:
    """
    Full pipeline: raw user idea → NLP → retrieval → KG expansion → GNN scoring → structured response.

    Args:
        user_idea: Free-text innovation idea from the user.
        top_k:     Number of patents to retrieve.

    Returns:
        RetrievalResponse dict conforming to the RetrievalResult/v1 schema.
    """
    logger.info("=== End-to-End Pipeline START ===")
    logger.info("User idea: '%s'", user_idea[:80])
    logger.info("GNN mode: '%s'", gnn_mode)

    # ── Step 1: NLP Preprocessing ──────────────────────────────────────────
    logger.info("Step 1 — Running NLP pipeline ...")
    nlp_result: NLPResult = process_user_query(user_idea)
    logger.info(
        "NLP result: %d keywords, %d entities, clean_text_len=%d",
        len(nlp_result.get("keywords", [])),
        len(nlp_result.get("entities", [])),
        len(nlp_result.get("clean_text", "")),
    )

    # ── Step 2: Prepare symmetric embedding query ──────────────────────────
    logger.info("Step 2 — Preparing retrieval query ...")
    query_text = prepare_retrieval_query(nlp_result)
    logger.info("Query text: '%s...'", query_text[:80])

    # ── Step 3: FAISS Retrieval ────────────────────────────────────────────
    logger.info("Step 3 — Running FAISS search (top_k=%d) ...", top_k)
    hits = faiss_search(query_text, top_k=top_k)

    # Stamp each hit with its pre-GNN FAISS rank, expansion type, source, and score fields
    for hit in hits:
        hit["faiss_rank"] = hit["rank"]
        hit["expansion_type"] = None
        hit["source"] = "faiss"
        hit["graph_score"] = None
        hit["combined_score"] = None

    # ── Step 4: Knowledge Graph Expansion ──────────────────────────────────
    logger.info("Step 4 — Running Knowledge Graph Expansion ...")
    patent_ids = [hit["patent_id"] for hit in hits]
    
    kg_status = "success"
    expanded_hits = []
    try:
        from kg.expander import expand_via_kg
        expansion_result = expand_via_kg(patent_ids)
        
        # Get query embedding for semantic scoring of expanded hits
        model = _get_model()
        query_vec = model.encode([query_text], convert_to_numpy=True)
        faiss.normalize_L2(query_vec)
        query_vec = query_vec[0]
        
        def get_patent_emb(pid, p_title, p_abstract):
            emb = None
            row_idx_str = None
            for k, v in _cached_metadata.items():
                if v == pid:
                    row_idx_str = k
                    break
            if row_idx_str is not None:
                try:
                    emb = _cached_index.reconstruct(int(row_idx_str))
                except Exception:
                    pass
            if emb is None:
                text = f"{p_title}. {p_abstract}".strip()
                emb = model.encode(text) if text and text != "." else np.zeros(768, dtype=np.float32)
            return emb
        
        # Add family members
        for p in expansion_result.get("family", []):
            p_emb = get_patent_emb(p["patent_id"], p["title"], p["abstract"])
            sem_score = float(np.dot(query_vec, p_emb))
            expanded_hits.append({
                "rank": -1,
                "patent_id": p["patent_id"],
                "source": "kg_family",
                "expansion_type": "family",
                "semantic_score": round(sem_score, 6),
                "graph_score": None,
                "combined_score": None,
                "title": p["title"],
                "abstract": p["abstract"],
                "domain": p["domain"],
                "url": p["url"],
                "faiss_rank": -1
            })
            
        # Add CPC siblings
        for p in expansion_result.get("cpc_siblings", []):
            p_emb = get_patent_emb(p["patent_id"], p["title"], p["abstract"])
            sem_score = float(np.dot(query_vec, p_emb))
            expanded_hits.append({
                "rank": -1,
                "patent_id": p["patent_id"],
                "source": "kg_cpc",
                "expansion_type": "cpc_sibling",
                "semantic_score": round(sem_score, 6),
                "graph_score": None,
                "combined_score": None,
                "title": p["title"],
                "abstract": p["abstract"],
                "domain": p["domain"],
                "url": p["url"],
                "faiss_rank": -1
            })
            
        logger.info("KG Expansion added %d patents.", len(expanded_hits))
    except Exception as exc:
        logger.warning("KG Expansion skipped due to database connection issue: %s", exc)
        kg_status = "skipped_database_offline"

    all_hits = hits + expanded_hits

    # ── Step 5: GNN Scoring ───────────────────────────────────────────────
    logger.info("Step 5 — Running GNN Scoring ...")
    gnn_status = "success"
    try:
        # Build query-time graph object from retrieved + expanded patents
        graph_data, pid_to_idx = build_subgraph(all_hits)
        
        # Run live forward pass
        graph_embeddings, preds = run_gnn(graph_data)
        
        # Perform hybrid re-ranking
        all_hits = hybrid_rerank(
            hits=all_hits,
            semantic_scores=None,
            graph_embeddings=graph_embeddings,
            preds=preds,
            pid_to_idx=pid_to_idx,
            gnn_mode=gnn_mode
        )
    except FileNotFoundError as exc:
        logger.warning("GNN scorer unavailable (%s) — skipping.", exc)
        gnn_status = "skipped_missing_embeddings"
        _apply_fallback_scores(all_hits, gnn_mode)
    except Exception as exc:
        logger.warning("GNN scorer failed: %s", exc)
        gnn_status = "failed"
        _apply_fallback_scores(all_hits, gnn_mode)

    response: RetrievalResponse = {
        "query_id":   nlp_result.get("patent_id", "user_query"),
        "query_text": query_text,
        "nlp_result": nlp_result,
        "model":      _MODEL_NAME,
        "top_k":      top_k,
        "results":    all_hits,
        "gnn_status": gnn_status,
        "kg_status":  kg_status,
    }

    logger.info("=== End-to-End Pipeline COMPLETE: %d results ===", len(all_hits))
    return response

def _apply_fallback_scores(all_hits, gnn_mode):
    for i, hit in enumerate(all_hits):
        hit["rank"] = i + 1
        hit["graph_score"] = None
        hit["combined_score"] = None
        hit["gnn_mode"] = gnn_mode
        hit["rank_change"] = 0
    all_hits.sort(key=lambda h: h.get("semantic_score") or 0.0, reverse=True)
    for i, hit in enumerate(all_hits):
        hit["rank"] = i + 1


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
        result = run_end_to_end(demo_idea, top_k=10)
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
        score_val = hit.get("semantic_score")
        score_str = f"{score_val:.4f}" if score_val is not None else "N/A"
        print(
            f"  [{hit['rank']}] Semantic Score: {score_str}  |  {hit['domain']}\n"
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
