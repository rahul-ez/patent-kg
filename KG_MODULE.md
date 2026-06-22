# Knowledge Graph Module — What Was Built and How It Works

## The Problem This Solves

When a user submits an invention idea, the system uses FAISS (a vector search tool)
to find the 100 most similar patents by comparing text. This works well but has a
blind spot — two patents covering the same invention can look completely different
in text if they are written in different styles or filed in different countries.
The Knowledge Graph module catches what text search misses by using the structural
relationships between patents.

---

## What a Knowledge Graph Is (in this context)

A knowledge graph is a database where data is stored as nodes (things) and edges
(relationships between things) rather than rows and columns.

In this system the nodes are:

- **Patent** — an actual patent from the dataset, or a related patent from another country
- **Company** — the organization that owns a patent
- **Inventor** — the person who invented it
- **CPCCode** — a standardized technology classification tag (e.g. G06N3/08 means neural networks)
- **Paper** — a scientific paper cited inside a patent

The edges (relationships) are:

- A Company **OWNS** a Patent
- An Inventor **INVENTED** a Patent
- A Patent **HAS_CPC** (belongs to a technology class)
- A Patent **SIMPLE_FAMILY_MEMBER** of another Patent (same invention, different country)
- A Patent **EXTENDED_FAMILY_MEMBER** of another Patent (related invention family)
- A Patent **CITES_PAPER** (references a scientific paper)

This structure lets you ask questions like "find all patents technically related to
this one" by following edges, which a text search cannot do.

---

## The Data

Seven CSV files were processed from Lens.org exports covering six domains
(AI, Medical, IoT, Automotive, Energy, Mechanical):

| File | What it contains |
|---|---|
| `patents.csv` | 58,428 patents with title, abstract, domain, legal status, citation counts |
| `assignees.csv` | 71,088 rows mapping patents to their owning companies |
| `inventors.csv` | 187,563 rows mapping patents to their inventors |
| `classifications.csv` | 1,020,178 rows mapping patents to CPC technology codes |
| `patent_families.csv` | 1,433,689 rows mapping patents to their international family members |
| `citations_metadata.csv` | 58,428 rows with citation count statistics per patent |
| `npl_metadata.csv` | 334,566 rows of scientific papers cited within patents |

All seven files share a common `patent_id` (the Lens ID) that is used to link
records across files.

---

## Part 1 — The Full Graph (Built Once)

### What it is

A complete graph of all 58,428 patents and every relationship between them,
loaded into a local Neo4j database. This is the structural backbone that the
rest of the module queries against.

### What is in it

**215,985 Patent nodes** — 58,428 are full nodes with all metadata. The remaining
157,557 are stub nodes representing international filings of the same inventions
(European, Japanese, Chinese, PCT versions) that were not in the original six-domain
dataset. These stubs exist so that family relationships are preserved even when
only one side of the relationship was in the dataset.

**Other node counts after deduplication:**

| Node type | Count | How |
|---|---|---|
| Inventor | 65,920 | 187,563 rows deduplicated by a hash of the inventor name |
| Paper | 60,135 | 334,566 NPL rows, only those with a valid Lens ID |
| CPCCode | 49,668 | 1,020,178 rows deduplicated by classification code |
| Company | 17,513 | 71,088 rows deduplicated by a hash of the company name |

**2.67 million edges** connecting everything together.

### How it was built

The builder reads each CSV file and writes to Neo4j in batches of 2,000 records
per transaction. The large files (classifications and families) are read in chunks
of 50,000 rows at a time so memory usage stays bounded. Every write uses MERGE
instead of CREATE, which means the builder can be re-run safely without creating
duplicates — it just updates existing records. Uniqueness constraints are created
on all five node ID properties before any writes, so lookups are index-based and fast.

The entire build completed in under 3 minutes.

### How teammates get it

The built database is exported to a single `.dump` file using Neo4j's built-in
admin tool. Teammates load this file into their own Neo4j installation in about
a minute, with no need to re-run the builder.

---

## Part 2 — Query-Time Subgraph (Built Per Search)

### What it is

Every time a user submits an idea, FAISS returns up to 100 patent IDs. The
subgraph builder takes those IDs and writes a focused slice of the graph into
Neo4j — just the nodes and edges relevant to those 100 patents. This subgraph
is what the GNN teammate reads to do re-ranking.

### What gets written

- Full Patent nodes for the 100 retrieved patents (with all metadata)
- Stub Patent nodes for any family members of those 100 that are not already in the retrieved set
- Company, Inventor, CPCCode, and Paper nodes connected to those 100 patents
- All six edge types for those nodes

A search returning 100 patents typically produces around 500 nodes and over 1,000
edges in the subgraph, due to the family members, shared classification codes,
and other connected entities.

### How duplicates are handled

MERGE ensures that if two queries retrieve overlapping patents, the second query
does not create duplicate nodes — it just updates the existing ones. Stub nodes
use ON CREATE SET so that a stub is never written over a full node that already
exists.

---

## Part 3 — KG Expansion (Reads the Full Graph Per Search)

### What it is

After the subgraph is built, the expander queries the full 2.67 million edge graph
to find additional patents that are structurally related to the 100 retrieved ones
but were not returned by FAISS. This is a read-only step — nothing new is written
to the database.

### Family expansion

The expander follows SIMPLE_FAMILY_MEMBER and EXTENDED_FAMILY_MEMBER edges outward
from all 100 retrieved patents. Any non-stub patent it reaches that is not already
in the retrieved set is added to the results.

These are the same invention filed in different countries. They are the strongest
form of prior art — if a user's idea matches a US patent, the corresponding EP
and JP filings are equally strong barriers even if their text looks different.
FAISS would not have found them because their abstracts were written independently.

### CPC sibling expansion

CPC (Cooperative Patent Classification) codes are a global taxonomy maintained
by the USPTO and EPO that tags patents by what technology they cover, independently
of how they are written. Two patents sharing a CPC code are covering the same
technology area.

The expander finds all CPC codes belonging to the 100 retrieved patents, then finds
all other patents in the full graph that share those same codes. To avoid returning
thousands of results for common codes, the results are grouped by code and only the
top 10 per code are kept, ranked by how many times they have been cited by other
patents (higher citation count = more influential prior art).

After capping, duplicates are removed across both expansion groups and against the
original 100 retrieved patents, so the final output contains no overlaps.

### Why this matters

FAISS works entirely in text embedding space. Two patents can be technically
identical but look dissimilar if one uses dense legal language and the other uses
plain technical language. CPC siblings catch this structural similarity that pure
text search misses.

### What the expansion produces (example from a real query)

| Group | Count | How found |
|---|---|---|
| FAISS results | 100 | Text similarity |
| Family members | 52 | Graph traversal via family edges |
| CPC siblings | 122 | Graph traversal via shared CPC codes |
| **Total handed to GNN** | **274** | — |

---

## What the GNN Teammate Receives

The GNN receives the combined set of patents from all three groups above. Each
patent has full metadata (title, abstract, domain, legal status, publication year,
citation count). The structural relationships between them are already in Neo4j
and the GNN reads the edge structure to build its message passing graph.

The key value of the KG module to the GNN is that patents which appear unrelated
by text alone are explicitly connected by edges — the GNN can propagate signals
across these connections in a way that FAISS embeddings alone cannot support.

---

## Files

| File | Purpose |
|---|---|
| `backend/src/kg/builder.py` | KGBuilder class — subgraph and full corpus builds |
| `backend/src/kg/expander.py` | expand_via_kg function — family and CPC sibling queries |
| `backend/src/kg/__init__.py` | Module exports |
| `backend/scripts/build_full_kg.py` | Terminal command for the one-time full build |
| `backend/scripts/dump_kg.py` | Exports the built database to a .dump file |
| `backend/scripts/load_kg.py` | Teammate command to load the .dump file |

---

## Technology Used

- **Neo4j** — the graph database storing all nodes and edges
- **neo4j Python driver** — used to connect and run Cypher queries from Python
- **pandas** — used to load, filter, and batch the CSV data before writing
- **Cypher** — Neo4j's query language, used for both writes (MERGE) and reads (MATCH)
- **Streamlit** — the UI framework where the KG status and expansion results are displayed
