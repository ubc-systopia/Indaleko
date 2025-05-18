"""Simple tests for the AblationTestRunner."""

import os
import sys
import tempfile
import unittest
import uuid
from unittest.mock import MagicMock, patch

# Add project root to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

# Mock dependencies before importing
sys.modules["seaborn"] = MagicMock()
sys.modules["pandas"] = MagicMock()
sys.modules["matplotlib"] = MagicMock()
sys.modules["matplotlib.pyplot"] = MagicMock()

from research.ablation.ablation_test_runner import AblationTestRunner
from research.ablation.ablation_tester import AblationConfig
from research.ablation.base import AblationResult


class TestSimpleAblationTestRunner(unittest.TestCase):
    """Simple test cases for the AblationTestRunner class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test outputs
        self.temp_dir = tempfile.mkdtemp()

        # Create a mock AblationTester
        self.mock_tester = MagicMock()

        # Patch AblationTester
        self.patcher = patch("research.ablation.ablation_test_runner.AblationTester", return_value=self.mock_tester)
        self.mock_tester_class = self.patcher.start()

        # Create a runner
        self.runner = AblationTestRunner(output_dir=self.temp_dir)

    def tearDown(self):
        """Clean up after tests."""
        self.patcher.stop()

        # Clean up the temporary directory
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_init(self):
        """Test initialization."""
        self.assertIsNotNone(self.runner)
        self.assertEqual(self.runner.output_dir, self.temp_dir)
        self.assertEqual(self.runner.tester, self.mock_tester)
        self.assertEqual(self.runner.results, {})

        # Verify the output directory was created
        self.assertTrue(os.path.exists(self.temp_dir))

    def test_run_single_test(self):
        """Test running a single ablation test."""
        # Create a mock result
        query_id = uuid.uuid4()
        test_results = {
            "test_collection": AblationResult(
                query_id=query_id,
                ablated_collection="test_collection",
                precision=0.8,
                recall=0.7,
                f1_score=0.75,
                execution_time_ms=100,
                result_count=10,
                true_positives=8,
                false_positives=2,
                false_negatives=3,
            ),
        }

        # Mock the run_ablation_test method
        self.mock_tester.run_ablation_test.return_value = test_results

        # Run a single test
        config = AblationConfig(collections_to_ablate=["test_collection"])
        results = self.runner.run_single_test(query_id, "test query", config)

        # Verify the results
        self.assertEqual(results, test_results)
        self.assertEqual(self.runner.results[str(query_id)], test_results)

        # Verify the tester's run_ablation_test was called
        self.mock_tester.run_ablation_test.assert_called_with(config, query_id, "test query")


if __name__ == "__main__":
    unittest.main()
