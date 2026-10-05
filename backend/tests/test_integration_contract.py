"""Contract checks that do not require database or AI-provider access."""
import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "src"))

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import JSON
from api.persistence import attach_saving_status
from api.routers import pipeline, kg, cases
from persistence import analysis_store as store


class IntegrationContractTests(unittest.TestCase):
    def test_graph_view_preserves_direction_and_unique_parallel_edge_ids(self):
        class Node(dict):
            def __init__(self, identifier, labels, **props):
                super().__init__(props)
                self.element_id = identifier
                self.labels = labels
        patent = Node('p1', {'Patent'}, patent_id='patent1')
        company = Node('c1', {'Company'}, company_name='Company A')
        first = types.SimpleNamespace(type='OWNS', element_id='r1', start_node=company, end_node=patent)
        second = types.SimpleNamespace(type='OWNS', element_id='r2', start_node=company, end_node=patent)
        rows = [{'n': patent, 'm': company, 'r': first}, {'n': patent, 'm': company, 'r': first}, {'n': patent, 'm': company, 'r': second}]
        app = FastAPI()
        app.include_router(kg.router, prefix='/api')
        with patch.object(kg, '_scoped_graph_rows', return_value=rows):
            result = TestClient(app).get('/api/kg/graph', params={'patent_ids': 'patent1'}).json()
        self.assertEqual([edge['id'] for edge in result['edges']], ['e-r1', 'e-r2'])
        self.assertTrue(all(edge['source'] == 'c1' and edge['target'] == 'p1' for edge in result['edges']))
        self.assertEqual(next(node['data']['label'] for node in result['nodes'] if node['id'] == 'c1'), 'Company A')

    def test_graph_stats_deduplicate_relationships_between_two_seeds(self):
        node = types.SimpleNamespace(labels={'Patent'}, element_id='p1')
        related = types.SimpleNamespace(labels={'Patent'}, element_id='p2')
        edge = types.SimpleNamespace(type='SIMPLE_FAMILY_MEMBER', element_id='r1')
        rows = [{'n': node, 'm': related, 'r': edge}, {'n': related, 'm': node, 'r': edge}]
        self.assertEqual(kg._counts_from_rows(rows), {'nodes': {'Patent': 2}, 'edges': {'SIMPLE_FAMILY_MEMBER': 1}})

    def test_mysql_datetimes_are_labelled_utc(self):
        from datetime import datetime, timezone
        value = store._utc_dates({"started_at": datetime(2026, 10, 5, 10, 24), "title": "Sensor"})
        self.assertEqual(value["started_at"].tzinfo, timezone.utc)
        self.assertEqual(value["title"], "Sensor")

    def test_json_bind_and_decode(self):
        statement = store._json_text("SELECT :payload")
        self.assertIsInstance(statement._bindparams["payload"].type, JSON)
        payload = {"results": [{"title": "Unicode α", "semantic_score": None}]}
        self.assertEqual(store._decode_payload(json.dumps(payload)), payload)
        self.assertEqual(store._decode_payload(payload), payload)

    def test_optional_failure_is_explicit(self):
        def fail():
            raise RuntimeError("private database details")
        with patch.dict(os.environ, {"PERSISTENCE_REQUIRED": "false"}):
            output = attach_saving_status({"results": []}, fail)
        self.assertEqual(output["persistence_status"], "not_saved")
        self.assertNotIn("private", output["persistence_message"])

    def test_required_failure_preserves_503_through_router(self):
        app = FastAPI()
        app.include_router(pipeline.router, prefix="/api")
        result = {"query_id": "q", "query_text": "idea", "nlp_result": {}, "model": "fixture", "top_k": 1, "results": []}
        fake = types.ModuleType("integration.pipeline")
        fake.run_end_to_end = lambda *args, **kwargs: dict(result)
        with patch.dict(sys.modules, {"integration.pipeline": fake}), patch.dict(os.environ, {"PERSISTENCE_REQUIRED": "true"}), patch.object(store, "persist_pipeline_result", side_effect=RuntimeError("offline")):
            response = TestClient(app).post("/api/pipeline/run", json={"idea": "idea", "top_k": 1})
        self.assertEqual(response.status_code, 503)

    def test_missing_case_is_404_not_unsaved_success(self):
        with self.assertRaises(HTTPException) as context:
            attach_saving_status({}, lambda: (_ for _ in ()).throw(ValueError("Case not found")))
        self.assertEqual(context.exception.status_code, 404)

    def test_graph_stats_and_legacy_build_only_read(self):
        app = FastAPI()
        app.include_router(kg.router, prefix="/api")
        with patch.object(kg, "_scoped_graph_rows", return_value=[]) as read:
            client = TestClient(app)
            self.assertEqual(client.get("/api/kg/stats", params={"patent_ids": "p1"}).status_code, 200)
            self.assertEqual(client.post("/api/kg/build", json={"patent_ids": ["p1"]}).status_code, 200)
            self.assertEqual(read.call_count, 2)

    def test_missing_run_is_404(self):
        app = FastAPI()
        app.include_router(cases.router, prefix="/api")
        with patch.object(store, "get_run", return_value=None):
            response = TestClient(app).get("/api/cases/wrong/runs/missing")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
