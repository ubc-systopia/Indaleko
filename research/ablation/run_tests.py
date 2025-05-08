#!/usr/bin/env python3
"""Test runner for ablation framework tests."""

import argparse
import logging
import os
import sys
import unittest

# Add parent directory to path to resolve relative imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def setup_logging():
    """Set up logging for tests."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def discover_and_run_tests(test_path="tests", pattern="test_*.py", verbosity=2):
    """Discover and run all tests matching the pattern.

    Args:
        test_path: Directory containing tests.
        pattern: Pattern to match test files.
        verbosity: Verbosity level (1-3).

    Returns:
        bool: True if all tests passed, False otherwise.
    """
    # Get the absolute path to the tests directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_dir = os.path.join(current_dir, test_path)

    # Discover tests
    loader = unittest.TestLoader()
    test_suite = loader.discover(start_dir=test_dir, pattern=pattern)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(test_suite)

    # Return True if all tests passed
    return result.wasSuccessful()


def run_unit_tests(verbosity=2):
    """Run unit tests for the ablation framework.

    Args:
        verbosity: Verbosity level (1-3).

    Returns:
        bool: True if all tests passed, False otherwise.
    """
    logging.info("Running unit tests")
    return discover_and_run_tests(test_path="tests/unit", pattern="test_*.py", verbosity=verbosity)


def run_integration_tests(verbosity=2):
    """Run integration tests for the ablation framework.

    Args:
        verbosity: Verbosity level (1-3).

    Returns:
        bool: True if all tests passed, False otherwise.
    """
    logging.info("Running integration tests")
    return discover_and_run_tests(test_path="tests/integration", pattern="test_*.py", verbosity=verbosity)


def main():
    """Run the test suite."""
    parser = argparse.ArgumentParser(description="Run tests for the ablation framework")
    parser.add_argument("--unit-only", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration-only", action="store_true", help="Run only integration tests")
    parser.add_argument("-v", "--verbose", action="store_true", help="Increase verbosity")
    args = parser.parse_args()

    # Set up logging
    setup_logging()

    # Set verbosity level
    verbosity = 3 if args.verbose else 2

    logging.info("Starting ablation framework tests")

    # Track if all tests passed
    all_passed = True

    # Run unit tests if requested or if neither type is specified
    if args.unit_only or (not args.unit_only and not args.integration_only):
        unit_passed = run_unit_tests(verbosity=verbosity)
        if not unit_passed:
            all_passed = False
            logging.warning("Some unit tests failed")

    # Run integration tests if requested or if neither type is specified
    if args.integration_only or (not args.unit_only and not args.integration_only):
        integration_passed = run_integration_tests(verbosity=verbosity)
        if not integration_passed:
            all_passed = False
            logging.warning("Some integration tests failed")

    # Log final result
    if all_passed:
        logging.info("All tests passed")
    else:
        logging.error("Some tests failed")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
