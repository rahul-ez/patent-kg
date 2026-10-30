# Pipeline performance

The first optimization pass shares public patent embeddings between retrieval
expansion and GNN graph construction. It also encodes the private query once,
batches concept searches, and records stage timings. No additional service is
required.

## Current implementation

- `backend/src/retrieval/patent_embeddings.py` resolves patent IDs to existing
  FAISS vectors, including other publications with the exact same encoder input.
  Publication IDs and their structural metadata remain separate. Case or
  whitespace differences are encoded separately to preserve existing scores.
- Missing vectors are encoded in batches of at most 32. They are reused through
  a 4,096-entry memory LRU and a local SQLite cache of at most 20,000 entries
  across all namespaces. SQLite is a disposable optimization, not an application
  database. MySQL remains authoritative.
- The disk cache is `data/cache/patent_embeddings.sqlite3`, ignored by Git.
  It contains content hashes, vectors, version identifiers, and access times.
  It stores neither patent text nor private queries. Disk failure falls back to
  memory/batched encoding. Failed/invalid encoder outputs are not cached.
- Only text from the loaded public corpus can populate shared caches. Unknown
  records use request-local encoding. Caller-supplied text cannot override a
  known publication's canonical text.
- `integration/pipeline.py` creates one corpus/model/vector store per process,
  shares the query vector between FAISS retrieval and expansion scoring, and
  exposes `stage_timings` in seconds on the pipeline response and saved snapshot.
- `gnn/scorer.py` passes the same embedding store to `gnn/graph_builder.py`.
  Each GNN still executes against the current query's graph; context-dependent
  GNN scores are not cached by patent ID.
- `evaluation/per_concept_search.py` embeds concepts and searches FAISS as one
  batch, reusing the canonical metadata lookup and pipeline model.

Timings include NLP, resource initialization, query embedding, FAISS search,
graph expansion, expansion embeddings, GNN neighbours/embeddings/edges/inference,
grouping, and total pipeline time. `gnn_total` includes the GNN sub-stages; do not
sum every field. `total` excludes HTTP handling, saving, and network delivery.
Startup imports/model loading happen before requests and are measured separately
by the benchmark.

## Invalidation and operation

The cache namespace includes the encoder name, `PATENT_EMBEDDING_REVISION`, text
preparation version, vector dimension, and SHA-256 fingerprints of the FAISS
index and metadata map. Individual entries also hash the exact encoder input.

Restart the API after corpus imports or rebuilding vector artifacts: the
existing corpus/model resource caches are process-local snapshots. Rebuild FAISS
after changing patent titles/abstracts so indexed text and canonical metadata
stay aligned. Bump
`PATENT_EMBEDDING_REVISION` whenever encoder weights/revision or preprocessing
change, rebuild FAISS with that encoder, and restart all workers. Rebuilding
FAISS changes its fingerprint automatically.

Set `PATENT_EMBEDDING_DISK_CACHE=false` before starting the API to use only
memory/batching. The default is `true`. To clear the disposable disk cache, stop
API/benchmark workers, then remove just `data/cache/patent_embeddings.sqlite3`.
It is recreated automatically; patent records and saved cases are unaffected.

Concurrent misses are serialized within a process so one text is encoded once.
Workers share the SQLite file but have separate models, indexes, memory caches,
and locks. Multiple workers may independently compute the same miss. This pass
does not introduce distributed single-flight or a job queue.

## Repeatable measurement

From the repository root, with the environment active and MySQL/Neo4j running:

```powershell
python backend/scripts/evaluation/benchmark_pipeline.py --runs 2 --output artifacts/performance/current.json
```

The default uses fixed NLP output for a public EEG/seizure-sensor example, real
PatentSBERTa/FAISS/Neo4j/GraphSAGE, and `top_k=10`. This isolates retrieval cost
from Gemini latency and changing NLP output. It creates no accounts or cases.
The output records initialization, encoder calls/text counts, stage timings,
statuses, and public patent IDs/scores for result comparisons. Run again in a
new process to verify disk reuse. `--live-nlp` exercises the normal Gemini/spaCy
path; its timings include whichever NLP source is actually available.

See [verification](reports/performance-verification.md) for measured results.

## Remaining phases

1. Reuse Neo4j driver pools and profile the GNN edge query, now the largest warm
   stage. Keep retrieval caps and graph context consistent while evaluating it.
2. Add bounded graph lookup caching with graph-version invalidation, and remove
   repeated graph requests in the UI.
3. Consider private result caching keyed by authenticated owner, exact input,
   settings, corpus/model/graph/prompt versions. Check ownership on every
   request and keep fresh run IDs/save status. Public patent caches do not imply
   that private analysis outputs may be shared.
4. Consider durable background jobs and status polling for responsiveness.
   Moving work off an HTTP request does not itself reduce computation time.
