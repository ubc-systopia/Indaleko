#!/usr/bin/env python3
"""
Script to run tests on generated data.

This script finds and runs tests based on a configuration file
and generated truth dataset.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add the project root to the Python path
current_path = Path(__file__).parent.resolve()
while not (current_path / "Indaleko.py").exists() and current_path != current_path.parent:
    current_path = current_path.parent
os.environ["INDALEKO_ROOT"] = str(current_path)
sys.path.insert(0, str(current_path))

from tools.data_generator_enhanced.testing.test_runner import ModelBasedTestRunner


def setup_logging():
    """Set up logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("test_runner.log")
        ]
    )


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run tests on generated data")

    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file",
        required=True
    )

    parser.add_argument(
        "--truth-data",
        type=str,
        help="Path to truth dataset file",
        required=True
    )

    parser.add_argument(
        "--report-path",
        type=str,
        help="Path to save test reports",
        default="./test_results"
    )

    parser.add_argument(
        "--report-format",
        type=str,
        choices=["json", "csv", "md", "html", "pdf"],
        help="Format for test reports",
        default="md"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    return parser.parse_args()


def load_json_file(file_path: Path):
    """Load a JSON file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Loaded JSON data
    """
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in file {file_path}: {e}")
        return None


def main():
    """Main function."""
    # Parse arguments
    args = parse_args()

    # Set up logging
    setup_logging()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logging.info("Starting test runner")

    # Load configuration
    config_path = Path(args.config)
    config = load_json_file(config_path)
    if not config:
        sys.exit(1)

    # Load truth dataset
    truth_path = Path(args.truth_data)
    truth_dataset = load_json_file(truth_path)
    if not truth_dataset:
        sys.exit(1)

    # Create report directory
    report_path = Path(args.report_path)
    os.makedirs(report_path, exist_ok=True)

    # Initialize test runner
    test_runner = ModelBasedTestRunner(config, truth_dataset)

    # Run tests
    logging.info("Running tests")
    results = test_runner.run_tests()

    # Save results
    logging.info("Saving results")
    test_runner.save_results(report_path / "test_results.json")

    # Generate report
    logging.info("Generating report")
    report_file = report_path / f"test_report.{args.report_format}"
    test_runner.generate_report(report_file, args.report_format)

    # Print summary
    summary = results.get("summary", {})
    if summary:
        logging.info("Test Results Summary:")
        logging.info(f"  Total Tests: {summary.get('total_tests', 0)}")
        logging.info(f"  Passed Tests: {summary.get('passed_tests', 0)}")
        logging.info(f"  Failed Tests: {summary.get('failed_tests', 0)}")
        logging.info(f"  Average Precision: {summary.get('avg_precision', 0)}%")
        logging.info(f"  Average Recall: {summary.get('avg_recall', 0)}%")
        logging.info(f"  Average F1 Score: {summary.get('avg_f1_score', 0)}%")

    logging.info(f"Test report saved to {report_file}")


if __name__ == "__main__":
    main()
