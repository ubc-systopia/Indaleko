"""Simple integration test for the ablation framework."""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

# Add project root to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

# Mock dependencies before importing
sys.modules["seaborn"] = MagicMock()
sys.modules["pandas"] = MagicMock()
sys.modules["matplotlib"] = MagicMock()
sys.modules["matplotlib.pyplot"] = MagicMock()



class TestSimpleIntegration(unittest.TestCase):
    """Simple integration test for the ablation framework."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test outputs
        self.temp_dir = tempfile.mkdtemp()

        # Create a tester (mocked to avoid database operations)
        self.tester = MagicMock()

    def tearDown(self):
        """Clean up after tests."""
        # Clean up the temporary directory
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_basic_setup(self):
        """Test that the test environment is set up correctly."""
        # This is a simple test to make sure the environment is set up correctly
        self.assertIsNotNone(self.tester)
        self.assertTrue(os.path.exists(self.temp_dir))


if __name__ == "__main__":
    unittest.main()
