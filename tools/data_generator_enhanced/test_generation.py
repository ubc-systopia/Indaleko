#!/usr/bin/env python3
"""
Simple integration test for the enhanced data generator.

This script runs the data generator with the 'minimal' scenario 
in dry-run mode to test the full generation pipeline without 
making any database changes.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

# Make sure we can import from the project root
current_path = Path(__file__).parent.resolve()
while not (current_path / "Indaleko.py").exists() and current_path != current_path.parent:
    current_path = current_path.parent
sys.path.insert(0, str(current_path))

from tools.data_generator_enhanced.agents.data_gen.config.defaults import DEFAULT_CONFIG
from tools.data_generator_enhanced.agents.data_gen.core.controller import GenerationController


def run_minimal_test():
    """Run a minimal test of the data generator."""
    print("Running minimal test of the enhanced data generator...")
    
    # Create a test configuration based on defaults
    config = DEFAULT_CONFIG.copy()
    
    # Modify for test purposes
    config["execution"]["dry_run"] = True  # Don't write to database
    config["generation"]["direct_generation"] = True  # Skip LLM calls
    config["generation"]["storage_count"] = 5  # Minimal record count
    config["generation"]["semantic_count"] = 3
    config["generation"]["activity_count"] = 2
    config["generation"]["relationship_count"] = 5
    config["generation"]["machine_config_count"] = 1
    
    # Set OpenAI API key
    config["llm"] = config.get("llm", {})
    config["llm"]["provider"] = "mock"  # Use mock provider for testing
    
    # Set up mock OpenAI API key environment variable
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test_api_key"}):
        # Mock OpenAI client
        with patch('tools.data_generator_enhanced.agents.data_gen.core.llm.OpenAI'):
            try:
                # Initialize controller
                print("Initializing generation controller...")
                controller = GenerationController(config)
                
                # Generate dataset using the minimal scenario
                print("Generating dataset with 'minimal' scenario...")
                result = controller.generate_dataset(scenario="minimal")
        
                # Print results
                print("\nGeneration Results:")
                print(f"  Storage records: {result.get('storage_count', 0)}")
                print(f"  Semantic records: {result.get('semantic_count', 0)}")
                print(f"  Activity records: {result.get('activity_count', 0)}")
                print(f"  Relationship records: {result.get('relationship_count', 0)}")
                print(f"  Machine configurations: {result.get('machine_config_count', 0)}")
                
                # Generate truth dataset for testing
                print("\nGenerating truth dataset...")
                # Set truth query in config
                config["truth"] = config.get("truth", {})
                config["truth"]["query"] = "Find all documents I created last week"
                config["truth"]["count"] = 2
                config["truth"]["enabled"] = True
                
                truth_result = controller.generate_truth_dataset()
                
                print("\nTruth Dataset Results:")
                print(f"  Query: {truth_result.get('truth_query', 'N/A')}")
                print(f"  Records: {truth_result.get('truth_count', 0)}")
                
                print("\nTest completed successfully!")
                return 0
                
            except Exception as e:
                print(f"Error during test: {e}")
                import traceback
                traceback.print_exc()
                return 1


if __name__ == "__main__":
    sys.exit(run_minimal_test())