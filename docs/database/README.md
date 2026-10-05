# MySQL Persistence Implementation

MySQL is the normalized source of truth. Neo4j is a one-way graph projection
for traversal, while FAISS is an embedding index rather than a database.

## Entity-relationship model

The Chen ER diagram is deliberately split into two print-ready sheets so its
attributes and relationships remain readable:

- [Sheet 1 — patent knowledge data (SVG)](er-diagram-chen-patent-data.svg)
- [Sheet 2 — user and analysis data (SVG)](er-diagram-chen-analysis-data.svg)

Both use rectangles for entities, diamonds for relationships, ovals for
attributes, and underlined key attributes. The earlier
[relational implementation map](er-model.svg) and its editable
[Mermaid source](er-model.mmd) remain available for the full physical-table view.

## Setup and demo

1. Copy `.env.example` to `.env` and assign all `MYSQL_*` and `NEO4J_*` values.
2. Start services: `docker compose up -d mysql neo4j`.
3. Import normalized CSVs: `cd backend && python scripts/database/bootstrap_mysql.py`.
4. Project relational facts to Neo4j: `python scripts/database/sync_mysql_to_neo4j.py`.
5. Export and rebuild FAISS from MySQL: `python scripts/database/export_mysql_retrieval.py`, then
   `python scripts/indexing/build_faiss_index.py --input ../data/vector_store/mysql_retrieval_export.csv`.
   Run the React/FastAPI analysis afterward.
6. Create a saved analysis through `POST /api/cases` or attach `case_id` to
   `POST /api/pipeline/run`; inspect persisted history and `/api/reports/*`.

## Updating an already-populated database

Run from the repository root with the project's Python environment active:

```powershell
python backend/scripts/database/migrate_integration.py
python backend/scripts/database/sync_mysql_to_neo4j.py --metadata-only
```

The additive migration adds jurisdiction, outgoing-citation count, source
family size, per-run idea text, and the complete improvement JSON snapshot.
It backfills patent metadata from `data/processed/patents.csv` without rerunning
the full import. Repeated `query_id` values are permitted: `run_id` identifies
each separate analysis. `--schema-only` skips the metadata backfill.

The projection command above updates Patent properties only. It does not replace
graph relationships. Existing snapshots lacking full improvement output cannot
be reconstructed retroactively; subsequent runs save the complete payload.

## Saving and reopening analyses

Pipeline, evaluation, and improvement responses each expose `persistence_status`
and, when saving fails, `persistence_message`. Set `PERSISTENCE_REQUIRED=true`
to return HTTP 503 on an unavailable persistence service; otherwise available
analysis output is returned with an explicit `not_saved` status. Missing cases
or runs return 404 rather than being treated as an offline saving failure.

`GET /api/cases/{case_id}/runs/{run_id}` restores the original per-run idea,
pipeline, evaluation, and improvement output. The browser stores only input and
the saved case/run identifiers; it does not use local storage as the result
authority. MySQL sessions use UTC and API timestamps include the timezone.

Graph viewing uses `GET /api/kg/stats` and `GET /api/kg/graph`; the deprecated
`POST /api/kg/build` is a read-only compatibility alias. All three inspect the
displayed graph slice, capped at 200 edges. Frontend graph requests use at most
100 result IDs; these statistics are not totals for the entire database.

See the [integration checklist](../planning/integration-checklist.md) and
[verification report](../reports/integration-verification.md).

## Implementation artefacts

- [`../../database/sql/01_schema.sql`](../../database/sql/01_schema.sql): 3NF DDL, keys, checks, indexes, and FK constraints.
- [`../../database/sql/02_reporting_views.sql`](../../database/sql/02_reporting_views.sql): retrieval and reporting views.
- [`../../database/sql/03_roles.sql`](../../database/sql/03_roles.sql): least-privilege MySQL accounts; replace placeholders locally.
- [`../../database/sql/04_query_portfolio.sql`](../../database/sql/04_query_portfolio.sql): eight SQL queries covering joins, grouping, `HAVING`, subqueries, update/delete, and division-style logic.
- [normalization.md](normalization.md): ER mapping, 3NF rationale, functional dependencies, relational algebra, and the three-schema explanation.

The `database/sql/03_roles.sql` script is deliberately not mounted in Docker;
it contains local-only placeholders and requires an administrator decision.

## Neo4j credentials and existing data

Docker mounts `neo4j_data` as Neo4j's persistent database directory.
`NEO4J_AUTH`, derived from `.env`, sets the password only for a new database;
it does not replace a password already stored in that directory. Restarting
Docker or editing `.env` therefore does not reset an existing login.

For a forgotten password, follow Neo4j's
[password recovery procedure](https://neo4j.com/docs/operations-manual/current/authentication-authorization/password-and-user-recovery/):
stop the server, back up the complete data directory, temporarily disable
authentication in an isolated recovery instance, change the password in the
`system` database, then stop recovery and restart with authentication enabled.
Never delete `neo4j_data` to fix a login problem. Recovery backups contain
database data and authentication records; keep them local and out of Git.

See the [verified migration status](../reports/database-migration-status.md)
for the latest local database counts, recovery backup location, and checks.
