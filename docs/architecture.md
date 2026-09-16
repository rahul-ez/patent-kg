# Architecture and Repository Map

## Purpose and current shape

This repository is a prototype **patent-intelligence platform**. A user submits an invention idea; the system cleans and enriches the text, retrieves similar patents with FAISS, expands the candidate set through a Neo4j knowledge graph, optionally re-ranks it with a GraphSAGE model, evaluates patentability heuristics, and generates improvement suggestions. The primary product surface is a React/Vite frontend backed by FastAPI. A large Streamlit application remains as a legacy/alternate UI.

`patent-kg/` is the complete project boundary. Raw and processed datasets, vector artefacts, populated MySQL/Neo4j databases, and local environment values are intentionally ignored by Git but live under this repository when available. MySQL is the normalized source of truth; Neo4j is a one-way graph projection and FAISS is a derived retrieval index.

## Runtime flow

```text
React browser
  └─ POST /api/pipeline/run
       └─ integration.pipeline.run_end_to_end()
            ├─ nlp.pipeline.process_user_query()
            │    └─ Gemini extraction when available; spaCy/heuristic fallback
            ├─ SentenceTransformer encode + FAISS top-k retrieval
            ├─ kg.expander.expand_via_kg() against Neo4j
            ├─ gnn.graph_builder + gnn.inference + gnn.reranker
            └─ structured pipeline result persisted in the browser Zustand store

React evaluation page ─ POST /api/evaluate ─ evaluation.patentability_engine
React improvement page ─ POST /api/improve ─ improvement.ImprovementAgent

React KG page ─ POST /api/kg/build, POST /api/kg/expand, GET /api/kg/graph
```

The pipeline can degrade when dependencies are absent: failed Neo4j expansion leaves FAISS results intact, and failed GNN inference falls back to semantic order. LLM-backed steps also have local fallback behavior. This makes the prototype usable with a partial setup, but can make apparent feature availability differ from the ideal architecture.

## Data and build lineage

```text
data/raw/*.csv (Lens-style source exports)
  └─ backend/scripts/data/process_patents.py
       └─ data/processed/*.csv (reproducible ETL inputs)
            ├─ backend/scripts/database/bootstrap_mysql.py → MySQL 3NF source of truth
            └─ backend/scripts/database/sync_mysql_to_neo4j.py → Neo4j projection`n                 └─ backend/scripts/database/export_mysql_retrieval.py → backend/scripts/indexing/build_faiss_index.py → data/vector_store/
                                                        patents.index
                                                        metadata_mapping.json
                                                        patents_deduped.csv

The API reads FAISS/vector artefacts and Neo4j. It does not build them automatically.
```

## Entry points and external services

| Component | Entry point / interface | Role |
|---|---|---|
| Web UI | `frontend/src/main.tsx` → `App.tsx` | Vite React SPA, served on port 5173 in development. |
| REST API | `backend/run_api.py` → `api/main.py` | FastAPI on port 8000; routes live under `/api`. |
| Legacy UI | `backend/streamlit_app.py` | Independent Streamlit dashboard, duplicating most pipeline/KG presentation logic. |
| Graph database | Neo4j Bolt, normally port 7687 | Stores patents, companies, inventors, CPC codes, papers, and relationships. |
| Vector retrieval | Local FAISS files | Production semantic retrieval. |
| LLM | Google Gemini credentials via `GOOGLE_API_KEY` | Used for NLP, evaluation sub-scorers, and improvement prose; fallbacks exist. |

Required environment values are `GOOGLE_API_KEY`, `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, and the `MYSQL_*` values; KG export/import scripts additionally use `NEO4J_HOME`. Copy `.env.example` to `.env`; both `.env` and `keys.txt` are ignored by Git.

## API contract and UI routes

| API route | Backend implementation | Frontend consumer | Notes |
|---|---|---|---|
| `GET /api/health` | `api/main.py` | Manual/operational use | Liveness only. |
| `POST /api/pipeline/run` | `api/routers/pipeline.py` → `integration/pipeline.py` | `api/pipeline.ts`, `usePipeline.ts` | Main end-to-end analysis. |
| `POST /api/kg/build` | `api/routers/kg.py` → `kg/builder.py` | `api/kg.ts`, `KGVisualizationPage.tsx` | Writes/builds Neo4j subgraph, then reports counts for the requested graph slice. |
| `POST /api/kg/expand` | `api/routers/kg.py` → `kg/expander.py` | Same as above | Returns family and CPC candidates. |
| `GET /api/kg/graph` | `api/routers/kg.py` | Same as above | Emits a requested-ID-scoped React Flow graph. |
| `POST /api/evaluate` | `api/routers/evaluate.py` → `evaluation/patentability_engine.py` | `api/evaluate.ts`, `EvaluationDashboardPage.tsx` | Nested dashboard response. |
| `POST /api/evaluate/full` | Same router | Scripts/external consumers | Flattened evaluation response. |
| `GET /api/evaluate/fields` | Same router | Manual/external consumers | Field catalogue. |
| `POST /api/improve` | `api/routers/improve.py` → `improvement/agent.py` | `api/improve.ts`, `ImprovementAgentPage.tsx` | Reuses supplied pipeline/evaluation output or recomputes missing pieces. |

Browser routes: `/`, `/analyze`, and `/pipeline` are standalone pages. `/results/nlp`, `/results/patents`, `/results/graph`, `/results/gnn`, `/results/evaluation`, and `/results/improvements` use `RootLayout` and the shared navigation shell.

## File inventory

### Local data and planning artefacts

| File or group | Role | Connected to |
|---|---|---|
| `keys.txt` | Local key/configuration file. It is tracked and currently modified; its contents were intentionally not inspected. | Security-sensitive; not used explicitly by code that instead reads `.env`. |
| `backend/scripts/data/process_patents.py` | Root ETL: reads six raw-domain CSVs, cleans patents, derives stable IDs and relational tables, and writes all seven `data/processed` outputs. | Upstream of FAISS index and Neo4j build. |
| `data/raw/ai.csv` | Full AI Lens-style source export. | Input to root ETL. |
| `data/raw/automotive.csv` | Full automotive source export. | Input to root ETL. |
| `data/raw/energy.csv` | Full energy source export. | Input to root ETL. |
| `data/raw/iot.csv` | Full IoT source export. | Input to root ETL. |
| `data/raw/mechanical.csv` | Full mechanical source export. | Input to root ETL. |
| `data/raw/medical.csv` | Full medical source export. | Input to root ETL. |
| `data/raw_limited/ai.csv` | Smaller AI source export. | Alternate/sample ETL input; not the default `RAW_DIR` corpus. |
| `data/raw_limited/automotive.csv` | Smaller automotive source export. | Alternate/sample input. |
| `data/raw_limited/energy.csv` | Smaller energy source export. | Alternate/sample input. |
| `data/raw_limited/iot.csv` | Smaller IoT source export. | Alternate/sample input. |
| `data/raw_limited/mechanical.csv` | Smaller mechanical source export. | Alternate/sample input. |
| `data/raw_limited/medical.csv` | Smaller medical source export. | Alternate/sample input. |
| `data/processed/patents.csv` | Canonical normalised patent corpus (title, abstract, domain and metadata). | FAISS builder; KG builder; integration fallback input. |
| `data/processed/assignees.csv` | Patent-to-company mappings. | KG builder. |
| `data/processed/inventors.csv` | Patent-to-inventor mappings. | KG builder. |
| `data/processed/classifications.csv` | Patent CPC classifications. | KG builder and graph/evaluation signals. |
| `data/processed/patent_families.csv` | Family relationships. | KG builder and KG expansion. |
| `data/processed/citations_metadata.csv` | Patent citation counts. | KG builder and ranking/evaluation metadata. |
| `data/processed/npl_metadata.csv` | Patent-to-non-patent-literature/paper data. | KG builder and citation-based evaluation. |
| `data/source_exports/patents_sample.csv` | Small manually shaped sample patent data. | Experiments/reference only. |
| `data/source_exports/patents.csv` | Small alternate patent dataset. | Legacy retrieval experiments. |
| `data/source_exports/assignees.csv` | Small alternate assignee map. | Legacy/experiment reference. |
| `data/source_exports/inventors.csv` | Small alternate inventor map. | Legacy/experiment reference. |
| `data/source_exports/citations.csv` | Essentially empty citation placeholder. | Unused/legacy. |
| `data/source_exports/indian-patents.csv` | Large separate Indian/Lens export. | Not wired into the production ETL/API. |
| `data/source_exports/lens-export.csv` | Large generic Lens export. | Not wired into the production ETL/API. |
| `docs/planning/implementation_plan.md` | Historical plan for retrieval deduplication and PatentSBERTa migration. | Explains why FAISS builder and integration auto-select by vector dimension. |
| `docs/planning/patent_platform_redesign_spec.md` | UI redesign specification. | Reference only; current frontend still uses its own implementation. |
| `docs/planning/redesign_spec_v3_implementation_ready.md` | More detailed UI design handoff. | Reference only; not runtime code. |

### Application documentation and deployment files

| File | Role |
|---|---|
| `patent-kg/README.md` | Primary overview and FastAPI/React setup guide. Describes the desired pipeline. |
| `patent-kg/docs/guides/legacy-streamlit.md` | Older Streamlit/KG-oriented setup guide. Useful for Neo4j data setup but no longer the primary UI path. |
| `patent-kg/docs/reference/knowledge-graph.md` | Detailed graph data model, import process, traversal rationale, and expected scale. |
| `patent-kg/docs/reference/gnn.md` | GNN implementation notes. |
| `patent-kg/docs/guides/evaluation.md` | Evaluation-engine documentation. |
| `docs/internal/developer-context.md` | Detailed narrative of live GNN and improvement-agent changes; useful context, but validate it against code. |
| `docs/internal/checklist.md` | Early ingestion checklist; largely historical. |
| `patent-kg/docker-compose.yml` | Starts the local Neo4j service only. Production retrieval uses FAISS. |
| `backend/requirements.txt` | Python runtime dependency list for the supported API, FAISS, PyG, Neo4j, and Gemini. |
| `backend/run_api.py` | Minimal Uvicorn launcher for `api.main:app`. |
| `backend/streamlit_app.py` | 883-line alternate dashboard with its own pipeline/KG loading and rendering functions. It is not called by FastAPI or React. |

### FastAPI layer: `backend/api/`

| File | Role and connections |
|---|---|
| `api/__init__.py` | Package marker. |
| `api/main.py` | Creates FastAPI, loads `patent-kg/.env`, injects `backend/src` into `sys.path`, preloads FAISS/model in lifespan, configures CORS, and mounts all routers. |
| `api/schemas.py` | Pydantic request/response models for pipeline, evaluation, and KG endpoints. Improvement models live separately in `improvement/schemas.py`. |
| `api/routers/__init__.py` | Package marker. |
| `api/routers/pipeline.py` | Validates idea/GNN mode and calls `run_end_to_end`. |
| `api/routers/kg.py` | Builds/expands graph and converts Neo4j responses to React Flow data. |
| `api/routers/evaluate.py` | Runs/reuses pipeline results; exposes nested, flattened, and field-reference evaluation routes. |
| `api/routers/improve.py` | Obtains missing pipeline/evaluation results and invokes `ImprovementAgent`. |

### Integration, NLP, and retrieval: `backend/src/`

| File | Role and connections |
|---|---|
| `config/paths.py` | Central path constants from `backend/src` to `data/vector_store` and root processed data. |
| `integration/__init__.py` | Exposes integration package context. |
| `integration/pipeline.py` | Production orchestrator. Caches FAISS, metadata CSV and encoder; processes query; retrieves; expands through KG; adds semantic scores to expansion candidates; builds a PyG subgraph; runs GraphSAGE; reranks/falls back. |
| `nlp/pipeline.py` | Hybrid query/patent NLP flow and embedding-input preparation. Combines preprocessing, spaCy analysis, optional LLM output, validation, entities, and keywords. |
| `nlp/preprocess.py` | Text cleaning/light preprocessing and LLM-output cleanup. |
| `nlp/llm_processor.py` | Calls the current `google.genai` SDK for structured language analysis when a key is available. |
| `nlp/validator.py` | Checks expected LLM-output shape before accepting it. |
| `nlp/extract_entities.py` | Extracts named/technical entities from a spaCy document. |
| `nlp/keywords.py` | Extracts/ranks keywords and performs verb-to-noun normalization. |
| `ingestions/download_patents.py` | Legacy PatentsView downloader: samples six keyword-defined domains, de-duplicates IDs, and appends a differently shaped `data/raw/patents_sample.csv`; it is not the source format consumed by the root ETL. |
| `retrieval/embed.py` | Cached SentenceTransformer embedding helper for the older in-memory NumPy retrieval path. |
| `retrieval/vector_store.py` | Saves/loads embeddings and source texts for that older NumPy retrieval path. |
| `retrieval/search.py` | NumPy cosine search and result shaping/explanations for the older path. |
| `retrieval/explain.py` | Token-overlap keyword extraction and human-readable similarity explanation. |
| `retrieval/metrics.py` | Precision, recall, hit rate, MRR and relevant-item similarity metrics for FAISS evaluation. |
| `retrieval/evaluate.py` | Separate, overlapping precision/recall and test-set evaluation utilities for the old NumPy path. |
| `retrieval/__init__.py` | Re-exports the old retrieval functions; imports use absolute package names and depend on `backend/src` path injection. |

### Knowledge graph and GNN: `backend/src/`

| File | Role and connections |
|---|---|
| `kg/builder.py` | `KGBuilder` creates constraints and batch-loads processed patents, companies, inventors, CPCs, families, citations and papers into Neo4j. Also builds a query subgraph. |
| `kg/expander.py` | Reads Neo4j to find family members and capped CPC siblings, converting them to API candidate dictionaries. Called by the main pipeline and KG endpoint. |
| `kg/__init__.py` | Re-exports builder and expander APIs. |
| `gnn/model.py` | Defines the three-layer residual `PatentGraphSAGE` model: 780 feature inputs and 64-dimensional embeddings plus novelty output. |
| `gnn/graph_builder.py` | Fetches relevant Neo4j neighbours/edges and builds the per-query PyTorch Geometric data object. Feature vector is sentence embedding plus jurisdiction/domain metadata. |
| `gnn/inference.py` | Loads/caches trained checkpoint (`gnn_model.pt` or `patent_gnn.pt`) and runs the forward pass. |
| `gnn/reranker.py` | Blends semantic and graph score (default 70/30), sets score fields, sorts results, and calculates rank change. |
| `gnn/scorer.py` | Backward-compatible scoring wrapper around graph building, inference and reranking; the production integration currently calls lower-level helpers directly instead. |
| `gnn/__init__.py` | Re-exports scorer helpers. |

### Patentability evaluation: `backend/src/evaluation/`

`patentability_engine.py` is the coordinator: it extracts concepts, retrieves patents for each concept, calls the individual scoring modules, applies weights/confidence damping, and returns the response consumed by `api/routers/evaluate.py` and the improvement agent.

| File | Role |
|---|---|
| `__init__.py` | Re-exports public concepts, searches and scorers. |
| `concept_extractor.py` | Gemini-assisted decomposition of an idea into independent `Concept` values, with keyword fallback. |
| `per_concept_search.py` | Independently loads FAISS/model resources, searches each concept, fetches CPC data from Neo4j, and returns typed concept-hit clusters. |
| `novelty_scorer.py` | Computes novelty from high semantic similarity and available GNN novelty scores. |
| `non_obviousness_scorer.py` | Combines the eight non-obviousness component scores below. |
| `combination_difficulty.py` | CPC tree distance, Neo4j path distance and embedding distance between concept clusters. |
| `motivation_analyzer.py` | Cross-citation-density heuristic plus optional Gemini analysis of motivation to combine. |
| `cross_domain_novelty.py` | CPC-section and application-domain diversity. |
| `reconstruction_tester.py` | Optional Gemini reconstruction of the solution and semantic comparison to invention. |
| `citation_isolation.py` | Neo4j paper/family connection isolation between concept clusters. |
| `long_felt_need.py` | Time/citation-based proxy for long-felt need. |
| `teaching_away.py` | Searches abstract text for conflicting/teaching-away language. |
| `unexpected_effect.py` | Optional Gemini assessment of unexpected effect. |
| `landscape_scorer.py` | Measures density, active status and assignee concentration. |
| `claim_breadth_scorer.py` | Uses CPC depth and uniqueness as a claim-breadth proxy. |
| `timing_scorer.py` | Uses patent timing/recency signals. |
| `india_eligibility.py` | Heuristic flags for India-specific subject-matter eligibility risk. |
| `technical_depth.py` | Estimates technical specificity and confidence from the idea/concept result set. |

### Improvement agent: `backend/src/improvement/`

| File | Role and connections |
|---|---|
| `config.py` | Central thresholds for semantic/graph overlap, landscape density and score weakness. |
| `schemas.py` | Pydantic models for `/api/improve`. |
| `analyzer.py` | Determines problems (overlap, crowding, low novelty) and converts them to weakness statements. |
| `strategies.py` | Hard-coded domain/problem strategy catalogue and primary-domain identification. |
| `opportunity_finder.py` | Hard-coded cross-domain opportunity catalogue, ordered by least-represented retrieved domain. |
| `generator.py` | Uses Gemini only to explain deterministic selections; produces markdown fallback when unavailable. |
| `agent.py` | `ImprovementAgent` orchestrates analysis, strategies, opportunities, explanation, and top overlapping patents. |

### Backend scripts and tests: `backend/scripts/`, `patent-kg/tests/`

| File | Role |
|---|---|
| `scripts/legacy/normalize_data.py` | Older/simple CSV normalisation script, separate from root `process_patents.py`. |
| `scripts/indexing/build_faiss_index.py` | Deduplicates title/abstract content, encodes with PatentSBERTa, normalizes vectors, and writes FAISS/runtime metadata artefacts. |
| `scripts/kg/build_full_kg.py` | One-time command to populate Neo4j with `KGBuilder`. |
| `scripts/kg/dump_kg.py` | Exports Neo4j database to a shareable dump using Neo4j tooling. |
| `scripts/kg/load_kg.py` | Imports a Neo4j dump into a local database. |
| `scripts/kg/export_cpc_edges.py` | One-off direct Neo4j export of CPC map and sibling edges to `data/exports/`. |
| `scripts/evaluation/generate_gnn_scores.py` | Older offline GNN/novelty-score generation experiment; live inference supersedes it. |
| `scripts/evaluation/evaluate_faiss.py` | Evaluates production FAISS queries against `evaluation_dataset.json`; uses the current `semantic_score` field. |
| `scripts/legacy/evaluate_ai_patents.py` | Small 1,000-row old NumPy retrieval experiment with hard-coded absolute input path. |
| `scripts/legacy/test_search.py` | Demonstrates/tests the old embedding/vector-store/search path. |
| `fixtures/retrieval_evaluation/dataset.json` | Hand-authored relevance set for FAISS evaluation. |
| `docs/reports/faiss-evaluation-sample.txt` | Saved output from FAISS evaluation. |
| `tests/test_gnn.py` | Integration-style test requiring real index, CSV, GNN checkpoint and usually Neo4j. |
| `tests/test_improvement.py` | Mostly mocked unit/API tests for improvement logic; imports the full FastAPI app. |
| `tests/test_connections.py` | Manual Neo4j connection probe using `.env` credentials; not an isolated automated test. |

### React frontend: `frontend/`

| File | Role and connections |
|---|---|
| `package.json` | Frontend commands and dependencies. |
| `package-lock.json` | Exact npm dependency tree. |
| `vite.config.ts` | Vite settings, `@` alias, port 5173 and `/api` proxy to FastAPI port 8000. |
| `tsconfig.json` | TypeScript settings; intentionally non-strict and permits unused locals/parameters. |
| `eslint.config.js` | ESLint configuration, currently scoped to JavaScript/JSX rather than TypeScript/TSX. |
| `tailwind.config.ts` | Tailwind token configuration. |
| `postcss.config.js` | Activates Tailwind and Autoprefixer. |
| `index.html` | Vite HTML shell. |
| `README.md` | Default/frontend-specific developer notes. |
| `public/favicon.svg` | Browser favicon. |
| `public/icons.svg` | Public SVG sprite/icon resource. |
| `src/main.tsx` | Mounts React and router/query-provider application context. |
| `src/App.tsx` | Lazy-loads pages and declares browser routes. |
| `src/index.css` | Global Tailwind directives and the actual shared CSS/component classes. |
| `src/theme.ts` | Shared JavaScript color/theme constants for charts and graph UI. |
| `src/assets/hero.png` | Landing-page bitmap illustration. |
| `src/assets/react.svg` | Vite starter asset; appears unused by product pages. |
| `src/assets/vite.svg` | Vite starter asset; appears unused by product pages. |
| `src/assets/PatentIcons.tsx` | Custom animated patent-themed SVG icon components. |
| `src/layouts/RootLayout.tsx` | Sidebar/navigation shell for result routes; calls store reset for a new analysis. |
| `src/api/client.ts` | Axios base URL, JSON headers, timeout and response-error normalization. |
| `src/api/pipeline.ts` | Typed call to `/pipeline/run`. |
| `src/api/kg.ts` | Typed calls to KG build, expand and graph routes. |
| `src/api/evaluate.ts` | Typed call to `/evaluate` with longer timeout. |
| `src/api/improve.ts` | Typed call to `/improve` with longer timeout. |
| `src/hooks/usePipeline.ts` | React Query mutation for main pipeline; controls navigation and store state. |
| `src/hooks/useKGBuild.ts` | React Query mutation for graph build and store stats. |
| `src/hooks/useKGExpand.ts` | React Query mutation for KG expansion and store state. |
| `src/hooks/useGNNRerank.ts` | Recalculates browser-side ranking from persisted pipeline hits and user-controlled weights. |
| `src/store/usePipelineStore.ts` | Zustand state: input, pipeline, KG, GNN-weight, evaluation and improvement state; selectively persisted to localStorage. |
| `src/types/pipeline.ts` | TypeScript request/result types for the pipeline and evaluation API. |
| `src/types/kg.ts` | KG statistics, expansion and React Flow types. |
| `src/types/gnn.ts` | GNN mode, UI weights and ranked-hit types. |
| `src/types/improvement.ts` | Improvement API types. |
| `src/pages/LandingPage.tsx` | Marketing/introduction and pipeline overview; starts analysis/navigation. |
| `src/pages/IdeaInputPage.tsx` | Idea text, top-k and GNN-mode input; invokes `usePipeline`. |
| `src/pages/PipelineProgressPage.tsx` | Animated progress/status view while the one API request is in flight. |
| `src/pages/NLPResultsPage.tsx` | Shows clean text, keywords, entities and retrieval query from stored pipeline result. |
| `src/pages/RetrievalResultsPage.tsx` | Shows/sorts returned patent candidates and links to graph view. |
| `src/pages/KGVisualizationPage.tsx` | Calls separate KG endpoints, stores graph result, and renders React Flow plus expansions. |
| `src/pages/GNNAnalysisPage.tsx` | Displays reranking charts/table and adjusts only browser-side semantic/GNN blend weights. |
| `src/pages/EvaluationDashboardPage.tsx` | Executes/reuses evaluation and displays score cards, radar chart and detailed breakdown. |
| `src/pages/ImprovementAgentPage.tsx` | Executes/reuses improvement analysis and presents diagnosis, strategies and overlapping patents. |

## Cleanup status and historical findings

The high-impact items from this audit have now been cleaned up: local secrets are
ignored and no longer tracked; Compose no longer embeds credentials or starts an
unused Chroma service; the graph endpoint and build statistics are scoped to the
requested patent IDs; blocking API handlers are synchronous (therefore run in
FastAPI's worker threadpool); cached lookup maps remove repeated DataFrame and
metadata scans; fallback embeddings are normalized; the duplicate GNN
orchestration was consolidated; UI blend defaults now agree with the server; and
the stale FAISS evaluation field was corrected. Chroma, Weaviate, LangChain,
OpenAI, and unused frontend packages were removed from the active dependency
sets. The Streamlit surface is explicitly retained as an optional legacy demo.

The list below is retained as an audit trail. Items 1-8, 10-11, and the
Neo4j/automation part of item 14 are resolved. Item 9 (old retrieval scripts),
item 12 (shared evaluation resources), item 13 (shared graph storage), item 15
(frontend decomposition), and the broader documentation refresh in item 16
remain deliberate follow-up work rather than silent defects in the active
request path.

1. **KG graph endpoint ignores the requested IDs (functional issue).** `GET /api/kg/graph` validates `patent_ids` but its Cypher query is simply `MATCH (n)-[r]->(m) RETURN n,r,m LIMIT 200`. It returns an arbitrary global slice rather than the requested query subgraph. Its layout therefore can be unrelated to the user’s search. Scope the Cypher query to the supplied IDs and/or an explicit query/session identifier.

2. **Sensitive credentials/configuration are unsafe.** `keys.txt` is tracked and modified, yet root `.gitignore` is absent. `docker-compose.yml` and `tests/test_connections.py` include the same illustrative Neo4j password in plaintext. Remove real credentials from Git history if applicable, stop tracking `keys.txt`, add a root `.gitignore`, provide `.env.example`, and use non-secret placeholders in compose/tests.

3. **The API’s `async` endpoints execute blocking CPU, disk, database, and network work inline.** SentenceTransformer loading/inference, FAISS queries, Neo4j driver calls, Gemini calls, and evaluation happen inside `async def` routes. Under concurrent traffic, this blocks the event loop. Move synchronous stages to a worker thread/process or make long analyses queued background jobs with polling/status.

4. **FAISS metadata enrichment is quadratic in practice.** `integration.pipeline.faiss_search()` filters the complete patents DataFrame for every returned hit. Build a `patent_id → row` mapping once alongside cached data instead. KG expansion also linearly scans `metadata_mapping` for each expanded patent; maintain the inverse mapping once.

5. **Expansion fallback embeddings can produce incorrect cosine scores.** Reconstructed FAISS vectors are normalized, but newly encoded family/CPC patents are dotted with the normalized query without first normalizing their encoded vectors. Use `normalize_embeddings=True` or L2-normalize the fallback vector before dot product. The zero-vector fallback should also match the actual detected index dimension rather than hard-coded 768.

6. **The same GNN pipeline is wired twice.** `integration/pipeline.py` has `build_subgraph`, `run_gnn`, and `hybrid_rerank` wrappers while `gnn/scorer.py` provides a wrapper that performs the same three operations. Production uses the former and `get_scorer()` is effectively compatibility code. Pick one orchestration boundary.

7. **Frontend and backend reranking disagree.** Backend rank uses 0.7 semantic / 0.3 graph, while persisted UI defaults are 0.6 / 0.4 and `useGNNRerank` recomputes rankings in the browser. This is a legitimate exploratory UI feature, but the dashboard should label it as a client-side simulation and use the backend weights as its initial state or submit changed weights to a supported API.

8. **The legacy Streamlit surface duplicates the React/FastAPI product.** `streamlit_app.py`, `docs/guides/legacy-streamlit.md`, and some GNN docs describe a different primary route and repeat presentation/orchestration responsibilities. Decide whether Streamlit is supported, demo-only, or retired; otherwise fixes will drift.

9. **Multiple old retrieval/data paths coexist.** The production path is `integration.pipeline → FAISS`; `retrieval/{embed,vector_store,search,evaluate}` plus `test_search.py` and `evaluate_ai_patents.py` use an old in-memory NumPy path. `normalize_data.py` overlaps root `process_patents.py`. Clearly label the experiments as archived or remove/consolidate them after migration.

10. **A production evaluation script is stale.** `scripts/evaluation/evaluate_faiss.py` reads `h["score"]`, but production `faiss_search()` emits `semantic_score`. It will fail with `KeyError` until updated. The script also tests raw query text rather than the production NLP query transformation.

11. **Unused infrastructure/dependencies increase setup time and attack surface.** Runtime code has no Chroma, Weaviate, LangChain, OpenAI, or frontend Lucide/clsx/tailwind-merge imports. Chroma is still launched in Compose and tested manually. Remove unused packages/services or explicitly preserve them as future integrations.

12. **Evaluation reopens heavy resources and many Neo4j sessions.** `per_concept_search.py` independently loads FAISS/model resources rather than using the integration cache. Several component scorers create a driver/session each. A shared resource/driver lifecycle and batched Cypher queries would substantially reduce evaluation latency.

13. **KG mutation and display are globally scoped.** `/kg/build` writes into a shared Neo4j graph and returns counts across the whole database. There is no query/run namespace, cleanup, or ownership boundary. Concurrent users can see/corrupt each other’s “query subgraph” views; the current graph display issue makes this more visible.

14. **Tests are environment-dependent and incomplete as a regression suite.** GNN tests require production artefacts and test connections needs live Neo4j/Chroma with a hard-coded password. There are no isolated tests for API pipeline validation, KG ID scoping, FAISS schema compatibility, or browser-store behavior. Add mocks/fixtures and categorize integration tests separately.

15. **Frontend maintainability is limited by large page components and weak checks.** Several pages are 300–650 lines with inline styles and local helper components. Shared cards/metadata patterns are reimplemented. TypeScript is non-strict and ESLint does not target `.ts`/`.tsx`, allowing UI/API-contract drift to accumulate.

16. **Documentation has drifted.** Some documents describe Streamlit as the main app, Chroma as an active service, static/offline GNN scoring, or a specific UI/index size. Treat this file and the current source as the implementation reference, and update/retire contradictory documents during the next cleanup.

## Recommended maintenance order

1. Secure configuration (`keys.txt`, Compose/test password, `.env.example`, root ignore rules).
2. Fix `/api/kg/graph` scoping and establish per-analysis graph/session semantics.
3. Correct `evaluate_faiss.py`, normalize expansion fallback embeddings, and remove the repeated DataFrame/metadata scans.
4. Choose the supported UI and retrieval paths; mark or remove legacy code and dependencies.
5. Introduce shared backend resources plus background execution for long runs; then add fixture-based tests around the resulting contracts.

## Practical handoff notes

- Start new implementation work from `backend/api/main.py`, `backend/src/integration/pipeline.py`, and `frontend/src/store/usePipelineStore.ts`; together they define the active product path.
- Before running the full API, verify the presence/version alignment of the FAISS index, `metadata_mapping.json`, deduplicated patents CSV, GNN checkpoint, Neo4j database, Python environment (including spaCy model), and `.env` values.
- The root `data/processed` CSVs are the authoritative reproducible source for rebuilding FAISS and Neo4j; generated vector/graph model artefacts are not in this checkout.
- Score field names in the active pipeline are `semantic_score`, `graph_score`, `novelty_score`, and `combined_score`; do not reintroduce the retired generic `score` field into production contracts.
