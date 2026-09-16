# Project Documentation

`README.md` at the repository root is the only setup and run entry point.
This directory holds supporting material so implementation documents do not
compete with the primary guide.

| Area | Document | Purpose |
|---|---|---|
| Architecture | [architecture.md](architecture.md) | Current implementation map, dependencies, cleanup status, and follow-up work. |
| Guides | [evaluation.md](guides/evaluation.md) | Evaluation-engine API and scoring details. |
| Guides | [legacy-streamlit.md](guides/legacy-streamlit.md) | Optional legacy Streamlit demo only. |
| Reference | [knowledge-graph.md](reference/knowledge-graph.md) | Neo4j model, build process, and graph operations. |
| Reference | [gnn.md](reference/gnn.md) | GraphSAGE and ranking notes. |
| Planning | [planning/](planning/) | Database integration plan and prior redesign specifications. |
| Database | [database/](database/) | MySQL schema, 3NF proof, relational algebra, security, and operational instructions. |
| Internal | [internal/](internal/) | Development context and checklist. |
| Reports | [reports/](reports/) | Checked-in example evaluation output. |

Operational commands are grouped in [`backend/scripts/README.md`](../backend/scripts/README.md).
