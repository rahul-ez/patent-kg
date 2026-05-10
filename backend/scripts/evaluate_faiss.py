import os
import sys
import json
import logging
from collections import defaultdict

# Suppress TensorFlow warnings
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_TORCH", "1")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

# Setup paths
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_BACKEND_DIR, "src"))

from integration.pipeline import faiss_search
from retrieval.metrics import (
    precision_at_k,
    recall_at_k,
    hit_at_k,
    mrr_at_k,
    average_similarity_of_relevant
)

# Suppress debug logs from other modules
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("integration.pipeline").setLevel(logging.WARNING)

def run_evaluation():
    dataset_path = os.path.join(os.path.dirname(__file__), "evaluation_dataset.json")
    if not os.path.exists(dataset_path):
        print(f"Dataset not found at {dataset_path}")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    print("Loading FAISS index (this may take a moment)...")
    # A dummy call to initialize the lazy-loaded FAISS index
    faiss_search("dummy", top_k=1)
    
    k_vals = [5, 10]
    
    # Store metrics for aggregation
    metrics_log = {k: defaultdict(list) for k in k_vals}
    domain_metrics = {k: defaultdict(lambda: defaultdict(list)) for k in k_vals}
    
    # Output file
    report_path = os.path.join(os.path.dirname(__file__), "evaluation_report.txt")
    
    with open(report_path, "w", encoding="utf-8") as out:
        def emit(text=""):
            print(text)
            out.write(text + "\n")
            
        emit("======================================================================")
        emit("                   FAISS SEMANTIC RETRIEVAL EVALUATION")
        emit("======================================================================")
        
        for item in dataset:
            domain = item["domain"]
            query = item["query"]
            relevant = set(item["relevant_patents"])
            
            emit(f"\n====================================================")
            emit(f"QUERY: {query}")
            emit(f"====================================================")
            emit(f"\nQuery text: {query}")
            emit(f"Expected relevant patents: {list(relevant)}")
            
            # Fetch top 10 (since max K is 10)
            hits = faiss_search(query, top_k=10)
            retrieved_ids = [h["patent_id"] for h in hits]
            retrieved_scores = [h["score"] for h in hits]
            
            emit(f"Retrieved patents: {retrieved_ids}")
            emit(f"Retrieved scores: {retrieved_scores}\n")
            
            emit("Metrics:")
            for k in k_vals:
                p = precision_at_k(relevant, retrieved_ids, k)
                r = recall_at_k(relevant, retrieved_ids, k)
                h = hit_at_k(relevant, retrieved_ids, k)
                mrr = mrr_at_k(relevant, retrieved_ids, k)
                
                metrics_log[k]["precision"].append(p)
                metrics_log[k]["recall"].append(r)
                metrics_log[k]["hit"].append(h)
                metrics_log[k]["mrr"].append(mrr)
                
                domain_metrics[k][domain]["precision"].append(p)
                domain_metrics[k][domain]["recall"].append(r)
                domain_metrics[k][domain]["hit"].append(h)
                domain_metrics[k][domain]["mrr"].append(mrr)
                
                if k == 5:
                    emit(f"- Precision@5: {p:.4f}")
                    emit(f"- Recall@5: {r:.4f}")
                    emit(f"- Hit@5: {h}")
                    emit(f"- MRR: {mrr:.4f}")
                    
            # For breakdown (using K=5 for match lists)
            k_breakdown = 5
            top_k_ids = set(retrieved_ids[:k_breakdown])
            matched = top_k_ids & relevant
            missed = relevant - top_k_ids
            false_positives = top_k_ids - relevant
            
            emit(f"\nMatched patents: {list(matched)}")
            emit(f"Missed patents: {list(missed)}")
            emit(f"False positives: {list(false_positives)}")
            emit("\n----------------------------------------------------")
            
        emit("\n====================================================")
        emit("FINAL AGGREGATE METRICS")
        emit("====================================================")
        
        for k in k_vals:
            avg_p = sum(metrics_log[k]["precision"]) / len(metrics_log[k]["precision"])
            avg_r = sum(metrics_log[k]["recall"]) / len(metrics_log[k]["recall"])
            avg_h = sum(metrics_log[k]["hit"]) / len(metrics_log[k]["hit"])
            avg_mrr = sum(metrics_log[k]["mrr"]) / len(metrics_log[k]["mrr"])
            
            emit(f"\nMetrics at K={k}:")
            emit(f"Average Precision@{k}: {avg_p:.4f}")
            emit(f"Average Recall@{k}: {avg_r:.4f}")
            emit(f"Average Hit@{k}: {avg_h:.4f}")
            emit(f"Average MRR@{k}: {avg_mrr:.4f}")
            
        emit("\nDomain-wise breakdown (K=5):")
        for domain, metrics in domain_metrics[5].items():
            avg_p = sum(metrics["precision"]) / len(metrics["precision"])
            avg_r = sum(metrics["recall"]) / len(metrics["recall"])
            avg_mrr = sum(metrics["mrr"]) / len(metrics["mrr"])
            
            emit(f"- {domain}")
            emit(f"  - Precision@5: {avg_p:.4f}")
            emit(f"  - Recall@5: {avg_r:.4f}")
            emit(f"  - MRR@5: {avg_mrr:.4f}")

    print(f"\nEvaluation complete. Detailed report saved to {report_path}")

if __name__ == "__main__":
    run_evaluation()
