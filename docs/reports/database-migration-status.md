# Database migration status

Verified locally on October 5, 2026. The MySQL import and MySQL-to-Neo4j
projection are complete. This is a live database verification, separate from
the earlier [CSV data audit](patent-data-audit.md).

## Password recovery

The `.env` credentials were correctly passed to Docker, but the persisted
Neo4j database rejected them. Its system database dates to November 22, 2025;
the reason its stored password differed was not established.

Following Neo4j's documented password-recovery procedure, the server was
stopped and its complete data directory copied to:

`artifacts/backups/neo4j-before-password-reset-20261005-120812/neo4j_data`

All 84 copied files were verified against their source SHA-256 hashes. The
password was reset to the existing `.env` value through an isolated recovery
container with no network access or published ports. The normal service was
then restarted with authentication enabled. The configured password succeeds;
an intentionally incorrect password is rejected. Temporary recovery containers
were removed. No graph data was deleted for password recovery.

The saved graph contained no nodes immediately after recovery, before the
projection began. MySQL's previously committed import was intact.

## Verified source and projection counts

Each row below was independently counted in both databases after the sync
script finished with exit code 0.

| MySQL source | Neo4j projection | Count in each |
| --- | --- | ---: |
| `patents` | `Patent` | 58,428 |
| `domains` | `Domain` | 6 |
| `assignees` | `Company` | 17,503 |
| `inventors` | `Inventor` | 65,740 |
| `cpc_codes` | `CPCCode` | 44,399 |
| `npl_references` | `Paper` | 181,955 |
| `patent_domains` | `IN_DOMAIN` | 58,693 |
| `patent_assignees` | `OWNS` | 71,058 |
| `patent_inventors` | `INVENTED` | 187,206 |
| `patent_cpc_codes` | `HAS_CPC` | 749,202 |
| `patent_npl_references` | `CITES_PAPER` | 277,934 |
| `patent_families`, SIMPLE | `SIMPLE_FAMILY_MEMBER` | 136,444 |
| `patent_families`, EXTENDED | `EXTENDED_FAMILY_MEMBER` | 215,520 |

MySQL also retains 58,428 citation snapshots; these are relational history,
not separate nodes in this graph projection.

## Additional checks and changes

- The complete Patent ID and CPC-code sets match between MySQL and Neo4j.
- Neo4j has zero duplicate Patent IDs, zero stub Patent nodes, and zero
  self-referential family edges.
- Every MySQL patent has a domain membership; 265 patents have multiple
  memberships. The missing `patent_domains.csv` was generated from the raw
  source collections, restricted to retained patent IDs, and imported without
  repeating the full MySQL bootstrap. The domain reporting view was refreshed.
- The projection script now creates indexes for its actual MERGE keys, waits
  for them to become online, checks connectivity before writes, validates
  batch size, explicitly marks imported patents as non-stubs, and prints
  batch progress. All indexes were verified online.
- Six regression tests pass, including projection-index and batch-size checks.
- An application-level `expand_via_kg` smoke test returned five family
  publications and 34 CPC siblings for a known family-linked patent.
- MySQL is healthy on host port 3307. Neo4j is running on ports 7474/7687.

## Scope and remaining limitations

**Subsequent integration update (October 5, 2026):** the jurisdiction gap noted
below is now closed, along with outgoing-citation counts and source family size.
These properties were backfilled in MySQL and refreshed in Neo4j without
rebuilding relationships. Live frontend analyses, saving, and reopening are
covered by the [integration verification report](integration-verification.md).
The following paragraphs retain the scope of the earlier migration snapshot.

Distinct patent publication IDs remain separate even when they share family,
classification, or identical text. The vector corpus and post-ranking result
grouping handle repeated text; this migration does not collapse legal documents.

The smoke test emitted a non-fatal missing-property warning for `jurisdiction`:
the MySQL patent schema and its projection do not currently carry that field,
although the expander requests it. Results default it to an empty string.
Adding jurisdiction to relational persistence is separate schema work.

FAISS/GNN artifacts were not rebuilt in this recovery, and a complete frontend
analysis was not run. Count equality and the reported node-set comparisons are
not a full per-property or per-edge-set comparison of every record.

Keep the recovery backup local: it includes patent data and authentication
records. The repository ignores `artifacts/` and `.env`.
