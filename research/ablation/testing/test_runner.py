"""Ablation test runner for measuring the impact of different activity types."""

import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from db.db_collections import IndalekoDBCollections
from db.db_config import IndalekoDBConfig

from ..db.database import AblationDatabaseManager
from ..models.ablation_results import (
    AblationQueryTruth,
    AblationResult,
    AblationTestMetadata,
    MetricType,
)
from ..models.activity import ActivityType
from ..query.generator import QueryGenerator
from ..query.truth_tracker import TruthTracker


class AblationTestRunner:
    """Test runner for ablation studies.

    This class manages the execution of ablation tests, measuring the
    impact of different activity types on query results.
    """

    def __init__(self, test_name: str, description: str = ""):
        """Initialize the ablation test runner.

        Args:
            test_name: The name of the test run.
            description: Optional description of the test run.
        """
        self.logger = logging.getLogger(__name__)
        self.db_manager = AblationDatabaseManager()
        self.query_generator = QueryGenerator()
        self.truth_tracker = TruthTracker()

        # Set up test metadata
        self.test_id = uuid.uuid4()
        self.test_name = test_name
        self.description = description
        self.timestamp = datetime.now(UTC)

        # Track collections that should be tested
        self.test_collections = [
            IndalekoDBCollections.Indaleko_Ablation_Music_Activity_Collection,
            IndalekoDBCollections.Indaleko_Ablation_Location_Activity_Collection,
            IndalekoDBCollections.Indaleko_Ablation_Task_Activity_Collection,
            IndalekoDBCollections.Indaleko_Ablation_Collaboration_Activity_Collection,
            IndalekoDBCollections.Indaleko_Ablation_Storage_Activity_Collection,
            IndalekoDBCollections.Indaleko_Ablation_Media_Activity_Collection,
        ]

        # Tracking metrics
        self.results: list[AblationResult] = []
        self.summary_metrics: dict[str, dict[str, float]] = {}
        self.impact_ranking: list[dict[str, str | float]] = []
        self.total_execution_time_ms = 0
        self.query_count = 0

        # Ensure database connection
        try:
            self.db_config = IndalekoDBConfig()
            self.db = self.db_config.get_arangodb()
        except Exception as e:
            self.logger.error(f"FATAL: Failed to connect to database: {e}")
            # Database connection is required, so this is always a fatal error
            raise RuntimeError(f"Database connection is required. Error: {e}") from e

        # Ensure all required collections exist
        if not self.db_manager.ensure_collections():
            raise RuntimeError("Failed to ensure collections exist")

    def run_test(
        self,
        num_queries: int = 25,
        activity_types: list[ActivityType] | None = None,
        difficulty_levels: list[str] | None = None,
    ) -> AblationTestMetadata:
        """Run a complete ablation test.

        Args:
            num_queries: Number of queries to generate and test.
            activity_types: Optional list of specific activity types to test.
                           If None, all activity types will be tested.
            difficulty_levels: Optional list of difficulty levels to include.
                             If None, all difficulty levels will be used.

        Returns:
            AblationTestMetadata: Metadata about the completed test run.
        """
        self.logger.info(f"Starting ablation test: {self.test_name}")
        start_time = time.time()

        # Filter collections by activity types if specified
        if activity_types:
            activity_type_names = [at.name for at in activity_types]
            self.test_collections = [
                col for col in self.test_collections if any(at in col for at in activity_type_names)
            ]

        self.logger.info(f"Testing collections: {self.test_collections}")

        # Generate test queries
        queries = self._generate_queries(num_queries, activity_types, difficulty_levels)
        self.query_count = len(queries)
        self.logger.info(f"Generated {self.query_count} test queries")

        # Run tests for each query against each collection
        for query in queries:
            self._test_query(query)

        # Calculate summary metrics
        self._calculate_summary_metrics()

        # Calculate total execution time
        self.total_execution_time_ms = (time.time() - start_time) * 1000
        self.average_query_time_ms = self.total_execution_time_ms / self.query_count if self.query_count > 0 else 0

        # Create and save test metadata
        metadata = self._create_test_metadata()
        self._save_test_metadata(metadata)

        self.logger.info(f"Completed ablation test: {self.test_name}")
        return metadata

    def _generate_queries(
        self,
        num_queries: int,
        activity_types: list[ActivityType] | None = None,
        difficulty_levels: list[str] | None = None,
    ) -> list[AblationQueryTruth]:
        """Generate test queries and their ground truth data.

        Args:
            num_queries: Number of queries to generate.
            activity_types: Optional list of specific activity types to target.
            difficulty_levels: Optional list of difficulty levels to include.

        Returns:
            List[AblationQueryTruth]: List of generated queries with ground truth.
        """
        self.logger.info(f"Generating {num_queries} test queries")

        # Generate diverse queries using the query generator
        # Using diverse queries helps ensure more meaningful ablation tests
        queries = self.query_generator.generate_diverse_queries(
            count=num_queries,
            activity_types=activity_types,
            difficulty_levels=difficulty_levels,
        )

        # Convert to AblationQueryTruth objects and save to database
        truth_queries = []
        for query in queries:
            # Try to get existing ground truth data for this query
            matching_ids = self.truth_tracker.get_matching_ids(query.query_text, query.activity_types)

            # If no matching IDs were found, we need to generate synthetic truth data
            if not matching_ids:
                self.logger.info(f"No existing truth data found for query: {query.query_text}")

                # Use the expected_matches from our enhanced query generator
                # This field is now populated during query generation
                matching_ids = query.expected_matches

                # Log the number of expected matches for debugging
                self.logger.info(f"Query has {len(matching_ids)} expected matches")

                # Record the ground truth data for future use
                self.truth_tracker.record_query_truth(
                    query_id=str(query.query_id),
                    matching_ids=matching_ids,
                    query_text=query.query_text,
                    activity_types=[at.name for at in query.activity_types],
                    difficulty=query.difficulty,
                    metadata=query.metadata,
                )

            # Create the query truth object
            truth = AblationQueryTruth(
                query_id=query.query_id,
                query_text=query.query_text,
                matching_ids=matching_ids,
                activity_types=[at.name for at in query.activity_types],
                synthetic=True,
                difficulty=query.difficulty,
                metadata=query.metadata,
            )

            # Add to list of truth queries
            truth_queries.append(truth)

            # Log the created truth object
            self.logger.info(f"Created truth object with {len(truth.matching_ids)} matching documents")

        return truth_queries

    def _test_query(self, query: AblationQueryTruth) -> None:
        """Test a single query against all collections.

        This method runs the query with no collections ablated (baseline),
        then runs it with each test collection ablated one by one.

        Args:
            query: The query to test.
        """
        self.logger.info(f"Testing query: {query.query_text}")

        # Run baseline query (no collections ablated)
        baseline_start = time.time()
        baseline_results = self._execute_query(query.query_text)
        baseline_time_ms = (time.time() - baseline_start) * 1000

        # Calculate baseline metrics
        baseline_metrics = self._calculate_metrics(query.matching_ids, [doc["_id"] for doc in baseline_results])

        # Test each collection
        for collection_name in self.test_collections:
            self.logger.info(f"Testing with {collection_name} ablated")

            # Ablate the collection
            if not self.db_manager.ablate_collection(collection_name):
                self.logger.error(f"Failed to ablate collection {collection_name}")
                continue

            try:
                # Run the query with the collection ablated
                ablated_start = time.time()
                ablated_results = self._execute_query(query.query_text)
                ablated_time_ms = (time.time() - ablated_start) * 1000

                # Calculate metrics with the collection ablated
                ablated_metrics = self._calculate_metrics(query.matching_ids, [doc["_id"] for doc in ablated_results])

                # Calculate impact metrics
                impact_metrics = {
                    metric: baseline_metrics[metric] - ablated_metrics[metric] for metric in baseline_metrics
                }

                # Create and save result
                result = AblationResult(
                    test_id=self.test_id,
                    query_id=query.query_id,
                    query_text=query.query_text,
                    ablated_collection=collection_name,
                    timestamp=datetime.now(UTC),
                    baseline_metrics=baseline_metrics,
                    ablated_metrics=ablated_metrics,
                    impact_metrics=impact_metrics,
                    baseline_result_count=len(baseline_results),
                    ablated_result_count=len(ablated_results),
                    execution_time_ms=ablated_time_ms,
                )

                self._save_result(result)
                self.results.append(result)

            finally:
                # Restore the collection
                if not self.db_manager.restore_collection(collection_name):
                    self.logger.error(f"Failed to restore collection {collection_name}")

        self.logger.info(f"Completed testing for query: {query.query_text}")

    def _execute_query(self, query_text: str) -> list[dict[str, Any]]:
        """Execute a query and return the results.

        Args:
            query_text: The natural language query to execute.

        Returns:
            List[Dict[str, Any]]: The query results.
        """
        # This is a placeholder for the actual query execution
        # In a real implementation, this would translate the natural language
        # query to AQL and execute it using the query subsystem

        self.logger.info(f"Executing query: {query_text}")

        try:
            # Here we would use the query translation and execution components
            # For now, we'll just execute a simple AQL query as a placeholder
            # This should be replaced with the actual query execution logic

            # Example placeholder implementation:
            aql = """
            FOR doc IN Objects
            FILTER LIKE(doc.Label, CONCAT('%', @query, '%'), true)
            LIMIT 100
            RETURN doc
            """

            cursor = self.db.aql.execute(aql, bind_vars={"query": query_text}, batch_size=100)

            return list(cursor)

        except Exception as e:
            self.logger.error(f"Error executing query '{query_text}': {e}")
            return []

    def _calculate_metrics(self, truth_ids: list[str], result_ids: list[str]) -> dict[str, float]:
        """Calculate performance metrics for query results.

        Args:
            truth_ids: List of IDs that should match the query.
            result_ids: List of IDs returned by the query.

        Returns:
            Dict[str, float]: Dictionary of metric names to values.
        """
        # Convert lists to sets for easier comparison
        truth_set = set(truth_ids)
        result_set = set(result_ids)

        # Calculate true positives, false positives, and false negatives
        true_positives = len(truth_set.intersection(result_set))
        false_positives = len(result_set - truth_set)
        false_negatives = len(truth_set - result_set)

        # Calculate precision, recall, and F1 score
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        return {
            MetricType.PRECISION.value: precision,
            MetricType.RECALL.value: recall,
            MetricType.F1_SCORE.value: f1_score,
        }

    def _calculate_summary_metrics(self) -> None:
        """Calculate summary metrics across all tests."""
        if not self.results:
            self.logger.warning("No results to calculate summary metrics")
            return

        # Group results by collection
        results_by_collection: dict[str, list[AblationResult]] = {}
        for result in self.results:
            if result.ablated_collection not in results_by_collection:
                results_by_collection[result.ablated_collection] = []
            results_by_collection[result.ablated_collection].append(result)

        # Calculate average metrics for each collection
        for collection, results in results_by_collection.items():
            # Calculate average impact
            avg_impact = {
                metric: sum(r.impact_metrics.get(metric, 0) for r in results) / len(results)
                for metric in MetricType.__members__.values()
                if any(metric in r.impact_metrics for r in results)
            }

            # Store in summary metrics
            self.summary_metrics[collection] = avg_impact

        # Create impact ranking based on F1 score impact
        self.impact_ranking = [
            {"collection": collection, "impact": metrics.get(MetricType.F1_SCORE.value, 0)}
            for collection, metrics in self.summary_metrics.items()
        ]

        # Sort by impact (highest first)
        self.impact_ranking.sort(key=lambda x: x["impact"], reverse=True)

    def _create_test_metadata(self) -> AblationTestMetadata:
        """Create test metadata from the current test state.

        Returns:
            AblationTestMetadata: Metadata about the test run.
        """
        return AblationTestMetadata(
            id=uuid.uuid4(),
            test_id=self.test_id,
            test_name=self.test_name,
            description=self.description,
            timestamp=self.timestamp,
            ablation_collections=self.test_collections,
            query_count=self.query_count,
            environment={
                "python_version": "3.x",  # This would be dynamic in a real implementation
                "platform": "unknown",  # This would be dynamic in a real implementation
            },
            summary_metrics=self.summary_metrics,
            impact_ranking=self.impact_ranking,
            total_execution_time_ms=self.total_execution_time_ms,
            average_query_time_ms=self.average_query_time_ms,
        )

    def _save_result(self, result: AblationResult) -> str | None:
        """Save an ablation result to the database.

        Args:
            result: The ablation result to save.

        Returns:
            Optional[str]: The document key if saved successfully, None otherwise.
        """
        try:
            # Convert to dictionary for storage
            result_dict = result.dict()

            # Convert UUID to string
            result_dict["id"] = str(result_dict["id"])
            result_dict["test_id"] = str(result_dict["test_id"])
            result_dict["query_id"] = str(result_dict["query_id"])

            # Insert into the database
            collection = self.db.collection(IndalekoDBCollections.Indaleko_Ablation_Results_Collection)
            result = collection.insert(result_dict)
            return result.get("_key") if result else None

        except Exception as e:
            self.logger.error(f"Failed to save result: {e}")
            return None

    def _save_test_metadata(self, metadata: AblationTestMetadata) -> str | None:
        """Save test metadata to the database.

        Args:
            metadata: The test metadata to save.

        Returns:
            Optional[str]: The document key if saved successfully, None otherwise.
        """
        try:
            # Convert to dictionary for storage
            metadata_dict = metadata.dict()

            # Convert UUID to string
            metadata_dict["id"] = str(metadata_dict["id"])
            metadata_dict["test_id"] = str(metadata_dict["test_id"])

            # Insert into the database
            collection = self.db.collection(IndalekoDBCollections.Indaleko_Ablation_Test_Metadata_Collection)
            result = collection.insert(metadata_dict)
            return result.get("_key") if result else None

        except Exception as e:
            self.logger.error(f"Failed to save test metadata: {e}")
            return None
