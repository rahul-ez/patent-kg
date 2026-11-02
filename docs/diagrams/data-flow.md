# Data-flow diagrams

These diagrams describe the current React/FastAPI application, its analysis
services, and the offline patent-data preparation scripts. They use
**Yourdon-DeMarco notation**: circular numbered processes, rectangular external
entities, two parallel horizontal lines for each data store, and labelled arrows
for data flows. Both ends of a store remain open, with no identifier compartment.
They describe data movement rather than a mandatory sequence of user actions.

- [Open/edit all three levels in draw.io](patent-data-flow.drawio)
- [Download the complete three-page PDF](../../output/pdf/patent-data-flow-diagram.pdf)
- [Download the combined ER, relational schema, and data-flow PDF](../../output/pdf/patent-system-diagrams.pdf)
- [Edit all three data-flow sheets in draw.io](patent-data-flow.drawio)
- Context / Level 0: [PNG](data-flow-1.png) / [editable SVG](data-flow-context.svg)
- Application / Level 1: [PNG](data-flow-2.png) / [editable SVG](data-flow-system.svg)
- Analysis / Level 2: [PNG](data-flow-3.png) / [editable SVG](data-flow-analysis.svg)

## Level 0: system context

The researcher supplies credentials, an invention idea, settings, and case,
graph, or report requests. The platform returns session status, ranked
publications, assessments, improvement guidance, saved history, and public
views. The data maintainer supplies patent export files and preparation
settings. Gemini supplies structured NLP, concept/scoring assistance, and
explanations in response to prompts from the analysis services. Local fallback
paths remain available when Gemini cannot be used.

## Level 1: application and stores

| Process | Implementation responsibility |
|---|---|
| 1.0 Authenticate user | Signup/login/logout, password hashing, cookie sessions, CSRF, expiry and throttling. |
| 2.0 Handle research requests | Authenticated dispatch, case/run ownership, saved-run reuse, CRUD, persistence and response saving status. |
| 3.0 Analyze and explore patent information | Retrieval, graph ranking, on-demand evaluation/improvement, and public graph/report reads. |
| 4.0 Prepare patent corpus and derived artifacts | Offline CSV normalization/import, MySQL export, Neo4j projection and FAISS rebuild. |

The processes are logical responsibilities; they group existing API handlers
and services rather than introducing new endpoints or background jobs. Authentication
and ownership checks apply to every protected request, not only the first login.

| Store | Physical implementation and contents |
|---|---|
| D1 Accounts and sessions | MySQL `app_users`, `roles`, `user_roles`, `auth_sessions`, `auth_rate_limits`. |
| D2 Private saved research | MySQL cases, runs, result links, evaluation metrics, recommendations and complete JSON snapshots. |
| D3 Public patent catalog | MySQL normalized patent, domain, inventor, assignee, classification, family and citation records. |
| D4 Semantic index | Local FAISS index and row-to-publication mapping. |
| D5 Patent knowledge graph | Derived Neo4j projection used for graph traversal and viewing. |
| D6 Public embedding cache | Bounded memory LRU and local SQLite public-patent vectors. |

D1-D3 are logical groups in the **same MySQL database**, not three separate
database servers. Repeated D3-D5 symbols refer to the same stores. Preparation
passes canonical data through the offline scripts before updating derived
projections; ordinary searches do not rebuild the corpus or graph.

## Level 2: analysis decomposition

Process 3.1 cleans the idea and extracts NLP information. Process 3.2 encodes
the query and retrieves semantic matches using FAISS and canonical metadata.
Process 3.3 expands family/CPC neighbours, builds the GraphSAGE subgraph, scores
and reranks candidates, and groups identical result text while keeping distinct
publication IDs available.

The query vector is request-local and reused within the pipeline. Public
publication vectors are read from FAISS/cache or batch-encoded as needed. Only
canonical public patent inputs populate D6; private query text/vectors and
analysis outputs are not shared through that cache.

Process 3.4 performs per-concept searches and patentability scoring. Process
3.5 uses overlap, weaknesses, domain strategies and the assessment to produce
improvement guidance. These are separate requests: a normal retrieval can
return after 3.3. Existing owned snapshots can supply prior hits and assessment
data; missing prerequisites may be computed by the evaluation/improvement
handlers. For saved-run work, server-side owned snapshots replace client-supplied
payloads. Process 2.0 persists the output when requested and reports the actual
saving status.

Process 3.6 reads public graph slices and SQL patent summaries. These reads do
not mutate the underlying graph. Private case-risk reports remain owner-filtered
reads through process 2.0 and D2.

## Source and regeneration

The diagrams were traced through `api/auth.py`, the authentication/case/pipeline/
evaluation/improvement/graph routers, `integration/pipeline.py`, GNN scoring,
`evaluation/patentability_engine.py`, `improvement/agent.py`, persistence stores,
the shared patent-vector resolver, and the database/index preparation scripts.
Current implementation details remain in [architecture](../architecture.md),
[authentication](../authentication.md), and [performance](../performance.md).

From the repository root, using a Python environment with the documentation-only
`reportlab` package and Poppler's `pdftoppm`:

```powershell
python backend/scripts/documentation/generate_data_flow.py
pdftoppm -scale-to 3200 -png output/pdf/patent-data-flow-diagram.pdf docs/diagrams/data-flow
```

Open the `.drawio` file in draw.io/diagrams.net using **File > Open From > Device**.
It contains three pages with native editable shapes, attached directional
connectors, process identifiers and data-flow labels. Its connectors use draw.io's
routing; the PDF and SVG exports use the generator's validated routing lanes.
The symbol styles follow the [draw.io DFD library](https://www.drawio.com/docs/diagram-types/data-flow-diagrams/)
and [Yourdon notation overview](https://www.ibm.com/think/topics/data-flow-diagram).

The generator validates that every flow has a process endpoint, routes meet the
circle boundaries and avoid node interiors, labels avoid nodes/arrows, and nodes
do not overlap. Small line
jumps distinguish unconnected crossings. It reuses the line-jump geometry from
`generate_horizontal_schema.py`. The exported PDF contains vector graphics and
searchable text; SVG copies and the native `.drawio` document remain editable.
All 57 existing labelled flows are retained across the three levels.
Generation does not access live
databases, accounts, external AI services, or user data.
