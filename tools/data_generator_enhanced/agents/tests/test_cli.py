#!/usr/bin/env python3
"""
Integration tests for the CLI interface.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from io import StringIO
from pathlib import Path

# Bootstrap project root so imports work
current_path = Path(__file__).parent.resolve()
while not (current_path / "Indaleko.py").exists() and current_path != current_path.parent:
    current_path = current_path.parent
sys.path.insert(0, str(current_path))

from tools.data_generator_enhanced.agents.handler_mixin import DataGeneratorHandlerMixin


class TestCLI(unittest.TestCase):
    """Test case for the CLI interface."""

    def setUp(self):
        """Set up test fixtures."""
        # Create patches for functions the tests will need
        self.controller_patch = patch('tools.data_generator_enhanced.agents.data_gen.core.controller.GenerationController')
        self.mock_controller_class = self.controller_patch.start()

        # Set up the mock controller instance
        self.mock_controller = MagicMock()
        self.mock_controller.generate_dataset.return_value = {
            "storage_count": 10,
            "semantic_count": 8,
            "activity_count": 5,
            "relationship_count": 15,
            "machine_config_count": 2,
            "truth_generated": False
        }
        self.mock_controller.generate_truth_dataset.return_value = {
            "storage_count": 5,
            "semantic_count": 5,
            "activity_count": 0,
            "relationship_count": 5,
            "machine_config_count": 1,
            "truth_generated": True,
            "truth_query": "test query",
            "truth_count": 5
        }
        self.mock_controller_class.return_value = self.mock_controller

        # Mock out the actual running of the controller for testing
        self.run_patch = patch.object(DataGeneratorHandlerMixin, '_setup_controller')
        self.mock_run = self.run_patch.start()
        self.mock_run.return_value = self.mock_controller

        # Mock out file operations
        self.open_patch = patch('builtins.open', create=True)
        self.mock_open = self.open_patch.start()
        self.mock_open.return_value = MagicMock()

        # Create a mock config
        self.test_config = {
            "database": {"url": "http://localhost:8529"},
            "generation": {
                "storage_count": 10,
                "semantic_count": 8,
                "activity_count": 5,
                "relationship_count": 15,
                "machine_config_count": 2,
                "direct_generation": False
            },
            "truth": {
                "enabled": False,
                "query": "test query",
                "count": 5
            },
            "execution": {
                "dry_run": False
            },
            "llm": {
                "provider": "mock"
            }
        }

    def tearDown(self):
        """Tear down test fixtures."""
        self.controller_patch.stop()
        self.run_patch.stop()
        self.open_patch.stop()

    def test_cli_parameters(self):
        """Test CLI parameter parsing."""
        # Create a simple argparse namespace with test parameters
        test_args = MagicMock()
        test_args.scenario = "basic"
        test_args.storage_count = 20
        test_args.semantic_count = 15
        test_args.llm_provider = "mock"
        test_args.direct_generation = True
        test_args.truth_only = False
        test_args.dry_run = True

        # Create kwargs for the run method
        kwargs = {
            "args": test_args,
            "config": self.test_config,
            "modules_loaded": True
        }

        # Run the handler
        DataGeneratorHandlerMixin.run(kwargs)

        # Check that the controller was set up with the correct parameters
        self.mock_run.assert_called_once()
        controller_args = self.mock_run.call_args[0][0]
        controller_config = self.mock_run.call_args[0][1]

        self.assertEqual(controller_args.scenario, "basic")
        self.assertEqual(controller_args.storage_count, 20)
        self.assertEqual(controller_args.semantic_count, 15)
        self.assertEqual(controller_args.llm_provider, "mock")
        self.assertTrue(controller_args.direct_generation)
        self.assertTrue(controller_args.dry_run)

    def test_truth_dataset_generation(self):
        """Test truth dataset generation mode."""
        # Create args for truth dataset generation
        test_args = MagicMock()
        test_args.scenario = "basic"
        test_args.truth_only = True
        test_args.truth_query = "Find important documents"
        test_args.truth_count = 10
        test_args.output = "test_report.json"

        # Create kwargs for the run method
        kwargs = {
            "args": test_args,
            "config": self.test_config,
            "modules_loaded": True
        }

        # Set up config with truth settings
        kwargs["config"]["truth"] = {
            "enabled": True,
            "query": test_args.truth_query,
            "count": test_args.truth_count
        }

        # Run with captured stdout to check output
        with patch('sys.stdout', new=StringIO()) as mock_stdout:
            DataGeneratorHandlerMixin.run(kwargs)
            output = mock_stdout.getvalue()

        # Check that truth dataset generation was called
        self.mock_controller.generate_truth_dataset.assert_called_once()
        
        # Check that the output contains expected text
        self.assertIn("Truth Dataset", output)
        self.assertIn("test query", output)  # Mock controller returns this

    def test_dry_run_mode(self):
        """Test dry run mode."""
        # Create args for dry run mode
        test_args = MagicMock()
        test_args.scenario = "minimal"
        test_args.dry_run = True
        test_args.truth_only = False
        test_args.output = "test_report.json"

        # Create kwargs for the run method
        kwargs = {
            "args": test_args,
            "config": self.test_config,
            "modules_loaded": True
        }

        # Run the handler
        DataGeneratorHandlerMixin.run(kwargs)

        # Set up mock controller
        self.mock_run.assert_called_once()
        
        # Check that dataset generation was called
        self.mock_controller.generate_dataset.assert_called_once_with(scenario="minimal")

    def test_save_report(self):
        """Test saving report to a file."""
        # Create test report
        test_report = {
            "storage_count": 10,
            "semantic_count": 8,
            "activity_count": 5,
            "relationship_count": 15,
            "machine_config_count": 2
        }
        
        output_path = "test_report.json"
        
        # Call save_report
        DataGeneratorHandlerMixin._save_report(test_report, output_path)
        
        # Check that open was called with correct parameters
        self.mock_open.assert_called_once_with(output_path, 'w')
        
        # Check that json.dump was called on the file handle
        file_handle = self.mock_open.return_value.__enter__.return_value
        file_handle.write.assert_called()


if __name__ == '__main__':
    unittest.main()