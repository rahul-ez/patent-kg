import sys
import os
import logging
import pandas as pd
import numpy as np
import time

# Suppress TensorFlow/Keras import in `transformers`
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_TORCH", "1")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

# Setup import path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from retrieval.embed import get_embeddings
from retrieval.search import search
from retrieval.evaluate import evaluate_search

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
logger = logging.getLogger("eval_ai_patents")

def main():
    csv_path = "c:/Users/Lenovo/Documents/Projects/Graph-Enhanced Patent Intelligence Platform/data/raw/ai.csv"
    logger.info(f"Loading data from {csv_path}")
    
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        logger.error(f"Failed to read CSV: {e}")
        return

    # To keep evaluation fast, let's take the first 1000 patents
    sample_size = min(1000, len(df))
    df_sample = df.head(sample_size).copy()
    
    # Fill NaNs
    df_sample['Title'] = df_sample['Title'].fillna("")
    df_sample['Abstract'] = df_sample['Abstract'].fillna("")
    
    # Combine Title and Abstract
    texts = (df_sample['Title'] + ". " + df_sample['Abstract']).tolist()
    
    logger.info(f"Generating embeddings for {sample_size} patents. This might take a minute...")
    start_time = time.time()
    embeddings = get_embeddings(texts)
    logger.info(f"Embeddings generated in {time.time() - start_time:.2f} seconds.")
    
    # Define some test queries related to the AI domain
    test_queries = [
        "autonomous driving and obstacle avoidance in urban environments",
        "deep learning for natural language processing",
        "dynamic spectrum management using machine learning",
        "quantum computing error correction",
        "artificial intelligence in transportation systems"
    ]
    
    print("\n" + "=" * 80)
    print("  SEMANTIC RETRIEVAL EVALUATION ON AI PATENTS")
    print("=" * 80)
    
    for query in test_queries:
        print("\n" + "-" * 80)
        print(f'  QUERY: "{query}"')
        print("-" * 80)
        
        results = search(query=query, embeddings=embeddings, texts=texts, top_k=3)
        
        for r in results:
            print(f"  [Rank {r['rank']}] Score: {r['score']:.4f}")
            print(f"      Text: {r['text'][:150]}...")
            print(f"      Explain: {r['explanation']}\n")

if __name__ == "__main__":
    main()
