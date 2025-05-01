#!/usr/bin/env python
"""
Test Module for NTFS Warm Tier Recorder.

This module provides comprehensive testing for the warm tier recorder
component of Indaleko's tiered memory architecture, focusing on:
1. Warm tier recording functionality
2. Activity aggregation algorithms
3. Tier transition operations
4. Storage efficiency metrics

The tests are designed to run in any environment with a database connection,
since the warm tier operates on data already in the database rather than
requiring live NTFS events.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import os
import sys
import unittest
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import recorder
from activity.collectors.storage.data_models.storage_activity_data_model import (
    NtfsStorageActivityData,
    StorageItemType,
    StorageProviderType,
)
from activity.recorders.storage.ntfs.tiered.hot.recorder import NtfsHotTierRecorder
from activity.recorders.storage.ntfs.tiered.importance_scorer import ImportanceScorer
from activity.recorders.storage.ntfs.tiered.tier_transition import TierTransitionManager
from activity.recorders.storage.ntfs.tiered.warm.recorder import NtfsWarmTierRecorder


class MockDatabase:
    """Mock database for testing without a real database connection."""

    def __init__(self):
        """Initialize the mock database."""
        self.collections = {}
        self.aql = MagicMock()
        self._arangodb = MagicMock()
        self._arangodb.aql = self.aql

    def get_collection(self, name):
        """Get or create a collection with the given name."""
        if name not in self.collections:
            self.collections[name] = MockCollection(name)
        return self.collections[name]

    def create_collection(self, name):
        """Create a collection with the given name."""
        self.collections[name] = MockCollection(name)
        return self.collections[name]


class MockCollection:
    """Mock collection for testing."""

    def __init__(self, name):
        """Initialize the mock collection."""
        self.name = name
        self.documents = {}
        self.indices = []

    def add_document(self, document):
        """Add a document to the collection."""
        if "_key" not in document:
            document["_key"] = f"doc{len(self.documents) + 1}"
        self.documents[document["_key"]] = document
        return {"_key": document["_key"], "_id": f"{self.name}/{document['_key']}"}

    def add_hash_index(self, fields, unique=False):
        """Add a hash index to the collection."""
        self.indices.append({"type": "hash", "fields": fields, "unique": unique})
        return {"id": f"idx{len(self.indices)}", "type": "hash", "fields": fields}

    def add_ttl_index(self, fields, expireAfter=None, ttl=None):
        """Add a TTL index to the collection."""
        self.indices.append({"type": "ttl", "fields": fields, "expireAfter": expireAfter or ttl})
        return {"id": f"idx{len(self.indices)}", "type": "ttl", "fields": fields}

    def indexes(self):
        """Get all indices for the collection."""
        return self.indices

    def count(self):
        """Get the number of documents in the collection."""
        return len(self.documents)


def create_test_activity(
    file_path: str,
    activity_type: str = "create",
    timestamp: datetime | None = None,
    is_directory: bool = False,
    attributes: dict[str, Any] | None = None,
) -> NtfsStorageActivityData:
    """Create a test activity for use in tests."""
    if timestamp is None:
        timestamp = datetime.now(UTC)

    # Generate deterministic file reference numbers based on path
    import hashlib

    path_hash = hashlib.md5(file_path.encode()).hexdigest()
    file_ref = int(path_hash[:16], 16)
    parent_ref = int(path_hash[16:], 16)

    return NtfsStorageActivityData(
        activity_id=f"test_{activity_type}_{file_path.replace('/', '_')}",
        timestamp=timestamp,
        file_reference_number=str(file_ref),
        parent_file_reference_number=str(parent_ref),
        activity_type=activity_type,
        file_name=os.path.basename(file_path),
        file_path=file_path,
        volume_name="C:",
        is_directory=is_directory,
        provider_type=StorageProviderType.LOCAL_NTFS,
        provider_id="7d8f5a92-35c7-41e6-b13d-6c4e89e7f2a5",
        item_type=StorageItemType.DIRECTORY if is_directory else StorageItemType.FILE,
        attributes=attributes or {},
    )


class TestNtfsWarmTierRecorder(unittest.TestCase):
    """Test the NTFS Warm Tier Recorder functionality."""

    def setUp(self):
        """Set up test environment."""
        # Mock database connection
        self.mock_db = MockDatabase()

        # Patch the database connection
        self.db_patcher = patch("activity.recorders.storage.base.IndalekoCollections")
        self.mock_collections = self.db_patcher.start()
        self.mock_collections.get_collection.side_effect = self.mock_db.get_collection

        # Create recorder with mocked database
        self.recorder = NtfsWarmTierRecorder(
            debug=True,
            no_db=False,  # We're using a mocked DB
            register_enabled=False,  # Skip registration for tests
        )

        # Replace real DB with mock
        self.recorder._db = self.mock_db

        # Set up collections
        self.recorder._collection = self.mock_db.get_collection("ntfs_activities_warm")
        self.recorder._hot_tier_collection_name = "ntfs_activities_hot"
        self.hot_collection = self.mock_db.get_collection("ntfs_activities_hot")

    def tearDown(self):
        """Clean up after tests."""
        self.db_patcher.stop()

    def test_init(self):
        """Test initialization of the recorder."""
        # Check basic initialization
        self.assertEqual(self.recorder._ttl_days, 30)
        self.assertEqual(self.recorder._collection_name, "ntfs_activities_warm")
        self.assertIsNotNone(self.recorder._scorer)

    def test_store_activity(self):
        """Test storing an activity in the warm tier."""
        # Create a test activity
        activity = create_test_activity(
            file_path="C:/Users/Documents/test_file.txt",
            activity_type="create",
        )

        # Store the activity
        result = self.recorder.store_activity(activity)

        # Check that the activity was stored
        self.assertEqual(result, activity.activity_id)
        self.assertEqual(len(self.recorder._collection.documents), 1)

        # Check stored document structure
        stored_doc = list(self.recorder._collection.documents.values())[0]
        self.assertIn("Record", stored_doc)
        self.assertIn("Data", stored_doc["Record"])

        # Check that timestamp is preserved
        data = stored_doc["Record"]["Data"]
        self.assertEqual(data["timestamp"], activity.timestamp.isoformat())

        # Check that TTL timestamp was added
        self.assertIn("ttl_timestamp", data)

    def test_aggregation_grouping(self):
        """Test grouping of activities for aggregation."""
        # Create a set of test activities
        activities = []

        # Multiple activities for the same file with different types
        base_time = datetime.now(UTC)
        path = "C:/Users/Documents/Project/report.docx"

        # Add create activity
        activities.append(
            {
                "Record": {
                    "Data": {
                        "entity_id": "1",
                        "activity_type": "create",
                        "file_path": path,
                        "timestamp": (base_time - timedelta(hours=1)).isoformat(),
                    },
                },
            },
        )

        # Add multiple modify activities
        for i in range(5):
            activities.append(
                {
                    "Record": {
                        "Data": {
                            "entity_id": "1",
                            "activity_type": "modify",
                            "file_path": path,
                            "timestamp": (base_time - timedelta(minutes=30 - i * 5)).isoformat(),
                        },
                    },
                },
            )

        # Add close activity
        activities.append(
            {
                "Record": {
                    "Data": {
                        "entity_id": "1",
                        "activity_type": "close",
                        "file_path": path,
                        "timestamp": base_time.isoformat(),
                    },
                },
            },
        )

        # Test grouping function
        grouped = self.recorder.group_activities_for_aggregation(activities)

        # Check that activities are properly grouped
        self.assertEqual(len(grouped), 3)  # 3 groups: create, modify, close

        # Check that each activity type has proper grouping
        for group, group_activities in grouped.items():
            activity_type = group_activities[0]["Record"]["Data"]["activity_type"]
            for activity in group_activities:
                self.assertEqual(activity["Record"]["Data"]["activity_type"], activity_type)

    def test_create_aggregated_activity(self):
        """Test creation of aggregated activity from multiple activities."""
        # Create a set of modify activities for the same file
        activities = []
        base_time = datetime.now(UTC)
        path = "C:/Users/Documents/Project/report.docx"

        # Add multiple modify activities
        for i in range(5):
            activities.append(
                {
                    "Record": {
                        "Data": {
                            "entity_id": "1",
                            "activity_type": "modify",
                            "file_path": path,
                            "file_name": "report.docx",
                            "volume_name": "C:",
                            "is_directory": False,
                            "timestamp": (base_time - timedelta(minutes=i * 5)).isoformat(),
                            "importance_score": 0.3 + (i * 0.1),  # Varying importance
                        },
                    },
                },
            )

        # Test aggregation function
        group_key = "1_modify_2025-04-24_1"  # Example group key
        aggregated = self.recorder.create_aggregated_activity(activities, group_key)

        # Check basic properties
        self.assertEqual(aggregated["entity_id"], "1")
        self.assertEqual(aggregated["activity_type"], "modify")
        self.assertEqual(aggregated["file_path"], path)
        self.assertEqual(aggregated["count"], 5)
        self.assertTrue(aggregated["is_aggregated"])

        # Check that time range is correct
        self.assertEqual(aggregated["timestamp"], activities[-1]["Record"]["Data"]["timestamp"])
        self.assertEqual(aggregated["end_timestamp"], activities[0]["Record"]["Data"]["timestamp"])

        # Check that we store the highest importance score
        self.assertEqual(aggregated["importance_score"], 0.7)  # Maximum from the set

    def test_aggregate_activities(self):
        """Test aggregation of multiple activities."""
        # Create a diverse set of activities
        activities = []
        base_time = datetime.now(UTC)

        # Group 1: Multiple modify activities for the same file (should be aggregated)
        path1 = "C:/Users/Documents/Project/report.docx"
        for i in range(5):
            activities.append(
                {
                    "Record": {
                        "Data": {
                            "entity_id": "1",
                            "activity_type": "modify",
                            "file_path": path1,
                            "file_name": "report.docx",
                            "volume_name": "C:",
                            "is_directory": False,
                            "timestamp": (base_time - timedelta(minutes=i * 5)).isoformat(),
                            "importance_score": 0.5,
                        },
                    },
                },
            )

        # Group 2: High importance activity (should not be aggregated)
        activities.append(
            {
                "Record": {
                    "Data": {
                        "entity_id": "2",
                        "activity_type": "create",
                        "file_path": "C:/Users/Documents/Important.pdf",
                        "file_name": "Important.pdf",
                        "volume_name": "C:",
                        "is_directory": False,
                        "timestamp": (base_time - timedelta(hours=1)).isoformat(),
                        "importance_score": 0.8,
                    },
                },
            },
        )

        # Group 3: Low importance temp files (should be aggregated)
        for i in range(3):
            activities.append(
                {
                    "Record": {
                        "Data": {
                            "entity_id": f"temp{i}",
                            "activity_type": "create",
                            "file_path": f"C:/Temp/temp{i}.txt",
                            "file_name": f"temp{i}.txt",
                            "volume_name": "C:",
                            "is_directory": False,
                            "timestamp": (base_time - timedelta(minutes=i * 2)).isoformat(),
                            "importance_score": 0.2,
                        },
                    },
                },
            )

        # Run aggregation
        aggregated = self.recorder.aggregate_activities(activities)

        # Check results
        self.assertEqual(len(aggregated), 3)  # 3 groups: modify, high-importance create, low-importance creates

        # Verify each type
        modify_aggregated = None
        high_importance = None
        low_importance = None

        for activity in aggregated:
            if activity["activity_type"] == "modify" and activity["file_path"] == path1:
                modify_aggregated = activity
            elif activity["importance_score"] >= 0.8:
                high_importance = activity
            elif "temp" in activity["file_path"]:
                low_importance = activity

        # Check modify group
        self.assertIsNotNone(modify_aggregated)
        self.assertTrue(modify_aggregated["is_aggregated"])
        self.assertEqual(modify_aggregated["count"], 5)

        # Check high importance wasn't aggregated
        self.assertIsNotNone(high_importance)
        self.assertFalse(high_importance.get("is_aggregated", False))

        # Check low importance was aggregated
        self.assertIsNotNone(low_importance)
        self.assertTrue(low_importance["is_aggregated"])
        self.assertEqual(low_importance["count"], 3)

    def test_process_hot_tier_activities(self):
        """Test processing activities from hot tier to warm tier."""
        # Create some test activities in the hot tier
        activities = []
        base_time = datetime.now(UTC)

        # Activity 1: High importance
        activities.append(
            {
                "Record": {
                    "Data": {
                        "entity_id": "1",
                        "activity_type": "create",
                        "file_path": "C:/Users/Documents/Important.docx",
                        "file_name": "Important.docx",
                        "volume_name": "C:",
                        "is_directory": False,
                        "timestamp": (base_time - timedelta(hours=24)).isoformat(),
                        "importance_score": 0.8,
                    },
                },
            },
        )

        # Activity 2-6: Medium importance, same file (should be aggregated)
        for i in range(5):
            activities.append(
                {
                    "Record": {
                        "Data": {
                            "entity_id": "2",
                            "activity_type": "modify",
                            "file_path": "C:/Users/Documents/Medium.docx",
                            "file_name": "Medium.docx",
                            "volume_name": "C:",
                            "is_directory": False,
                            "timestamp": (base_time - timedelta(hours=12, minutes=i * 10)).isoformat(),
                            "importance_score": 0.5,
                        },
                    },
                },
            )

        # Activity 7-9: Low importance (should be aggregated)
        for i in range(3):
            activities.append(
                {
                    "Record": {
                        "Data": {
                            "entity_id": f"temp{i}",
                            "activity_type": "create",
                            "file_path": f"C:/Temp/temp{i}.txt",
                            "file_name": f"temp{i}.txt",
                            "volume_name": "C:",
                            "is_directory": False,
                            "timestamp": (base_time - timedelta(hours=6, minutes=i * 10)).isoformat(),
                            "importance_score": 0.2,
                        },
                    },
                },
            )

        # Process activities
        processed = self.recorder.process_hot_tier_activities(activities)

        # Check results
        self.assertEqual(len(processed), 3)  # 3 groups

        # Check that we have the right activities
        aggregated_count = 0
        individual_count = 0

        for activity in processed:
            if activity.get("is_aggregated", False):
                aggregated_count += 1
            else:
                individual_count += 1

        self.assertEqual(aggregated_count, 2)  # Two aggregated groups
        self.assertEqual(individual_count, 1)  # One individual high-importance activity

    @patch.object(NtfsWarmTierRecorder, "transition_from_hot_tier")
    def test_tier_transition_manager(self, mock_transition):
        """Test the tier transition manager."""
        # Set up mock return value
        mock_transition.return_value = 5  # 5 activities transitioned

        # Create transition manager
        manager = TierTransitionManager(
            hot_tier_recorder=NtfsHotTierRecorder(no_db=True),
            warm_tier_recorder=self.recorder,
            age_threshold_hours=12,
            batch_size=100,
            debug=True,
        )

        # Replace the check_readiness method to return True
        manager.check_readiness = lambda: True

        # Run transition
        result = manager.run_transition(max_batches=1)

        # Check that transition was called
        mock_transition.assert_called_once()

        # Check result
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["total_activities_transitioned"], 5)


class TestImportanceScorer(unittest.TestCase):
    """Test the importance scoring functionality."""

    def setUp(self):
        """Set up test environment."""
        self.scorer = ImportanceScorer(debug=True)

    def test_recency_score(self):
        """Test recency-based scoring."""
        # Recent activity (within 1 day)
        recent_data = {"timestamp": datetime.now(UTC).isoformat()}
        recent_score = self.scorer._calculate_recency_score(recent_data)
        self.assertGreater(recent_score, 0.9)

        # Older activity (7 days ago)
        older_data = {"timestamp": (datetime.now(UTC) - timedelta(days=7)).isoformat()}
        older_score = self.scorer._calculate_recency_score(older_data)
        self.assertLess(older_score, 0.6)
        self.assertGreater(older_score, 0.4)

        # Very old activity (30 days ago)
        very_old_data = {"timestamp": (datetime.now(UTC) - timedelta(days=30)).isoformat()}
        very_old_score = self.scorer._calculate_recency_score(very_old_data)
        self.assertLess(very_old_score, 0.2)

    def test_content_score(self):
        """Test content-based scoring."""
        # Important document
        doc_data = {"file_path": "C:/Users/Documents/Project/report.docx", "is_directory": False}
        doc_score = self.scorer._calculate_content_score(doc_data)
        self.assertGreater(doc_score, 0.6)

        # Temporary file
        temp_data = {"file_path": "C:/Temp/cache/temp.txt", "is_directory": False}
        temp_score = self.scorer._calculate_content_score(temp_data)
        self.assertLess(temp_score, 0.4)

        # Directory test
        dir_data = {"file_path": "C:/Users/Documents/Project", "is_directory": True}
        dir_score = self.scorer._calculate_content_score(dir_data)
        self.assertGreater(dir_score, doc_score)  # Directories should score higher

    def test_type_score(self):
        """Test activity type scoring."""
        # Create activity
        create_data = {"activity_type": "create"}
        create_score = self.scorer._calculate_type_score(create_data)
        self.assertGreater(create_score, 0.6)

        # Close activity
        close_data = {"activity_type": "close"}
        close_score = self.scorer._calculate_type_score(close_data)
        self.assertLess(close_score, create_score)

    def test_overall_scoring(self):
        """Test overall importance scoring with all factors."""
        # Important document, recent creation
        important_data = {
            "file_path": "C:/Users/Documents/Project/thesis.docx",
            "activity_type": "create",
            "timestamp": datetime.now(UTC).isoformat(),
            "is_directory": False,
        }
        important_score = self.scorer.calculate_importance(important_data)
        self.assertGreater(important_score, 0.7)

        # Temporary file, old modification
        unimportant_data = {
            "file_path": "C:/Temp/cache/temp.txt",
            "activity_type": "modify",
            "timestamp": (datetime.now(UTC) - timedelta(days=15)).isoformat(),
            "is_directory": False,
        }
        unimportant_score = self.scorer.calculate_importance(unimportant_data)
        self.assertLess(unimportant_score, 0.4)


"""
Transition Snapshots Tests: Verify run_transition_with_snapshots behavior
"""
class TestWarmTierTransitionSnapshots(unittest.TestCase):
    """Test the warm-tier transition snapshots and compression logic."""

    def setUp(self):
        # Create a temporary data directory for snapshots
        import tempfile
        self.temp_dir = tempfile.mkdtemp()

        # Initialize recorder in no-db mode with snapshot dir
        self.recorder = NtfsWarmTierRecorder(
            ttl_days=1,
            debug=False,
            no_db=True,
            transition_enabled=True,
            data_dir=self.temp_dir,
        )

        # Prepare fake hot-tier documents and processed warm-tier docs
        self.raw_docs = [{'_key': f'doc{i}', 'foo': 'bar'} for i in range(5)]
        self.processed_docs = self.raw_docs[:2]

        # Monkey-patch methods
        self.recorder.find_hot_tier_activities_to_transition = MagicMock(return_value=self.raw_docs)
        self.recorder.process_hot_tier_activities = MagicMock(return_value=self.processed_docs)
        self.recorder.store_activities = MagicMock()
        self.recorder.mark_hot_tier_activities_transitioned = MagicMock()

    def tearDown(self):
        # Remove temporary data directory
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_run_transition_with_snapshots_creates_files_and_calls_store(self):
        # Execute transition with snapshots
        hot_count, warm_count = self.recorder.run_transition_with_snapshots(
            age_threshold_hours=1,
            batch_size=10,
            data_root=self.temp_dir,
        )
        # Verify counts
        self.assertEqual(hot_count, len(self.raw_docs))
        self.assertEqual(warm_count, len(self.processed_docs))

        # Verify store_activities called with processed docs
        self.recorder.store_activities.assert_called_once_with(self.processed_docs)

        # Verify snapshot files exist and have correct line counts
        import os
        # Locate snapshot subdirectory
        snapshot_root = os.path.join(self.temp_dir, 'warm_snapshots')
        subdirs = os.listdir(snapshot_root)
        self.assertEqual(len(subdirs), 1)
        snapshot_dir = os.path.join(snapshot_root, subdirs[0])
        hot_path = os.path.join(snapshot_dir, 'hot.jsonl')
        warm_path = os.path.join(snapshot_dir, 'warm.jsonl')
        self.assertTrue(os.path.isfile(hot_path))
        self.assertTrue(os.path.isfile(warm_path))

        # Check line counts
        with open(hot_path, 'r', encoding='utf-8') as hf:
            self.assertEqual(sum(1 for _ in hf), len(self.raw_docs))
        with open(warm_path, 'r', encoding='utf-8') as wf:
            self.assertEqual(sum(1 for _ in wf), len(self.processed_docs))

if __name__ == "__main__":
    # Run tests
    unittest.main()
    
class TestWarmTierTransitionIntegration(unittest.TestCase):
    """Integration test: run transition against a live test database."""

    @classmethod
    def setUpClass(cls):
        # Attempt to load real database config
        from db.db_config import IndalekoDBConfig
        import tempfile, shutil

        # Path to test DB config (adjust as needed)
        config_path = os.path.join(os.environ.get("INDALEKO_ROOT", ""), "config", "indaleko-db-config-local.ini")
        if not os.path.exists(config_path):
            raise unittest.SkipTest(f"Integration DB config not found: {config_path}")
        # Connect to DB
        cls.db_config = IndalekoDBConfig(config_file=config_path)
        if not getattr(cls.db_config, 'started', False):
            raise unittest.SkipTest("Could not start database for integration test")
        cls.db = cls.db_config
        # Prepare test collections
        import uuid
        cls.hot_name = f"test_hot_{uuid.uuid4().hex[:8]}"
        cls.warm_name = f"test_warm_{uuid.uuid4().hex[:8]}"
        # Create or get collections
        cls.db_config._arangodb.db(cls.db_config.config['database']['database']).create_collection(cls.hot_name)
        cls.db_config._arangodb.db(cls.db_config.config['database']['database']).create_collection(cls.warm_name)
        cls.hot_coll = cls.db.get_collection(cls.hot_name)
        cls.warm_coll = cls.db.get_collection(cls.warm_name)
        # Insert test hot-tier docs (older than threshold)
        from datetime import UTC, datetime, timedelta
        now = datetime.now(UTC)
        docs = []
        for i in range(5):
            docs.append({
                '_key': f'doc{i}',
                'Record': {'Data': {
                    'timestamp': (now - timedelta(hours=13)).isoformat(),
                    'transitioned': False
                }}
            })
        for d in docs:
            cls.hot_coll.insert(d)
        # Create recorder
        tmpdir = tempfile.mkdtemp()
        cls.tmpdir = tmpdir
        from activity.recorders.storage.ntfs.tiered.warm.recorder import NtfsWarmTierRecorder
        cls.recorder = NtfsWarmTierRecorder(
            ttl_days=1,
            debug=False,
            no_db=True,
            transition_enabled=True,
            data_dir=tmpdir,
        )
        # Override DB and collections
        cls.recorder._db = cls.db_config
        cls.recorder._hot_tier_collection_name = cls.hot_name
        cls.recorder._collection_name = cls.warm_name
        cls.recorder._collection = cls.warm_coll

    @classmethod
    def tearDownClass(cls):
        # Cleanup test collections and tempdir
        cls.db_config._arangodb.db(cls.db_config.config['database']['database']).delete_collection(cls.hot_name)
        cls.db_config._arangodb.db(cls.db_config.config['database']['database']).delete_collection(cls.warm_name)
        import shutil
        shutil.rmtree(cls.tmpdir)

    def test_integration_transition_writes_db_and_snapshots(self):
        # Run transition
        hot_count, warm_count = self.recorder.run_transition_with_snapshots(
            age_threshold_hours=12,
            batch_size=10,
            data_root=self.tmpdir,
        )
        # Verify counts
        self.assertEqual(hot_count, 5)
        self.assertEqual(warm_count, 5)
        # Verify warm-tier collection has docs
        self.assertEqual(self.warm_coll.count(), 5)
        # Verify snapshot files exist
        snapshot_root = os.path.join(self.tmpdir, 'warm_snapshots')
        subdirs = os.listdir(snapshot_root)
        self.assertEqual(len(subdirs), 1)
        sd = os.path.join(snapshot_root, subdirs[0])
        self.assertTrue(os.path.isfile(os.path.join(sd, 'hot.jsonl')))
        self.assertTrue(os.path.isfile(os.path.join(sd, 'warm.jsonl')))
