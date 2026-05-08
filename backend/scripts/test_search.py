"""
Test script for the Semantic Retrieval Module.

Simulates a small patent dataset, generates embeddings, runs queries,
prints ranked results with explanations, and evaluates retrieval quality
using Precision@K and Recall@K.

Usage:
    cd backend/
    python -m scripts.test_search
"""

import sys
import os
import logging

# ── Suppress TensorFlow/Keras import in `transformers` ────────────────────────
# sentence_transformers → transformers tries to import TF/Keras when both are
# installed, which crashes on Keras 3 (incompatible with transformers TF layer).
# We only use the PyTorch backend, so disable TF entirely before any ST import.
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_TORCH", "1")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

# -- Setup import path so `retrieval` is importable ----------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from retrieval.embed import get_embeddings
from retrieval.vector_store import save_embeddings, load_embeddings
from retrieval.search import search
from retrieval.evaluate import evaluate_search

# -- Logging -------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("test_search")

# -- Simulated patent data (title + abstract combined) -------------
SAMPLE_PATENTS: list[str] = [
    # 0 - drone / obstacle avoidance
    "AI-based drone navigation system "
    "A real-time obstacle avoidance system for autonomous drones using "
    "deep reinforcement learning and LiDAR sensor fusion to enable safe "
    "flight in complex urban environments.",

    # 1 - autonomous vehicle
    "Self-driving vehicle perception module "
    "An integrated perception pipeline for autonomous vehicles combining "
    "camera, radar, and ultrasonic data to detect pedestrians, cyclists, "
    "and other vehicles under varying weather conditions.",

    # 2 - NLP search engine
    "Natural language patent search engine "
    "A transformer-based semantic search system that converts patent "
    "abstracts into dense vector representations for efficient prior-art "
    "retrieval using approximate nearest-neighbour algorithms.",

    # 3 - medical imaging
    "Deep learning for medical image analysis "
    "A convolutional neural network architecture optimized for detecting "
    "early-stage tumours in chest X-ray images with high sensitivity and "
    "specificity, aiding radiologists in clinical decision-making.",

    # 4 - battery technology
    "Solid-state lithium battery with enhanced lifespan "
    "A novel solid-state electrolyte composition for lithium-ion batteries "
    "that improves energy density by 40% while reducing degradation over "
    "charge-discharge cycles.",

    # 5 - robotics
    "Robotic arm with adaptive grasping "
    "A six-axis robotic manipulator equipped with tactile sensors and "
    "reinforcement learning algorithms enabling adaptive grasping of "
    "irregularly shaped objects in warehouse automation.",

    # 6 - 5G networking
    "5G network slicing for IoT applications "
    "A dynamic network slicing framework for 5G infrastructure that "
    "allocates bandwidth and latency budgets to heterogeneous IoT devices "
    "based on real-time traffic classification.",

    # 7 - quantum computing
    "Quantum error correction code "
    "A surface-code-based quantum error correction scheme that reduces "
    "logical qubit error rates below the fault-tolerance threshold on "
    "superconducting quantum processors.",

    # 8 - agriculture
    "Precision agriculture using satellite imagery "
    "A crop health monitoring system that processes multispectral satellite "
    "images with machine learning models to predict yield and detect plant "
    "diseases across large farmlands.",

    # 9 - cybersecurity
    "AI-powered intrusion detection system "
    "An anomaly-based intrusion detection system using autoencoders and "
    "graph neural networks to identify zero-day attacks in enterprise "
    "network traffic with minimal false positives.",
]

# -- Ground truth: query -> list of relevant patent indices --------
# These represent what a human would consider "relevant" results.
GROUND_TRUTH: dict[str, list[int]] = {
    "AI-based drone navigation system for obstacle avoidance": [0, 1],
    "patent search using natural language processing": [2],
    "battery technology for electric vehicles": [4, 1],
    "deep learning for medical diagnosis": [3, 8],
    "robotic manipulation and grasping": [5, 0],
}


def main() -> None:
    """Run the end-to-end retrieval test with evaluation and explanations."""

    print("=" * 70)
    print("  SEMANTIC RETRIEVAL MODULE -- FULL TEST SUITE")
    print("=" * 70)

    # == Step 1: Generate embeddings ================================
    print("\n> Step 1 - Generating embeddings for %d sample patents ..."
          % len(SAMPLE_PATENTS))
    embeddings = get_embeddings(SAMPLE_PATENTS)
    print(f"  Embedding matrix shape: {embeddings.shape}")

    # == Step 2: Save embeddings to disk ============================
    print("\n> Step 2 - Saving embeddings to disk ...")
    save_dir = save_embeddings(embeddings, SAMPLE_PATENTS)
    print(f"  Saved to: {save_dir}")

    # == Step 3: Load embeddings back ===============================
    print("\n> Step 3 - Loading embeddings from disk ...")
    loaded_embeddings, loaded_texts = load_embeddings()
    assert loaded_embeddings.shape == embeddings.shape, "Shape mismatch!"
    assert len(loaded_texts) == len(SAMPLE_PATENTS), "Text count mismatch!"
    print("  [OK] Loaded successfully - shapes match.")

    # == Step 4: Semantic search with explanations ===================
    search_queries = [
        "AI-based drone navigation system for obstacle avoidance",
        "patent search using natural language processing",
        "battery technology for electric vehicles",
    ]

    print("\n" + "=" * 70)
    print("  PART A: SEMANTIC SEARCH + EXPLAINABILITY")
    print("=" * 70)

    for query in search_queries:
        print("\n" + "-" * 70)
        print(f'  QUERY: "{query}"')
        print("-" * 70)

        results = search(
            query=query,
            embeddings=loaded_embeddings,
            texts=loaded_texts,
            top_k=5,
        )

        for r in results:
            score_bar = "#" * int(r["score"] * 30)
            print(
                f"  [{r['rank']}] Score: {r['score']:.4f}  {score_bar}\n"
                f"      {r['text'][:90]}...\n"
                f"      >> {r['explanation']}\n"
            )

    # == Step 5: Evaluation metrics ==================================
    print("\n" + "=" * 70)
    print("  PART B: EVALUATION METRICS")
    print("=" * 70)

    eval_queries = list(GROUND_TRUTH.keys())

    for k_val in [3, 5]:
        print(f"\n  --- Evaluation @ K={k_val} ---")

        metrics = evaluate_search(
            test_queries=eval_queries,
            ground_truth=GROUND_TRUTH,
            embeddings=loaded_embeddings,
            texts=loaded_texts,
            k=k_val,
        )

        print(f"\n  Avg Precision@{k_val} : {metrics['avg_precision_at_k']:.4f}")
        print(f"  Avg Recall@{k_val}    : {metrics['avg_recall_at_k']:.4f}")
        print(f"  Queries evaluated  : {metrics['num_queries']}")

        print("\n  Per-query breakdown:")
        for detail in metrics["details"]:
            print(
                f"    Query: \"{detail['query'][:50]}...\"\n"
                f"      P@{k_val}={detail['precision_at_k']:.4f}  "
                f"R@{k_val}={detail['recall_at_k']:.4f}  "
                f"Retrieved: {detail['retrieved_indices']}  "
                f"Relevant: {detail['relevant_indices']}"
            )

    # == Done ========================================================
    print("\n" + "=" * 70)
    print("  [PASS]  ALL TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()
