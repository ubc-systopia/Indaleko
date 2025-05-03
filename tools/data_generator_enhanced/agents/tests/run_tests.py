#!/usr/bin/env python3
"""
Test runner for the Enhanced Data Generator test suite.
"""

import os
import sys
import unittest
from pathlib import Path

# Bootstrap project root so imports work
current_path = Path(__file__).parent.resolve()
while not (current_path / "Indaleko.py").exists() and current_path != current_path.parent:
    current_path = current_path.parent
sys.path.insert(0, str(current_path))


def run_tests():
    """Run all tests in the test suite."""
    # Discover and run all test files in the current directory
    loader = unittest.TestLoader()
    test_suite = loader.discover(os.path.dirname(__file__), pattern="test_*.py")
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Return appropriate exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())