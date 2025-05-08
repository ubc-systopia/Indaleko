#!/usr/bin/env python
"""Test runner for the ablation framework."""

import argparse
import logging
import os
import sys
import unittest

import pytest

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


def run_unittest_tests(test_dir: str = "unit", pattern: str = "test_*.py", verbosity: int = 2) -> bool:
    """Run unit tests using unittest framework.

    Args:
        test_dir: The directory containing the tests.
        pattern: The pattern for test files.
        verbosity: The verbosity level.

    Returns:
        bool: True if all tests pass, False otherwise.
    """
    test_loader = unittest.TestLoader()

    # Get the path to the test directory
    test_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), test_dir)

    # Discover and run tests
    test_suite = test_loader.discover(test_path, pattern=pattern)
    test_runner = unittest.TextTestRunner(verbosity=verbosity)
    result = test_runner.run(test_suite)

    # Return True if all tests pass, False otherwise
    return result.wasSuccessful()


def run_pytest_tests(test_dirs: list[str] | None = None, options: list[str] | None = None) -> bool:
    """Run tests using pytest framework.

    Args:
        test_dirs: The directories containing the tests.
        options: Additional pytest options.

    Returns:
        bool: True if all tests pass, False otherwise.
    """
    test_dirs = test_dirs or ["unit", "integration", "system"]
    options = options or []

    # Get the path to the test directories
    test_paths = []
    for test_dir in test_dirs:
        test_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), test_dir)
        if os.path.exists(test_path):
            test_paths.append(test_path)

    if not test_paths:
        print(f"No test directories found: {test_dirs}")
        return False

    # Run tests
    args = options + test_paths
    return pytest.main(args) == 0


def main() -> None:
    """Run the tests."""
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Run tests for the ablation framework")
    parser.add_argument("--unittest", action="store_true", help="Run tests using unittest framework")
    parser.add_argument("--pytest", action="store_true", help="Run tests using pytest framework")
    parser.add_argument("--test-dir", action="append", help="Test directory to run")
    parser.add_argument("--pattern", default="test_*.py", help="Pattern for test files (unittest only)")
    parser.add_argument("--verbosity", type=int, default=2, help="Verbosity level (unittest only)")
    parser.add_argument("--pytest-option", action="append", help="Additional pytest options")
    parser.add_argument("--unittest-option", action="append", help="Additional unittest options")

    # Parse arguments
    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # If neither framework is specified, default to pytest
    if not args.unittest and not args.pytest:
        args.pytest = True

    # Run tests
    success = True

    if args.unittest:
        test_dirs = args.test_dir or ["unit"]
        for test_dir in test_dirs:
            unittest_success = run_unittest_tests(
                test_dir=test_dir,
                pattern=args.pattern,
                verbosity=args.verbosity,
            )
            success = success and unittest_success

    if args.pytest:
        pytest_success = run_pytest_tests(
            test_dirs=args.test_dir,
            options=args.pytest_option,
        )
        success = success and pytest_success

    # Exit with appropriate status code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
