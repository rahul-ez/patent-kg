"""Opt-in real model/DB test: warm computation still saves separate owned runs."""
import os
import secrets
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "backend/src"))


@unittest.skipUnless(os.getenv("RUN_PERFORMANCE_TESTS") == "1", "Set RUN_PERFORMANCE_TESTS=1; requires live databases/models")
class LivePerformanceTests(unittest.TestCase):
    def test_warm_pipeline_keeps_fresh_owned_runs_and_saved_timings(self):
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        from fastapi.testclient import TestClient
        from sqlalchemy import text
        from api.main import app
        from api.routers import auth
        from persistence.database import get_engine
        from integration import pipeline

        client = TestClient(app, headers={"X-Requested-With": "patent-client"})
        email = f"performance-check-{uuid4()}@example.com"
        with patch.object(auth.auth_store, "throttle", return_value=True):
            signup = client.post("/api/auth/signup", json={
                "email": email, "password": secrets.token_urlsafe(24), "display_name": "Temporary performance check",
            })
        self.assertEqual(signup.status_code, 201)
        user_id = signup.json()["user"]["user_id"]
        client.headers["X-CSRF-Token"] = signup.json()["csrf_token"]
        try:
            idea = "A wearable EEG sensor uses machine learning to predict epileptic seizures and alert caregivers."
            fixture = {"patent_id": "user_query", "clean_text": idea, "keywords": [], "entities": [], "source": "benchmark_fixture"}
            with patch.object(pipeline, "process_user_query", return_value=fixture):
                first = client.post("/api/pipeline/run", json={"idea": idea, "top_k": 10})
                self.assertEqual(first.status_code, 200)
                first = first.json()
                second = client.post("/api/pipeline/run", json={"idea": idea, "top_k": 10, "case_id": first["case_id"]})
                self.assertEqual(second.status_code, 200)
                second = second.json()
            self.assertEqual(first["persistence_status"], "persisted")
            self.assertEqual(second["persistence_status"], "persisted")
            self.assertNotEqual(first["run_id"], second["run_id"])
            self.assertEqual(first["case_id"], second["case_id"])
            self.assertEqual(second["gnn_status"], "success")
            self.assertEqual(second["kg_status"], "success")
            self.assertTrue(second["results"])
            self.assertIn("gnn_embeddings", second["stage_timings"])
            saved = client.get(f"/api/cases/{first['case_id']}/runs/{second['run_id']}")
            self.assertEqual(saved.status_code, 200)
            self.assertEqual(saved.json()["pipeline_result"]["stage_timings"], second["stage_timings"])
        finally:
            client.post("/api/auth/logout")
            client.close()
            with get_engine().begin() as connection:
                # Only data belonging to this newly-created UUID account is removed.
                connection.execute(text("DELETE FROM analysis_cases WHERE owner_user_id=:id"), {"id": user_id})
                connection.execute(text("DELETE FROM app_users WHERE user_id=:id"), {"id": user_id})


if __name__ == "__main__":
    unittest.main()
