"""Regression checks for metadata parsing and non-indexed GNN candidates."""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))


class RuntimeMetadataTests(unittest.TestCase):
    def test_nullable_sql_integers_remain_parseable_and_unknown_is_not_zero(self):
        from persistence import patent_repository as repo
        frame = pd.DataFrame({
            'patent_id': ['p1', 'p2'], 'publication_year': [2024.0, None],
            'cited_by_patent_count': [0.0, None], 'cites_patent_count': [4.0, None],
            'family_size': [3.0, None],
        })
        with patch.object(repo, 'get_engine', return_value=MagicMock()), patch.object(repo.pd, 'read_sql', return_value=frame):
            result = repo.load_patent_dataframe()
        self.assertEqual(result.iloc[0]['publication_year'], '2024')
        self.assertEqual(result.iloc[0]['cited_by_patent_count'], '0')
        self.assertEqual(result.iloc[1]['cited_by_patent_count'], '')
        self.assertEqual(result.iloc[0]['family_size'], '3')

    def test_gnn_fallback_embedding_is_normalized_without_name_error(self):
        from gnn import graph_builder as builder
        index = MagicMock(d=768)
        encoder = MagicMock()
        encoder.encode.return_value = np.full((1, 768), 2.0, dtype=np.float32)
        frame = pd.DataFrame([{'patent_id': 'not-indexed', 'title': 'Sensor', 'abstract': 'Battery monitor'}])
        with patch.object(builder, 'fetch_subgraph_neighbors', return_value=[]), patch.object(builder, 'fetch_subgraph_edges', return_value=[]):
            data, mapping = builder.build_subgraph_data([{'patent_id': 'not-indexed'}], frame, {}, index, encoder)
        self.assertEqual(tuple(data.x.shape), (1, 780))
        self.assertAlmostEqual(float(np.linalg.norm(data.x[0, :768].numpy())), 1.0, places=5)
        self.assertEqual(mapping, {'not-indexed': 0})


if __name__ == '__main__':
    unittest.main()
