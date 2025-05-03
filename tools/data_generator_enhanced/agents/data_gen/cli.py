#!/usr/bin/env python3
"""
Command-line interface for the enhanced data generator.
"""

import argparse
import json
import logging
import os
import sys
import time
from typing import Any, Dict, Optional

from data_gen.core.controller import GenerationController
from data_gen.config.defaults import DEFAULT_CONFIG
from data_gen.config.scenarios import SCENARIOS
from data_gen.utils.logger import setup_logging


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Indaleko Enhanced Data Generator")
    
    # Basic options
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--scenario", help="Scenario to generate data for", default="basic")
    parser.add_argument("--output", help="Output path for generation report", 
                        default="./generation_report.json")
    
    # Generation options
    parser.add_argument("--storage-count", type=int, help="Number of storage records to generate")
    parser.add_argument("--semantic-count", type=int, help="Number of semantic records to generate")
    parser.add_argument("--activity-count", type=int, help="Number of activity records to generate")
    parser.add_argument("--relationship-count", type=int, help="Number of relationship records to generate")
    parser.add_argument("--machine-count", type=int, help="Number of machine configurations to generate")
    
    # Truth dataset options
    parser.add_argument("--truth-only", action="store_true", help="Generate only truth records")
    parser.add_argument("--truth-query", help="Natural language query for truth data generation")
    parser.add_argument("--truth-count", type=int, default=10, 
                        help="Number of truth records to generate")
    
    # LLM options
    parser.add_argument("--llm-provider", choices=["openai", "anthropic", "mock"], 
                        default="openai", help="LLM provider to use")
    parser.add_argument("--direct-generation", action="store_true", 
                        help="Use direct generation instead of LLM")
    
    # Execution options
    parser.add_argument("--dry-run", action="store_true", 
                        help="Simulate generation without database writes")
    parser.add_argument("--verbose", "-v", action="count", default=0, 
                        help="Increase verbosity level")
    parser.add_argument("--list-scenarios", action="store_true", 
                        help="List available generation scenarios")
    
    return parser.parse_args()


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from file or use defaults."""
    config = DEFAULT_CONFIG.copy()
    
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                config.update(user_config)
        except Exception as e:
            logging.error(f"Error loading config file {config_path}: {e}")
            print(f"Error: Failed to load configuration from {config_path}")
            sys.exit(1)
    
    return config


def list_scenarios():
    """Print available scenarios."""
    print("Available generation scenarios:")
    print("-" * 30)
    
    for name, details in SCENARIOS.items():
        print(f"{name}:")
        print(f"  Description: {details.get('description', 'No description')}")
        print(f"  Storage count: {details.get('storage_count', 'default')}")
        print(f"  Semantic count: {details.get('semantic_count', 'default')}")
        print(f"  Activity count: {details.get('activity_count', 'default')}")
        print(f"  Relationship count: {details.get('relationship_count', 'default')}")
        print(f"  Machine configurations: {details.get('machine_config_count', 'default')}")
        print()


def setup_controller(args, config: Dict[str, Any]) -> GenerationController:
    """Set up the generation controller with command line arguments and config."""
    # Override config with command line arguments
    if args.storage_count:
        config["generation"]["storage_count"] = args.storage_count
    if args.semantic_count:
        config["generation"]["semantic_count"] = args.semantic_count
    if args.activity_count:
        config["generation"]["activity_count"] = args.activity_count
    if args.relationship_count:
        config["generation"]["relationship_count"] = args.relationship_count
    if args.machine_count:
        config["generation"]["machine_config_count"] = args.machine_count
    
    # Set LLM provider
    config["llm"]["provider"] = args.llm_provider
    config["generation"]["direct_generation"] = args.direct_generation
    
    # Configure truth dataset generation
    if args.truth_only or args.truth_query:
        config["truth"]["enabled"] = True
        if args.truth_query:
            config["truth"]["query"] = args.truth_query
        if args.truth_count:
            config["truth"]["count"] = args.truth_count
    
    # Set dry run mode
    config["execution"]["dry_run"] = args.dry_run
    
    # Create controller
    return GenerationController(config)


def save_report(report: Dict[str, Any], output_path: str) -> None:
    """Save generation report to a file."""
    try:
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Generation report saved to {output_path}")
    except Exception as e:
        logging.error(f"Error saving report to {output_path}: {e}")
        print(f"Error: Failed to save report to {output_path}")


def main():
    """Main entry point for the CLI."""
    args = parse_args()
    
    # Set up logging
    log_level = logging.WARNING
    if args.verbose == 1:
        log_level = logging.INFO
    elif args.verbose >= 2:
        log_level = logging.DEBUG
    
    setup_logging(log_level)
    logger = logging.getLogger(__name__)
    
    # Handle list scenarios command
    if args.list_scenarios:
        list_scenarios()
        return 0
    
    # Load configuration
    config = load_config(args.config)
    logger.info("Configuration loaded")
    
    # Set up controller
    try:
        controller = setup_controller(args, config)
        logger.info("Generation controller initialized")
    except Exception as e:
        logger.error(f"Failed to initialize controller: {e}")
        print(f"Error: {e}")
        return 1
    
    # Run generation
    try:
        print(f"Starting data generation for scenario: {args.scenario}")
        start_time = time.time()
        
        if args.truth_only:
            print(f"Generating {args.truth_count} truth records for query: {config['truth']['query']}")
            result = controller.generate_truth_dataset(
                query=config['truth']['query'],
                count=config['truth']['count']
            )
        else:
            print(f"Generating dataset using scenario: {args.scenario}")
            result = controller.generate_dataset(scenario=args.scenario)
        
        elapsed = time.time() - start_time
        print(f"Generation completed in {elapsed:.2f} seconds")
        
        # Summarize results
        print("\nGeneration Summary:")
        print(f"  Storage records: {result.get('storage_count', 0)}")
        print(f"  Semantic records: {result.get('semantic_count', 0)}")
        print(f"  Activity records: {result.get('activity_count', 0)}")
        print(f"  Relationship records: {result.get('relationship_count', 0)}")
        print(f"  Machine configurations: {result.get('machine_config_count', 0)}")
        
        if result.get('truth_generated'):
            print(f"\nTruth Dataset:")
            print(f"  Query: {result.get('truth_query', 'N/A')}")
            print(f"  Records: {result.get('truth_count', 0)}")
        
        # Save report
        save_report(result, args.output)
        
        return 0
        
    except KeyboardInterrupt:
        print("\nGeneration interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        print(f"Error: Generation failed - {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())