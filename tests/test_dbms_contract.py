import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

TEST_DIR = Path(__file__).resolve().parent
BACKEND_SRC = TEST_DIR.parent / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))


class TestDBMSLabContract(unittest.TestCase):
    def test_mysql_url_uses_environment_credentials(self):
        from persistence.database import database_url

        with patch.dict(os.environ, {
            "MYSQL_HOST": "db.example", "MYSQL_PORT": "3307", "MYSQL_DATABASE": "patents",
            "MYSQL_USER": "lab_user", "MYSQL_PASSWORD": "safe value",
        }, clear=True):
            self.assertEqual(
                database_url(),
                "mysql+pymysql://lab_user:safe+value@db.example:3307/patents?charset=utf8mb4",
            )

    def test_pipeline_request_supports_case_linking(self):
        sys.path.insert(0, str(TEST_DIR.parent / "backend"))
        from api.schemas import PipelineRequest

        request = PipelineRequest(idea="A sensor platform", case_id="case-1", case_title="Sensor case")
        self.assertEqual(request.case_id, "case-1")
        self.assertEqual(request.case_title, "Sensor case")

    def test_schema_contains_core_and_application_relations(self):
        schema = (TEST_DIR.parent / "database" / "sql" / "01_schema.sql").read_text(encoding="utf-8")
        for table in ("patents", "patent_cpc_codes", "analysis_cases", "analysis_runs", "run_patent_results"):
            self.assertIn(f"CREATE TABLE {table}", schema)


if __name__ == "__main__":
    unittest.main()
