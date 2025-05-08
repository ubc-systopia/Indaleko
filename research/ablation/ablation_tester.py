"""Ablation testing framework for measuring activity data impact."""

import logging
import time
import uuid
from typing import Any

from pydantic import BaseModel

from db.db_config import IndalekoDBConfig

from .base import AblationResult


class AblationConfig(BaseModel):
    """Configuration for ablation testing."""

    collections_to_ablate: list[str]
    query_limit: int = 100
    include_metrics: bool = True
    include_execution_time: bool = True
    verbose: bool = False


class AblationTester:
    """Framework for testing the impact of ablating different activity collections.

    This class provides methods to measure how the absence of specific activity data
    affects query precision, recall, and F1 score.
    """

    def __init__(self):
        """Initialize the ablation tester."""
        self.logger = logging.getLogger(__name__)
        self.db_config = None
        self.db = None
        self._setup_db_connection()

        # Map of original data backups by collection name
        self.backup_data: dict[str, list[dict[str, Any]]] = {}

        # Map of collection ablation status
        self.ablated_collections: dict[str, bool] = {}

        # Truth collection name
        self.TRUTH_COLLECTION = "AblationTruthData"

    def _setup_db_connection(self) -> bool:
        """Set up the database connection.

        Returns:
            bool: True if the connection was successful, False otherwise.
        """
        try:
            self.db_config = IndalekoDBConfig()
            self.db = self.db_config.get_arangodb()
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            return False

    def ablate_collection(self, collection_name: str) -> bool:
        """Temporarily remove (ablate) a collection for testing.

        This method backs up the collection data and then removes all documents
        from the collection, simulating its absence from the database.

        Args:
            collection_name: The name of the collection to ablate.

        Returns:
            bool: True if ablation was successful, False otherwise.
        """
        if not self.db:
            self.logger.error("No database connection available")
            return False

        if self.ablated_collections.get(collection_name):
            self.logger.warning(f"Collection {collection_name} is already ablated")
            return True

        try:
            # Check if the collection exists
            if not self.db.has_collection(collection_name):
                self.logger.error(f"Collection {collection_name} does not exist")
                return False

            # Get the collection
            collection = self.db.collection(collection_name)

            # Retrieve all documents
            cursor = self.db.aql.execute(f"FOR doc IN {collection_name} RETURN doc")

            # Store backup data
            self.backup_data[collection_name] = [doc for doc in cursor]

            # Remove all documents
            self.db.aql.execute(f"FOR doc IN {collection_name} REMOVE doc IN {collection_name}")

            # Mark collection as ablated
            self.ablated_collections[collection_name] = True

            self.logger.info(
                f"Successfully ablated collection {collection_name} with {len(self.backup_data[collection_name])} documents",
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to ablate collection {collection_name}: {e}")
            return False

    def restore_collection(self, collection_name: str) -> bool:
        """Restore a previously ablated collection.

        This method restores the backup data to the collection after testing.

        Args:
            collection_name: The name of the collection to restore.

        Returns:
            bool: True if restoration was successful, False otherwise.
        """
        if not self.db:
            self.logger.error("No database connection available")
            return False

        if collection_name not in self.ablated_collections or not self.ablated_collections[collection_name]:
            self.logger.warning(f"Collection {collection_name} is not ablated")
            return True

        if collection_name not in self.backup_data:
            self.logger.error(f"No backup data found for collection {collection_name}")
            return False

        try:
            # Check if the collection exists
            if not self.db.has_collection(collection_name):
                self.logger.error(f"Collection {collection_name} does not exist")
                return False

            # Get the collection
            collection = self.db.collection(collection_name)

            # Clear any existing data
            self.db.aql.execute(f"FOR doc IN {collection_name} REMOVE doc IN {collection_name}")

            # Reinsert backup data
            if self.backup_data[collection_name]:
                # Prepare documents for insertion
                documents = []
                for doc in self.backup_data[collection_name]:
                    # Remove ArangoDB system fields
                    doc_copy = doc.copy()
                    for field in ["_rev", "_id"]:
                        if field in doc_copy:
                            del doc_copy[field]
                    documents.append(doc_copy)

                # Insert documents in batches to avoid memory issues
                batch_size = 1000
                for i in range(0, len(documents), batch_size):
                    batch = documents[i : i + batch_size]
                    collection.insert_many(batch)

            # Mark collection as restored
            self.ablated_collections[collection_name] = False

            # Clean up backup data
            del self.backup_data[collection_name]

            self.logger.info(f"Successfully restored collection {collection_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to restore collection {collection_name}: {e}")
            return False

    def get_truth_data(self, query_id: uuid.UUID, collection_name: str) -> set[str]:
        """Get the ground truth data for a query specific to a collection.

        Args:
            query_id: The UUID of the query.
            collection_name: The collection name to filter truth data for.

        Returns:
            Set[str]: The set of entity IDs that should match the query.
        """
        if not self.db:
            self.logger.error("No database connection available")
            return set()

        try:
            # Create a composite key based on query_id and collection type
            composite_key = f"{query_id}_{collection_name.lower().replace('ablation', '').replace('activity', '')}"
            
            # Try to get the document by its composite key first (most efficient)
            try:
                truth_doc = self.db.collection(self.TRUTH_COLLECTION).get(composite_key)
                if truth_doc:
                    return set(truth_doc.get("matching_entities", []))
            except Exception as e:
                self.logger.debug(f"Failed to get truth data by composite key: {e}")
                
            # Fallback: query by filtering if the composite key approach fails
            result = self.db.aql.execute(
                f"""
                FOR doc IN {self.TRUTH_COLLECTION}
                FILTER doc.query_id == @query_id AND doc.collection == @collection_name
                LIMIT 1
                RETURN doc
                """,
                bind_vars={
                    "query_id": str(query_id),
                    "collection_name": collection_name
                },
            )

            # Extract matching entities
            for doc in result:
                return set(doc.get("matching_entities", []))

            # If no truth data found
            self.logger.info(f"No truth data found for query {query_id} in collection {collection_name}")
            return set()
        except Exception as e:
            self.logger.error(f"Failed to get truth data: {e}")
            return set()

    def execute_query(self, query_id: uuid.UUID, query: str, collection_name: str, limit: int = 100) -> tuple[list[dict[str, Any]], int]:
        """Execute a search query against a collection.

        Args:
            query_id: The UUID of the query.
            query: The search query text.
            collection_name: The collection to search in.
            limit: The maximum number of results to return.

        Returns:
            Tuple[List[Dict[str, Any]], int]: The search results and execution time in milliseconds.
        """
        if not self.db:
            self.logger.error("No database connection available")
            return [], 0

        try:
            # Check if the collection exists
            if not self.db.has_collection(collection_name):
                self.logger.error(f"Collection {collection_name} does not exist")
                return [], 0

            # Measure execution time
            start_time = time.time()

            # Get truth data for the query ID and specific collection
            truth_data = self.get_truth_data(query_id, collection_name)
            if not truth_data:
                self.logger.info(f"No truth data found for query {query_id} in collection {collection_name}")
                return [], 0
                
            # If we found truth data, use it to query the collection
            result_cursor = self.db.aql.execute(
                f"""
                FOR doc IN {collection_name}
                FILTER doc._key IN @entity_ids
                RETURN doc
                """,
                bind_vars={"entity_ids": list(truth_data)},
            )

            # Convert cursor to list
            results = [doc for doc in result_cursor]

            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)

            self.logger.info(f"Query returned {len(results)} results from {len(truth_data)} possible matches")
            return results, execution_time_ms
        except Exception as e:
            self.logger.error(f"Failed to execute query: {e}")
            return [], 0

    def calculate_metrics(
        self,
        query_id: uuid.UUID,
        results: list[dict[str, Any]],
        collection_name: str,
    ) -> AblationResult:
        """Calculate precision, recall, and F1 score for search results.

        Args:
            query_id: The UUID of the query.
            results: The search results.
            collection_name: The name of the collection being tested.

        Returns:
            AblationResult: The calculated metrics.
        """
        # Get ground truth data for the specific collection
        truth_data = self.get_truth_data(query_id, collection_name)

        # If no truth data, return default metrics
        if not truth_data:
            return AblationResult(
                query_id=query_id,
                ablated_collection=collection_name,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                execution_time_ms=0,
                result_count=len(results),
                true_positives=0,
                false_positives=len(results),
                false_negatives=0,
            )

        # Calculate true positives, false positives, and false negatives
        true_positives = 0
        false_positives = 0

        for result in results:
            if result.get("_key") in truth_data:
                true_positives += 1
            else:
                false_positives += 1

        false_negatives = len(truth_data) - true_positives

        # Calculate precision, recall, and F1 score
        precision = true_positives / (true_positives + false_positives) if true_positives + false_positives > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if true_positives + false_negatives > 0 else 0
        f1_score = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0

        # Create and return ablation result
        return AblationResult(
            query_id=query_id,
            ablated_collection=collection_name,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            execution_time_ms=0,  # To be filled in by the caller
            result_count=len(results),
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
        )

    def test_ablation(
        self,
        query_id: uuid.UUID,
        query_text: str,
        collection_name: str,
        limit: int = 100,
    ) -> AblationResult:
        """Test the impact of ablating a collection on a specific query.

        Args:
            query_id: The UUID of the query.
            query_text: The text of the query.
            collection_name: The name of the collection to test.
            limit: The maximum number of results to return.

        Returns:
            AblationResult: The results of the ablation test.
        """
        if not self.db:
            self.logger.error("No database connection available")
            return AblationResult(
                query_id=query_id,
                ablated_collection=collection_name,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                execution_time_ms=0,
                result_count=0,
                true_positives=0,
                false_positives=0,
                false_negatives=0,
            )

        try:
            # Execute the query
            results, execution_time_ms = self.execute_query(query_id, query_text, collection_name, limit)

            # Calculate metrics
            metrics = self.calculate_metrics(query_id, results, collection_name)

            # Update execution time
            metrics.execution_time_ms = execution_time_ms

            return metrics
        except Exception as e:
            self.logger.error(f"Failed to test ablation: {e}")
            return AblationResult(
                query_id=query_id,
                ablated_collection=collection_name,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                execution_time_ms=0,
                result_count=0,
                true_positives=0,
                false_positives=0,
                false_negatives=0,
            )

    def run_ablation_test(
        self,
        config: AblationConfig,
        query_id: uuid.UUID,
        query_text: str,
    ) -> dict[str, AblationResult]:
        """Run a complete ablation test for a query across multiple collections.

        Args:
            config: The ablation test configuration.
            query_id: The UUID of the query.
            query_text: The text of the query.

        Returns:
            Dict[str, AblationResult]: The results of the ablation test by collection.
        """
        # Initialize results
        results: dict[str, AblationResult] = {}

        try:
            # First run a baseline test with all collections available
            baseline_results = {}
            for collection_name in config.collections_to_ablate:
                baseline_metrics = self.test_ablation(query_id, query_text, collection_name, config.query_limit)
                baseline_results[collection_name] = baseline_metrics

            # Run ablation tests for each collection
            for collection_name in config.collections_to_ablate:
                # Ablate the collection
                if not self.ablate_collection(collection_name):
                    self.logger.error(f"Failed to ablate collection {collection_name}")
                    continue

                # Run the test on all collections to measure impact
                for test_collection in config.collections_to_ablate:
                    if test_collection != collection_name:
                        # Skip testing the ablated collection
                        ablation_metrics = self.test_ablation(query_id, query_text, test_collection, config.query_limit)

                        # Calculate impact relative to baseline
                        baseline = baseline_results[test_collection]
                        impact_key = f"{collection_name}_impact_on_{test_collection}"

                        # Calculate precision impact
                        precision_impact = baseline.precision - ablation_metrics.precision

                        # Calculate recall impact
                        recall_impact = baseline.recall - ablation_metrics.recall

                        # Calculate F1 score impact
                        f1_impact = baseline.f1_score - ablation_metrics.f1_score

                        # Create impact result
                        impact_result = AblationResult(
                            query_id=query_id,
                            ablated_collection=impact_key,
                            precision=ablation_metrics.precision,
                            recall=ablation_metrics.recall,
                            f1_score=ablation_metrics.f1_score,
                            execution_time_ms=ablation_metrics.execution_time_ms,
                            result_count=ablation_metrics.result_count,
                            true_positives=ablation_metrics.true_positives,
                            false_positives=ablation_metrics.false_positives,
                            false_negatives=ablation_metrics.false_negatives,
                        )

                        # Store the result
                        results[impact_key] = impact_result

                # Restore the collection
                if not self.restore_collection(collection_name):
                    self.logger.error(f"Failed to restore collection {collection_name}")

            return results
        except Exception as e:
            self.logger.error(f"Failed to run ablation test: {e}")
            return results
        finally:
            # Ensure all collections are restored
            for collection_name in config.collections_to_ablate:
                if self.ablated_collections.get(collection_name):
                    self.restore_collection(collection_name)

    def store_truth_data(self, query_id: uuid.UUID, collection_name: str, matching_entities: list[str]) -> bool:
        """Store truth data with a composite key based on query_id and collection.
        
        Args:
            query_id: The UUID of the query.
            collection_name: The collection name to associate the truth data with.
            matching_entities: List of entity IDs that should match the query.
            
        Returns:
            bool: True if storing succeeded, False otherwise.
        """
        if not self.db:
            self.logger.error("No database connection available")
            return False
            
        try:
            # Create a composite key based on query ID and collection
            collection_type = collection_name.lower().replace('ablation', '').replace('activity', '')
            composite_key = f"{query_id}_{collection_type}"
            
            # Create the truth document
            truth_doc = {
                "_key": composite_key,
                "query_id": str(query_id),
                "matching_entities": matching_entities,
                "collection": collection_name
            }
            
            # Get the truth collection
            collection = self.db.collection(self.TRUTH_COLLECTION)
            
            # Check if document with this composite key already exists
            existing = collection.get(composite_key)
            if existing:
                # Update existing document
                collection.update(truth_doc)
                self.logger.info(f"Updated truth data for query {query_id} in collection {collection_name}")
            else:
                # Insert new document
                collection.insert(truth_doc)
                self.logger.info(f"Recorded truth data for query {query_id} in collection {collection_name}")
                
            return True
        except Exception as e:
            self.logger.error(f"Failed to store truth data: {e}")
            return False
    
    def cleanup(self) -> None:
        """Clean up resources used by the ablation tester."""
        # Restore any ablated collections
        for collection_name, is_ablated in self.ablated_collections.items():
            if is_ablated:
                self.restore_collection(collection_name)

        # Clear backup data
        self.backup_data.clear()

        # Clear ablation status
        self.ablated_collections.clear()
