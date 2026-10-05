# Integration verification — October 5, 2026

The existing frontend and backend are connected to the migrated databases.
This work hardens saving, restoration, metadata, and read-only graph viewing;
it does not add login, new invention-input fields, or a visual redesign.

## Implemented and applied

- Correctly typed JSON persistence for pipeline, evaluation, and improvements.
- Separate saving status, safe optional-failure messages, required-save 503,
  and missing-record 404 handling.
- Multiple runs per case, original per-run idea text, and complete API snapshots.
- Additive MySQL migration, executed against the existing database, plus metadata
  backfill for all 58,428 publication records. A second schema-only run succeeded.
- Jurisdiction, outgoing-citation count, and source family size refreshed in
  Neo4j without rewriting relationships. Unknown metadata is not displayed as
  a fabricated zero or family size of one.
- Read-only graph statistics/viewing; legacy build endpoint retained as a
  deprecated read-only alias. Unique edge counts prevent double-counting when
  both endpoints are requested seeds. Graph rendering uses unique relationship
  IDs, preserves stored direction, and labels projected companies/inventors.
- API-backed refresh and history reopening. Local storage contains input and
  a case/run pointer, not result payloads.
- Independent saved/unsaved UI messages, honest pipeline/evaluation progress,
  correct corpus labels, real patent metadata, and stale-response protection.
- Fixed TypeScript errors, missing GNN FAISS import, actual NLP-source labelling,
  nullable-integer metadata formatting, and UTC timestamp labelling.

## Evidence

| Check | Result |
|---|---|
| Backend unit/contract suite | 17 passed; covers JSON, missing records, required/optional saving, graph reads, unique edge IDs/direction, UTC, metadata formatting, and non-indexed GNN encoding |
| Existing persistence contracts | 3 passed |
| Real MySQL/Neo4j tests | 3 passed: complete snapshots, repeated query IDs, transactional rollback, metadata, graph-count invariance |
| Frontend isolated state tests | 6 passed: clearing, in-flight invalidation, unsaved pointer, pointer-only storage, full restoration, reset |
| TypeScript and production build | Passed; TypeScript checking is part of the build |
| Schema migration repeatability | Second schema-only application passed |
| Browser live AI journey | Submitted idea, retrieved patents, evaluated in fast mode, generated improvements, refreshed, and reopened history |
| Second run in same case | Saved independently; new run cleared prior evaluation/improvements; GraphSAGE completed successfully |
| Grouped publication disclosure | Expanded and displayed retained publication IDs and Lens links |
| Optional-saving failure UI | Controlled fixture visibly showed unsaved analysis plus graph/GNN fallback warnings |

The live browser example was a generic solid-state lithium-battery/temperature
sensor idea, labelled “Integration verification”. Gemini requests returned 200;
PatentSBERTa/FAISS, graph expansion, MySQL saving, evaluation, and improvement
generation ran against actual services, not mocked production responses.

The first run exposed a missing FAISS import in GNN fallback encoding. It saved
with a truthful semantic-fallback warning. The import was fixed, covered by a
regression test, and the second live run loaded the trained GraphSAGE checkpoint
and completed GNN ranking. The second run returned 87 grouped results from a
top-five semantic seed request; graph expansion intentionally adds candidates.

One verification case with two real runs remains in Saved Cases. The first has
saved evaluation and improvements; the second demonstrates corrected live GNN
ranking. Automated database tests deleted only their own temporary UUID cases.
No patent publications or existing graph relationships were removed.

The unavailable-database/missing-model UI check used
`tests/serve_unsaved_fixture.py`; no live database was stopped or modified for
that failure scenario. The fixture performs no AI calls or database writes.
It was stopped afterward and the real API restored. Required-save failures
were separately verified as HTTP 503 in the contract tests.

## Repeating checks

The suites above total 29 passing tests. Screenshot evidence is stored locally
in `artifacts/verification/integration-saved-runs.jpg` (ignored by Git).

From the repository root, in PowerShell:

```powershell
venv/Scripts/python.exe -m unittest discover -s backend/tests -v
venv/Scripts/python.exe -m unittest discover -s tests -p test_persistence_contract.py -v
$env:RUN_DATABASE_TESTS = '1'
venv/Scripts/python.exe -m unittest discover -s tests -p test_live_integration.py -v
Remove-Item Env:RUN_DATABASE_TESTS
cd frontend
npm test
npm run build
```

Frontend state tests use Node 24 or newer. Live database tests use local
`.env` configuration and create/delete only their own isolated verification
cases. Do not run a full bootstrap, graph rebuild, or delete Docker volumes to
apply these integration changes; use the additive migration described in
[database setup](../database/README.md#updating-an-already-populated-database).

## Remaining limitations and next work

- **Dependency audit:** npm reports 17 advisories (14 high, 2 moderate, 1 low).
  Some suggested fixes require a major Tailwind upgrade. No forced dependency
  upgrade was applied; plan compatible updates and rerun the browser/build
  checks before treating this as deployment-ready.
- **Latency:** the second CPU-based pipeline took about 89 seconds. Expansion
  and structural-neighbor embedding use repeated encoder calls. Batch encoding,
  shared embedding caches, and queued jobs are suitable performance follow-ups;
  the progress UI no longer pretends these stages finish on a timer.
- **Access control:** case/report routes remain unauthenticated. Login and
  ownership enforcement are separate work, required before multi-user exposure.
- **Model quality:** this verifies execution and persistence, not retrieval
  relevance, GNN calibration, patentability accuracy, or legal validity. Only
  fast-mode evaluation was exercised live; deep reconstruction is not covered
  by this browser check.
- **Scope of graph checks:** request-time graph counts were unchanged; this
  is not a full per-edge/property comparison of the entire projection.
- **Historical runs:** existing snapshots missing newly added fields cannot
  be retroactively reconstructed. Their unknown source/metadata stays unknown.
- **Database/schema lifecycle:** cached runtime metadata updates after API
  restart. SQL DDL commits implicitly; migration structure changes are not one
  atomic rollback unit, while the metadata backfill is transactional.

See the [completed checklist](../planning/integration-checklist.md) and
[current architecture](../architecture.md) for future sessions.
