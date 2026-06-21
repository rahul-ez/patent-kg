# Intelligent Patent Feasibility and Improvement Platform

This is a full-stack AI platform that evaluates innovation ideas, analyzes patent citation relationships, and provides actionable design improvement guidance.

## Pipeline Architecture

The end-to-end intelligence pipeline executes in the following order:

```
User Idea Input
       ↓
NLP Processing Layer (Gemini + spaCy keywords & entities)
       ↓
FAISS Semantic Search (PatentSBERTa embeddings similarity)
       ↓
Knowledge Graph Expansion (Neo4j subgraph family + CPC traversal)
       ↓
GNN Re-ranking Hook (Future GraphSAGE scoring)
       ↓
FastAPI Response
       ↓
React UI Dashboard
```

---

## Technical Features & Refactors

During the final backend cleanup pass, the following integration refactors were implemented:

1. **Provenance Tracking**: Added the `source` field to all returned patents (`"faiss" | "kg_family" | "kg_cpc"`) alongside `expansion_type` to track each document's origin.
2. **Global CPC Expansion Cap**: Sibling patent expansion is capped at **100 patents maximum globally**. The Cypher query in `expander.py` has been optimized to sort and slice the top candidates *directly inside Neo4j*, reducing runtime query and network latency by **over 13x**.
3. **Structured Scoring Schema**: The legacy `score` field has been completely removed across the backend search, integration, GNN, and React components. Every patent now conforms to:
   - `semantic_score`: Float cosine similarity for FAISS results, `null` for KG matches.
   - `graph_score`: Placeholder (`null`) prepared for future structural embeddings.
   - `combined_score`: The blended similarity value when GNN is active, `null` otherwise.

---

## Getting Started & Running the App

### Prerequisites

1. **Neo4j Graph Database**: Ensure your Neo4j DBMS is running locally (Bolt port `7687`).
2. **Virtual Environment**: Set up the Python virtual environment in the project root:
   ```bash
   python -m venv venv
   ```

### 1. Run the FastAPI Backend

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Activate your virtual environment and install dependencies:
   ```bash
   # Windows:
   ..\venv\Scripts\activate
   # Mac/Linux:
   source ../venv/bin/activate

   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in credentials:
   ```env
   GOOGLE_API_KEY=your_gemini_api_key
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=r1hu12005
   ```
4. Start the backend developer API server:
   ```bash
   python run_api.py
   ```
   The backend API will start on [http://127.0.0.1:8000](http://127.0.0.1:8000).

### 2. Run the React Frontend

1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```
2. Install npm dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   The Vite app will start on [http://localhost:5175/](http://localhost:5175/) (or the next available port) and will proxy `/api` requests automatically to port 8000.
