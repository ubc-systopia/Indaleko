"""Integration tests for the ablation testing framework."""

import os
import shutil
import sys
import tempfile
import unittest
import uuid

# Add project root to path to resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from research.ablation.ablation_test_runner import AblationTestRunner
from research.ablation.ablation_tester import AblationConfig, AblationTester
from research.ablation.collectors.location_collector import LocationActivityCollector
from research.ablation.collectors.task_collector import TaskActivityCollector
from research.ablation.ner.entity_manager import NamedEntityManager
from research.ablation.recorders.location_recorder import LocationActivityRecorder
from research.ablation.recorders.task_recorder import TaskActivityRecorder


class TestAblationIntegration(unittest.TestCase):
    """Integration tests for the ablation testing framework."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures once for all tests."""
        # Create a temporary directory for test outputs
        cls.temp_dir = tempfile.mkdtemp()

        # Create entity manager
        cls.entity_manager = NamedEntityManager()

        # Create collectors
        cls.location_collector = LocationActivityCollector(entity_manager=cls.entity_manager)
        cls.task_collector = TaskActivityCollector(entity_manager=cls.entity_manager)

        # Create recorders
        cls.location_recorder = LocationActivityRecorder()
        cls.task_recorder = TaskActivityRecorder()

        # Create testers
        cls.tester = AblationTester()
        cls.runner = AblationTestRunner(output_dir=cls.temp_dir)

    def setUp(self):
        """Set up for each test."""
        # Clean up any existing test data
        self.location_recorder.delete_all()
        self.task_recorder.delete_all()

        # Generate small amount of test data
        self._generate_test_data()

    def _generate_test_data(self, num_records=10):
        """Generate test data for ablation testing.

        Args:
            num_records: Number of records to generate for each activity type.
        """
        # Generate and record location data
        location_data = self.location_collector.generate_batch(num_records)
        self.location_recorder.record_batch(location_data)

        # Generate and record task data
        task_data = self.task_collector.generate_batch(num_records)
        self.task_recorder.record_batch(task_data)

    def _generate_test_query(self, query_type="location"):
        """Generate a test query with truth data.

        Args:
            query_type: The type of query to generate ("location" or "task").

        Returns:
            tuple: (query_id, query_text)
        """
        query_id = uuid.uuid4()

        if query_type == "location":
            # Create a location query
            query_text = "Find files I accessed while at Home"

            # Generate matching data
            matching_data = self.location_collector.generate_matching_data(query_text, count=5)
            self.location_recorder.record_batch(matching_data)

            # Generate truth data
            entity_ids = self.location_collector.generate_truth_data(query_text)
            self.location_recorder.record_truth_data(query_id, entity_ids)

        else:  # task query
            # Create a task query
            query_text = "Find documents I edited in Microsoft Word"

            # Generate matching data
            matching_data = self.task_collector.generate_matching_data(query_text, count=5)
            self.task_recorder.record_batch(matching_data)

            # Generate truth data
            entity_ids = self.task_collector.generate_truth_data(query_text)
            self.task_recorder.record_truth_data(query_id, entity_ids)

        return query_id, query_text

    def test_ablate_and_restore_collection(self):
        """Test the ablation and restoration of a collection."""
        # Count records before ablation
        location_count_before = self.location_recorder.count_records()
        self.assertGreater(location_count_before, 0)

        # Ablate the collection
        result = self.tester.ablate_collection("AblationLocationActivity")
        self.assertTrue(result)

        # Count records after ablation
        location_count_after = self.location_recorder.count_records()
        self.assertEqual(location_count_after, 0)

        # Restore the collection
        result = self.tester.restore_collection("AblationLocationActivity")
        self.assertTrue(result)

        # Count records after restoration
        location_count_restored = self.location_recorder.count_records()
        self.assertEqual(location_count_restored, location_count_before)

    def test_single_ablation_test(self):
        """Test a single ablation test."""
        # Create a test query
        query_id, query_text = self._generate_test_query("location")

        # Run ablation test
        metrics = self.tester.test_ablation(
            query_id=query_id, query_text=query_text, collection_name="AblationLocationActivity", limit=10,
        )

        # Verify metrics were calculated
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics.query_id, query_id)
        self.assertEqual(metrics.ablated_collection, "AblationLocationActivity")

        # Metrics should have sensible values
        self.assertGreaterEqual(metrics.precision, 0)
        self.assertLessEqual(metrics.precision, 1)
        self.assertGreaterEqual(metrics.recall, 0)
        self.assertLessEqual(metrics.recall, 1)
        self.assertGreaterEqual(metrics.f1_score, 0)
        self.assertLessEqual(metrics.f1_score, 1)

    def test_run_ablation_test_batch(self):
        """Test running a batch of ablation tests."""
        # Create test queries
        location_query = {"id": str(uuid.uuid4()), "text": "Find files I accessed while at Home", "type": "location"}

        task_query = {"id": str(uuid.uuid4()), "text": "Find documents I edited in Microsoft Word", "type": "task"}

        # Generate truth data for each query
        location_collector = LocationActivityCollector(entity_manager=self.entity_manager)
        task_collector = TaskActivityCollector(entity_manager=self.entity_manager)

        # Location truth data
        matching_location = location_collector.generate_matching_data(location_query["text"], count=5)
        self.location_recorder.record_batch(matching_location)
        entity_ids = location_collector.generate_truth_data(location_query["text"])
        self.location_recorder.record_truth_data(uuid.UUID(location_query["id"]), entity_ids)

        # Task truth data
        matching_task = task_collector.generate_matching_data(task_query["text"], count=5)
        self.task_recorder.record_batch(matching_task)
        entity_ids = task_collector.generate_truth_data(task_query["text"])
        self.task_recorder.record_truth_data(uuid.UUID(task_query["id"]), entity_ids)

        # Create config
        config = AblationConfig(
            collections_to_ablate=["AblationLocationActivity", "AblationTaskActivity"],
            query_limit=10,
            include_metrics=True,
            include_execution_time=True,
            verbose=False,
        )

        # Run batch tests
        results = self.runner.run_batch_tests(queries=[location_query, task_query], config=config, max_queries=2)

        # Verify results were returned
        self.assertIsNotNone(results)
        self.assertGreaterEqual(len(results), 1)

        # Both queries should be in results
        self.assertIn(location_query["id"], results)
        self.assertIn(task_query["id"], results)

    def test_generate_reports_and_visualizations(self):
        """Test generation of reports and visualizations."""
        # Create test queries and run batch tests
        location_query = {"id": str(uuid.uuid4()), "text": "Find files I accessed while at Home", "type": "location"}

        task_query = {"id": str(uuid.uuid4()), "text": "Find documents I edited in Microsoft Word", "type": "task"}

        # Generate truth data for each query
        location_collector = LocationActivityCollector(entity_manager=self.entity_manager)
        task_collector = TaskActivityCollector(entity_manager=self.entity_manager)

        # Location truth data
        matching_location = location_collector.generate_matching_data(location_query["text"], count=5)
        self.location_recorder.record_batch(matching_location)
        entity_ids = location_collector.generate_truth_data(location_query["text"])
        self.location_recorder.record_truth_data(uuid.UUID(location_query["id"]), entity_ids)

        # Task truth data
        matching_task = task_collector.generate_matching_data(task_query["text"], count=5)
        self.task_recorder.record_batch(matching_task)
        entity_ids = task_collector.generate_truth_data(task_query["text"])
        self.task_recorder.record_truth_data(uuid.UUID(task_query["id"]), entity_ids)

        # Create config
        config = AblationConfig(
            collections_to_ablate=["AblationLocationActivity", "AblationTaskActivity"], query_limit=10,
        )

        # Run batch tests
        self.runner.run_batch_tests(queries=[location_query, task_query], config=config, max_queries=2)

        # Generate reports
        json_path = self.runner.save_results_json()
        csv_path = self.runner.save_results_csv()
        summary_path = self.runner.generate_summary_report()

        # Verify reports were generated
        self.assertTrue(os.path.exists(json_path))
        self.assertTrue(os.path.exists(csv_path))
        self.assertTrue(os.path.exists(summary_path))

        # Generate visualizations
        try:
            viz_paths = self.runner.generate_visualizations()

            # Verify visualizations were generated
            for viz_path in viz_paths:
                self.assertTrue(os.path.exists(viz_path))
        except ImportError:
            # Skip visualization tests if matplotlib/pandas not available
            pass

    def tearDown(self):
        """Clean up after each test."""
        # Clean up the test data
        self.location_recorder.delete_all()
        self.task_recorder.delete_all()

        # Clean up the tester
        self.tester.cleanup()
        self.runner.cleanup()

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        # Clean up the temporary directory
        shutil.rmtree(cls.temp_dir)


if __name__ == "__main__":
    unittest.main()
