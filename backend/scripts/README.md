# Backend Operations

Run commands from `patent-kg/backend`. Production request handling belongs in
`api/` and `src/`; these scripts are one-off build, maintenance, or evaluation
tools.

| Directory | Purpose | Command examples |
|---|---|---|
| `database/` | Add authentication tables or explicitly assign a legacy case. | `python scripts/database/migrate_auth.py`; `python scripts/database/assign_case_owner.py --list-unowned` — see [authentication](../../docs/authentication.md). |
| `data/` | Create normalized relational CSV tables from raw Lens exports. | `python scripts/data/process_patents.py` |
| `indexing/` | Build the FAISS index from `data/processed/patents.csv`. | `python scripts/indexing/build_faiss_index.py` |
| `kg/` | Build, dump, load, or export the Neo4j graph. | `python scripts/kg/build_full_kg.py` |
| `evaluation/` | Evaluate retrieval, benchmark pipeline performance, and generate optional offline novelty artefacts. | `python scripts/evaluation/evaluate_faiss.py`; from the repository root: `python backend/scripts/evaluation/benchmark_pipeline.py --output artifacts/performance/current.json` |
| `legacy/` | Superseded NumPy retrieval experiments; not part of production. | Do not use for the React/FastAPI path. |

Generated reports are written under `docs/reports/`; local data, vector indexes,
and Neo4j files are ignored by Git.
