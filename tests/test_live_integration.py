"""Opt-in checks against configured MySQL/Neo4j; only own UUID cases are removed."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend/src"))


@unittest.skipUnless(os.getenv("RUN_DATABASE_TESTS") == "1", "Set RUN_DATABASE_TESTS=1 for live checks")
class LiveIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dotenv import load_dotenv
        from sqlalchemy import text
        load_dotenv(ROOT / ".env")
        from persistence.database import get_engine
        cls.engine = get_engine()
        with cls.engine.connect() as connection:
            cls.patent_id = connection.execute(text("SELECT patent_id FROM patents LIMIT 1")).scalar_one()

    def setUp(self):
        from persistence import analysis_store as store
        self.store = store
        self.case = store.create_case("Integration check (temporary)", "Original sensor idea")

    def tearDown(self):
        self.store.delete_case(self.case["case_id"])

    def pipeline(self):
        return {"query_id": "repeated-query-for-integration-check", "query_text": "sensor idea", "model": "fixture",
                "nlp_result": {"clean_text": "sensor idea", "keywords": ["sensor"], "entities": [], "source": "fixture"},
                "top_k": 1, "kg_status": "success", "gnn_status": "success", "results": [
                    {"patent_id": self.patent_id, "rank": 1, "source": "faiss", "semantic_score": 0.5,
                     "title": "Sensor α", "abstract": "A test disclosure", "related_publications": [{"patent_id": "publication-variant"}]}]}

    def test_complete_snapshot_and_repeated_runs(self):
        first = self.store.persist_pipeline_result("Original sensor idea", 1, "novelty", self.pipeline(), self.case["case_id"])
        second = self.store.persist_pipeline_result("Revised sensor idea", 1, "novelty", self.pipeline(), self.case["case_id"])
        evaluation = {"patentability_score": 61.5, "risk": "Medium", "verdict": "Investigate", "novelty": {"score": 50}}
        improvement = {"diagnosis": ["overlap"], "weaknesses": ["scope"], "strategies": [{"strategy": "Change sensor architecture", "impact": "high", "reason": "Reduce overlap"}],
                       "alternative_directions": ["Low-power monitoring"], "recommendations": "Full explanation α", "overlapping_patents": []}
        self.store.persist_evaluation(first["run_id"], evaluation)
        self.store.persist_improvements(first["run_id"], improvement)
        saved = self.store.get_run(self.case["case_id"], first["run_id"])
        self.assertEqual(saved["idea_text"], "Original sensor idea")
        self.assertEqual(saved["pipeline_result"]["results"], self.pipeline()["results"])
        self.assertEqual(saved["evaluation_result"]["novelty"], evaluation["novelty"])
        self.assertEqual(saved["improvement_result"]["recommendations"], "Full explanation α")
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertEqual(len(self.store.get_case(self.case["case_id"])["runs"]), 2)
        self.assertEqual(self.store.get_run(self.case["case_id"], second["run_id"])["idea_text"], "Revised sensor idea")
        self.assertIsNone(self.store.get_run("wrong-case", first["run_id"]))
        listed = next(c for c in self.store.list_cases() if c["case_id"] == self.case["case_id"])
        self.assertEqual(len(listed["runs"]), 2)
        self.assertEqual(listed["status"], "active")

    def test_failed_result_write_rolls_back_entire_run(self):
        from sqlalchemy import text
        bad = self.pipeline()
        bad["results"][0]["source"] = "invalid-source"
        with self.assertRaises(Exception):
            self.store.persist_pipeline_result("Broken run", 1, "novelty", bad, self.case["case_id"])
        with self.engine.connect() as connection:
            count = connection.execute(text("SELECT COUNT(*) FROM analysis_runs WHERE case_id=:id"), {"id": self.case["case_id"]}).scalar_one()
        self.assertEqual(count, 0)
        self.assertEqual(self.store.get_case(self.case["case_id"])["status"], "draft")

    def test_graph_views_are_read_only_and_metadata_is_real(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from neo4j import GraphDatabase
        from api.routers.kg import router
        from persistence.patent_repository import load_patent_dataframe
        with GraphDatabase.driver(os.getenv("NEO4J_URI"), auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD"))) as driver:
            def counts():
                with driver.session() as session:
                    return (session.run("MATCH (n) RETURN count(n) AS c").single()["c"], session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"])
            before = counts()
            app = FastAPI()
            app.include_router(router, prefix="/api")
            client = TestClient(app)
            self.assertEqual(client.get("/api/kg/stats", params={"patent_ids": self.patent_id}).status_code, 200)
            self.assertEqual(client.get("/api/kg/graph", params={"patent_ids": self.patent_id}).status_code, 200)
            self.assertEqual(client.post("/api/kg/build", json={"patent_ids": [self.patent_id]}).status_code, 200)
            self.assertEqual(before, counts())
        frame = load_patent_dataframe()
        self.assertEqual(len(frame), 58428)
        self.assertTrue((frame["cites_patent_count"].astype(float) > 0).any())
        self.assertTrue((frame.loc[frame["family_size"] != "", "family_size"].astype(float) > 1).any())
        self.assertTrue(frame["jurisdiction"].str.len().gt(0).all())


if __name__ == "__main__":
    unittest.main()
