#!/usr/bin/env python3
"""
Wrapper script for running the ablation integration test.

This script provides a convenient entry point for executing the ablation integration
test with default settings or command-line arguments.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import os
import sys
import time
import logging
import datetime
import argparse
from pathlib import Path

# Add the Indaleko root to the path
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import the test module
from tools.data_generator_enhanced.testing.ablation_integration_test import AblationIntegrationTest, setup_logging


def parse_args():
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Run ablation integration test")
    
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--dataset-size", type=int, default=100,
                        help="Number of test data records to generate (default: 100)")
    parser.add_argument("--num-queries", type=int, default=10,
                        help="Number of test queries to generate (default: 10)")
    parser.add_argument("--output-dir", type=str, default="ablation_results",
                        help="Output directory for results (default: ablation_results)")
    parser.add_argument("--truncate-collections", action="store_true",
                        help="Truncate collections before running the test")
    parser.add_argument("--use-llm", action="store_true",
                        help="Use LLM for query generation")
    parser.add_argument("--llm-provider", type=str, default="openai",
                        choices=["openai", "anthropic"],
                        help="LLM provider for query generation (default: openai)")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    
    return parser.parse_args()


def main():
    """Main entry point."""
    start_time = time.time()
    
    # Parse arguments
    args = parse_args()
    
    # Set up logging
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(args.output_dir, exist_ok=True)
    log_file = os.path.join(args.output_dir, f"ablation_test_{timestamp}.log")
    
    setup_logging(
        level=logging.DEBUG if args.debug else logging.INFO,
        log_file=log_file
    )
    
    # Configure the test
    config = {
        "seed": args.seed,
        "dataset_size": args.dataset_size,
        "num_queries": args.num_queries,
        "output_dir": args.output_dir,
        "truncate_collections": args.truncate_collections,
        "use_llm": args.use_llm,
        "llm_provider": args.llm_provider,
        "study_name": f"Ablation Study {timestamp}",
        "study_description": "Automated ablation test for activity metadata"
    }
    
    # Display test configuration
    print("=" * 80)
    print(f"Indaleko Ablation Integration Test - {timestamp}")
    print("=" * 80)
    print(f"Seed:           {config['seed']}")
    print(f"Dataset size:   {config['dataset_size']}")
    print(f"Queries:        {config['num_queries']}")
    print(f"Output dir:     {config['output_dir']}")
    print(f"Truncate DB:    {config['truncate_collections']}")
    print(f"Use LLM:        {config['use_llm']}")
    if config['use_llm']:
        print(f"LLM Provider:   {config['llm_provider']}")
    print("=" * 80)
    
    # Create and run the test
    test = AblationIntegrationTest(config)
    results = test.run_test()
    
    # Calculate execution time
    execution_time = time.time() - start_time
    
    # Display results
    print("\n" + "=" * 80)
    print(f"Test Execution Complete - {execution_time:.2f} seconds")
    print("=" * 80)
    
    if results["success"]:
        print("Status: SUCCESS")
    else:
        print("Status: FAILED")
        for error in results["errors"]:
            print(f"- {error}")
    
    print(f"\nResults saved to: {os.path.abspath(args.output_dir)}")
    print("=" * 80)
    
    # Return exit code
    return 0 if results["success"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)