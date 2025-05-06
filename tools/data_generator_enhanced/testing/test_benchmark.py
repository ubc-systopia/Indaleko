#!/usr/bin/env python3
"""
Unit tests for the model-based data generator benchmark suite.
"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the project root to the Python path
current_path = Path(__file__).parent.resolve()
while not (current_path / "Indaleko.py").exists() and current_path != current_path.parent:
    current_path = current_path.parent
os.environ["INDALEKO_ROOT"] = str(current_path)
sys.path.insert(0, str(current_path))

from tools.data_generator_enhanced.testing.benchmark import BenchmarkSuite
from tools.data_generator_enhanced.testing.metrics import SearchMetrics


class TestBenchmarkSuite(unittest.TestCase):
    """Test cases for the BenchmarkSuite class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a minimal configuration for testing
        self.config = {
            "scenarios": [
                {
                    "name": "test_scenario",
                    "description": "Test scenario",
                    "scale_factor": 0.1,
                    "storage_count": 10,
                    "semantic_count": 8,
                    "activity_count": 5,
                    "relationship_count": 15,
                    "queries": ["Find all PDF files"]
                }
            ],
            "generators": [
                {
                    "name": "test_generator",
                    "description": "Test generator",
                    "model_based": True,
                    "use_model_templates": True
                }
            ],
            "output_dir": "./test_results",
            "repeat": 1
        }

        # Write the configuration to a temporary file
        self.config_path = Path("./test_config.json")
        with open(self.config_path, "w") as f:
            json.dump(self.config, f)

    def tearDown(self):
        """Clean up after tests."""
        # Remove the temporary configuration file
        if self.config_path.exists():
            self.config_path.unlink()

        # Remove any test results directory
        test_results = Path("./test_results")
        if test_results.exists():
            import shutil
            shutil.rmtree(test_results)

    def test_load_config(self):
        """Test loading configuration from a file."""
        suite = BenchmarkSuite(config_path=self.config_path)

        # Check that the configuration was loaded correctly
        self.assertEqual(suite.config["output_dir"], "./test_results")
        self.assertEqual(len(suite.config["scenarios"]), 1)
        self.assertEqual(len(suite.config["generators"]), 1)
        self.assertEqual(suite.config["scenarios"][0]["name"], "test_scenario")
        self.assertEqual(suite.config["generators"][0]["name"], "test_generator")

    def test_default_config(self):
        """Test loading default configuration when no file is provided."""
        suite = BenchmarkSuite()

        # Check that default configuration was used
        self.assertIn("scenarios", suite.config)
        self.assertIn("generators", suite.config)
        self.assertEqual(suite.config["output_dir"], "./benchmark_results")

    @patch('tools.data_generator_enhanced.testing.benchmark.GenerationController')
    @patch('tools.data_generator_enhanced.testing.benchmark.ModelBasedTestRunner')
    def test_run_single_benchmark(self, mock_runner, mock_controller):
        """Test running a single benchmark scenario and generator combination."""
        # Configure mocks
        mock_controller_instance = MagicMock()
        mock_controller.return_value = mock_controller_instance

        mock_runner_instance = MagicMock()
        mock_runner.return_value = mock_runner_instance

        # Set up mock generation stats
        mock_controller_instance.generate_dataset.return_value = {
            "counts": {
                "storage": 10,
                "semantic": 8,
                "activity": 5,
                "relationship": 15,
                "total": 38
            }
        }

        mock_controller_instance.generate_truth_dataset.return_value = {}

        # Set up mock query generator
        mock_runner_instance.query_generator = MagicMock()

        # Set up mock truth records and truth IDs
        mock_controller_instance.truth_records = {}
        mock_runner_instance.truth_ids = {"all": set(["id1", "id2", "id3"])}

        # Set up mock AQL executor
        mock_runner_instance.aql_executor = MagicMock()
        mock_runner_instance.aql_executor.execute.return_value = [
            {"_id": "doc1", "ObjectIdentifier": "id1"},
            {"_id": "doc2", "ObjectIdentifier": "id2"}
        ]

        # Set up mock extract_result_ids
        mock_runner_instance._extract_result_ids.return_value = set(["id1", "id2"])

        # Create benchmark suite
        suite = BenchmarkSuite()
        suite.config = self.config

        # Run a single benchmark
        result = suite._run_single_benchmark(
            self.config["scenarios"][0],
            self.config["generators"][0]
        )

        # Check the result
        self.assertEqual(result["storage_count"], 10)
        self.assertEqual(result["semantic_count"], 8)
        self.assertEqual(result["activity_count"], 5)
        self.assertEqual(result["relationship_count"], 15)
        self.assertEqual(result["total_count"], 38)
        self.assertIn("generation_time", result)
        self.assertIn("query_time", result)
        self.assertIn("average_precision", result)
        self.assertIn("average_recall", result)
        self.assertIn("average_f1_score", result)

    def test_create_metadata_context(self):
        """Test creating metadata context for queries."""
        suite = BenchmarkSuite()

        # Test PDF query
        context = suite._create_metadata_context("Find all PDF files")
        self.assertEqual(context.get("extension"), "pdf")
        self.assertEqual(context.get("mime_type"), "application/pdf")

        # Test video query
        context = suite._create_metadata_context("Find large video files")
        self.assertEqual(context.get("extension"), "mp4")
        self.assertEqual(context.get("mime_type"), "video/mp4")
        self.assertGreater(context.get("min_size", 0), 0)

        # Test recent query
        context = suite._create_metadata_context("Show me files modified in the last week")
        self.assertIn("start_time", context)
        self.assertIn("end_time", context)

    def test_calculate_average_metrics(self):
        """Test calculating average metrics from a list of metrics."""
        suite = BenchmarkSuite()

        # Test with empty list
        avg_metrics = suite._calculate_average_metrics([])
        self.assertEqual(avg_metrics, {})

        # Test with metrics
        metrics_list = [
            {"precision": 0.8, "recall": 0.6, "f1_score": 0.686},
            {"precision": 0.7, "recall": 0.7, "f1_score": 0.7},
            {"precision": 0.9, "recall": 0.5, "f1_score": 0.643}
        ]

        avg_metrics = suite._calculate_average_metrics(metrics_list)
        self.assertAlmostEqual(avg_metrics["precision"], 0.8, places=3)
        self.assertAlmostEqual(avg_metrics["recall"], 0.6, places=3)
        self.assertAlmostEqual(avg_metrics["f1_score"], 0.676, places=3)

    def test_find_best_generator(self):
        """Test finding the generator with the highest F1 score."""
        suite = BenchmarkSuite()

        summary = {
            "generator_comparison": {
                "legacy": {"average_f1_score": 0.6},
                "model_based": {"average_f1_score": 0.7},
                "model_based_templates": {"average_f1_score": 0.8}
            }
        }

        best_generator = suite._find_best_generator(summary)
        self.assertEqual(best_generator, "model_based_templates")

    def test_find_most_challenging_scenario(self):
        """Test finding the scenario with the lowest F1 score."""
        suite = BenchmarkSuite()

        summary = {
            "scenario_comparison": {
                "small_dataset": {"average_f1_score": 0.8},
                "medium_dataset": {"average_f1_score": 0.7},
                "large_dataset": {"average_f1_score": 0.6}
            }
        }

        most_challenging = suite._find_most_challenging_scenario(summary)
        self.assertEqual(most_challenging, "large_dataset")


class TestSearchMetrics(unittest.TestCase):
    """Test cases for the SearchMetrics class."""

    def test_precision_recall_calculation(self):
        """Test calculating precision, recall, and F1 score."""
        # Test with perfect match
        truth_ids = set(["id1", "id2", "id3"])
        result_ids = set(["id1", "id2", "id3"])

        metrics = SearchMetrics(truth_ids, result_ids)
        self.assertEqual(metrics.precision, 1.0)
        self.assertEqual(metrics.recall, 1.0)
        self.assertEqual(metrics.f1_score, 1.0)

        # Test with partial match
        truth_ids = set(["id1", "id2", "id3", "id4"])
        result_ids = set(["id1", "id2", "id5", "id6"])

        metrics = SearchMetrics(truth_ids, result_ids)
        self.assertEqual(metrics.precision, 0.5)  # 2 out of 4 results are relevant
        self.assertEqual(metrics.recall, 0.5)     # 2 out of 4 truth items are found
        self.assertEqual(metrics.f1_score, 0.5)   # Harmonic mean of 0.5 and 0.5

        # Test with no matches
        truth_ids = set(["id1", "id2", "id3"])
        result_ids = set(["id4", "id5", "id6"])

        metrics = SearchMetrics(truth_ids, result_ids)
        self.assertEqual(metrics.precision, 0.0)
        self.assertEqual(metrics.recall, 0.0)
        self.assertEqual(metrics.f1_score, 0.0)

        # Test with empty truth set
        truth_ids = set()
        result_ids = set(["id1", "id2"])

        metrics = SearchMetrics(truth_ids, result_ids)
        self.assertEqual(metrics.precision, 0.0)
        self.assertEqual(metrics.recall, 0.0)
        self.assertEqual(metrics.f1_score, 0.0)

        # Test with empty result set
        truth_ids = set(["id1", "id2"])
        result_ids = set()

        metrics = SearchMetrics(truth_ids, result_ids)
        self.assertEqual(metrics.precision, 0.0)
        self.assertEqual(metrics.recall, 0.0)
        self.assertEqual(metrics.f1_score, 0.0)


if __name__ == "__main__":
    unittest.main()
