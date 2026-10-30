"""Repeatable local performance check using real retrieval/graph/GNN resources.

The default fixes NLP output to isolate retrieval cost from network/LLM variance.
It never saves a case or user input. Run from the repository root.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend" / "src"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live-nlp", action="store_true")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be positive")

    import_started = perf_counter()
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    import integration.pipeline as pipeline
    import kg.expander as expander
    from gnn import graph_builder
    import_seconds = perf_counter() - import_started

    idea = "A wearable EEG sensor uses machine learning to predict epileptic seizures and alert caregivers."
    started = perf_counter()
    index, _, frame = pipeline._load_resources()
    model = pipeline._get_model()
    preload = perf_counter() - started
    report = {
        "nlp": "live" if args.live_nlp else "fixed benchmark fixture (no LLM call)",
        "model": pipeline._MODEL_NAME,
        "vectors": index.ntotal,
        "patents": len(frame),
        "import_seconds": round(import_seconds, 4),
        "preload_seconds": round(preload, 4),
        "runs": [],
    }
    original_encode = model.encode
    for number in range(1, args.runs + 1):
        metrics = {"run": number, "encode_calls": 0, "encoded_texts": 0, "encode_seconds": 0.0}

        def encode(texts, *positional, **kwargs):
            started = perf_counter()
            result = original_encode(texts, *positional, **kwargs)
            metrics["encode_calls"] += 1
            metrics["encoded_texts"] += len(texts)
            metrics["encode_seconds"] += perf_counter() - started
            return result

        def timed(name, function):
            def call(*positional, **kwargs):
                started = perf_counter()
                try:
                    return function(*positional, **kwargs)
                finally:
                    metrics[name] = perf_counter() - started
            return call

        nlp = pipeline.process_user_query if args.live_nlp else lambda text: {
            "patent_id": "user_query", "clean_text": text,
            "keywords": ["EEG", "seizure prediction", "wearable sensor"],
            "entities": [], "source": "benchmark_fixture",
        }
        with (
            patch.object(model, "encode", side_effect=encode),
            patch.object(pipeline, "process_user_query", side_effect=timed("nlp_seconds", nlp)),
            patch.object(expander, "expand_via_kg", side_effect=timed("kg_lookup_seconds", expander.expand_via_kg)),
            patch.object(graph_builder, "fetch_subgraph_neighbors", side_effect=timed("gnn_neighbors_seconds", graph_builder.fetch_subgraph_neighbors)),
            patch.object(graph_builder, "fetch_subgraph_edges", side_effect=timed("gnn_edges_seconds", graph_builder.fetch_subgraph_edges)),
        ):
            started = perf_counter()
            result = pipeline.run_end_to_end(idea, top_k=10)
            metrics["total_seconds"] = perf_counter() - started
        metrics.update({
            "kg_status": result.get("kg_status"), "gnn_status": result.get("gnn_status"),
            "nlp_source": result.get("nlp_result", {}).get("source"),
            "result_count": len(result["results"]),
            "stage_timings": result.get("stage_timings", {}),
            "results": [{"patent_id": hit["patent_id"], "semantic_score": hit.get("semantic_score"),
                         "combined_score": hit.get("combined_score")} for hit in result["results"]],
        })
        report["runs"].append(metrics)
        print(json.dumps({key: value for key, value in metrics.items() if key != "results"}), flush=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
