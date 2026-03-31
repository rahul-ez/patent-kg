# Patent Intelligence Platform

This project brings about an end-to-end AI-driven patent intelligence system. Using natural language, users can get answers to their queries or generate summaries through the application. It leverages graph-based machine learning to learn embeddings and predict related patents, combined with a retrieval-augmented LLM.

## Features

- **Natural Language Querying**: Ask questions about patents in plain English.
- **Summarization**: Generate concise summaries of patent documents.
- **Graph-Based ML**: Uses graph embeddings to find semantically related patents.
- **Retrieval-Augmented Generation (RAG)**: Combines retrieved patent information with a Large Language Model (LLM) for accurate, context-aware responses.

## Getting Started

### Prerequisites

- Python 3.8+
- Java 11+ (for Neo4j)
- Docker (optional, for running Neo4j locally)

### Installation

1.  **Clone the repository** (if you haven't already).

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

