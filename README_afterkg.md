# Setup Guide — After Knowledge Graph Module

This document covers everything a teammate needs to get the full pipeline
running locally, including the Knowledge Graph (Neo4j) and KG expansion steps.

---

## What Has Been Built (KG Module)

The following has been added on top of the existing NLP + FAISS retrieval pipeline:

| Component | What it does |
|---|---|
| `backend/src/kg/builder.py` | Builds a Neo4j subgraph for any set of patent IDs |
| `backend/src/kg/expander.py` | Expands retrieved patents via family edges and CPC sibling links |
| `backend/scripts/build_full_kg.py` | One-time script to populate Neo4j with all 58K patents |
| `backend/scripts/dump_kg.py` | Exports the built database to a shareable `.dump` file |
| `backend/scripts/load_kg.py` | Loads a `.dump` file into your local Neo4j instance |

The Streamlit app now runs the following steps automatically after each search:

```
User Idea
  → NLP (Gemini + spaCy)
  → FAISS retrieval (top-k patents)
  → KG subgraph construction (Neo4j)     ← new
  → KG expansion (family + CPC siblings) ← new
  → Results displayed
```

---

## Prerequisites

Install these before anything else:

- **Python 3.12**
- **Neo4j Desktop** — download from https://neo4j.com/download/
  - Create a new local DBMS (any name)
  - Set a password and note it down
  - Start the DBMS — it must be running when the app runs

---

## Step 1 — Clone and Install

```powershell
git clone https://github.com/rahul-ez/patent-kg.git
cd patent-kg
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
python -m spacy download en_core_web_sm
```

---

## Step 2 — Add the Data Files

The CSV files are not in the repository (too large). Get these 7 files from the
shared drive and place them directly in the `patent-kg/` root folder:

```
patent-kg/
  patents.csv
  assignees.csv
  inventors.csv
  classifications.csv
  patent_families.csv
  citations_metadata.csv
  npl_metadata.csv
```

---

## Step 3 — Configure Environment Variables

Copy the example env file and fill in your values:

```powershell
cp .env.example .env
```

Open `.env` and set:

```
GOOGLE_API_KEY=your_google_gemini_api_key

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# Find this in Neo4j Desktop:
# Click the three dots next to your DBMS → Open Folder → DBMS
# Copy that folder path here
NEO4J_HOME=C:\Users\you\.Neo4jDesktop2\Data\dbmss\dbms-<your-id>
```

---

## Step 4 — Set Up the Knowledge Graph

You have two options. **Option A is strongly preferred** — it takes under a minute.

### Option A — Load from the shared dump file (recommended)

Get the `neo4j.dump` file from the shared Google Drive / OneDrive folder.

**Stop your Neo4j DBMS in Neo4j Desktop first**, then run:

```powershell
cd patent-kg/backend
python scripts/load_kg.py --dump "C:/path/to/neo4j.dump"
```

Start your DBMS again in Neo4j Desktop when it finishes.

### Option B — Build from scratch (if you don't have the dump)

Make sure your Neo4j DBMS is **running**, then:

```powershell
cd patent-kg/backend
python scripts/build_full_kg.py
```

This takes a few minutes. When it finishes, you will have the full graph
(~215K nodes, ~2.67M edges) in your local Neo4j instance.

---

## Step 5 — Set Up the FAISS Index

The FAISS index is pre-built and available on the shared drive alongside the Neo4j dump.
Copy both files into the correct folder — no rebuilding needed:

```
patent-kg/
  data/
    vector_store/
      patents.index            ← copy from shared drive
      metadata_mapping.json    ← copy from shared drive
```

If for any reason the pre-built files are missing, you can rebuild locally (takes ~15 minutes):

```powershell
cd patent-kg/backend
python scripts/build_faiss_index.py
```

---

## Step 6 — Run the App

Make sure your Neo4j DBMS is running in Neo4j Desktop, then:

```powershell
cd patent-kg/backend
python -m streamlit run streamlit_app.py
```

Open `http://localhost:8501` in your browser.

---

## Verifying the Graph Loaded Correctly

Open Neo4j Browser at `http://localhost:7474` and run:

```cypher
MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC
```

Expected output:

| label | count |
|---|---|
| Patent | ~215,985 |
| Inventor | ~65,920 |
| Paper | ~60,135 |
| CPCCode | ~49,668 |
| Company | ~17,513 |

```cypher
MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count ORDER BY count DESC
```

| type | count |
|---|---|
| EXTENDED_FAMILY_MEMBER | ~936,557 |
| HAS_CPC | ~864,392 |
| SIMPLE_FAMILY_MEMBER | ~495,613 |
| INVENTED | ~187,563 |
| CITES_PAPER | ~114,947 |
| OWNS | ~71,088 |

If these match, everything is set up correctly.

---

## Troubleshooting

| Error | Fix |
|---|---|
| `No module named 'spacy'` | Run `pip install spacy` then `python -m spacy download en_core_web_sm` |
| `No module named 'faiss'` | Run `pip install faiss-cpu` |
| `streamlit not recognized` | Use `python -m streamlit run streamlit_app.py` |
| `FileNotFoundError: patents.index` | Run `python scripts/build_faiss_index.py` first |
| `Neo4j connection failed` | Make sure the DBMS is started (green Active badge in Neo4j Desktop) |
| `torchvision` warnings in terminal | Harmless — Streamlit's file watcher noise, app works fine |
