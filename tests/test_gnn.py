import os
import sys
import unittest
from pathlib import Path
import numpy as np

# Setup path so backend/src is importable
TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
sys.path.insert(0, str(BACKEND_SRC))

from gnn.model import PatentGraphSAGE
from gnn.graph_builder import build_subgraph_data
from gnn.inference import get_model, run_gnn_inference
from gnn.reranker import rerank_hits
from integration.pipeline import _load_resources, _get_model

class TestGNNInferencePipeline(unittest.TestCase):
    
    def test_model_architecture(self):
        """Test model load and keys in state_dict."""
        model = get_model()
        self.assertIsNotNone(model)
        self.assertTrue(isinstance(model, PatentGraphSAGE))
        
    def test_graph_builder_and_inference(self):
        """Test GNN graph building and running inference on seed patents."""
        # Load real resources
        faiss_index, metadata_mapping, patents_df = _load_resources()
        st_model = _get_model()
        
        # Grab first 5 patent IDs from the deduplicated CSV
        sample_pids = patents_df["patent_id"].head(5).tolist()
        self.assertGreater(len(sample_pids), 0)
        
        # Build mock hits list
        hits = []
        for i, pid in enumerate(sample_pids):
            # Locate record in dataframe
            row = patents_df[patents_df["patent_id"] == pid].iloc[0]
            hits.append({
                "rank": i + 1,
                "faiss_rank": i + 1,
                "patent_id": pid,
                "semantic_score": 0.9 - (i * 0.05),
                "title": row.get("title", ""),
                "abstract": row.get("abstract", ""),
                "domain": row.get("domain", ""),
                "url": row.get("url", ""),
                "source": "faiss",
                "expansion_type": None
            })
            
        # Build graph object
        data, pid_to_idx = build_subgraph_data(hits, patents_df, metadata_mapping, faiss_index, st_model)
        
        # Validate PyG Data dimensions
        N = data.x.shape[0]
        self.assertEqual(data.x.shape[1], 780)
        self.assertEqual(data.edge_index.shape[0], 2)
        
        # Run live forward pass
        embeddings, preds = run_gnn_inference(data)
        
        # Validate output shapes
        self.assertEqual(embeddings.shape, (N, 64))
        self.assertEqual(preds.shape, (N, 1))
        
        # Test reranker for novelty mode
        reranked_novelty = rerank_hits(hits, embeddings, preds, pid_to_idx, "novelty", 0.7, 0.3)
        self.assertEqual(len(reranked_novelty), len(hits))
        for hit in reranked_novelty:
            self.assertIn("graph_score", hit)
            self.assertIn("combined_score", hit)
            self.assertIn("novelty_score", hit)
            self.assertIn("rank", hit)
            self.assertIn("rank_change", hit)
            self.assertEqual(hit["gnn_mode"], "novelty")
            
        # Test reranker for graph_sim mode
        reranked_sim = rerank_hits(hits, embeddings, preds, pid_to_idx, "graph_sim", 0.7, 0.3)
        self.assertEqual(len(reranked_sim), len(hits))
        for hit in reranked_sim:
            self.assertIn("graph_score", hit)
            self.assertIn("combined_score", hit)
            self.assertIn("novelty_score", hit)
            self.assertIn("rank", hit)
            self.assertIn("rank_change", hit)
            self.assertEqual(hit["gnn_mode"], "graph_sim")

if __name__ == "__main__":
    unittest.main()
