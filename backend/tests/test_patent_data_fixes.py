"""Regression checks for CPC imports and repeated-publication result grouping."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "src"))

from retrieval.classifications import cpc_rows  # noqa: E402
from retrieval.result_grouping import group_identical_publications  # noqa: E402


class ClassificationTests(unittest.TestCase):
    def test_only_cpc_links_are_selected(self):
        frame = pd.DataFrame([
            {"patent_id": "p1", "classification_type": "CPC", "classification_code": " G06N20/00 "},
            {"patent_id": "p1", "classification_type": "IPCR", "classification_code": "G06N20/00"},
            {"patent_id": "p2", "classification_type": "US", "classification_code": "123"},
            {"patent_id": "p3", "classification_type": "CPC", "classification_code": " "},
        ])
        result = cpc_rows(frame)
        self.assertEqual(result[["patent_id", "classification_code"]].values.tolist(), [["p1", "G06N20/00"]])

    def test_mysql_import_reconciles_using_only_cpc_rows(self):
        script = BACKEND / "scripts" / "database" / "bootstrap_mysql.py"
        spec = importlib.util.spec_from_file_location("bootstrap_mysql_for_test", script)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        class RecordingConnection:
            def __init__(self):
                self.calls = []

            def execute(self, statement, parameters=None):
                self.calls.append((str(statement), parameters))

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "classifications.csv"
            pd.DataFrame([
                {"patent_id": "p1", "classification_type": "CPC", "classification_code": "G06N20/00"},
                {"patent_id": "p2", "classification_type": "IPCR", "classification_code": "H01M10/00"},
            ]).to_csv(path, index=False)
            connection = RecordingConnection()
            self.assertEqual(module._import_cpc(connection, path, batch_size=2), 1)
        inserted = [parameters for sql, parameters in connection.calls if "INSERT IGNORE INTO patent_cpc_codes" in sql]
        self.assertEqual(inserted, [[{"patent_id": "p1", "cpc_code": "G06N20/00"}]])
        self.assertTrue(any("DELETE linked FROM patent_cpc_codes" in sql for sql, _ in connection.calls))


class ResultGroupingTests(unittest.TestCase):
    def test_groups_only_identical_full_text_and_keeps_publication_ids(self):
        hits = [
            {"rank": 1, "patent_id": "grant", "title": "Battery Controller", "abstract": "A long disclosure about charging.", "semantic_score": 0.9},
            {"rank": 2, "patent_id": "application", "title": " battery controller ", "abstract": "A  long disclosure about charging.", "semantic_score": 0.8, "url": "https://example.test/patent"},
            {"rank": 3, "patent_id": "different", "title": "Battery Controller", "abstract": "Different disclosure.", "semantic_score": 0.7},
        ]
        grouped = group_identical_publications(hits)
        self.assertEqual([hit["patent_id"] for hit in grouped], ["grant", "different"])
        self.assertEqual(grouped[0]["related_publications"][0]["patent_id"], "application")
        self.assertEqual(grouped[1]["rank"], 2)
        self.assertEqual(hits[0]["rank"], 1)  # inputs stay unchanged

    def test_missing_text_is_not_merged(self):
        hits = [
            {"patent_id": "a", "title": "", "abstract": "", "rank": 1},
            {"patent_id": "b", "title": "", "abstract": "", "rank": 2},
        ]
        self.assertEqual(len(group_identical_publications(hits)), 2)


if __name__ == "__main__":
    unittest.main()
