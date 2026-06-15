# Graph Neural Network (GNN) Integration Details

This document outlines all the modifications and implementations carried out to integrate the Graph Neural Network (GNN) layer into the Patent Intelligence Platform.

---

## 1. GNN Core Scorer Engine (`backend/src/gnn/scorer.py`)
The GNN scoring engine has been completely overhauled to support two distinct operational modes:
*   **Pre-computed Novelty Mode (`"novelty"`)**:
    *   Retrieves novelty scores pre-computed during GNN training.
    *   These scores are loaded from `novelty_scores.json`.
*   **Live Graph Similarity Mode (`"graph_sim"`)**:
    *   Evaluates live structural uniqueness/similarity in the graph space.
    *   Loads 64-dimensional GraphSAGE node embeddings from `node_embeddings.npy`.
    *   Calculates the pairwise cosine similarity between the retrieved patent embeddings and the target subgraph to identify structural anomalies or close clusters.
*   **Robust Fallbacks**: Both modes fall back gracefully to default scores (e.g. `0.5` or `0.0`) if the underlying vector store files are missing.

---

## 2. GNN Training Notebook Updates (`patent_gnn_training.ipynb`)
The training script was updated to implement a more robust GNN target and model structure:
*   **New Target Novelty Metric**:
    Replaced the simplistic novelty label with a log-damped composite score balancing recency, citation infrequency, and family size:
    \[\text{Target Novelty} = 0.30 \times \text{Recency} + 0.40 \times (1 - \log(\text{Citations})) + 0.30 \times (1 - \log(\text{Family Size}))\]
*   **GraphSAGE Architecture**:
    Configured a 3-layer GraphSAGE model (projection layer $\to$ 128 $\to$ 64 $\to$ 32 dimensions) featuring residual skip connections to preserve localized graph properties and prevent oversmoothing.

---

## 3. Integration Pipeline Updates (`backend/src/integration/pipeline.py`)
*   **Flexible Evaluation Execution**:
    Added a `gnn_mode` parameter (defaulting to `"novelty"`) to `run_end_to_end()`. This parameter is routed directly to the updated `get_scorer(mode=gnn_mode)` API.
*   **Rank Change Tracking**:
    Each patent retrieved from the initial FAISS semantic search is stamped with a `faiss_rank` index prior to GNN re-ranking. This allows the system to compute exact rank shifts (deltas) caused by structural GNN insights.
*   **Dataset Alignment**:
    Enforced the use of `patents_deduped.csv` as the canonical reference source instead of `patents.csv` to ensure consistent data flow.

---

## 4. Dashboard Streamlit UI Overhaul (`backend/streamlit_app.py`)
The dashboard was redesigned to graduate the GNN evaluation from a secondary add-on to a dedicated **GNN Intelligence Layer**:
*   **Mode Selector UI**: Added a sidebar toggle allowing the user to select between `"novelty"` and `"graph_sim"` GNN scoring modes.
*   **Interactive Weight Sliders**: Let users dynamically balance **Semantic Similarity Weight** vs. **GNN Score Weight** in real-time, instantly updating the re-ranked results without needing to re-run the end-to-end NLP/FAISS pipeline.
*   **Rank Change Badges**: Introduced visual indicator badges (`▲+N` / `▼-N`) displaying how many positions each patent gained or lost during GNN optimization.
*   **Visual Distributions**: Integrated a detailed horizontal bar chart showing the breakdown of Semantic, GNN, and Combined scores side-by-side for each result.
*   **Insight Callouts**: Features a "GNN Optimization Callout" card highlighting the patent that received the largest ranking boost from the GNN engine.
