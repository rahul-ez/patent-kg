# Safe Retrieval Layer Upgrade — Dataset Deduplication + PatentSBERTa Migration

## Overview

Two precisely scoped changes to the patent retrieval layer:

1. **Deduplication** — Strip duplicate invention records from the semantic retrieval corpus using content-hash (MD5 of normalised title + abstract), keeping first occurrence per unique invention.
2. **PatentSBERTa** — Replace `all-MiniLM-L6-v2` (384-dim) with `AI-Growth-Lab/PatentSBERTa` in the FAISS index builder and the integration pipeline query encoder.
3. **FAISS Rebuild** — Regenerate `patents.index` + `metadata_mapping.json` using deduplicated corpus + new model.

**Zero changes** to: KG, GNN, NLP, Streamlit UI, FastAPI, `retrieval.engine`, `retrieval.search`, `retrieval.evaluate`, function signatures, or JSON output schema.

---

## User Review Required

> [!IMPORTANT]
> **PatentSBERTa embedding dimension** — `AI-Growth-Lab/PatentSBERTa` outputs **768-dimensional** embeddings (BERT-base backbone), versus the current **384-dim** MiniLM. The FAISS index will be rebuilt at 768-dim. The old `patents.index` (384-dim) and `metadata_mapping.json` will be **overwritten**. This is irreversible without re-running the old `build_faiss_index.py` script.

> [!IMPORTANT]
> **Rebuild time** — PatentSBERTa is significantly larger than MiniLM. Encoding ~36k deduplicated patents will take considerably longer than the current index. Estimated: 5–20 minutes on CPU depending on hardware.

> [!WARNING]
> The Streamlit UI sidebar still shows `"all-MiniLM-L6-v2 (384-dim)"` and `"58,428 Patents Indexed"` as hard-coded display strings. Per task constraints these are **not modified** (UI/Streamlit is off-limits). The underlying retrieval will use PatentSBERTa — only the display label will be stale. This is acceptable per task scope.

---

## Open Questions

> [!NOTE]
> No blocking open questions. Scope is fully defined. Proceeding.

---

## Proposed Changes

### Component 1 — `build_faiss_index.py` (the index builder script)

#### [MODIFY] [build_faiss_index.py](file:///c:/Users/Lenovo/Documents/Projects/Graph-Enhanced%20Patent%20Intelligence%20Platform/backend/scripts/indexing/build_faiss_index.py)

**Changes:**
- Add deduplication step using `content_hash = md5(normalized_title + " " + normalized_abstract)`
- Replace `all-MiniLM-L6-v2` → `AI-Growth-Lab/PatentSBERTa`
- Auto-detect embedding dimension from `embeddings.shape[1]` (no hardcoding)
- Print deduplication summary stats
- Add post-build validation: metadata count == FAISS vector count
- All other logic (L2 normalization, IndexFlatIP, metadata_mapping.json format) remains identical

---

### Component 2 — `integration/pipeline.py` (the query encoder)

#### [MODIFY] [pipeline.py](file:///c:/Users/Lenovo/Documents/Projects/Graph-Enhanced%20Patent%20Intelligence%20Platform/patent-kg/backend/src/integration/pipeline.py)

**Changes (minimal — one line + one comment):**
- Change `_MODEL_NAME = "all-MiniLM-L6-v2"` → `_MODEL_NAME = "AI-Growth-Lab/PatentSBERTa"`

This ensures the query is encoded with the same model used during indexing (critical for embedding symmetry). No function signatures change. The `faiss_search()`, `run_end_to_end()`, and all downstream contracts remain unchanged.

---

### Component 3 — `retrieval/embed.py` (the retrieval module embedder)

#### [MODIFY] [embed.py](file:///c:/Users/Lenovo/Documents/Projects/Graph-Enhanced%20Patent%20Intelligence%20Platform/patent-kg/backend/src/retrieval/embed.py)

**Changes (minimal):**
- Change `_MODEL_NAME = "all-MiniLM-L6-v2"` → `_MODEL_NAME = "AI-Growth-Lab/PatentSBERTa"`
- Remove hardcoded fallback shape `(0, 384)` → use `(0, 768)` OR (better) detect dynamically

> [!NOTE]
> `retrieval/embed.py` is used only by `retrieval/search.py` (the old NumPy-based cosine search path). The production FAISS search path used by Streamlit goes through `integration/pipeline.py → faiss_search()` which has its own `SentenceTransformer` instance. Both must use the same model name for correctness.

---

## Files NOT Modified

| File | Reason |
|------|--------|
| `retrieval/__init__.py` | No changes needed |
| `retrieval/search.py` | Function signature unchanged |
| `retrieval/vector_store.py` | NumPy store unchanged |
| `retrieval/evaluate.py` | Evaluation logic unchanged |
| `retrieval/explain.py` | Unchanged |
| `retrieval/metrics.py` | Unchanged |
| `backend/scripts/evaluation/evaluate_faiss.py` | Unchanged — calls `faiss_search()` which is unchanged |
| `streamlit_app.py` | Off-limits per task |
| `kg/*`, `nlp/*`, `gnn/*` | Off-limits per task |

---

## Verification Plan

### Automated (post-script)
The upgraded `build_faiss_index.py` will self-validate:
1. No duplicate `content_hash` values remain in deduplicated DataFrame
2. `len(metadata_mapping) == faiss_index.ntotal`
3. Print dedup stats: original count → removed → final count

### Manual Verification
1. Run `python backend/scripts/indexing/build_faiss_index.py` — confirm it completes and prints the dedup summary + validation results
2. Run `python backend/scripts/evaluation/evaluate_faiss.py` — confirm it still executes without errors
3. Run `streamlit run streamlit_app.py` from `patent-kg/backend/` — confirm search results still appear with the same JSON fields (`rank`, `patent_id`, `score`, `title`, `abstract`, `domain`, `url`)

### Expected dedup output (approximate)
```
Original patents: 58,428
Duplicate inventions removed: ~22,000
Final patents: ~36,000
```
