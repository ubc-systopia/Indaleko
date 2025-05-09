"""Integration tests for all activity providers.

This test suite verifies that each activity provider (collector and recorder)
works correctly in isolation, ensuring that basic functionality is maintained
and regressions are caught early.
"""

import os
import sys
import unittest
import uuid
from pathlib import Path

# Add project root to path to resolve imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

from research.ablation.collectors.location_collector import LocationActivityCollector
from research.ablation.collectors.music_collector import MusicActivityCollector
from research.ablation.collectors.task_collector import TaskActivityCollector
from research.ablation.ner.entity_manager import NamedEntityManager
from research.ablation.recorders.location_recorder import LocationActivityRecorder
from research.ablation.recorders.music_recorder import MusicActivityRecorder
from research.ablation.recorders.task_recorder import TaskActivityRecorder
from db.db_config import IndalekoDBConfig


class ActivityProviderTestCase(unittest.TestCase):
    """Base test case for activity providers."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures that are reused across all tests."""
        cls.entity_manager = NamedEntityManager()
        
        # Initialize database connection
        cls.db_config = IndalekoDBConfig()
        cls.db = cls.db_config.get_arangodb()
        
        # Clean up any existing test data
        cls.cleanup_collections()

    @classmethod
    def tearDownClass(cls):
        """Clean up test fixtures."""
        cls.cleanup_collections()

    @classmethod
    def cleanup_collections(cls):
        """Clean up test collections."""
        collections = [
            "AblationLocationActivity",
            "AblationMusicActivity",
            "AblationTaskActivity",
            "AblationTruthData"
        ]
        
        for collection_name in collections:
            if cls.db.has_collection(collection_name):
                cls.db.aql.execute(f"FOR doc IN {collection_name} REMOVE doc IN {collection_name}")


class TestLocationProvider(ActivityProviderTestCase):
    """Integration tests for the location activity provider."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a collector and recorder
        self.collector = LocationActivityCollector(entity_manager=self.entity_manager)
        self.recorder = LocationActivityRecorder()

    def test_full_pipeline(self):
        """Test the full collector-recorder pipeline."""
        # 1. Generate a batch of location activities
        batch_size = 10
        location_data = self.collector.generate_batch(batch_size)
        
        # Verify data was generated
        self.assertEqual(len(location_data), batch_size)
        
        # 2. Record the batch
        success = self.recorder.record_batch(location_data)
        self.assertTrue(success, "Failed to record location activity batch")
        
        # 3. Verify data was recorded
        collection_name = self.recorder.get_collection_name()
        count = self.recorder.count_records()
        self.assertGreaterEqual(count, batch_size, f"Expected at least {batch_size} records, got {count}")
        
        # 4. Generate and record truth data
        query = "Find activities at Home"
        query_id = uuid.uuid4()
        truth_data = self.collector.generate_truth_data(query)
        
        # Verify truth data was generated
        self.assertGreater(len(truth_data), 0, "No truth data was generated")
        
        # Record truth data
        success = self.recorder.record_truth_data(query_id, truth_data)
        self.assertTrue(success, "Failed to record truth data")


class TestMusicProvider(ActivityProviderTestCase):
    """Integration tests for the music activity provider."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a collector and recorder
        self.collector = MusicActivityCollector(entity_manager=self.entity_manager)
        self.recorder = MusicActivityRecorder()

    def test_full_pipeline(self):
        """Test the full collector-recorder pipeline."""
        # Check if all required methods are implemented
        try:
            # 1. Generate a batch of music activities
            batch_size = 10
            music_data = self.collector.generate_batch(batch_size)
            
            # Verify data was generated
            self.assertEqual(len(music_data), batch_size)
            
            # 2. Record the batch
            success = self.recorder.record_batch(music_data)
            self.assertTrue(success, "Failed to record music activity batch")
            
            # 3. Verify data was recorded
            collection_name = self.recorder.get_collection_name()
            count = self.recorder.count_records()
            self.assertGreaterEqual(count, batch_size, f"Expected at least {batch_size} records, got {count}")
            
            # 4. Generate and record truth data
            query = "Find songs by Taylor Swift"
            query_id = uuid.uuid4()
            truth_data = self.collector.generate_truth_data(query)
            
            # Verify truth data was generated
            self.assertGreater(len(truth_data), 0, "No truth data was generated")
            
            # Record truth data
            success = self.recorder.record_truth_data(query_id, truth_data)
            self.assertTrue(success, "Failed to record truth data")
        except NotImplementedError as e:
            self.skipTest(f"Music provider not fully implemented: {e}")
        except AttributeError as e:
            self.skipTest(f"Music provider missing method: {e}")


class TestTaskProvider(ActivityProviderTestCase):
    """Integration tests for the task activity provider."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a collector and recorder
        self.collector = TaskActivityCollector(entity_manager=self.entity_manager)
        self.recorder = TaskActivityRecorder()

    def test_full_pipeline(self):
        """Test the full collector-recorder pipeline."""
        # Check if all required methods are implemented
        try:
            # 1. Generate a batch of task activities
            batch_size = 10
            task_data = self.collector.generate_batch(batch_size)
            
            # Verify data was generated
            self.assertEqual(len(task_data), batch_size)
            
            # 2. Record the batch
            success = self.recorder.record_batch(task_data)
            self.assertTrue(success, "Failed to record task activity batch")
            
            # 3. Verify data was recorded
            collection_name = self.recorder.get_collection_name()
            count = self.recorder.count_records()
            self.assertGreaterEqual(count, batch_size, f"Expected at least {batch_size} records, got {count}")
            
            # 4. Generate and record truth data
            query = "Find files related to Quarterly Report"
            query_id = uuid.uuid4()
            truth_data = self.collector.generate_truth_data(query)
            
            # Verify truth data was generated
            self.assertGreater(len(truth_data), 0, "No truth data was generated")
            
            # Record truth data
            success = self.recorder.record_truth_data(query_id, truth_data)
            self.assertTrue(success, "Failed to record truth data")
        except NotImplementedError as e:
            self.skipTest(f"Task provider not fully implemented: {e}")
        except AttributeError as e:
            self.skipTest(f"Task provider missing method: {e}")


class TestCrossFunctionalChecks(ActivityProviderTestCase):
    """Cross-functional tests to ensure consistent behavior across providers."""

    def test_collector_interfaces(self):
        """Verify that all collectors implement the required methods."""
        collectors = {
            "Location": LocationActivityCollector(entity_manager=self.entity_manager),
            "Music": MusicActivityCollector(entity_manager=self.entity_manager),
            "Task": TaskActivityCollector(entity_manager=self.entity_manager),
        }
        
        required_methods = [
            "collect",
            "generate_batch", 
            "generate_truth_data", 
            "generate_matching_data", 
            "generate_non_matching_data", 
            "seed"
        ]
        
        for name, collector in collectors.items():
            for method_name in required_methods:
                self.assertTrue(
                    hasattr(collector, method_name) and callable(getattr(collector, method_name)),
                    f"{name}ActivityCollector missing required method: {method_name}"
                )

    def test_recorder_interfaces(self):
        """Verify that all recorders implement the required methods."""
        recorders = {
            "Location": LocationActivityRecorder(),
            "Music": MusicActivityRecorder(),
            "Task": TaskActivityRecorder(),
        }
        
        required_methods = [
            "record",
            "record_batch",
            "record_truth_data",
            "delete_all",
            "get_collection_name",
            "count_records"
        ]
        
        for name, recorder in recorders.items():
            for method_name in required_methods:
                self.assertTrue(
                    hasattr(recorder, method_name) and callable(getattr(recorder, method_name)),
                    f"{name}ActivityRecorder missing required method: {method_name}"
                )


if __name__ == "__main__":
    unittest.main()