"""Simple tests for the AblationTester."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add project root to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from research.ablation.ablation_tester import AblationTester


class TestSimpleAblationTester(unittest.TestCase):
    """Simple test cases for the AblationTester class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock for IndalekoDBConfig
        self.mock_db_config = MagicMock()
        self.mock_db = MagicMock()
        self.mock_db_config.get_arangodb.return_value = self.mock_db

        # Patch IndalekoDBConfig
        self.patcher = patch("db.db_config.IndalekoDBConfig", return_value=self.mock_db_config)
        self.mock_db_config_class = self.patcher.start()

        # Create a tester with the mocked database
        self.tester = AblationTester()

        # Replace the tester's db with our mock
        self.tester.db = self.mock_db
        self.tester.db_config = self.mock_db_config

    def tearDown(self):
        """Clean up after tests."""
        self.patcher.stop()

    def test_init(self):
        """Test initialization."""
        self.assertIsNotNone(self.tester)
        self.assertEqual(self.tester.db, self.mock_db)
        self.assertEqual(self.tester.db_config, self.mock_db_config)
        self.assertEqual(self.tester.backup_data, {})
        self.assertEqual(self.tester.ablated_collections, {})


if __name__ == "__main__":
    unittest.main()
