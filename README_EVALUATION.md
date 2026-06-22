# Patent Evaluation Engine

Scores any technical idea against 215 K patents on five dimensions (Novelty, Non-Obviousness, Landscape, Claim Breadth, Timing), applies India Section 3 eligibility analysis, and returns a final patentability score with a confidence-dampened verdict.

---

## Table of Contents

1. [Architecture](#architecture)
2. [Prerequisites](#prerequisites)
3. [Environment Variables](#environment-variables)
4. [Build & Run](#build--run)
5. [Optional: Generate GNN Scores](#optional-generate-gnn-scores)
6. [API Endpoints](#api-endpoints)
7. [Field Reference](#field-reference)
8. [Scoring Formula](#scoring-formula)
9. [Limitations](#limitations)

---

## Architecture

```
Frontend (Vite + React)   →  POST /api/evaluate
         ↓
FastAPI Router (evaluate.py)
         ↓
PatentabilityEngine  ←  runs pipeline (FAISS + Neo4j KG) if no hits cached
         ├── NoveltyScorer          (60% FAISS isolation + 40% GNN when available)
         ├── NonObviousnessScorer   (8 sub-scorers including Gemini LLM calls)
         ├── LandscapeScorer        (citation density, assignee concentration)
         ├── ClaimBreadthScorer     (CPC hierarchy depth)
         ├── TimingScorer           (publication year spread)
         ├── IndiaEligibilityChecker (rule-based Section 3 flags)
         └── TechnicalDepthAnalyser  (confidence dampening multiplier)
```

Scorers degrade gracefully:
- **Neo4j offline** → neutral 0.5 defaults returned
- **Gemini key missing** → Gemini-dependent sub-scorers return 0.5
- **GNN files missing** → GNN novelty path skipped, `gnn_status: "skipped_missing_embeddings"`

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.10+ |
| Node.js | 18+ |
| Neo4j (optional) | 5.x |
| Google Gemini API key | any |

Python packages (see `backend/requirements.txt`):
```
fastapi uvicorn faiss-cpu sentence-transformers
google-generativeai python-dotenv neo4j pandas numpy tqdm
```

---

## Environment Variables

Create `patent-kg/.env` (the backend loads this automatically):

```env
# Required for non-obviousness LLM sub-scorers (motivation-to-combine, reconstruction)
GOOGLE_API_KEY=your_gemini_key_here

# Optional — evaluation works without Neo4j (scores degrade to neutral 0.5)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

---

## Build & Run

### 1. Install backend dependencies

```bash
cd patent-kg/backend
pip install -r requirements.txt
```

### 2. Install frontend dependencies

```bash
cd patent-kg/frontend
npm install
```

### 3. (One-time) Build the FAISS index

If `data/vector_store/patents.index` does not exist:

```bash
cd patent-kg/backend
python scripts/build_faiss_index.py
```

### 4. (Optional) Generate GNN scores

Enables GNN-based novelty scoring (~5–20 min, one-time):

```bash
cd patent-kg/backend
python scripts/generate_gnn_scores.py
```

Output: `data/vector_store/novelty_scores.json` and `data/vector_store/node_embeddings.npy`

### 5. Start the API server

```bash
cd patent-kg/backend
uvicorn api.main:app --reload --port 8000
```

Verify at [http://localhost:8000/docs](http://localhost:8000/docs).

### 6. Start the frontend

```bash
cd patent-kg/frontend
npm run dev
```

Opens at [http://localhost:5173](http://localhost:5173). The Vite proxy forwards `/api/*` → `http://localhost:8000`.

---

## Optional: Generate GNN Scores

`backend/scripts/generate_gnn_scores.py` derives novelty scores locally without a trained GNN or Colab:

1. Reconstructs all embeddings from the FAISS index
2. Computes **embedding isolation** — how far each patent sits from its K nearest neighbours in vector space (patents in sparse regions = novel)
3. Blends with **inverse citation rank** and **recency rank**
4. Writes `novelty_scores.json` and `node_embeddings.npy` to `data/vector_store/`

Weights: 60% isolation + 25% inverse citation + 15% recency.

Restart the API server after running the script to pick up the new files.

---

## API Endpoints

All endpoints are mounted under `/api`. The Vite frontend uses the proxy at `/api`.

---

### `POST /api/evaluate`

Full evaluation. Returns nested JSON (one key per dimension).

**Request body**

```json
{
  "idea": "A wearable that measures blood glucose non-invasively using near-infrared spectroscopy",
  "top_k": 10,
  "gnn_mode": "novelty",
  "run_fast": false,
  "n_reconstruction_samples": 5,
  "pipeline_result": null
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `idea` | string | required | Natural-language description of the invention |
| `top_k` | int | 10 | Number of prior-art hits to retrieve |
| `gnn_mode` | string | `"novelty"` | `"novelty"` or `"graph_sim"` |
| `run_fast` | bool | false | Skip Gemini sub-scorers; ~15 s vs ~120 s |
| `n_reconstruction_samples` | int | 5 | Reconstruction difficulty samples (non-obviousness) |
| `pipeline_result` | object | null | Pass previous pipeline output to skip re-retrieval |

**Response** — see [Field Reference](#field-reference) below.

---

### `POST /api/evaluate/full`

Flat single-level JSON — all ~80 keys at the top level. Designed for teammates using curl/Postman or downstream scripts.

Same request body as `/api/evaluate`.

**Example (curl)**

```bash
curl -s -X POST http://localhost:8000/api/evaluate/full \
  -H "Content-Type: application/json" \
  -d '{
    "idea": "Blockchain-based supply chain tracking for pharmaceuticals",
    "top_k": 10,
    "gnn_mode": "novelty",
    "run_fast": true,
    "n_reconstruction_samples": 3
  }' | python -m json.tool
```

**Example response (excerpt)**

```json
{
  "patentability_score": 61.4,
  "patentability_raw": 63.1,
  "verdict": "Conditionally Patentable",
  "risk": "Medium",
  "confidence": 0.65,
  "novelty_score": 72.3,
  "novelty_semantic": 0.741,
  "non_obviousness_score": 55.2,
  "landscape_score": 48.0,
  "claim_breadth_score": 60.0,
  "timing_score": 55.0,
  "timing_recency_flag": "ACTIVE",
  "india_is_flagged": false,
  "india_flag_count": 0,
  "technical_depth_level": "Medium",
  "elapsed_seconds": 14.8,
  ...
}
```

---

### `GET /api/evaluate/fields`

Returns a machine-readable description of every field in the `/full` response.

```bash
curl http://localhost:8000/api/evaluate/fields | python -m json.tool
```

**Response structure**

```json
{
  "count": 82,
  "fields": [
    {
      "name": "patentability_score",
      "type": "float",
      "range": "0–100",
      "group": "summary",
      "description": "Confidence-dampened final patentability score (0=not patentable, 100=highly patentable)"
    },
    ...
  ]
}
```

---

## Field Reference

### Summary fields

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `patentability_score` | float | 0–100 | Confidence-dampened final score |
| `patentability_raw` | float | 0–100 | Raw blended score before dampening |
| `verdict` | string | — | Human-readable verdict |
| `risk` | string | Low/Medium/High | Prosecution risk |
| `confidence` | float | 0–1 | Technical depth confidence multiplier |
| `elapsed_seconds` | float | — | Total wall time |
| `fast_mode` | bool | — | Whether `run_fast` was used |

### Novelty (`novelty_*`)

| Field | Description |
|-------|-------------|
| `score` | 0–100, higher = more novel |
| `semantic_novelty` | 1 − weighted mean FAISS similarity |
| `gnn_novelty` | GNN isolation score (null if files missing) |
| `gnn_mode` | `"novelty"` or `"graph_sim"` |
| `top_semantic_score` | Highest cosine similarity in retrieved hits |
| `n_hits_used` | Number of FAISS hits used |

### Non-Obviousness (`non_obviousness_*`)

| Field | Description |
|-------|-------------|
| `score` | 0–100 |
| `score_raw` | Before any post-processing |
| `breakdown.*` | 8 sub-factor scores (see below) |

Sub-factors and weights:

| Sub-factor | Weight |
|-----------|--------|
| Combination Difficulty | 25% |
| Motivation to Combine | 20% |
| Cross-Domain Novelty | 15% |
| Reconstruction | 15% |
| Citation Isolation | 10% |
| Long-Felt Need | 10% |
| Teaching Away (bonus) | up to +5 pts |
| Unexpected Effect (bonus) | up to +5 pts |

### Landscape (`landscape_*`)

| Field | Description |
|-------|-------------|
| `score` | 0–100, higher = more open landscape |
| `density` | Mean similarity of retrieved hits |
| `active_ratio` | Fraction of hits from last 5 years |
| `assignee_concentration` | Herfindahl index of assignees |

### Claim Breadth (`claim_breadth_*`)

| Field | Description |
|-------|-------------|
| `score` | 0–100 |
| `avg_cpc_depth` | Mean CPC hierarchy depth of retrieved patents |
| `unique_section_ratio` | Fraction of distinct CPC sections |
| `total_cpc_codes` | Total CPC codes across hits |

### Timing (`timing_*`)

| Field | Description |
|-------|-------------|
| `score` | 0–100 |
| `newest_year` | Most recent publication year in hits |
| `oldest_year` | Oldest publication year |
| `year_spread` | `newest_year − oldest_year` |
| `recency_flag` | `ACTIVE` / `CLEARING` / `LEGACY` / `UNKNOWN` |

### India Eligibility (`india_*`)

Sections checked: 3(k) — computer programs/algorithms, 3(d) — new forms of known substances, 3(c) — mere discovery of biological material.

| Field | Description |
|-------|-------------|
| `india_is_flagged` | True if any section triggers |
| `india_flag_count` | Number of flags |
| `india_flags` | Array of flag objects with section, severity, explanation |
| `india_safe_harbors` | Applicable safe harbors |

### Technical Depth (`technical_depth_*`)

| Field | Description |
|-------|-------------|
| `level` | Low / Medium / High |
| `confidence` | 0.40 / 0.65 / 0.90 — used as dampening multiplier |
| `quantitative_hits` | Number of numerical values in the idea text |
| `entity_count` | Named entities extracted |
| `word_count` | Word count of the idea |

---

## Scoring Formula

```
raw_blend = (
    0.30 × novelty_score +
    0.35 × non_obviousness_score +
    0.15 × landscape_score +
    0.10 × claim_breadth_score +
    0.10 × timing_score
)

patentability_score = raw_blend × confidence + 50.0 × (1 − confidence)
```

Confidence comes from Technical Depth: Low=0.40, Medium=0.65, High=0.90.

**Verdict thresholds**

| Score | Verdict |
|-------|---------|
| ≥ 75 | Likely Patentable |
| 55–74 | Conditionally Patentable |
| 40–54 | Marginal |
| < 40 | Unlikely Patentable |

---

## Limitations

- **Scoring weights are heuristic** — the 30/35/15/10/10 blend is not calibrated against real USPTO outcomes.
- **No claim drafting** — the engine evaluates a free-text idea description, not formal patent claims.
- **GNN scores are approximate** when generated by `generate_gnn_scores.py` (embedding isolation proxy). A GNN trained on the citation graph would be more accurate.
- **India eligibility is rule-based keyword matching** — consult a patent attorney for definitive advice.
- **Gemini sub-scorers (Motivation-to-Combine, Reconstruction) require an API key** — without one `run_fast=true` is effectively always active for those sub-factors.
- **Neo4j data coverage** — the KG contains ~215 K patents; gaps in coverage may affect landscape and citation signals.
