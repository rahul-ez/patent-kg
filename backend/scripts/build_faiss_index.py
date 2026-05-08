import os
import json
import faiss
import pandas as pd
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

# Setup paths relative to the script location
# scripts/ → backend/ → patent-kg/ → PROJECT_ROOT
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_SCRIPTS_DIR)))

# Input: canonical processed patents from the project root data layer
DATA_FILE = os.path.join(PROJECT_ROOT, "data", "processed", "patents.csv")

# Output: FAISS index stored inside patent-kg/ (co-located with the backend)
BASE_DIR = os.path.dirname(os.path.dirname(_SCRIPTS_DIR))  # → patent-kg/
INDEX_DIR = os.path.join(BASE_DIR, "data", "vector_store")
FAISS_INDEX_FILE = os.path.join(INDEX_DIR, "patents.index")
METADATA_FILE = os.path.join(INDEX_DIR, "metadata_mapping.json")

# Ensure the vector_store directory exists
os.makedirs(INDEX_DIR, exist_ok=True)

def build_faiss_index():
    print("Loading embedding model (all-MiniLM-L6-v2)...")
    # This is a lightweight, blazing fast Sentence Transformer perfect for dense search
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    print(f"Loading patent data from {DATA_FILE}...")
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(
            f"patents.csv not found at '{DATA_FILE}'.\n"
            "Run: python src/processing/process_patents.py  (from the project root)"
        )
    df = pd.read_csv(DATA_FILE)
    
    # We only want to embed patents that actually have text
    df = df.dropna(subset=['title', 'abstract'])
    
    print(f"Generating semantic text representations for {len(df)} patents...")
    # For massive bulk ingestion (100k+ rows), combining Title + Abstract directly is standard and fast.
    # We don't hit the LLM API here because that would cost a fortune and take days!
    texts = (df['title'] + ". " + df['abstract']).tolist()
    patent_ids = df['patent_id'].tolist()
    
    print("Computing mathematical embeddings (this may take a few moments)...")
    # Encode the entire list of strings into a massive Numpy array matrix
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    
    print("Initializing FAISS Index...")
    dimension = embeddings.shape[1]
    
    # We normalize the vectors using L2. This allows us to use Inner Product (IndexFlatIP) 
    # to efficiently calculate exact Cosine Similarity.
    faiss.normalize_L2(embeddings)
    index = faiss.IndexFlatIP(dimension)
    
    print(f"Adding {len(embeddings)} vectors to FAISS...")
    index.add(embeddings)
    
    print("Saving FAISS index and metadata...")
    faiss.write_index(index, FAISS_INDEX_FILE)
    
    # FAISS only maps to row numbers (0, 1, 2...). We have to map those back to our actual 'patent_id'
    metadata_mapping = {i: str(pid) for i, pid in enumerate(patent_ids)}
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata_mapping, f)
        
    print(f"\n✅ Successfully built and saved the FAISS Index!")
    print(f"Index Location: {FAISS_INDEX_FILE}")
    print(f"Metadata Map Location: {METADATA_FILE}")

if __name__ == "__main__":
    build_faiss_index()
