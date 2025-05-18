"""Unit tests for the ablation test runner."""

import json
import os
import shutil
import sys
import tempfile
import unittest
import uuid
from unittest.mock import MagicMock, patch

# Add project root to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from research.ablation.ablation_test_runner import AblationTestRunner
from research.ablation.ablation_tester import AblationConfig
from research.ablation.base import AblationResult


class TestAblationTestRunner(unittest.TestCase):
    """Test cases for the AblationTestRunner class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test outputs
        self.temp_dir = tempfile.mkdtemp()

        # Create a mock ablation tester
        self.mock_tester = MagicMock()

        # Create a test query ID
        self.test_query_id = uuid.uuid4()

        # Create a test query
        self.test_query = {"id": str(self.test_query_id), "text": "test query", "type": "location"}

        # Create test results
        self.test_results = {
            "TestCollection1_impact_on_TestCollection2": AblationResult(
                query_id=self.test_query_id,
                ablated_collection="TestCollection1_impact_on_TestCollection2",
                precision=0.8,
                recall=0.7,
                f1_score=0.75,
                execution_time_ms=100,
                result_count=10,
                true_positives=8,
                false_positives=2,
                false_negatives=3,
            ),
            "TestCollection2_impact_on_TestCollection1": AblationResult(
                query_id=self.test_query_id,
                ablated_collection="TestCollection2_impact_on_TestCollection1",
                precision=0.6,
                recall=0.5,
                f1_score=0.55,
                execution_time_ms=100,
                result_count=10,
                true_positives=6,
                false_positives=4,
                false_negatives=6,
            ),
        }

        # Patch the AblationTester to return our mock
        self.patcher = patch("research.ablation.ablation_test_runner.AblationTester", return_value=self.mock_tester)
        self.patcher.start()

        # Mock the tester's run_ablation_test method
        self.mock_tester.run_ablation_test.return_value = self.test_results

        # Create the runner
        self.runner = AblationTestRunner(output_dir=self.temp_dir)

        # Set up test results in the runner
        self.runner.results = {str(self.test_query_id): self.test_results}

    def tearDown(self):
        """Clean up after tests."""
        # Stop the patcher
        self.patcher.stop()

        # Clean up the temporary directory
        shutil.rmtree(self.temp_dir)

    def test_init(self):
        """Test initialization of AblationTestRunner."""
        # Verify the runner was created
        self.assertIsNotNone(self.runner)

        # Verify the output directory was created
        self.assertTrue(os.path.exists(self.temp_dir))

    def test_run_single_test(self):
        """Test running a single ablation test."""
        # Create a config
        config = AblationConfig(collections_to_ablate=["TestCollection1", "TestCollection2"], query_limit=10)

        # Run a single test
        results = self.runner.run_single_test(self.test_query_id, "test query", config)

        # Verify the tester was called
        self.mock_tester.run_ablation_test.assert_called_with(config, self.test_query_id, "test query")

        # Verify results were returned
        self.assertEqual(results, self.test_results)

        # Verify results were stored
        self.assertIn(str(self.test_query_id), self.runner.results)

    def test_run_batch_tests(self):
        """Test running a batch of ablation tests."""
        # Create a list of test queries
        test_queries = [self.test_query]

        # Create a config
        config = AblationConfig(collections_to_ablate=["TestCollection1", "TestCollection2"], query_limit=10)

        # Run batch tests
        results = self.runner.run_batch_tests(test_queries, config)

        # Verify the tester was called for each query
        self.mock_tester.run_ablation_test.assert_called_with(config, self.test_query_id, "test query")

        # Verify results were returned
        self.assertEqual(results, self.runner.results)

    def test_calculate_aggregate_metrics(self):
        """Test calculation of aggregate metrics."""
        # Calculate aggregate metrics
        metrics = self.runner.calculate_aggregate_metrics()

        # Verify metrics were calculated
        self.assertIn("TestCollection1_impact_on_TestCollection2", metrics)
        self.assertIn("TestCollection2_impact_on_TestCollection1", metrics)

        # Verify metric values
        self.assertAlmostEqual(metrics["TestCollection1_impact_on_TestCollection2"]["avg_precision"], 0.8)
        self.assertAlmostEqual(metrics["TestCollection1_impact_on_TestCollection2"]["avg_recall"], 0.7)
        self.assertAlmostEqual(metrics["TestCollection1_impact_on_TestCollection2"]["avg_f1"], 0.75)
        self.assertAlmostEqual(metrics["TestCollection1_impact_on_TestCollection2"]["avg_impact"], 0.25)

        self.assertAlmostEqual(metrics["TestCollection2_impact_on_TestCollection1"]["avg_precision"], 0.6)
        self.assertAlmostEqual(metrics["TestCollection2_impact_on_TestCollection1"]["avg_recall"], 0.5)
        self.assertAlmostEqual(metrics["TestCollection2_impact_on_TestCollection1"]["avg_f1"], 0.55)
        self.assertAlmostEqual(metrics["TestCollection2_impact_on_TestCollection1"]["avg_impact"], 0.45)

    def test_save_results_json(self):
        """Test saving results to JSON."""
        # Save results to JSON
        filepath = self.runner.save_results_json()

        # Verify the file was created
        self.assertTrue(os.path.exists(filepath))

        # Verify the file contains the expected data
        with open(filepath) as f:
            data = json.load(f)

            # Verify structure
            self.assertIn(str(self.test_query_id), data)

            # Verify content
            query_data = data[str(self.test_query_id)]
            self.assertIn("TestCollection1_impact_on_TestCollection2", query_data)
            self.assertIn("TestCollection2_impact_on_TestCollection1", query_data)

            # Verify values
            tc1_data = query_data["TestCollection1_impact_on_TestCollection2"]
            self.assertEqual(tc1_data["precision"], 0.8)
            self.assertEqual(tc1_data["recall"], 0.7)
            self.assertEqual(tc1_data["f1_score"], 0.75)

    def test_save_results_csv(self):
        """Test saving results to CSV."""
        # Save results to CSV
        filepath = self.runner.save_results_csv()

        # Verify the file was created
        self.assertTrue(os.path.exists(filepath))

        # Verify the file contains data (we won't parse CSV here)
        with open(filepath) as f:
            content = f.read()

            # Verify headers
            self.assertIn("query_id", content)
            self.assertIn("ablated_collection", content)
            self.assertIn("precision", content)
            self.assertIn("recall", content)
            self.assertIn("f1_score", content)

            # Verify data
            self.assertIn(str(self.test_query_id), content)
            self.assertIn("TestCollection1_impact_on_TestCollection2", content)

    def test_generate_summary_report(self):
        """Test generation of summary report."""
        # Generate summary report
        filepath = self.runner.generate_summary_report()

        # Verify the file was created
        self.assertTrue(os.path.exists(filepath))

        # Verify the file contains the expected content
        with open(filepath) as f:
            content = f.read()

            # Verify sections
            self.assertIn("# Ablation Study Results Summary", content)
            self.assertIn("## Overview", content)
            self.assertIn("## Aggregate Metrics", content)
            self.assertIn("## Interpretation", content)
            self.assertIn("## Recommendations", content)

            # Verify data
            self.assertIn("TestCollection1", content)
            self.assertIn("TestCollection2", content)

    @patch("matplotlib.pyplot.savefig")
    @patch("matplotlib.pyplot.figure")
    @patch("pandas.DataFrame")
    def test_generate_visualizations(self, mock_df, mock_figure, mock_savefig):
        """Test generation of visualizations."""
        # Set up DataFrame mock
        mock_df_instance = MagicMock()
        mock_df.return_value = mock_df_instance

        # Mock groupby and pivot_table
        mock_grouped = MagicMock()
        mock_pivot = MagicMock()
        mock_df_instance.groupby.return_value = mock_grouped
        mock_df_instance.pivot_table.return_value = mock_pivot

        # Mock reset_index
        mock_reset = MagicMock()
        mock_grouped.mean.return_value.reset_index.return_value = mock_reset

        # Mock sort_values
        mock_reset.sort_values.return_value = mock_reset

        # Generate visualizations
        filepaths = self.runner.generate_visualizations()

        # Verify savefig was called for each visualization
        self.assertEqual(mock_savefig.call_count, 4)

        # Verify filepaths were returned
        self.assertEqual(len(filepaths), 4)

    def test_cleanup(self):
        """Test cleanup of resources."""
        # Run cleanup
        self.runner.cleanup()

        # Verify tester's cleanup was called
        self.mock_tester.cleanup.assert_called_once()


if __name__ == "__main__":
    unittest.main()
