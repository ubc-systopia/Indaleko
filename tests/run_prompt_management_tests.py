#!/usr/bin/env python
"""
Test runner for prompt management system tests.

Usage:
    python tests/run_prompt_management_tests.py

This script runs all tests for the prompt management system components.
"""

import logging
import sys
import unittest
from pathlib import Path

# Add parent directory to path so we can import modules
sys.path.append(str(Path(__file__).parent.parent))

# Import test modules
from tests.prompt_management.test_llm_guardian import TestLLMGuardian
from tests.prompt_management.test_prompt_guardian import TestPromptGuardian


def configure_logging():
    """Configure logging for test runs."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def run_tests():
    """Run all prompt management tests."""
    # Create test suite
    test_suite = unittest.TestSuite()

    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestPromptGuardian))
    test_suite.addTest(unittest.makeSuite(TestLLMGuardian))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Return exit code based on test result
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    configure_logging()
    logging.info("Starting prompt management test suite")

    exit_code = run_tests()

    logging.info(f"Test suite completed with exit code: {exit_code}")
    sys.exit(exit_code)
