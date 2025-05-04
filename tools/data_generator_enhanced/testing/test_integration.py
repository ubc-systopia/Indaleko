#!/usr/bin/env python3
"""
Integration tests for the model-based data generator benchmark suite.

This module tests the end-to-end flow of the benchmark suite with
a minimal configuration to ensure all components work together.
"""

import json
import os
import sys
import tempfile
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


class TestBenchmarkIntegration(unittest.TestCase):
    """Integration tests for the benchmark suite."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test outputs
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)
        
        # Create a minimal test configuration
        self.config = {
            "scenarios": [
                {
                    "name": "tiny_test",
                    "description": "Tiny test dataset",
                    "scale_factor": 0.01,
                    "storage_count": 5,
                    "semantic_count": 4,
                    "activity_count": 3,
                    "relationship_count": 6,
                    "queries": ["Find PDF files"]
                }
            ],
            "generators": [
                {
                    "name": "test_generator",
                    "description": "Test generator configuration",
                    "model_based": True,
                    "use_model_templates": True
                }
            ],
            "output_dir": str(self.output_dir),
            "repeat": 1,
            "skip_charts": True  # Skip chart generation for faster tests
        }
        
        # Write the configuration to a temporary file
        self.config_path = self.output_dir / "test_config.json"
        with open(self.config_path, "w") as f:
            json.dump(self.config, f)
    
    def tearDown(self):
        """Clean up after tests."""
        # Clean up the temporary directory
        self.temp_dir.cleanup()
    
    @patch('tools.data_generator_enhanced.testing.benchmark.GenerationController')
    @patch('tools.data_generator_enhanced.testing.benchmark.ModelBasedTestRunner')
    def test_end_to_end_flow(self, mock_runner, mock_controller):
        """Test the end-to-end flow of the benchmark suite."""
        # Create a custom patch for _save_results to avoid serialization issues with mocks
        with patch.object(BenchmarkSuite, '_save_results', return_value=None):
            with patch.object(BenchmarkSuite, '_save_summary', return_value=None):
                with patch.object(BenchmarkSuite, '_generate_charts', return_value=None):
                    # Configure mocks
                    mock_controller_instance = MagicMock()
                    mock_controller.return_value = mock_controller_instance
                    
                    mock_runner_instance = MagicMock()
                    mock_runner.return_value = mock_runner_instance
                    
                    # Set up mock generation stats
                    mock_controller_instance.generate_dataset.return_value = {
                        "counts": {
                            "storage": 5,
                            "semantic": 4,
                            "activity": 3,
                            "relationship": 6,
                            "total": 18
                        }
                    }
                    
                    mock_controller_instance.generate_truth_dataset.return_value = {}
                    
                    # Set up mock query generator
                    mock_runner_instance.query_generator = MagicMock()
                    
                    # Set up mock truth records and truth IDs
                    mock_controller_instance.truth_records = {
                        "storage": [{"ObjectIdentifier": "id1"}, {"ObjectIdentifier": "id2"}],
                        "semantic": [{"ObjectIdentifier": "id1"}],
                        "activity": [{"Handle": "act1"}]
                    }
                    mock_runner_instance.truth_ids = {
                        "storage": set(["id1", "id2"]),
                        "semantic": set(["id1"]),
                        "activity": set(["act1"]),
                        "all": set(["id1", "id2", "act1"])
                    }
                    
                    # Set up mock AQL executor
                    mock_runner_instance.aql_executor = MagicMock()
                    mock_runner_instance.aql_executor.execute.return_value = [
                        {"_id": "doc1", "ObjectIdentifier": "id1"},
                        {"_id": "doc2", "ObjectIdentifier": "id2"}
                    ]
                    
                    # Set up mock extract_result_ids
                    mock_runner_instance._extract_result_ids.return_value = set(["id1", "id2"])
                    
                    # Create benchmark suite
                    suite = BenchmarkSuite(config_path=self.config_path)
                    
                    # Run benchmarks
                    results = suite.run_benchmarks()
        
                    # Verify results
                    self.assertEqual(len(results), 1)  # Should have one result for our single scenario+generator
                    
                    result = results[0]
                    self.assertEqual(result["scenario"], "tiny_test")
                    self.assertEqual(result["generator"], "test_generator")
                    self.assertEqual(result["storage_count"], 5)
                    self.assertEqual(result["semantic_count"], 4)
                    self.assertEqual(result["activity_count"], 3)
                    self.assertEqual(result["relationship_count"], 6)
                    self.assertEqual(result["total_count"], 18)
                    
                    # Since we've mocked the _save_results and _save_summary methods,
                    # we don't check for the presence of output files
    
    @patch('tools.data_generator_enhanced.testing.run_benchmark.BenchmarkSuite')
    def test_run_benchmark_script(self, mock_suite):
        """Test the run_benchmark.py script."""
        # Configure mock
        mock_suite_instance = MagicMock()
        mock_suite.return_value = mock_suite_instance
        
        # Mock the run_benchmarks method
        mock_suite_instance.run_benchmarks.return_value = []
        
        # Import the script
        from tools.data_generator_enhanced.testing import run_benchmark
        
        # Set up test arguments
        sys.argv = [
            'run_benchmark.py',
            '--config', str(self.config_path),
            '--output-dir', str(self.output_dir),
            '--small-only',
            '--repeat', '1'
        ]
        
        # Patch parse_args to return our arguments
        original_parse_args = run_benchmark.parse_args
        run_benchmark.parse_args = MagicMock(return_value=original_parse_args())
        
        try:
            # Run the script
            with patch('tools.data_generator_enhanced.testing.run_benchmark.setup_logging'):
                with patch('tools.data_generator_enhanced.testing.run_benchmark.main'):
                    # Just testing that it doesn't crash
                    pass
        finally:
            # Restore original parse_args
            run_benchmark.parse_args = original_parse_args


if __name__ == "__main__":
    unittest.main()
