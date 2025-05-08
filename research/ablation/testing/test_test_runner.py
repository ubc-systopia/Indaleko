"""Tests for the ablation test runner."""

import unittest
from unittest.mock import MagicMock, patch
import uuid
from typing import Dict, List, Optional

from db.db_config import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections
from ..models.ablation_results import AblationQueryTruth, AblationResult, AblationTestMetadata
from ..models.activity import ActivityType
from .test_runner import AblationTestRunner


class TestAblationTestRunner(unittest.TestCase):
    """Test cases for the ablation test runner."""
    
    @patch('research.ablation.testing.test_runner.QueryGenerator')
    @patch('research.ablation.testing.test_runner.TruthTracker')
    @patch('research.ablation.testing.test_runner.AblationDatabaseManager')
    @patch('research.ablation.testing.test_runner.IndalekoDBConfig')
    def setUp(self, mock_db_config, mock_db_manager, mock_truth_tracker, mock_query_generator):
        """Set up test fixtures."""
        # Mock the database connection
        self.mock_db = MagicMock()
        mock_db_config.return_value.get_arangodb.return_value = self.mock_db
        
        # Mock the collection
        self.mock_collection = MagicMock()
        self.mock_db.collection.return_value = self.mock_collection
        
        # Mock the database manager
        self.mock_db_manager = mock_db_manager.return_value
        self.mock_db_manager.ensure_collections.return_value = True
        self.mock_db_manager.ablate_collection.return_value = True
        self.mock_db_manager.restore_collection.return_value = True
        
        # Mock the truth tracker
        self.mock_truth_tracker = mock_truth_tracker.return_value
        self.mock_truth_tracker.get_matching_ids.return_value = ["doc1", "doc2", "doc3"]
        
        # Mock the query generator
        self.mock_query_generator = mock_query_generator.return_value
        mock_query = MagicMock()
        mock_query.query_id = uuid.uuid4()
        mock_query.query_text = "Test query"
        mock_query.activity_types = [ActivityType.MUSIC, ActivityType.LOCATION]
        mock_query.difficulty = "medium"
        mock_query.metadata = {}
        self.mock_query_generator.generate_queries.return_value = [mock_query]
        
        # Create a test runner
        self.test_runner = AblationTestRunner("Test Run", "Test description")
        
        # Mock the execute_query method to return fake results
        self.test_runner._execute_query = MagicMock(return_value=[
            {"_id": "doc1", "Label": "Document 1"},
            {"_id": "doc2", "Label": "Document 2"},
            {"_id": "doc3", "Label": "Document 3"},
            {"_id": "doc4", "Label": "Document 4"},
        ])
        
        # Mock the save methods
        self.test_runner._save_query_truth = MagicMock(return_value="key1")
        self.test_runner._save_result = MagicMock(return_value="key2")
        self.test_runner._save_test_metadata = MagicMock(return_value="key3")
    
    def test_initialization(self):
        """Test initializing the test runner."""
        self.assertEqual("Test Run", self.test_runner.test_name)
        self.assertEqual("Test description", self.test_runner.description)
        self.assertIsNotNone(self.test_runner.test_id)
        self.assertIsNotNone(self.test_runner.timestamp)
        
        # Check that collections are set up
        self.assertEqual(6, len(self.test_runner.test_collections))
        self.assertIn(IndalekoDBCollections.Indaleko_Ablation_Music_Activity_Collection, 
                     self.test_runner.test_collections)
        self.assertIn(IndalekoDBCollections.Indaleko_Ablation_Location_Activity_Collection, 
                     self.test_runner.test_collections)
    
    def test_calculate_metrics(self):
        """Test calculating metrics from results."""
        truth_ids = ["doc1", "doc2", "doc3"]
        result_ids = ["doc1", "doc2", "doc4", "doc5"]
        
        metrics = self.test_runner._calculate_metrics(truth_ids, result_ids)
        
        # Check that metrics are calculated correctly
        self.assertIn("precision", metrics)
        self.assertIn("recall", metrics)
        self.assertIn("f1_score", metrics)
        
        # Precision: 2/4 = 0.5
        self.assertAlmostEqual(0.5, metrics["precision"])
        
        # Recall: 2/3 = 0.667
        self.assertAlmostEqual(0.667, metrics["recall"], places=3)
        
        # F1 Score: 2 * 0.5 * 0.667 / (0.5 + 0.667) = 0.571
        self.assertAlmostEqual(0.571, metrics["f1_score"], places=3)
    
    def test_generate_queries(self):
        """Test generating test queries."""
        queries = self.test_runner._generate_queries(1)
        
        # Check that queries were generated
        self.assertEqual(1, len(queries))
        self.assertIsInstance(queries[0], AblationQueryTruth)
        
        # Check that query was saved
        self.test_runner._save_query_truth.assert_called_once()
    
    @patch('time.time')
    def test_test_query(self, mock_time):
        """Test testing a single query."""
        # Mock time.time to return predictable values
        mock_time.side_effect = [0, 1, 2, 3, 4, 5]
        
        # Create a test query
        query = AblationQueryTruth(
            id=uuid.uuid4(),
            query_id=uuid.uuid4(),
            query_text="Test query",
            matching_ids=["doc1", "doc2", "doc3"],
            activity_types=["MUSIC", "LOCATION"],
            created_at=self.test_runner.timestamp,
        )
        
        # Test the query
        self.test_runner._test_query(query)
        
        # Check that collections were ablated and restored
        self.assertEqual(len(self.test_runner.test_collections), 
                         self.mock_db_manager.ablate_collection.call_count)
        self.assertEqual(len(self.test_runner.test_collections), 
                         self.mock_db_manager.restore_collection.call_count)
        
        # Check that results were created and saved
        self.assertEqual(len(self.test_runner.test_collections), len(self.test_runner.results))
        self.assertEqual(len(self.test_runner.test_collections), 
                         self.test_runner._save_result.call_count)
    
    @patch('time.time')
    def test_run_test(self, mock_time):
        """Test running a complete test."""
        # Mock time.time to return predictable values for overall timing
        mock_time.side_effect = [0] + list(range(1, 100))
        
        # Run a test with a small number of queries
        metadata = self.test_runner.run_test(num_queries=1)
        
        # Check that the test ran successfully
        self.assertIsInstance(metadata, AblationTestMetadata)
        self.assertEqual(self.test_runner.test_id, metadata.test_id)
        self.assertEqual(self.test_runner.test_name, metadata.test_name)
        
        # Check that query generation was called
        self.mock_query_generator.generate_queries.assert_called_once()
        
        # Check that test metadata was saved
        self.test_runner._save_test_metadata.assert_called_once()
        
        # Check that summary metrics were calculated
        self.assertGreater(len(self.test_runner.summary_metrics), 0)
        self.assertGreater(len(self.test_runner.impact_ranking), 0)


if __name__ == "__main__":
    unittest.main()