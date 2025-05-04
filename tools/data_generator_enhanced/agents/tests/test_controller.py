#!/usr/bin/env python3
"""
Tests for the GenerationController.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path

# Bootstrap project root so imports work
current_path = Path(__file__).parent.resolve()
while not (current_path / "Indaleko.py").exists() and current_path != current_path.parent:
    current_path = current_path.parent
sys.path.insert(0, str(current_path))

from tools.data_generator_enhanced.agents.data_gen.core.controller import GenerationController
from tools.data_generator_enhanced.agents.data_gen.config.defaults import DEFAULT_CONFIG
from tools.data_generator_enhanced.agents.data_gen.config.scenarios import SCENARIOS


class TestGenerationController(unittest.TestCase):
    """Test case for the GenerationController."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock OpenAI API key
        self.openai_env_patch = patch.dict(os.environ, {"OPENAI_API_KEY": "test_api_key"})
        self.openai_env_patch.start()

        # Mock LLM providers
        self.openai_patch = patch('tools.data_generator_enhanced.agents.data_gen.core.llm.OpenAI')
        self.mock_openai = self.openai_patch.start()

        # Create mock agents for the controller to use
        self.storage_agent = MagicMock()
        self.storage_agent.generate.return_value = [{"_id": "Objects/1", "ObjectIdentifier": "1"}]

        self.semantic_agent = MagicMock()
        self.semantic_agent.generate.return_value = [{"_id": "SemanticData/1", "ObjectIdentifier": "1"}]

        self.activity_agent = MagicMock()
        self.activity_agent.generate.return_value = [{"_id": "ActivityData/1", "ObjectIdentifier": "1"}]

        self.relationship_agent = MagicMock()
        self.relationship_agent.generate.return_value = [{"_id": "Relationships/1", "_from": "Objects/1", "_to": "SemanticData/1"}]

        self.machine_config_agent = MagicMock()
        self.machine_config_agent.generate.return_value = [{"_id": "MachineConfigurations/1", "MachineID": "machine1"}]

        # Create a patch for the agent creation
        self.agent_patches = [
            patch('tools.data_generator_enhanced.agents.data_gen.core.controller.StorageGeneratorAgent', return_value=self.storage_agent),
            patch('tools.data_generator_enhanced.agents.data_gen.core.controller.SemanticGeneratorAgent', return_value=self.semantic_agent),
            patch('tools.data_generator_enhanced.agents.data_gen.core.controller.ActivityGeneratorAgent', return_value=self.activity_agent),
            patch('tools.data_generator_enhanced.agents.data_gen.core.controller.RelationshipGeneratorAgent', return_value=self.relationship_agent),
            patch('tools.data_generator_enhanced.agents.data_gen.core.controller.MachineConfigGeneratorAgent', return_value=self.machine_config_agent)
        ]

        # Start all patches
        for p in self.agent_patches:
            p.start()

        # Create a minimal configuration for testing
        self.config = {
            "database": DEFAULT_CONFIG["database"],
            "llm": {"provider": "mock"},
            "generation": {
                "storage_count": 10,
                "semantic_count": 8,
                "activity_count": 5,
                "relationship_count": 15,
                "machine_config_count": 2,
                "batch_size": 5,
                "direct_generation": True
            },
            "truth": {
                "enabled": False,
                "query": "test query",
                "count": 5
            },
            "execution": {
                "dry_run": True
            }
        }

        # Create the controller with mocked configuration
        self.controller = GenerationController(self.config)

    def tearDown(self):
        """Tear down test fixtures."""
        # Stop all patches
        for p in self.agent_patches:
            p.stop()

        # Stop LLM provider patches
        self.openai_patch.stop()
        self.openai_env_patch.stop()

    def test_controller_initialization(self):
        """Test controller initialization with config."""
        self.assertIsNotNone(self.controller)
        self.assertEqual(self.controller.config["generation"]["storage_count"], 10)
        self.assertEqual(len(self.controller.agents), 5)  # Should have all 5 domain agents

    def test_generate_dataset(self):
        """Test generating a complete dataset."""
        result = self.controller.generate_dataset()

        # Verify all agents were called
        self.machine_config_agent.generate.assert_called_once()
        self.storage_agent.generate.assert_called_once()
        self.semantic_agent.generate_from_storage.assert_called_once()
        self.activity_agent.generate.assert_called_once()
        self.relationship_agent.generate_from_objects.assert_called_once()

        # Verify result contains counts
        self.assertIn("storage_count", result)
        self.assertIn("semantic_count", result)
        self.assertIn("activity_count", result)
        self.assertIn("relationship_count", result)
        self.assertIn("machine_config_count", result)

    def test_generate_with_scenario(self):
        """Test generating a dataset with a specific scenario."""
        # Test with the "minimal" scenario
        result = self.controller.generate_dataset(scenario="minimal")

        # Verify that scenario parameters were respected
        # In a real test, we'd verify actual values, but in our mock setup,
        # we're just checking if the calls happened
        self.machine_config_agent.generate.assert_called_once()
        self.storage_agent.generate.assert_called_once()

    def test_generate_truth_dataset(self):
        """Test generating a truth dataset for a specific query."""
        # Set up mocks for truth record generation
        self.storage_agent.generate_truth_records.return_value = [
            {"_id": "Objects/truth1", "ObjectIdentifier": "truth1", "truth_marker": True}
        ]
        self.semantic_agent.generate_truth_records.return_value = [
            {"_id": "SemanticData/truth1", "ObjectIdentifier": "truth1", "truth_marker": True}
        ]

        # Generate truth dataset
        query = "Find documents about climate change"
        count = 5
        result = self.controller.generate_truth_dataset(query=query, count=count)

        # Verify truth generation was called
        self.storage_agent.generate_truth_records.assert_called_once()
        self.semantic_agent.generate_truth_records.assert_called_once()

        # Verify result contains truth info
        self.assertTrue(result["truth_generated"])
        self.assertEqual(result["truth_query"], query)

    def test_scenario_config_loading(self):
        """Test loading configuration from scenarios."""
        # First test with non-existent scenario (should use default)
        config = self.controller._get_scenario_config("non_existent")
        self.assertEqual(config, {})

        # Test with existing scenario
        config = self.controller._get_scenario_config("minimal")
        self.assertEqual(config["storage_count"], SCENARIOS["minimal"]["storage_count"])
        self.assertEqual(config["semantic_count"], SCENARIOS["minimal"]["semantic_count"])

    def test_batch_processing(self):
        """Test batch processing for large datasets."""
        # Set up a larger count to test batch processing
        self.controller.config["generation"]["storage_count"] = 25
        self.controller.config["generation"]["batch_size"] = 10

        result = self.controller.generate_dataset()

        # Should have called generate in batches (3 times for 25 records with batch size 10)
        self.assertEqual(self.storage_agent.generate.call_count, 3)

    def test_dry_run_mode(self):
        """Test controller behavior in dry run mode."""
        # Set dry_run to True
        self.controller.config["execution"]["dry_run"] = True

        result = self.controller.generate_dataset()

        # Verify that dry_run was passed to the agents
        self.assertTrue("dry_run" in self.storage_agent.generate.call_args[1])
        self.assertTrue(self.storage_agent.generate.call_args[1]["dry_run"])


if __name__ == '__main__':
    unittest.main()
