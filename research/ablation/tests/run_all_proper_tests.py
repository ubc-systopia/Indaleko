#!/usr/bin/env python3
"""
Run all proper tests that follow the fail-stop principle.

This script runs all the tests that use real connections and adhere to the
fail-stop principle. These tests are critical for scientific experiments
like ablation studies, where using mocks would compromise the validity of results.
"""

import logging
import os
import sys
import unittest

# Set up the environment
current_path = os.path.dirname(os.path.abspath(__file__))
root_path = os.path.dirname(os.path.dirname(os.path.dirname(current_path)))
if os.environ.get("INDALEKO_ROOT") is None:
    os.environ["INDALEKO_ROOT"] = root_path
    sys.path.insert(0, root_path)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# List of proper test modules that follow the fail-stop principle
PROPER_TEST_MODULES = [
    "research.ablation.tests.unit.test_cross_collection_query_generator_proper",
    "research.ablation.tests.integration.test_cross_collection_aql_proper",
    "research.ablation.tests.integration.test_cross_collection_queries_proper",
    "research.ablation.tests.integration.test_ablation_cross_collection_proper",
]


def run_all_proper_tests():
    """Run all proper tests that follow the fail-stop principle."""
    logger.info("Running all proper tests that follow the fail-stop principle")

    # Initialize the test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all proper test modules to the suite
    for module_name in PROPER_TEST_MODULES:
        try:
            # Import the module
            module = __import__(module_name, fromlist=["*"])

            # Add all test cases from the module
            tests = loader.loadTestsFromModule(module)
            suite.addTests(tests)

            logger.info(f"Added tests from {module_name}")
        except ImportError as e:
            logger.error(f"Failed to import {module_name}: {e!s}")
            sys.exit(1)  # Fail-stop on import error

    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Check the result
    if result.wasSuccessful():
        logger.info("All proper tests passed!")
        return 0
    else:
        logger.error("Some proper tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_proper_tests())
