import os
import sys
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

# Setup path so backend/src is importable
TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent
BACKEND_SRC = PROJECT_ROOT / "backend" / "src"
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Import modules under test
from improvement.analyzer import analyze_overlap, detect_weaknesses
from improvement.strategies import choose_improvement_strategies
from improvement.opportunity_finder import find_low_density_opportunities
from improvement.generator import generate_llm_explanation
from improvement.agent import ImprovementAgent

# Import FastAPI app to test integration
from api.main import app

class TestImprovementAgent(unittest.TestCase):

    def setUp(self):
        # Sample mock inputs
        self.user_idea = "A wearable EEG headset that uses deep learning to detect epilepsy seizures and alert doctors."
        
        self.mock_pipeline_result = {
            "query_id": "test_query",
            "query_text": self.user_idea,
            "results": [
                {
                    "patent_id": "US-12345-B2",
                    "semantic_score": 0.85,
                    "graph_score": 0.80,
                    "combined_score": 0.835,
                    "domain": "Medical",
                    "title": "EEG Seizure Monitor",
                    "abstract": "A system detecting seizures using EEG brainwaves.",
                },
                {
                    "patent_id": "US-67890-B2",
                    "semantic_score": 0.75,
                    "graph_score": 0.72,
                    "combined_score": 0.741,
                    "domain": "Medical",
                    "title": "Seizure warning system",
                    "abstract": "Device utilizing sensor data to warn of neurological events.",
                }
            ],
            "gnn_status": "success",
            "kg_status": "success"
        }

        self.mock_evaluation_result = {
            "patentability_score": 45.0,
            "patentability_raw": 48.0,
            "verdict": "Weak patentability potential",
            "risk": "High",
            "confidence": 0.9,
            "novelty": {
                "score": 38.0,
                "top_semantic_score": 0.85,
                "semantic_novelty": 0.35,
                "gnn_novelty": 0.40,
                "blend": {"semantic": 0.6, "gnn": 0.4},
                "interpretation": "Low novelty"
            },
            "non_obviousness": {
                "score": 48.0,
                "breakdown": {
                    "combination_difficulty": {"score": 0.4},
                    "motivation_to_combine": {"score": 0.3},
                    "cross_domain_novelty": {"score": 0.5},
                    "reconstruction": {"score": 0.3},
                    "citation_isolation": {"score": 0.4},
                    "long_felt_need": {"score": 0.2},
                    "teaching_away": {"score": 0.0},
                    "unexpected_effect": {"score": 0.0}
                }
            },
            "landscape": {
                "score": 0.35,
                "density": 15,
                "active_ratio": 0.8,
                "assignee_concentration": 0.6,
                "interpretation": "Crowded landscape"
            },
            "claim_breadth": {"score": 50.0},
            "timing": {"score": 45.0},
            "india_eligibility": {"is_flagged": False, "flags": []},
            "technical_depth": {"confidence": 0.9}
        }

    def test_analyzer_high_overlap(self):
        """Test analyzer identifies semantic/graph overlaps, crowded domain, and low novelty."""
        problems = analyze_overlap(self.mock_pipeline_result, self.mock_evaluation_result)
        self.assertIn("high_semantic_overlap", problems)
        self.assertIn("high_graph_overlap", problems)
        self.assertIn("crowded_domain", problems)
        self.assertIn("low_novelty", problems)

        weaknesses = detect_weaknesses(self.mock_pipeline_result, self.mock_evaluation_result, problems)
        self.assertEqual(len(weaknesses), 4)
        self.assertTrue(any("semantic" in w.lower() or "overlap" in w.lower() for w in weaknesses))
        self.assertTrue(any("graph" in w.lower() or "structural similarity" in w.lower() for w in weaknesses))

    def test_analyzer_clean_case(self):
        """Test analyzer behavior when metrics are well within safe bounds."""
        clean_pipeline = {
            "results": [
                {"semantic_score": 0.45, "graph_score": 0.50, "domain": "Energy"}
            ]
        }
        clean_eval = {
            "patentability_score": 85.0,
            "novelty": {"score": 88.0, "top_semantic_score": 0.45},
            "non_obviousness": {"score": 82.0},
            "landscape": {"score": 0.85, "density": 2}
        }
        problems = analyze_overlap(clean_pipeline, clean_eval)
        self.assertEqual(len(problems), 0)
        
        weaknesses = detect_weaknesses(clean_pipeline, clean_eval, problems)
        self.assertEqual(len(weaknesses), 1)
        self.assertEqual(weaknesses[0], "No critical patentability or overlap weaknesses detected based on system metrics.")

    def test_strategy_engine(self):
        """Test strategy selector engine handles problems and domains correctly."""
        problems = ["high_semantic_overlap", "crowded_domain"]
        strategies = choose_improvement_strategies(problems, domain="Medical")
        
        # Verify strategies are domain-specific dictionaries
        self.assertGreater(len(strategies), 0)
        self.assertTrue(all(isinstance(s, dict) for s in strategies))
        self.assertIn("strategy", strategies[0])
        self.assertIn("impact", strategies[0])
        self.assertIn("reason", strategies[0])
        
        # Check domain-specific medical strategy is present
        self.assertTrue(any("spectroscopy" in s["strategy"] or "capacitive" in s["strategy"] or "neurogaming" in s["strategy"] for s in strategies))

        # Test fallback
        fallback_strategies = choose_improvement_strategies([], domain="Medical")
        self.assertGreater(len(fallback_strategies), 0)
        self.assertEqual(fallback_strategies[0]["strategy"], "Optimize system configuration parameters for specific edge nodes")

    def test_opportunity_finder(self):
        """Test opportunity finder returns crossover opportunities from dominant domains."""
        # Dominant domain in setUp results is "Medical"
        directions = find_low_density_opportunities(self.user_idea, self.mock_pipeline_result["results"])
        self.assertGreater(len(directions), 0)
        self.assertLessEqual(len(directions), 3)
        # Expected crossovers for Medical are specific non-naive suggestions
        self.assertTrue(any(isinstance(d, str) for d in directions))

    def test_opportunity_finder_keyword_fallback(self):
        """Test opportunity finder keyword fallback when retrieved patents are empty."""
        directions = find_low_density_opportunities("epilepsy sensor", [])
        self.assertGreater(len(directions), 0)

    def test_generator_fallback(self):
        """Test generator falls back gracefully if Gemini API/client is offline."""
        import improvement.generator
        original_client = improvement.generator.client
        improvement.generator.client = None
        try:
            explanation = generate_llm_explanation(
                idea=self.user_idea,
                diagnosis=["high semantic overlap", "crowded patent domain"],
                weaknesses=["Textual overlap is high.", "Domain is congested."],
                strategies=[
                    {"strategy": "shift sensor technology", "impact": "high", "reason": "avoids overlap"}
                ],
                alternative_directions=["Acoustic sensor fusion"]
            )
            self.assertIsNotNone(explanation)
            self.assertTrue("Weakness Diagnosis" in explanation or "Patent Innovation" in explanation)
        finally:
            improvement.generator.client = original_client

    def test_agent_orchestration(self):
        """Test end-to-end orchestrator pipeline and return format compliance."""
        agent = ImprovementAgent()
        output = agent.run_improvement_pipeline(
            user_idea=self.user_idea,
            pipeline_result=self.mock_pipeline_result,
            evaluation_result=self.mock_evaluation_result
        )
        
        self.assertIn("diagnosis", output)
        self.assertIn("weaknesses", output)
        self.assertIn("strategies", output)
        self.assertIn("alternative_directions", output)
        self.assertIn("recommendations", output)
        self.assertIn("overlapping_patents", output)
        
        self.assertTrue(isinstance(output["diagnosis"], list))
        self.assertTrue(isinstance(output["weaknesses"], list))
        self.assertTrue(isinstance(output["strategies"], list))
        self.assertTrue(isinstance(output["strategies"][0], dict))
        self.assertTrue(isinstance(output["alternative_directions"], list))
        self.assertTrue(isinstance(output["recommendations"], str))
        self.assertTrue(isinstance(output["overlapping_patents"], list))
        self.assertEqual(len(output["overlapping_patents"]), 2)  # Check we got the patents from our mock pipeline results

    def test_fastapi_endpoint(self):
        """Test FastAPI endpoint /api/improve using TestClient."""
        client = TestClient(app)
        
        # Test requesting with pre-computed data (runs fast, no DB/LLM dependencies)
        req_payload = {
            "idea": self.user_idea,
            "pipeline_result": self.mock_pipeline_result,
            "evaluation_result": self.mock_evaluation_result
        }
        
        response = client.post("/api/improve", json=req_payload)
        self.assertEqual(response.status_code, 200)
        
        resp_json = response.json()
        self.assertIn("diagnosis", resp_json)
        self.assertIn("weaknesses", resp_json)
        self.assertIn("strategies", resp_json)
        self.assertIn("alternative_directions", resp_json)
        self.assertIn("recommendations", resp_json)
        self.assertIn("overlapping_patents", resp_json)
        self.assertTrue(isinstance(resp_json["overlapping_patents"], list))
        self.assertEqual(len(resp_json["overlapping_patents"]), 2)

if __name__ == "__main__":
    unittest.main()
