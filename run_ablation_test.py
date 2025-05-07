#!/usr/bin/env python3
"""
Ablation test runner for Indaleko project.

This script provides a simple interface to run the ablation testing framework
with various configuration options, including different testing modes.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import os
import sys
import logging
import argparse
import time
import datetime
import json
import random
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# Set up environment variables and paths
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import Indaleko modules
from db.db_config import IndalekoDBConfig
from tools.data_generator_enhanced.testing.ablation_integration_test import AblationIntegrationTest
from tools.data_generator_enhanced.testing.ablation_tester import AblationTester
from tools.data_generator_enhanced.testing.run_comprehensive_ablation import ComprehensiveAblationTest


def setup_logging(level=logging.INFO):
    """Set up logging configuration."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"ablation_test_{timestamp}.log"
    
    handlers = [
        logging.StreamHandler(),
        logging.FileHandler(log_file)
    ]
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers
    )
    
    logging.info(f"Logging initialized. Log file: {log_file}")


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run ablation tests for the Indaleko project",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument("--mode", type=str, default="integration",
                        choices=["integration", "comprehensive", "simple"],
                        help="Test mode to run")
    
    parser.add_argument("--reset-db", action="store_true",
                        help="Reset the database before running tests")
    
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility")
    
    parser.add_argument("--dataset-size", type=int, default=100,
                        help="Number of test data records to generate")
    
    parser.add_argument("--num-queries", type=int, default=10,
                        help="Number of test queries to generate")
    
    parser.add_argument("--output-dir", type=str, default="ablation_results",
                        help="Output directory for results")
    
    parser.add_argument("--use-llm", action="store_true",
                        help="Use LLM for query generation")
    
    parser.add_argument("--llm-provider", type=str, default="openai",
                        choices=["openai", "anthropic", "google"],
                        help="LLM provider for query generation")
    
    parser.add_argument("--skip-cleanup", action="store_true",
                        help="Skip cleanup after testing")
    
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")

    parser.add_argument("--num-clusters", type=int, default=3,
                        help="Number of test clusters to generate (comprehensive mode only)")
    
    parser.add_argument("--query", type=str,
                        help="Run a single query test (simple mode only)")
    
    parser.add_argument("--collection", type=str, nargs="+",
                        help="Collections to ablate (simple mode only)")
    
    return parser.parse_args()


def run_integration_test(args):
    """Run the integration ablation test."""
    logging.info("Running integration ablation test...")
    
    # Set up configuration
    config = {
        "seed": args.seed,
        "dataset_size": args.dataset_size,
        "num_queries": args.num_queries,
        "output_dir": args.output_dir,
        "truncate_collections": args.reset_db,
        "use_llm": args.use_llm,
        "llm_provider": args.llm_provider,
        "study_name": f"Ablation Study {datetime.datetime.now().strftime('%Y-%m-%d')}",
        "study_description": "Automated ablation test for activity metadata"
    }
    
    # Create and run the test
    test = AblationIntegrationTest(config)
    results = test.run_test()
    
    # Display results
    if results["success"]:
        logging.info("Integration ablation test completed successfully!")
    else:
        logging.error("Integration ablation test completed with errors:")
        for error in results.get("errors", []):
            logging.error(f"- {error}")
    
    logging.info(f"Results saved to directory: {args.output_dir}")
    return results["success"]


def run_comprehensive_test(args):
    """Run the comprehensive ablation test."""
    logging.info("Running comprehensive ablation test...")
    
    # Set up configuration
    config = {
        "dataset_size": args.dataset_size,
        "output_dir": args.output_dir,
        "skip_cleanup": args.skip_cleanup,
        "seed": args.seed
    }
    
    # Create and run the test
    test = ComprehensiveAblationTest(config)
    results = test.run()
    
    # Check results
    success = True
    if not results or "collection_impact" not in results:
        logging.error("Comprehensive ablation test failed")
        success = False
    else:
        logging.info("Comprehensive ablation test completed successfully!")
        
        # Print a summary of the results
        if "collection_impact" in results:
            logging.info("\nCollection Impact Summary:")
            for collection, metrics in results["collection_impact"].items():
                logging.info(f"- {collection}:")
                logging.info(f"  Precision: {metrics.get('precision', 0):.4f}")
                logging.info(f"  Recall: {metrics.get('recall', 0):.4f}")
                logging.info(f"  F1 Score: {metrics.get('f1', 0):.4f}")
                logging.info(f"  Impact: {metrics.get('impact', 0):.4f}")
    
    logging.info(f"Results saved to directory: {args.output_dir}")
    return success


def run_simple_test(args):
    """Run a simple ablation test with a single query."""
    logging.info("Running simple ablation test...")
    
    # Check if we have the necessary arguments
    if not args.query:
        logging.error("Query is required for simple mode")
        return False
    
    # Set up the ablation tester
    tester = AblationTester()
    
    # Use provided collections, or default to a basic set
    collections_to_ablate = args.collection if args.collection else [
        "ActivityContext", "MusicActivityData", "GeoActivityData"
    ]
    
    # Run the test
    logging.info(f"Testing query: {args.query}")
    logging.info(f"Ablating collections: {', '.join(collections_to_ablate)}")
    
    result = tester.test_collection_ablation(
        query=args.query,
        collections_to_ablate=collections_to_ablate
    )
    
    # Save the result
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(args.output_dir, f"simple_ablation_{timestamp}.json")
    os.makedirs(args.output_dir, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    # Print a summary of the results
    logging.info("\nAblation Test Summary:")
    logging.info(f"Query: {result['query']}")
    logging.info(f"Ablated collections: {result['ablated_collections']}")
    logging.info("\nBaseline results:")
    logging.info(f"  Count: {result['baseline']['result_count']}")
    logging.info(f"  Time: {result['baseline']['execution_time']:.4f}s")
    
    logging.info("\nAblated results:")
    logging.info(f"  Count: {result['ablated']['result_count']}")
    logging.info(f"  Time: {result['ablated']['execution_time']:.4f}s")
    
    logging.info("\nMetrics:")
    metrics = result['metrics']
    logging.info(f"  Precision: {metrics['precision']:.4f}")
    logging.info(f"  Recall: {metrics['recall']:.4f}")
    logging.info(f"  F1 Score: {metrics['f1']:.4f}")
    logging.info(f"  True positives: {metrics['true_positives']}")
    logging.info(f"  False positives: {metrics['false_positives']}")
    logging.info(f"  False negatives: {metrics['false_negatives']}")
    
    logging.info(f"\nResults saved to: {output_file}")
    return True


def reset_database():
    """Reset the database to a clean state."""
    logging.info("Resetting database...")
    
    try:
        # Create a DB config instance first
        db_config = IndalekoDBConfig()
        # Then call start() with reset=True
        db_config.start(reset=True)
        logging.info("Database reset successful")
        return True
    except Exception as e:
        logging.error(f"Error resetting database: {e}")
        return False


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()
    
    # Set up logging
    setup_logging(level=logging.DEBUG if args.debug else logging.INFO)
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Reset database if requested
    if args.reset_db:
        if not reset_database():
            logging.error("Database reset failed. Aborting test.")
            return 1
    
    # Set random seed
    random.seed(args.seed)
    logging.info(f"Random seed set to {args.seed}")
    
    # Run the selected test mode
    start_time = time.time()
    
    success = False
    if args.mode == "integration":
        success = run_integration_test(args)
    elif args.mode == "comprehensive":
        success = run_comprehensive_test(args)
    elif args.mode == "simple":
        success = run_simple_test(args)
    
    # Print execution time
    execution_time = time.time() - start_time
    logging.info(f"Test execution completed in {execution_time:.2f} seconds")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())