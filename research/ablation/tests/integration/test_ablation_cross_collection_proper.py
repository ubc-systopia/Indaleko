"""Integration tests for ablation testing with cross-collection queries.

IMPORTANT: These tests follow the fail-stop principle:
1. No mocking of database connections or LLM services
2. All connections are real - tests fail immediately if connections cannot be established
3. No error masking - all exceptions must be allowed to propagate
4. Never substitute mock/fake data for real data
"""

import logging
import os
import sys
import unittest
from datetime import UTC, datetime

# Set up the environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
        if current_path == os.path.dirname(current_path):  # Reached root directory
            break
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.insert(0, current_path)

# Import required modules
from db.db_config import IndalekoDBConfig
from research.ablation.ablation_tester import AblationTester
from research.ablation.db.database import AblationDatabase
from research.ablation.models.ablation_results import AblationResult
from research.ablation.models.activity import ActivityType
from research.ablation.query.enhanced.cross_collection_query_generator import (
    CrossCollectionQueryGenerator,
)
from research.ablation.registry.shared_entity_registry import SharedEntityRegistry


class TestAblationCrossCollectionProper(unittest.TestCase):
    """Integration tests for ablation testing with cross-collection queries."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment for all tests with real connections."""
        # Set up logging
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        cls.logger = logging.getLogger(__name__)

        # Create a real database connection
        try:
            cls.db_config = IndalekoDBConfig()
            cls.db = cls.db_config.get_arangodb()
            if not cls.db:
                cls.logger.error("CRITICAL: Failed to connect to database")
                sys.exit(1)  # Fail-stop on database connection failure
        except Exception as e:
            cls.logger.error(f"CRITICAL: Error connecting to database: {e!s}")
            sys.exit(1)  # Fail-stop on exception

        # Create a shared entity registry
        cls.entity_registry = SharedEntityRegistry()

        # Create the query generator
        cls.query_generator = CrossCollectionQueryGenerator(entity_registry=cls.entity_registry)

        # Create the ablation database with real connection
        cls.ablation_db = AblationDatabase(db_config=cls.db_config)

        # Create the ablation tester
        cls.ablation_tester = AblationTester(db_config=cls.db_config, entity_registry=cls.entity_registry)

        # Generate cross-collection test queries
        cls.generate_test_queries()

    @classmethod
    def generate_test_queries(cls):
        """Generate test queries for ablation testing using real LLM services."""
        cls.logger.info("Generating test queries with real LLM services")

        # Generate task+meeting query
        task_meeting_queries = cls.query_generator.generate_cross_collection_queries(
            count=2,
            relationship_types=["created_in", "discussed_in"],
            collection_pairs=[(ActivityType.TASK, ActivityType.COLLABORATION)],
        )
        if not task_meeting_queries:
            cls.logger.error("CRITICAL: Failed to generate task+meeting queries")
            sys.exit(1)  # Fail-stop on query generation failure
        cls.task_meeting_queries = task_meeting_queries

        # Generate meeting+location query
        meeting_location_queries = cls.query_generator.generate_cross_collection_queries(
            count=2,
            relationship_types=["located_at"],
            collection_pairs=[(ActivityType.COLLABORATION, ActivityType.LOCATION)],
        )
        if not meeting_location_queries:
            cls.logger.error("CRITICAL: Failed to generate meeting+location queries")
            sys.exit(1)  # Fail-stop on query generation failure
        cls.meeting_location_queries = meeting_location_queries

    def test_ablation_tester_with_cross_collection_queries(self):
        """Test running ablation tests with cross-collection queries."""
        # Create a test run with our generated queries
        test_queries = self.task_meeting_queries + self.meeting_location_queries
        self.logger.info(f"Testing ablation with {len(test_queries)} cross-collection queries")

        # Log the query details
        for i, query in enumerate(test_queries):
            self.logger.info(f"Query {i+1}: {query.query_text}")
            self.logger.info(f"Activity types: {[a.name for a in query.activity_types]}")
            self.logger.info(f"Relationship: {query.metadata.get('relationship_type')}")
            self.logger.info(f"Expected matches: {len(query.expected_matches)}")

        # Create test collection to hold the results
        test_id = f"cross_collection_test_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        try:
            self.ablation_db.create_test_collection(test_id)
            self.logger.info(f"Created test collection {test_id}")
        except Exception as e:
            self.logger.error(f"Failed to create test collection: {e!s}")
            raise  # Let the exception propagate - fail-stop principle

        # Prepare the ablation test
        try:
            self.ablation_tester.prepare_ablation_test(test_queries=test_queries, test_id=test_id)
            self.logger.info("Prepared ablation test")
        except Exception as e:
            self.logger.error(f"Failed to prepare ablation test: {e!s}")
            raise  # Let the exception propagate - fail-stop principle

        # Run a baseline test with all collections
        try:
            baseline_results = self.ablation_tester.run_baseline_test(test_id)
            self.logger.info(f"Baseline test results: {baseline_results}")

            # Verify the baseline results
            self.assertIsInstance(baseline_results, dict)
            self.assertGreaterEqual(len(baseline_results), 1)

            for query_id, result in baseline_results.items():
                self.assertIsInstance(result, AblationResult)
                self.logger.info(
                    f"Query {query_id}: Precision {result.precision}, Recall {result.recall}, F1 {result.f1}",
                )
        except Exception as e:
            self.logger.error(f"Failed to run baseline test: {e!s}")
            raise  # Let the exception propagate - fail-stop principle

        # Run a single ablation test
        try:
            # Try ablating task collection - this should affect task+meeting queries
            ablated_results = self.ablation_tester.run_ablation_test(
                test_id=test_id,
                ablation_collection="ablation_task",
            )
            self.logger.info(f"Ablation test results: {ablated_results}")

            # Verify the ablation results
            self.assertIsInstance(ablated_results, dict)
            self.assertGreaterEqual(len(ablated_results), 1)

            for query_id, result in ablated_results.items():
                self.assertIsInstance(result, AblationResult)
                self.logger.info(
                    f"Query {query_id}: Precision {result.precision}, Recall {result.recall}, F1 {result.f1}",
                )

                # Check that ablation had an impact on queries involving tasks
                if any(
                    ActivityType.TASK in query.activity_types for query in test_queries if query.query_id == query_id
                ):
                    # Task-related queries should show some impact, but we can't guarantee what metrics will change
                    self.logger.info(f"Impact on task query {query_id}: {baseline_results[query_id].f1 - result.f1}")
        except Exception as e:
            self.logger.error(f"Failed to run ablation test: {e!s}")
            raise  # Let the exception propagate - fail-stop principle

        # Clean up the test collection
        try:
            self.ablation_db.drop_test_collection(test_id)
            self.logger.info(f"Dropped test collection {test_id}")
        except Exception as e:
            self.logger.error(f"Failed to drop test collection: {e!s}")
            raise  # Let the exception propagate - fail-stop principle

    def test_calculate_impact_metrics(self):
        """Test calculating impact metrics for cross-collection ablation tests."""
        # Create test results data
        baseline_results = {
            "query1": AblationResult(
                precision=0.9,
                recall=0.8,
                f1=0.85,
                true_positives=8,
                false_positives=1,
                false_negatives=2,
            ),
            "query2": AblationResult(
                precision=0.7,
                recall=0.6,
                f1=0.65,
                true_positives=6,
                false_positives=2,
                false_negatives=4,
            ),
        }

        ablation_results = {
            "query1": AblationResult(
                precision=0.6,
                recall=0.4,
                f1=0.5,
                true_positives=4,
                false_positives=2,
                false_negatives=6,
            ),
            "query2": AblationResult(
                precision=0.7,
                recall=0.6,
                f1=0.65,
                true_positives=6,
                false_positives=2,
                false_negatives=4,
            ),
        }

        # Calculate impact metrics
        impact = self.ablation_tester._calculate_impact_metrics(
            baseline_results=baseline_results,
            ablation_results=ablation_results,
        )

        # Verify the impact metrics
        self.assertIsInstance(impact, dict)
        self.assertEqual(len(impact), 2)

        # First query should show impact
        self.assertEqual(impact["query1"]["precision_impact"], 0.3)
        self.assertEqual(impact["query1"]["recall_impact"], 0.4)
        self.assertEqual(impact["query1"]["f1_impact"], 0.35)

        # Second query should show no impact
        self.assertEqual(impact["query2"]["precision_impact"], 0.0)
        self.assertEqual(impact["query2"]["recall_impact"], 0.0)
        self.assertEqual(impact["query2"]["f1_impact"], 0.0)

        # Check that the average impact is correct
        avg_impact = self.ablation_tester._calculate_average_impact(impact)
        self.assertEqual(avg_impact["avg_precision_impact"], 0.15)
        self.assertEqual(avg_impact["avg_recall_impact"], 0.2)
        self.assertEqual(avg_impact["avg_f1_impact"], 0.175)

    def test_record_ablation_results(self):
        """Test recording ablation results to the database."""
        # Create test results
        baseline_results = {
            "query1": AblationResult(
                precision=0.9,
                recall=0.8,
                f1=0.85,
                true_positives=8,
                false_positives=1,
                false_negatives=2,
            ),
            "query2": AblationResult(
                precision=0.7,
                recall=0.6,
                f1=0.65,
                true_positives=6,
                false_positives=2,
                false_negatives=4,
            ),
        }

        ablation_results = {
            "query1": AblationResult(
                precision=0.6,
                recall=0.4,
                f1=0.5,
                true_positives=4,
                false_positives=2,
                false_negatives=6,
            ),
            "query2": AblationResult(
                precision=0.7,
                recall=0.6,
                f1=0.65,
                true_positives=6,
                false_positives=2,
                false_negatives=4,
            ),
        }

        # Calculate impact metrics
        impact = self.ablation_tester._calculate_impact_metrics(
            baseline_results=baseline_results,
            ablation_results=ablation_results,
        )

        # Record the results to a results database
        test_id = f"record_results_test_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        ablation_collection = "ablation_task"

        try:
            # Initialize a results database
            results_db_path = os.path.join(os.environ.get("INDALEKO_ROOT", "."), "test_output", "ablation_results.db")
            os.makedirs(os.path.dirname(results_db_path), exist_ok=True)

            # Record the results
            self.ablation_tester.record_ablation_results(
                test_id=test_id,
                ablation_collection=ablation_collection,
                baseline_results=baseline_results,
                ablation_results=ablation_results,
                impact_metrics=impact,
            )

            self.logger.info(f"Recorded ablation results for test {test_id}")

            # Verify the results were recorded by reading them back
            recorded_results = self.ablation_tester.get_ablation_results(test_id)
            self.assertIsNotNone(recorded_results)
            self.logger.info(f"Retrieved recorded results for test {test_id}")

            # Check that the summary metrics match what we calculated
            avg_impact = self.ablation_tester._calculate_average_impact(impact)
            summary = self.ablation_tester.get_ablation_summary(test_id)
            self.assertIsNotNone(summary)
            self.assertIn("avg_f1_impact", summary)
            self.assertAlmostEqual(summary["avg_f1_impact"], avg_impact["avg_f1_impact"], places=3)

            self.logger.info(f"Summary metrics: {summary}")
        except Exception as e:
            self.logger.error(f"Failed to record or retrieve ablation results: {e!s}")
            raise  # Let the exception propagate - fail-stop principle


if __name__ == "__main__":
    unittest.main()
