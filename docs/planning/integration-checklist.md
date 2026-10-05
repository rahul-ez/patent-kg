# Integration hardening checklist

Scope: make the existing application reliably read the migrated data, save
analyses, and reopen them. Login, new input fields, and visual redesign are
separate work. Existing user changes and patent publications are preserved.

## Backend contracts and persistence

- [x] Serialize JSON payloads correctly for MySQL; preserve complete results.
- [x] Return explicit saving status for pipeline, evaluation, and improvements.
- [x] Preserve required-persistence HTTP errors instead of swallowing them.
- [x] Support multiple runs under one case and reload complete saved runs.
- [x] Restore evaluation and full improvement output, not only strategy rows.
- [x] Test rollback, missing cases/runs, and repeat analysis behaviour.

## Metadata and graph safety

- [x] Add an additive, repeatable migration for missing patent metadata.
- [x] Backfill jurisdiction, outgoing citations, and source family size.
- [x] Expose real metadata or unknown values through retrieval and expansion.
- [x] Make graph viewing/statistics read-only; do not invoke CSV graph writes.
- [x] Keep MySQL authoritative and preserve existing graph relationships.

## Frontend integration

- [x] Fix TypeScript errors and make type-checking part of the build.
- [x] Display saved/unsaved status independently of analysis success.
- [x] Replace simulated progress with honest request/stage status.
- [x] Correct corpus counts and handle unknown patent metadata.
- [x] Retain expandable identical-text publications with accurate labels.
- [x] Open a saved run from history and restore results from the API.
- [x] Reanalyse within the same case, keeping separate run history.
- [x] Clear stale results when beginning a different analysis.

## Verification and handoff

- [x] Backend unit/contract tests pass.
- [x] Real MySQL save/read/update/rollback checks pass using isolated test data.
- [x] Graph-view requests do not change live graph counts.
- [x] Frontend type-check and production build pass.
- [x] Browser journey: submit, retrieve, evaluate, improve, refresh, reopen.
- [x] Exercise missing-database/model fallbacks and visibly unsaved output.
- [x] Attempt a live AI analysis; distinguish external failures from fixtures.
- [x] Document actual results, limitations, and commands for future sessions.

## Verification notes

Completed October 5, 2026. All scoped integration checks passed: 17 backend
unit/contract tests, 3 existing persistence tests, 3 live-database tests, and
6 frontend state tests (29 total), plus TypeScript/build and the live browser
journey. The second live run completed GraphSAGE ranking successfully.

The unsaved/missing-model UI scenario used a controlled failure fixture; the
successful analysis/evaluation/improvement checks used real services. One
verification case with two real runs remains available in Saved Cases.

Full evidence, commands, and limitations are in the
[verification report](../reports/integration-verification.md). Current technical
behaviour is reflected in [architecture](../architecture.md).

## Follow-up work outside this checklist's scope

- [ ] Address the 17 npm audit advisories with compatible dependency upgrades.
- [ ] Add login and enforce per-user case/report ownership before multi-user deployment.
- [ ] Batch/cache structural embeddings and reduce the observed CPU pipeline latency.
- [ ] Evaluate model/retrieval quality and exercise full reconstruction mode.
