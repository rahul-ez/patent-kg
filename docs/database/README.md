# MySQL Persistence Implementation

MySQL is the normalized source of truth. Neo4j is a one-way graph projection
for traversal, while FAISS is an embedding index rather than a database.

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

## Implementation artefacts

- [`../../database/sql/01_schema.sql`](../../database/sql/01_schema.sql): 3NF DDL, keys, checks, indexes, and FK constraints.
- [`../../database/sql/02_reporting_views.sql`](../../database/sql/02_reporting_views.sql): retrieval and reporting views.
- [`../../database/sql/03_roles.sql`](../../database/sql/03_roles.sql): least-privilege MySQL accounts; replace placeholders locally.
- [`../../database/sql/04_query_portfolio.sql`](../../database/sql/04_query_portfolio.sql): eight SQL queries covering joins, grouping, `HAVING`, subqueries, update/delete, and division-style logic.
- [normalization.md](normalization.md): ER mapping, 3NF rationale, functional dependencies, relational algebra, and the three-schema explanation.

The `database/sql/03_roles.sql` script is deliberately not mounted in Docker;
it contains local-only placeholders and requires an administrator decision.
