# Performance verification — October 30, 2026

The first performance pass is implemented: shared public-patent embeddings,
batched misses/concept searches, query-vector reuse, and pipeline stage timings.
Operational details and remaining phases are in [performance](../performance.md).

## Controlled before/after measurement

CPU execution, PatentSBERTa (768 dimensions), 36,353 indexed texts, 58,428
canonical publications, `top_k=10`, live MySQL/Neo4j and trained GraphSAGE.
The public example is a wearable EEG sensor for seizure prediction and caregiver
alerts. NLP output is fixed for this comparison; Gemini/network time is excluded.

| Condition | Pipeline seconds | Encoder calls | Texts encoded | Grouped results |
|---|---:|---:|---:|---:|
| Before, first run | 98.90 | 347 | 347 | 103 |
| Before, repeat | 100.22 | 347 | 347 | 103 |
| After, empty embedding cache | 34.76 | 5 | 98 | 103 |
| After, repeat in same process | 9.47 | 1 | 1 | 103 |
| After, new process with disk cache | 10.96 | 1 | 1 | 103 |

The optimized repeat was approximately 10.6 times faster than the baseline
repeat in this example. This is one workload, not a latency guarantee. Both KG
and GNN statuses were successful in every completed benchmark run.

The encoder's remaining single text is the private query. The initial optimized
run encoded 97 unique missing public texts plus that query; the disk cache held
97 public vectors afterward. Existing exact-text FAISS vectors supplied many
other publications without encoding or removing their legal IDs.

The result IDs and their ordering matched the baseline exactly. Maximum absolute
changes in rounded semantic and combined scores were 0.000001. Graph context
remained 114 candidate publications plus 544 structural neighbours (658 nodes).
Retrieval limits, GNN weights, and family/CPC expansion caps were unchanged.

The benchmark preloads index/metadata/model resources before these pipeline
measurements. Module import, that preload, HTTP transport, and saving are excluded;
first-use embedding-store initialization is included. Resource/model preload was 12.57 seconds
before, 13.10 seconds after, and 10.24 seconds in the restarted process. Module
import time was not recorded in these initial comparison artifacts; the current
benchmark script records it separately for subsequent runs.

On the optimized warm comparison, GNN edge fetching accounted for most remaining
time (approximately 8 seconds). A later authenticated API repeat completed the
pipeline in 4.36 seconds with a warmer graph cache; the conservative comparison
above remains the primary benchmark. Driver pooling and edge-query profiling
are the next performance phase.

## Verification

72 automated checks passed:

| Suite | Checks |
|---|---:|
| Backend unit/contracts, including embedding/performance regressions | 46 |
| Real database authentication/ownership and integration | 11 |
| Real model/database authenticated performance integration | 1 |
| Existing persistence contracts | 3 |
| Frontend state/session tests | 11 |

TypeScript checking, the production frontend build, Python compilation of changed
modules, and `git diff --check` also passed.

The performance regressions cover exact-text index reuse, raw-text differences,
batched result alignment and normalization, memory/disk reuse, encoder/index
revision and text invalidation, cache size bounds, corrupt/unwritable storage,
failed inference, concurrent identical misses, unknown/private text exclusion,
publication-specific GNN features/edges, query reuse, and concept batch parity.

The authenticated integration check used real signup/session/CSRF, two identical
pipeline requests in one case, fresh distinct run IDs, successful owned saving,
and reloading the saved stage timings. NLP alone was a fixed fixture. Temporary
accounts/cases were removed. An earlier interrupted attempt was retried, and its
temporary account was removed explicitly. The canonical patent count remains
58,428; the original ownerless case is preserved.

Commands from the repository root, with its environment active:

```powershell
python -m unittest discover -s backend/tests -v
python -m unittest discover -s tests -p test_persistence_contract.py -v
$env:RUN_DATABASE_TESTS='1'
python -m unittest discover -s tests -p 'test_live_*.py' -v
$env:RUN_PERFORMANCE_TESTS='1'
python -m unittest discover -s tests -p test_live_performance.py -v
python backend/scripts/evaluation/benchmark_pipeline.py --runs 2 --output artifacts/performance/current.json
```

Frontend: run `npm test` and `npm run build` from `frontend/`.

Local ignored evidence includes `artifacts/performance/before.json`, `after.json`,
`restarted.json`, `unit-tests.log`, `live-tests.log`, and
`live-performance-retry.log`. No private analysis result caching, Redis service,
graph lookup cache, or background job queue was added in this pass. End-to-end
Gemini evaluation/improvement latency and broader workload quality are not
established by this retrieval benchmark.
