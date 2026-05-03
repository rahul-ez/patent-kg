# Intelligent Patent Feasibility and Improvement Platform

This project is a full-stack AI system that takes a **user-inputted idea or patent description** and performs:
1. **Idea Evaluation**: Determines novelty and strength of the idea, comparing it with existing patents.
2. **Improvement Guidance (Core Feature)**: Suggests how to refine the idea, reduces similarity with existing patents, and identifies unexplored areas.

## End-to-End Pipeline

1. **NLP Layer**: Cleans raw user idea text, extracts keywords, and performs entity recognition (technology, domain, components) to output a structured JSON representation.
2. **Embedding + Semantic Retrieval**: Converts text into embeddings (Sentence Transformers), stores/queries in a vector database (FAISS/Chroma), returning Top-K similar patents.
3. **Knowledge Graph (KG)**: Uses nodes (Patent, Keyword, Technology Area, Company) and edges (SIMILAR_TO, BELONGS_TO, CITES) to expand retrieved patents into a local subgraph.
4. **Graph Neural Network (GNN)**: Learns structural relationships from the KG subgraph to improve similarity and recommendation quality, outputting graph-based similarity scores/embeddings.
5. **Hybrid Retrieval**: Combines semantic similarity (embeddings) and graph similarity (GNN) for a final refined set of relevant patents.
6. **Idea Evaluation Engine**: Computes Semantic Similarity Score, kNN Density Score, and Graph Novelty Score to output a Final Idea Strength Score with metric breakdown.
7. **Improvement Agent**: Analyzes user idea, retrieved patents, and evaluation scores to detect overlaps, identify weak areas, and suggest actionable improvements (e.g., modify components, combine with new domains, explore low-density areas).
8. **RAG + LLM Integration**: Generates explanations of idea strength, justification of scores, and human-readable improvement suggestions based on retrieved patents, graph context, evaluation results, and agent insights.
9. **API Layer**: Exposes `/evaluate`, `/improve`, and `/search` endpoints using FastAPI.
10. **UI**: Provides a Streamlit interface for users to input ideas and view scores, similar patents, and improvement suggestions.

## Tech Stack

*   **NLP**: spaCy / SciBERT
*   **Embeddings**: Sentence Transformers
*   **Vector DB**: FAISS or Chroma
*   **Graph DB**: Neo4j
*   **GNN**: PyTorch Geometric
*   **Backend**: FastAPI
*   **UI**: Streamlit

## Important Notes

*   Retrieval happens BEFORE GNN.
*   GNN is used to enhance results, not replace retrieval.
*   Improvement Agent is a key differentiator — logic here is prioritized.
*   Outputs are interpretable, not just numerical.
