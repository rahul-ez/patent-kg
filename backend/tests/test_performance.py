"""Embedding correctness, invalidation, bounds, privacy, and pipeline reuse."""
from __future__ import annotations

import hashlib
import sqlite3
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import faiss
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from retrieval.patent_embeddings import PatentEmbeddings, patent_text


class Encoder:
    def __init__(self):
        self.calls = []

    def encode(self, texts, **kwargs):
        self.calls.append(list(texts))
        return np.array([[float(v) + 1 for v in hashlib.sha256(text.encode()).digest()[:3]]
                         for text in texts], dtype=np.float32)


class EmbeddingCacheTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "vectors.sqlite3"
        self.index = faiss.IndexFlatIP(3)
        self.index.add(np.array([[1, 0, 0]], dtype=np.float32))
        self.rows = {
            "p1": {"title": "Sensor", "abstract": "A monitor"},
            "alias": {"title": "Sensor", "abstract": "A monitor"},
            "p2": {"title": "Charger", "abstract": "A battery"},
            "p3": {"title": "Camera", "abstract": "A lens"},
        }
        self.encoder = Encoder()

    def store(self, **kwargs):
        return PatentEmbeddings(self.index, {"0": "p1"}, self.rows, self.encoder,
                                cache_path=self.path, namespace=kwargs.pop("namespace", "model-index-v1"), **kwargs)

    def test_identical_text_uses_existing_index_without_merging_ids(self):
        store = self.store()
        result = store.get_many([{"patent_id": "alias"}, {"patent_id": "p1"}])
        np.testing.assert_array_equal(result, [[1, 0, 0], [1, 0, 0]])
        self.assertEqual(self.encoder.calls, [])
        self.assertEqual(set(store.patent_rows), set(self.rows))

    def test_batch_deduplicates_and_normalizes_and_preserves_order(self):
        store = self.store(batch_size=2)
        records = [{"patent_id": pid} for pid in ("p3", "p2", "p3")]
        result = store.get_many(records)
        self.assertEqual(self.encoder.calls, [[patent_text(self.rows["p3"]), patent_text(self.rows["p2"])]])
        np.testing.assert_allclose(np.linalg.norm(result, axis=1), 1, atol=1e-6)
        np.testing.assert_array_equal(result[0], result[2])
        expected = Encoder().encode([patent_text(self.rows["p3"]), patent_text(self.rows["p2"])])
        faiss.normalize_L2(expected)
        np.testing.assert_allclose(result[:2], expected)

    def test_raw_text_changes_are_not_aliased_to_indexed_vector(self):
        self.rows["alias"]["title"] = "sensor"
        result = self.store().get_many([{"patent_id": "alias"}])
        self.assertEqual(self.encoder.calls, [["sensor. A monitor"]])
        self.assertFalse(np.array_equal(result[0], [1, 0, 0]))

    def test_cache_survives_new_store_and_returned_vectors_are_copies(self):
        records = [{"patent_id": "p2"}]
        store = self.store()
        expected = store.get_many(records)
        altered = store.get_many(records)
        altered[:] = 0
        np.testing.assert_array_equal(store.get_many(records), expected)
        self.encoder.calls.clear()
        np.testing.assert_array_equal(self.store().get_many(records), expected)
        self.assertEqual(self.encoder.calls, [])

    def test_revision_and_changed_text_invalidate_vectors(self):
        records = [{"patent_id": "p2"}]
        first = self.store().get_many(records)
        self.store(namespace="different-model-or-index").get_many(records)
        self.rows["p2"] = {"title": "Changed", "abstract": "Different text"}
        changed = self.store().get_many(records)
        self.assertEqual(len(self.encoder.calls), 3)
        self.assertFalse(np.array_equal(first, changed))

    def test_private_or_unknown_text_never_populates_shared_caches(self):
        store = self.store()
        private = [{"patent_id": "unknown", "title": "Private invention", "abstract": "Secret"}]
        store.get_many(private)
        store.get_many(private)
        self.assertEqual(len(self.encoder.calls), 2)
        self.assertEqual(len(store._memory), 0)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM vectors").fetchone()[0], 0)

    def test_supplied_text_cannot_poison_known_public_patent(self):
        result = self.store().get_many([{"patent_id": "p1", "title": "Injected private text"}])
        np.testing.assert_array_equal(result, [[1, 0, 0]])
        self.assertEqual(self.encoder.calls, [])

    def test_memory_and_disk_bounds_cover_multiple_namespaces(self):
        store = self.store(memory_limit=1, disk_limit=1)
        store.get_many([{"patent_id": "p2"}, {"patent_id": "p3"}])
        self.assertEqual(len(store._memory), 1)
        self.store(namespace="other", disk_limit=1).get_many([{"patent_id": "p2"}])
        with closing(sqlite3.connect(self.path)) as connection, connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM vectors").fetchone()[0], 1)

    def test_corrupt_or_unwritable_cache_falls_back_to_encoding(self):
        store = self.store(memory_limit=0)
        records = [{"patent_id": "p2"}]
        store.get_many(records)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("UPDATE vectors SET vector=?", (b"corrupt",))
        result = store.get_many(records)
        self.assertEqual(len(self.encoder.calls), 2)
        with patch.object(store, "_connect", side_effect=sqlite3.OperationalError("readonly")):
            np.testing.assert_array_equal(store.get_many(records), result)
        self.assertIsNone(store.cache_path)

    def test_concurrent_requests_encode_identical_miss_once(self):
        store = self.store()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: store.get_many([{"patent_id": "p2"}]), range(2)))
        np.testing.assert_array_equal(results[0], results[1])
        self.assertEqual(len(self.encoder.calls), 1)

    def test_failed_encode_does_not_poison_cache(self):
        store = self.store()
        with patch.object(self.encoder, "encode", side_effect=RuntimeError("encoder offline")):
            with self.assertRaises(RuntimeError):
                store.get_many([{"patent_id": "p2"}])
        self.assertEqual(len(store._memory), 0)
        self.assertTrue(np.isfinite(store.get_many([{"patent_id": "p2"}])).all())

    def test_empty_unknown_text_returns_zero_without_encoding(self):
        store = self.store()
        np.testing.assert_array_equal(store.get_many([{"patent_id": "missing"}]), [[0, 0, 0]])
        self.assertEqual(store.get_many([]).shape, (0, 3))
        self.assertEqual(self.encoder.calls, [])


class PipelinePerformanceTests(unittest.TestCase):
    def test_shared_text_keeps_distinct_gnn_nodes_and_structural_features(self):
        from gnn import graph_builder as builder
        frame = pd.DataFrame([
            {"patent_id": "grant", "title": "Sensor", "abstract": "Monitor", "cited_by_patent_count": "5"},
            {"patent_id": "application", "title": "Sensor", "abstract": "Monitor", "cited_by_patent_count": "0"},
        ])
        index = faiss.IndexFlatIP(3)
        index.add(np.array([[1, 0, 0]], dtype=np.float32))
        encoder = Encoder()
        with patch.object(builder, "fetch_subgraph_neighbors", return_value=["application", "application"]), patch.object(builder, "fetch_subgraph_edges", return_value=[("grant", "application")]):
            data, mapping = builder.build_subgraph_data(
                [{"patent_id": "grant"}, {"patent_id": "grant"}], frame, {"0": "grant"}, index, encoder,
            )
        self.assertEqual(mapping, {"grant": 0, "application": 1})
        self.assertEqual(tuple(data.x.shape), (2, 15))
        np.testing.assert_array_equal(data.x[:, :3].numpy(), [[1, 0, 0], [1, 0, 0]])
        self.assertAlmostEqual(float(data.x[0, 4]), float(np.log1p(5)), places=6)
        self.assertEqual(float(data.x[1, 4]), 0)
        self.assertEqual(set(map(tuple, data.edge_index.T.tolist())), {(0, 1), (1, 0)})
        self.assertEqual(encoder.calls, [])

    def test_one_query_encoding_and_stage_timings_with_offline_fallbacks(self):
        from integration import pipeline
        import kg.expander as expander
        frame = pd.DataFrame([{"patent_id": "p1", "title": "Sensor", "abstract": "Monitor"}])
        index = faiss.IndexFlatIP(3)
        index.add(np.array([[1, 0, 0]], dtype=np.float32))
        encoder = Encoder()
        encoder._loaded_name = "fixture"
        rows = {"p1": {"title": "Sensor", "abstract": "Monitor"}}
        embeddings = PatentEmbeddings(index, {"0": "p1"}, rows, encoder)
        with (
            patch.object(pipeline, "_load_resources", return_value=(index, {"0": "p1"}, frame)),
            patch.object(pipeline, "_get_model", return_value=encoder),
            patch.object(pipeline, "_get_patent_embeddings", return_value=embeddings),
            patch.object(pipeline, "_cached_index", index),
            patch.object(pipeline, "_cached_patents_df", frame),
            patch.object(pipeline, "_cached_patent_rows", rows),
            patch.object(pipeline, "process_user_query", return_value={"clean_text": "Private idea"}),
            patch.object(expander, "expand_via_kg", side_effect=RuntimeError("offline")),
            patch.object(pipeline, "run_live_gnn_rerank", side_effect=FileNotFoundError("missing")),
        ):
            result = pipeline.run_end_to_end("Private idea", top_k=1)
        self.assertEqual(encoder.calls, [["Private idea"]])
        self.assertEqual(result["kg_status"], "skipped_database_offline")
        self.assertEqual(result["gnn_status"], "skipped_missing_embeddings")
        self.assertEqual(result["results"][0]["patent_id"], "p1")
        self.assertTrue(all(value >= 0 for value in result["stage_timings"].values()))
        self.assertGreaterEqual(result["stage_timings"]["total"], result["stage_timings"]["query_embedding"])

    def test_concept_batch_matches_independent_searches_and_order(self):
        from evaluation import per_concept_search as search
        from evaluation.concept_extractor import Concept
        index = faiss.IndexFlatIP(3)
        vectors = Encoder().encode(["sensor", "battery", "camera"])
        faiss.normalize_L2(vectors)
        index.add(vectors)
        metadata = {str(i): f"p{i}" for i in range(3)}
        frame = pd.DataFrame([{"patent_id": f"p{i}", "title": str(i)} for i in range(3)])
        encoder = Encoder()
        concepts = [Concept("sensor", "monitor", "IoT"), Concept("battery", "charger", "Energy")]
        with patch.object(search, "_load_faiss_resources", return_value=(index, metadata, frame)), patch.object(search, "_get_model", return_value=encoder):
            results = search.search_per_concept(concepts, top_k=2, enrich_cpc=False)
        self.assertEqual(len(encoder.calls), 1)
        for concept, result in zip(concepts, results):
            vector = Encoder().encode([f"{concept.label}. {concept.description}"])
            faiss.normalize_L2(vector)
            scores, ids = index.search(vector, 2)
            self.assertEqual([hit.patent_id for hit in result.hits], [metadata[str(i)] for i in ids[0]])
            np.testing.assert_allclose([hit.score for hit in result.hits], scores[0], atol=1e-6)
            self.assertIs(result.concept, concept)


if __name__ == "__main__":
    unittest.main()
