# Patent data audit

Audited on 2026-09-28 against the local CSV exports and retrieval metadata. This is a read-only audit: no source records, processed tables, graph data, or vector index were changed. Reproduce the counts from the repository root with `python backend/scripts/audit_patent_data.py`.

## Executive finding

The suspected overlap is real, but it is primarily **multiple patent documents for related inventions**, not duplicate patent primary keys. `patents.csv` has 58,428 rows and 58,428 unique Lens IDs. Exact normalized title-and-abstract matching finds 13,961 repeated-content groups, with 22,075 rows beyond one representative per group (37.8% of the patent rows). Of those groups, 13,687 contain at least one pair linked through a SIMPLE-family component **and** sharing at least one CPC code. A shared CPC code alone is not evidence of duplication: classifications are intentionally many-to-many and can cover thousands of unrelated patents.

The existing retrieval corpus has already reduced the 58,428 patent documents to 36,353 unique title-and-abstract hashes. The distinct patent documents remain in the processed data so publication, jurisdiction, legal status, citation, and family relationships are not lost.

## Counts by data layer

| Data | Observed | Interpretation |
| --- | ---: | --- |
| Six raw domain CSVs | 60,000 rows; 59,735 unique Lens IDs | 265 IDs appear in two domain files; no repeated ID within an individual file. |
| `processed/patents.csv` | 58,428 rows; 58,428 unique IDs | No duplicate primary keys. Two repeated display keys deserve a separate identifier check. |
| Identical normalized title + abstract | 13,961 groups; 22,075 excess rows | Exact-content overlap, not a legal-document identity test. |
| Repeated normalized title alone | 14,754 groups; 28,463 excess rows | Weaker signal; titles alone should not drive deduplication. |
| Identical-content groups with a SIMPLE-family connection | 13,688 | At least one pair in each group is connected through SIMPLE-family links. |
| Identical-content groups with a shared CPC | 13,916 | At least one pair in each group shares a CPC classification. |
| Identical-content groups with **both**, on the same pair | 13,687 | Strong support for the reported family/classification overlap. |
| Identical-content groups with an EXTENDED-family connection | 13,873 | Extended families are broader and should not be collapsed indiscriminately. |
| Retrieval corpus and metadata mapping | 36,353 rows each | Corpus patent IDs are unique; content hashes are unique; mapping order matches the CSV. |

Example: `US 12153417 B2` and `US 2020/0194031 A1` have different Lens IDs and publication identifiers but the same normalized title and abstract. They appear in the same repeated-content group. Application/grant and cross-jurisdiction variants may be legitimate separate patent documents; a text match is not sufficient grounds to delete either one.

## Relationships and classification quality

- `classifications.csv` has 1,020,178 rows: 749,202 CPC, 268,921 IPCR, and 2,055 US. There are no repeated `(patent_id, classification_type, classification_code)` triples and no source patent IDs absent from `patents.csv`. CPC is present on 58,372 patents. Of 44,399 CPC codes, 35,020 occur on multiple patents; for example `G06N20/00` occurs on 4,439 patents. This is normal classification reuse.
- `patent_families.csv` has 1,433,689 rows. Among patents in the local corpus, SIMPLE links form 15,576 multi-patent connected components containing 43,637 patents; EXTENDED links form 15,271 such components containing 45,097 patents. These are graph components computed from the exported links, **not** certified canonical family IDs. The largest SIMPLE/EXTENDED components contain 75/171 local patents respectively. Review unusually large components before treating them as one invention.
- Family relations name 157,557 member IDs not present in `patents.csv`. These are references outside the sampled patent corpus, not missing source rows. The MySQL importer intentionally skips absent members to preserve foreign keys; the Neo4j builder creates stub patent nodes for them. There are also 1,519 repeated `(patent_id, family_type, family_member)` triples when jurisdiction is excluded from the key. Check whether those are alternate jurisdiction annotations or export noise; they should not create multiple logical family edges.
- `citations_metadata.csv` has exactly one row for each of the 58,428 processed patent IDs, with no orphan IDs.

## Implementation risks found

1. **Non-CPC classifications are treated as CPC.** [`bootstrap_mysql.py`](../../backend/scripts/database/bootstrap_mysql.py) imports every classification row into `cpc_codes` and `patent_cpc_codes`, without filtering `classification_type == "CPC"`. There are 115,190 distinct patent–code links contributed only by IPCR/US rows that would be added to those CPC tables. [`builder.py`](../../backend/src/kg/builder.py) likewise creates `CPCCode` nodes and `HAS_CPC` edges from all classification types. This can make classification-based graph expansion return false CPC siblings. The count is based on the CSV and importer logic; it is not a live database count.
2. **Search can reintroduce repeated inventions.** [`build_faiss_index.py`](../../backend/scripts/indexing/build_faiss_index.py) keeps the first row per exact normalized title-and-abstract hash for the vector corpus. [`expander.py`](../../backend/src/kg/expander.py) then adds family members and classification siblings from the full graph, and [`pipeline.py`](../../backend/src/integration/pipeline.py) combines those with vector hits without a final content- or family-level grouping step. Distinct IDs can therefore appear as near-identical search cards even though the vector corpus itself is deduplicated. The actual frequency in user queries was not measured here.
3. **“Semantic duplicate” is an overstatement in the indexer.** Its hash detects only text that matches after lowercasing and whitespace normalization. Paraphrases, changed abstracts, and different-language family publications remain separate. Conversely, exact text alone should not erase distinct legal documents from the canonical tables.
4. **Raw domain overlap loses secondary labels.** [`process_patents.py`](../../backend/scripts/data/process_patents.py) keeps the first row per Lens ID after concatenating domain files. For the 265 cross-domain IDs, the canonical `domain` field preserves only the first domain. If cross-domain membership matters, model it as a separate patent–domain relationship.

## Recommended order of work

1. Filter CPC-only data in both MySQL and Neo4j import paths, then rebuild the affected classification tables/edges. If IPCR/US are needed, retain them as explicitly typed classifications rather than relabeling them as CPC.
2. Keep `patent_id` as the document key. Add an explicit family/grouping key or result-grouping layer for the UI, while preserving each publication as a child record with its own jurisdiction, dates, status, and citations. Prefer source family identifiers where available; do not infer one legal family solely from a matching title, abstract, or CPC code.
3. Group or collapse identical-content results **after** graph expansion, with an option to reveal all publications. Record which representative-selection rule is used; “first CSV row” is not a quality ranking.
4. Investigate the two repeated display keys and the 1,519 repeated family triples before relying on those fields as unique identifiers. Preserve raw evidence until each case is resolved.
5. Add regression checks for unique patent IDs, valid source IDs, classification type separation, retrieval mapping alignment, and result grouping. This audit script can supply a baseline, but it does not replace live MySQL/Neo4j integrity checks.

## Remediation status (2026-09-28)

The code now filters CPC-only rows in both MySQL and Neo4j import paths. Re-running the MySQL bootstrap also reconciles `patent_cpc_codes` against the CPC rows in the processed CSV and removes unreferenced, undescribed CPC-code rows. The MySQL-to-Neo4j projection and full graph builder replace old `HAS_CPC` edges before rebuilding them. These refreshes change persisted projections; back up either database before running them in an environment containing other work.

The search response now groups results with identical normalized **full** titles and abstracts after GNN ranking (or semantic fallback). The highest-ranked publication is shown, and other matching result IDs remain available under `related_publications` and in an expandable list on the retrieval page. It does not group merely because publications share a family or CPC code. The canonical patent CSV remains unchanged.

After supplying local database credentials and starting the services, refresh the projections from the repository root:

```text
cd backend
python scripts/database/bootstrap_mysql.py
python scripts/database/sync_mysql_to_neo4j.py
```

The local database refresh was not run during this change because the Docker Compose configuration lacks a value for `MYSQL_USER`. Code-level regression tests pass with `python -m unittest discover -s backend/tests -p test_patent_data_fixes.py -v`.

The two repeated display keys, repeated family export triples, and potential multi-domain membership are retained for review rather than automatically merged or discarded.

## Method and limits

Title/abstract equality uses the same lowercase-and-whitespace normalization and MD5 construction as the vector-index builder. The family counts use undirected connected components among IDs in `patents.csv`; a component can be broader than a single filing. The CPC-overlap count requires a shared **CPC** code, not merely any classification code. No live MySQL, Neo4j, or FAISS index contents were queried; the audit covers the local CSVs, retrieval corpus CSV, mapping JSON, and the ingestion/query code paths. It does not establish legal equivalence or measure search-result frequency.
