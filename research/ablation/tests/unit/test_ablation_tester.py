"""Unit tests for the ablation tester."""

import os
import sys
import unittest
import uuid
from unittest.mock import MagicMock, patch

# Add project root to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from research.ablation.ablation_tester import AblationConfig, AblationTester
from research.ablation.base import AblationResult


class TestAblationTester(unittest.TestCase):
    """Test cases for the AblationTester class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a mock database configuration and connection
        self.mock_db_config = MagicMock()
        self.mock_db = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_collection = MagicMock()

        # Set up the mock database connection
        self.mock_db_config.get_arangodb.return_value = self.mock_db
        self.mock_db.aql.execute.return_value = self.mock_cursor
        self.mock_db.has_collection.return_value = True
        self.mock_db.collection.return_value = self.mock_collection

        # Patch the IndalekoDBConfig to return our mock
        self.patcher = patch("db.db_config.IndalekoDBConfig", return_value=self.mock_db_config)
        self.patcher.start()

        # Create an ablation tester
        self.tester = AblationTester()

        # Set up test collections and data
        self.collection_name = "TestCollection"
        self.test_data = [
            {"_key": "1", "name": "Test1", "type": "location"},
            {"_key": "2", "name": "Test2", "type": "task"},
        ]

        # Mock cursor to return test data
        self.mock_cursor.__iter__.return_value = iter(self.test_data)

    def tearDown(self):
        """Clean up after tests."""
        # Stop the patcher
        self.patcher.stop()

        # Clean up the tester
        self.tester.cleanup()

    def test_init(self):
        """Test initialization of AblationTester."""
        # Verify the tester was created
        self.assertIsNotNone(self.tester)

        # Verify database connection was attempted
        self.mock_db_config.get_arangodb.assert_called_once()

    def test_ablate_collection(self):
        """Test ablation of a collection."""
        # Set up mock for database calls
        self.mock_db.has_collection.return_value = True
        self.mock_cursor.__iter__.return_value = iter(self.test_data)

        # Ablate the collection
        result = self.tester.ablate_collection(self.collection_name)

        # Verify the result
        self.assertTrue(result)

        # Verify the collection was checked
        self.mock_db.has_collection.assert_called_with(self.collection_name)

        # Verify data was retrieved
        self.mock_db.aql.execute.assert_called()

        # Verify backup data was stored
        self.assertIn(self.collection_name, self.tester.backup_data)
        self.assertEqual(self.tester.backup_data[self.collection_name], self.test_data)

        # Verify collection was marked as ablated
        self.assertIn(self.collection_name, self.tester.ablated_collections)
        self.assertTrue(self.tester.ablated_collections[self.collection_name])

    def test_restore_collection(self):
        """Test restoration of an ablated collection."""
        # Set up mock for database calls
        self.mock_db.has_collection.return_value = True

        # First ablate the collection
        self.tester.ablate_collection(self.collection_name)

        # Reset the mocks
        self.mock_db.aql.execute.reset_mock()
        self.mock_collection.insert_many.reset_mock()

        # Now restore the collection
        result = self.tester.restore_collection(self.collection_name)

        # Verify the result
        self.assertTrue(result)

        # Verify the collection was checked
        self.mock_db.has_collection.assert_called_with(self.collection_name)

        # Verify data was cleared
        self.mock_db.aql.execute.assert_called()

        # Verify data was reinserted
        self.mock_collection.insert_many.assert_called()

        # Verify collection was marked as not ablated
        self.assertIn(self.collection_name, self.tester.ablated_collections)
        self.assertFalse(self.tester.ablated_collections[self.collection_name])

        # Verify backup data was cleared
        self.assertNotIn(self.collection_name, self.tester.backup_data)

    def test_get_truth_data(self):
        """Test retrieval of truth data."""
        # Create a test query ID
        query_id = uuid.uuid4()

        # Set up mock to return truth data
        truth_doc = {"matching_entities": ["1", "2", "3"]}
        mock_result = MagicMock()
        mock_result.__iter__.return_value = iter([truth_doc])
        self.mock_db.aql.execute.return_value = mock_result

        # Get truth data
        truth_data = self.tester.get_truth_data(query_id)

        # Verify the result
        self.assertEqual(truth_data, set(["1", "2", "3"]))

        # Verify the query was executed
        self.mock_db.aql.execute.assert_called()

    def test_calculate_metrics(self):
        """Test calculation of metrics."""
        # Create a test query ID
        query_id = uuid.uuid4()

        # Mock truth data
        with patch.object(self.tester, "get_truth_data", return_value=set(["1", "2", "3"])):
            # Create test results
            results = [
                {"_key": "1"},  # True positive
                {"_key": "2"},  # True positive
                {"_key": "4"},  # False positive
            ]

            # Calculate metrics
            metrics = self.tester.calculate_metrics(query_id, results, self.collection_name)

            # Verify the metrics
            self.assertIsInstance(metrics, AblationResult)
            self.assertEqual(metrics.query_id, query_id)
            self.assertEqual(metrics.ablated_collection, self.collection_name)
            self.assertEqual(metrics.true_positives, 2)
            self.assertEqual(metrics.false_positives, 1)
            self.assertEqual(metrics.false_negatives, 1)

            # Verify calculated metrics
            self.assertAlmostEqual(metrics.precision, 2 / 3)
            self.assertAlmostEqual(metrics.recall, 2 / 3)
            self.assertAlmostEqual(metrics.f1_score, 2 / 3)

    def test_execute_query(self):
        """Test execution of a query."""
        # Set up mock for query results
        mock_results = [{"_key": "1"}, {"_key": "2"}]
        mock_result_cursor = MagicMock()
        mock_result_cursor.__iter__.return_value = iter(mock_results)
        self.mock_db.aql.execute.return_value = mock_result_cursor

        # Execute query
        results, time_ms = self.tester.execute_query("test query", self.collection_name)

        # Verify the results
        self.assertEqual(results, mock_results)
        self.assertIsInstance(time_ms, int)

        # Verify the query was executed
        self.mock_db.aql.execute.assert_called()

    @patch("time.time")
    def test_test_ablation(self, mock_time):
        """Test the complete ablation test process."""
        # Mock time
        mock_time.side_effect = [0, 0.1]  # 100ms execution time

        # Create a test query ID
        query_id = uuid.uuid4()

        # Set up mocks
        mock_results = [{"_key": "1"}, {"_key": "2"}]

        # Mock execute_query
        with patch.object(self.tester, "execute_query", return_value=(mock_results, 100)):
            # Mock calculate_metrics
            mock_metrics = AblationResult(
                query_id=query_id,
                ablated_collection=self.collection_name,
                precision=0.5,
                recall=0.5,
                f1_score=0.5,
                execution_time_ms=0,
                result_count=2,
                true_positives=1,
                false_positives=1,
                false_negatives=1,
            )

            with patch.object(self.tester, "calculate_metrics", return_value=mock_metrics):
                # Run the test
                result = self.tester.test_ablation(query_id, "test query", self.collection_name)

                # Verify the result
                self.assertEqual(result.query_id, query_id)
                self.assertEqual(result.ablated_collection, self.collection_name)
                self.assertEqual(result.precision, 0.5)
                self.assertEqual(result.recall, 0.5)
                self.assertEqual(result.f1_score, 0.5)
                self.assertEqual(result.execution_time_ms, 100)

    def test_run_ablation_test(self):
        """Test running a complete ablation test."""
        # Create a test query ID and config
        query_id = uuid.uuid4()
        config = AblationConfig(
            collections_to_ablate=["TestCollection1", "TestCollection2"],
            query_limit=10,
        )

        # Mock test_ablation to return a test result
        mock_result = AblationResult(
            query_id=query_id,
            ablated_collection="TestCollection1",
            precision=0.5,
            recall=0.5,
            f1_score=0.5,
            execution_time_ms=100,
            result_count=2,
            true_positives=1,
            false_positives=1,
            false_negatives=1,
        )

        with patch.object(self.tester, "test_ablation", return_value=mock_result):
            # Mock ablate and restore
            with patch.object(self.tester, "ablate_collection", return_value=True):
                with patch.object(self.tester, "restore_collection", return_value=True):
                    # Run the test
                    results = self.tester.run_ablation_test(config, query_id, "test query")

                    # Verify results were returned
                    self.assertIsInstance(results, dict)
                    self.assertTrue(len(results) > 0)

    def test_cleanup(self):
        """Test cleanup of resources."""
        # First make the tester have resources to clean up
        self.tester.ablated_collections = {"TestCollection": True}
        self.tester.backup_data = {"TestCollection": [{"_key": "1"}]}

        # Mock restore_collection
        with patch.object(self.tester, "restore_collection", return_value=True):
            # Run cleanup
            self.tester.cleanup()

            # Verify resources were cleaned up
            self.assertEqual(self.tester.ablated_collections, {})
            self.assertEqual(self.tester.backup_data, {})


if __name__ == "__main__":
    unittest.main()
