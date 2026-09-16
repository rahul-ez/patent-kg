# PLAN.md — MySQL Integration Plan for Patent Intelligence Platform

Blueprint ready.

## Summary

Keep the full NLP → FAISS → Neo4j → GNN → evaluation → improvement pipeline intact. Add MySQL as the normalized relational source of truth and retain Neo4j as its derived graph-query layer, with clear SQL–NoSQL integration boundaries.

## Architecture and database design

- Use Docker Compose to run MySQL and Neo4j. Remove Chroma from the required demo stack because the active system uses FAISS, not Chroma.
- Import existing processed patent CSVs into MySQL through an idempotent, batched bootstrap command. Keep CSVs as reproducible raw/ETL inputs, but make MySQL the application’s authoritative structured datastore.
- Model and document a 3NF relational schema:
  - Core: `patents`, `assignees`, `inventors`, `cpc_codes`, `npl_references`, citation snapshots.
  - Junction/relationship tables: patent–assignee, patent–inventor, patent–CPC, patent–NPL, and patent-family relationships.
  - Application records: `analysis_cases`, `analysis_runs`, `run_patent_results`, evaluation metrics, and improvement recommendations.
  - Minimal user/role records for ownership, auditing, and database security demonstration.
- Define primary keys, foreign keys, unique constraints, check constraints, indexes, cardinalities, and functional dependencies. Include ER/EER diagram, relational mapping, normalization proof through 3NF, and a three-schema architecture explanation.
- Build Neo4j from MySQL through a one-way projection/synchronization command. MySQL owns entity and relationship facts; Neo4j owns no independent business data and is used only for family, CPC, inventor/company, and citation traversal.
- Rebuild FAISS from a MySQL retrieval view/export. Preserve the current embedding model, index structure, NLP, GNN, and Gemini behavior.

## Application changes

- Add a database access layer with parameterized MySQL queries/ORM models and environment-based credentials.
- Keep the existing pipeline endpoint and UI behavior. On every analysis:
  - Create or reuse an analysis case.
  - Create an analysis-run record.
  - Run the current AI pipeline unchanged.
  - Persist retrieved/expanded/reranked patent results, scores, evaluation results, and improvement recommendations.
  - Return `case_id` and `run_id` alongside the existing pipeline response.
- Add case-management CRUD endpoints and a small frontend view for saved analyses:
  - Create/list/view/update/delete draft analysis cases.
  - View prior runs and their stored candidate patents, scores, and recommendations.
  - Preserve existing result pages as the primary live-analysis experience.
- Replace CSV-only runtime patent metadata lookup with a MySQL-backed repository/cache while preserving the DataFrame interface needed by GNN code.
- Add read-only reporting endpoints/pages backed by SQL joins and aggregations: patent counts by domain/year, top assignees, prolific inventors, CPC distribution, family size/citation reports, and analysis-case risk summaries.
- Use a dedicated application database user, read-only reporting user, environment secrets, least privilege, foreign-key enforcement, validation, and audit timestamps. Do not expose database passwords in Compose, tests, or tracked files.

## Database operations and documentation

- Provide SQL DDL, seed/bootstrap scripts, sample DML, views, indexes, and documented complex queries using joins, grouping, `HAVING`, subqueries, updates, and deletes.
- Include relational-algebra equivalents for representative selection, projection, join, and division-style queries.
- Document why Neo4j is the NoSQL component and why FAISS is a retrieval index rather than the project database.
- Maintain:
  - ER/EER diagram and cardinality/key documentation.
  - Relational schema and 3NF proof.
  - SQL query portfolio with expected output screenshots.
  - Docker setup guide and demo script.
  - Architecture notes covering domain, requirements, security, database design, AI integration, limitations, and future work.
- Demo sequence: seed MySQL → project to Neo4j → build FAISS → run a complete AI analysis → show persisted case/run data → execute SQL reports → show equivalent Neo4j traversal.

## Test plan

- Verify bootstrap row counts, uniqueness, foreign keys, null handling, and idempotent re-import behavior.
- Verify MySQL-to-Neo4j projection parity for sampled patents and relationships.
- Verify existing pipeline output remains available when persistence succeeds and produces a clear error when database persistence fails.
- Test analysis-case CRUD, saved-run retrieval, SQL report accuracy, invalid input handling, and authorization boundaries.
- Run regression tests for FAISS retrieval, KG expansion, GNN reranking, evaluation, and improvement-agent fallback behavior.
- Acceptance criterion: a clean Docker setup can demonstrate the complete AI pipeline plus normalized MySQL CRUD/reporting and Neo4j graph traversal without depending on manually edited database state.

## Assumptions

- MySQL + Neo4j is accepted as the required SQL–NoSQL integrated solution.
- The initial scope excludes transaction/concurrency and distributed-data features.
- The existing AI pipeline remains mandatory and unchanged in purpose; database integration adds persistence, traceability, and reproducible reporting.
- The implementation includes the running application and its supporting technical documentation.
