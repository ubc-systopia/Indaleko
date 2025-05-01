#!/usr/bin/env python3
"""
Integration Test for NTFS Warm Tier Transition

Runs an end-to-end transition from a real hot-tier collection to a real warm-tier collection
using a live ArangoDB instance configured via the project's test DB config.
"""
import os
import unittest
import tempfile
import shutil
import uuid
from datetime import UTC, datetime, timedelta

from db.db_config import IndalekoDBConfig
from activity.recorders.storage.ntfs.tiered.warm.recorder import NtfsWarmTierRecorder


class TestWarmTierTransitionIntegration(unittest.TestCase):
    """Live integration test against a test ArangoDB database."""

    @classmethod
    def setUpClass(cls):
        # Path to the test DB config
        root = os.environ.get("INDALEKO_ROOT", os.getcwd())
        config_path = os.path.join(root, "config", "indaleko-db-config-local.ini")
        if not os.path.exists(config_path):
            raise unittest.SkipTest(f"DB config not found: {config_path}")
        # Connect to DB
        cls.db_config = IndalekoDBConfig(config_file=config_path)
        if not getattr(cls.db_config, 'started', False):
            raise unittest.SkipTest("Database not available for integration test")
        # Prepare unique hot and warm collections
        cls.hot_name = f"test_hot_{uuid.uuid4().hex[:8]}"
        cls.warm_name = f"test_warm_{uuid.uuid4().hex[:8]}"
        # Create collections in ArangoDB
        db = cls.db_config._arangodb.db(cls.db_config.config['database']['database'])
        db.create_collection(cls.hot_name)
        db.create_collection(cls.warm_name)
        cls.hot_coll = cls.db_config.get_collection(cls.hot_name)
        cls.warm_coll = cls.db_config.get_collection(cls.warm_name)
        # Insert sample hot-tier documents older than threshold
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
        # Set up temp dir for snapshots
        cls.temp_dir = tempfile.mkdtemp()
        # Initialize recorder in no-db mode (we'll attach real DB)
        cls.recorder = NtfsWarmTierRecorder(
            ttl_days=1,
            debug=False,
            no_db=True,
            transition_enabled=True,
            data_dir=cls.temp_dir,
        )
        # Override with real DB and collections
        cls.recorder._db = cls.db_config
        cls.recorder._hot_tier_collection_name = cls.hot_name
        cls.recorder._collection_name = cls.warm_name
        cls.recorder._collection = cls.warm_coll

    @classmethod
    def tearDownClass(cls):
        # Drop test collections and remove snapshots
        db = cls.db_config._arangodb.db(cls.db_config.config['database']['database'])
        db.delete_collection(cls.hot_name)
        db.delete_collection(cls.warm_name)
        shutil.rmtree(cls.temp_dir)

    def test_transition_integration(self):
        # Run the transition with snapshots
        hot_count, warm_count = self.recorder.run_transition_with_snapshots(
            age_threshold_hours=12,
            batch_size=10,
            data_root=self.temp_dir,
        )
        # Verify counts and DB writes
        self.assertEqual(hot_count, 5)
        self.assertEqual(warm_count, 5)
        self.assertEqual(self.warm_coll.count(), 5)
        # Verify snapshots
        snapshot_root = os.path.join(self.temp_dir, 'warm_snapshots')
        subdirs = os.listdir(snapshot_root)
        self.assertEqual(len(subdirs), 1)
        sd = os.path.join(snapshot_root, subdirs[0])
        self.assertTrue(os.path.isfile(os.path.join(sd, 'hot.jsonl')))
        self.assertTrue(os.path.isfile(os.path.join(sd, 'warm.jsonl')))

if __name__ == '__main__':
    unittest.main()