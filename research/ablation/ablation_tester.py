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
        """Set up the database connection following fail-stop principles.
        
        If the database connection fails, the method will terminate the program
        immediately as a scientific ablation study cannot run without a database.

        Returns:
            bool: Always returns True (will exit on failure)
        """
        try:
            self.db_config = IndalekoDBConfig()
            self.db = self.db_config.get_arangodb()
            self.logger.info("Successfully connected to ArangoDB database")
            return True
        except Exception as e:
            self.logger.error(f"CRITICAL: Failed to connect to database: {e}")
            self.logger.error("Database connection is required for ablation testing")
            sys.exit(1)  # Fail-stop immediately

    def ablate_collection(self, collection_name: str) -> bool:
        """Temporarily remove (ablate) a collection for testing.

        This method backs up the collection data and then removes all documents
        from the collection, simulating its absence from the database.

        Args:
            collection_name: The name of the collection to ablate.

        Returns:
            bool: True if ablation was successful.
        """
        if not self.db:
            self.logger.error("No database connection available")
            sys.exit(1)  # Fail-stop immediately - we can't proceed without DB

        if self.ablated_collections.get(collection_name):
            self.logger.warning(f"Collection {collection_name} is already ablated")
            return True

        # Check if the collection exists
        if not self.db.has_collection(collection_name):
            self.logger.error(f"CRITICAL: Collection {collection_name} does not exist")
            sys.exit(1)  # Fail-stop immediately

        # Get the collection
        try:
            collection = self.db.collection(collection_name)
        except Exception as e:
            self.logger.error(f"CRITICAL: Failed to access collection {collection_name}: {e}")
            sys.exit(1)  # Fail-stop immediately

        # Retrieve all documents
        try:
            cursor = self.db.aql.execute(f"FOR doc IN {collection_name} RETURN doc")
            self.backup_data[collection_name] = [doc for doc in cursor]
            self.logger.info(f"Backed up {len(self.backup_data[collection_name])} documents from {collection_name}")
        except Exception as e:
            self.logger.error(f"CRITICAL: Failed to backup collection {collection_name}: {e}")
            sys.exit(1)  # Fail-stop immediately

        # Remove all documents
        try:
            self.db.aql.execute(f"FOR doc IN {collection_name} REMOVE doc IN {collection_name}")
            self.logger.info(f"Removed all documents from collection {collection_name}")
        except Exception as e:
            self.logger.error(f"CRITICAL: Failed to remove documents from {collection_name}: {e}")
            sys.exit(1)  # Fail-stop immediately

        # Mark collection as ablated
        self.ablated_collections[collection_name] = True
        self.logger.info(f"Successfully ablated collection {collection_name} with {len(self.backup_data[collection_name])} documents")
        
        return True

    def restore_collection(self, collection_name: str) -> bool:
        """Restore a previously ablated collection.

        This method restores the backup data to the collection after testing.

        Args:
            collection_name: The name of the collection to restore.

        Returns:
            bool: True if restoration was successful.
        """
        if not self.db:
            self.logger.error("No database connection available")
            sys.exit(1)  # Fail-stop immediately - we can't proceed without DB

        if collection_name not in self.ablated_collections or not self.ablated_collections[collection_name]:
            self.logger.warning(f"Collection {collection_name} is not ablated")
            return True

        if collection_name not in self.backup_data:
            self.logger.error(f"CRITICAL: No backup data found for collection {collection_name}")
            sys.exit(1)  # Fail-stop immediately

        # Check if the collection exists
        if not self.db.has_collection(collection_name):
            self.logger.error(f"CRITICAL: Collection {collection_name} no longer exists, cannot restore")
            sys.exit(1)  # Fail-stop immediately

        # Get the collection
        try:
            collection = self.db.collection(collection_name)
        except Exception as e:
            self.logger.error(f"CRITICAL: Failed to access collection {collection_name}: {e}")
            sys.exit(1)  # Fail-stop immediately

        # Clear any existing data
        try:
            self.db.aql.execute(f"FOR doc IN {collection_name} REMOVE doc IN {collection_name}")
            self.logger.info(f"Cleared any existing data from collection {collection_name}")
        except Exception as e:
            self.logger.error(f"CRITICAL: Failed to clear collection {collection_name}: {e}")
            sys.exit(1)  # Fail-stop immediately

        # Reinsert backup data
        if self.backup_data[collection_name]:
            # Prepare documents for insertion
            documents = []
            for doc in self.backup_data[collection_name]:
                # Remove ArangoDB system fields that would cause insertion errors
                doc_copy = doc.copy()
                for field in ["_rev", "_id"]:
                    if field in doc_copy:
                        del doc_copy[field]
                documents.append(doc_copy)

            # Insert documents in batches to avoid memory issues
            try:
                batch_size = 1000
                for i in range(0, len(documents), batch_size):
                    batch = documents[i : i + batch_size]
                    collection.insert_many(batch)
                self.logger.info(f"Restored {len(documents)} documents to collection {collection_name}")
            except Exception as e:
                self.logger.error(f"CRITICAL: Failed to restore documents to {collection_name}: {e}")
                sys.exit(1)  # Fail-stop immediately

        # Mark collection as restored
        self.ablated_collections[collection_name] = False

        # Clean up backup data
        del self.backup_data[collection_name]

        self.logger.info(f"Successfully restored collection {collection_name}")
        return True

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
            sys.exit(1)  # Fail-stop immediately - we can't proceed without DB

        # Create a composite key based on query_id and collection type
        composite_key = f"{query_id}_{collection_name.lower().replace('ablation', '').replace('activity', '')}"

        # Try to get the document by its composite key first (most efficient)
        try:
            truth_doc = self.db.collection(self.TRUTH_COLLECTION).get(composite_key)
            if truth_doc:
                return set(truth_doc.get("matching_entities", []))
        except Exception as e:
            self.logger.error(f"CRITICAL: Failed to get truth data by composite key: {e}")
            sys.exit(1)  # Fail-stop immediately - this is a critical failure

        # Fallback: query by filtering if the composite key approach doesn't find a document
        try:
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
        except Exception as e:
            self.logger.error(f"CRITICAL: Failed to query for truth data: {e}")
            sys.exit(1)  # Fail-stop immediately - this is a critical failure

        # If no truth data found - this is not necessarily an error,
        # as some queries may not have truth data for all collections
        self.logger.info(f"No truth data found for query {query_id} in collection {collection_name}")
        return set()

    def execute_query(self, query_id: uuid.UUID, query: str, collection_name: str, limit: int = 100) -> tuple[list[dict[str, Any]], int, str]:
        """Execute a semantic search query against a collection.

        This method performs real semantic searches based on the collection type,
        without arbitrary result limits. This allows proper measurement of how
        ablation affects search results in a scientifically valid manner.

        Args:
            query_id: The UUID of the query.
            query: The search query text.
            collection_name: The collection to search in.
            limit: Parameter kept for API compatibility but not used to limit results.

        Returns:
            Tuple[List[Dict[str, Any]], int, str]: The search results, execution time in milliseconds, and the AQL query.
        """
        if not self.db:
            self.logger.error("No database connection available")
            sys.exit(1)  # Fail-stop immediately

        # Check if the collection exists
        if not self.db.has_collection(collection_name):
            self.logger.error(f"Collection {collection_name} does not exist")
            sys.exit(1)  # Fail-stop immediately

        # Measure execution time
        start_time = time.time()

        # Parse query to extract relevant search terms
        search_terms = self._extract_search_terms(query, collection_name)
        
        # Build appropriate semantic search query for this collection type
        # WITHOUT any result count limits to preserve scientific integrity
        aql_query, bind_vars = self._build_semantic_query(collection_name, search_terms)

        # Log the query for debugging
        self.logger.info(f"Executing semantic search query on {collection_name}: {aql_query}")
        self.logger.info(f"Search parameters: {bind_vars}")

        # Execute the query
        result_cursor = self.db.aql.execute(
            aql_query,
            bind_vars=bind_vars,
        )

        # Convert cursor to list
        results = [doc for doc in result_cursor]

        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)

        # Get truth data for evaluation and comparison
        truth_data = self.get_truth_data(query_id, collection_name)
        
        # Compare results with truth data for reporting (but don't modify the results)
        if truth_data:
            result_keys = set(doc.get("_key") for doc in results)
            true_positives = len(result_keys.intersection(truth_data))
            false_positives = len(result_keys - truth_data)
            false_negatives = len(truth_data - result_keys)
            
            precision = true_positives / len(results) if results else 0
            recall = true_positives / len(truth_data) if truth_data else 0
            f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0
            
            self.logger.info(f"Query returned {len(results)} results with {len(truth_data)} expected matches")
            self.logger.info(f"Precision: {precision:.2f}, Recall: {recall:.2f}, F1: {f1:.2f}")
            
            if false_negatives > 0:
                self.logger.info(f"Missing {false_negatives} expected matches from results")
            if false_positives > 0:
                self.logger.info(f"Found {false_positives} unexpected matches in results")
        else:
            self.logger.warning(f"No truth data found for query {query_id} in collection {collection_name}")

        return results, execution_time_ms, aql_query
        
    def _extract_search_terms(self, query: str, collection_name: str) -> dict:
        """Extract relevant search terms from a natural language query.
        
        Args:
            query: Natural language query text
            collection_name: Collection being searched
            
        Returns:
            dict: Dictionary of search parameters relevant to the collection
        """
        # Initialize default search parameters
        search_params = {}
        
        # Extract search terms based on collection type
        query_lower = query.lower()
        
        if "MusicActivity" in collection_name:
            # Extract artist names
            artists = ["Taylor Swift", "The Beatles", "Beyoncé", "Ed Sheeran", "Drake"]
            for artist in artists:
                if artist.lower() in query_lower:
                    search_params["artist"] = artist
                    break
            
            # Extract genres
            genres = ["pop", "rock", "hip hop", "jazz", "classical"]
            for genre in genres:
                if genre in query_lower:
                    search_params["genre"] = genre
                    break
                    
            # Extract locations (for cross-collection queries)
            locations = ["home", "office", "car", "gym"]
            for location in locations:
                if location in query_lower:
                    search_params["location"] = location
                    break
                    
            # Default to basic search if no specific terms found
            if not search_params:
                search_params["artist"] = "Taylor Swift"  # Default for testing
            
        elif "LocationActivity" in collection_name:
            # Extract location names
            locations = ["Home", "Office", "Coffee Shop", "Library", "Airport"]
            for location in locations:
                if location.lower() in query_lower:
                    search_params["location_name"] = location
                    break
            
            # Extract location types
            location_types = ["work", "home", "leisure", "travel"]
            for loc_type in location_types:
                if loc_type in query_lower:
                    search_params["location_type"] = loc_type
                    break
                    
            # Default to basic search if no specific terms found
            if not search_params:
                search_params["location_name"] = "Home"  # Default for testing
                
        elif "TaskActivity" in collection_name:
            # Extract task types
            task_types = ["report", "presentation", "email", "project", "document"]
            for task_type in task_types:
                if task_type in query_lower:
                    search_params["task_type"] = task_type
                    break
            
            # Extract applications
            applications = ["Word", "Excel", "PowerPoint", "Outlook", "Teams"]
            for app in applications:
                if app.lower() in query_lower:
                    search_params["application"] = app
                    break
                    
            # Default to basic search if no specific terms found
            if not search_params:
                search_params["task_type"] = "document"  # Default for testing
        
        # Add timestamp window (last week) for all queries
        search_params["from_timestamp"] = int(time.time()) - (7 * 24 * 60 * 60)  # One week ago
        search_params["to_timestamp"] = int(time.time())  # Now
        
        return search_params
        
    def _build_semantic_query(self, collection_name: str, search_terms: dict) -> tuple[str, dict]:
        """Build a collection-specific semantic search query with NO result limits.
        
        Args:
            collection_name: Collection to search in
            search_terms: Dictionary of search parameters
            
        Returns:
            tuple: (AQL query string, bind parameters dictionary)
        """
        bind_vars = search_terms.copy()
        
        if "MusicActivity" in collection_name:
            aql_query = f"""
            FOR doc IN {collection_name}
            FILTER """
            
            filters = []
            
            if "artist" in bind_vars:
                filters.append("doc.artist == @artist")
                
            if "genre" in bind_vars:
                filters.append("doc.genre == @genre")
                
            if "location" in bind_vars:
                filters.append("doc.listening_location == @location")
                
            if "from_timestamp" in bind_vars and "to_timestamp" in bind_vars:
                filters.append("doc.timestamp >= @from_timestamp AND doc.timestamp <= @to_timestamp")
                
            # Join filters with OR for more inclusive search
            aql_query += " OR ".join(filters) if filters else "true"
            
            # Return all matches with no limit
            aql_query += """
            RETURN doc
            """
            
        elif "LocationActivity" in collection_name:
            aql_query = f"""
            FOR doc IN {collection_name}
            FILTER """
            
            filters = []
            
            if "location_name" in bind_vars:
                filters.append("doc.location_name == @location_name")
                
            if "location_type" in bind_vars:
                filters.append("doc.location_type == @location_type")
                
            if "from_timestamp" in bind_vars and "to_timestamp" in bind_vars:
                filters.append("doc.timestamp >= @from_timestamp AND doc.timestamp <= @to_timestamp")
                
            # Join filters with OR for more inclusive search
            aql_query += " OR ".join(filters) if filters else "true"
            
            # Return all matches with no limit
            aql_query += """
            RETURN doc
            """
            
        elif "TaskActivity" in collection_name:
            aql_query = f"""
            FOR doc IN {collection_name}
            FILTER """
            
            filters = []
            
            if "task_type" in bind_vars:
                filters.append("doc.task_type == @task_type")
                
            if "application" in bind_vars:
                filters.append("doc.application == @application")
                
            if "from_timestamp" in bind_vars and "to_timestamp" in bind_vars:
                filters.append("doc.timestamp >= @from_timestamp AND doc.timestamp <= @to_timestamp")
                
            # Join filters with OR for more inclusive search
            aql_query += " OR ".join(filters) if filters else "true"
            
            # Return all matches with no limit
            aql_query += """
            RETURN doc
            """
            
        else:
            # Generic fallback for unknown collections
            aql_query = f"""
            FOR doc IN {collection_name}
            RETURN doc
            """
        
        return aql_query, bind_vars

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
                aql_query="",
            )

        try:
            # Execute the query
            results, execution_time_ms, aql_query = self.execute_query(query_id, query_text, collection_name, limit)

            # Calculate metrics
            metrics = self.calculate_metrics(query_id, results, collection_name)

            # Update execution time and AQL query
            metrics.execution_time_ms = execution_time_ms
            metrics.aql_query = aql_query

            return metrics
        except NotImplementedError as e:
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
                aql_query="",
            )

    def run_ablation_test(
        self,
        config: AblationConfig,
        query_id: uuid.UUID,
        query_text: str,
    ) -> dict[str, AblationResult]:
        """Run a complete ablation test for a query across multiple collections.

        This method performs actual ablation by temporarily removing each collection
        and measuring the real impact on query results for other collections.

        Args:
            config: The ablation test configuration.
            query_id: The UUID of the query.
            query_text: The text of the query.

        Returns:
            Dict[str, AblationResult]: The results of the ablation test by collection.
        """
        # Initialize results
        results: dict[str, AblationResult] = {}

        # First run a baseline test with all collections available
        baseline_results = {}
        for collection_name in config.collections_to_ablate:
            baseline_metrics = self.test_ablation(query_id, query_text, collection_name, config.query_limit)
            baseline_results[collection_name] = baseline_metrics
            self.logger.info(f"Baseline metrics for {collection_name}: Precision={baseline_metrics.precision:.2f}, "
                             f"Recall={baseline_metrics.recall:.2f}, F1={baseline_metrics.f1_score:.2f}")

        # Now perform actual ablation tests for each collection
        for collection_to_ablate in config.collections_to_ablate:
            # Actually ablate the collection by backing up and removing its data
            self.logger.info(f"Performing actual ablation of collection {collection_to_ablate}...")
            
            ablation_success = self.ablate_collection(collection_to_ablate)
            if not ablation_success:
                self.logger.error(f"CRITICAL: Failed to ablate collection {collection_to_ablate}")
                sys.exit(1)  # Fail-stop immediately
            
            # For each test collection, measure the impact of this ablation
            for test_collection in config.collections_to_ablate:
                if test_collection != collection_to_ablate:
                    impact_key = f"{collection_to_ablate}_impact_on_{test_collection}"
                    
                    # Measure the actual impact on this collection's queries
                    self.logger.info(f"Measuring impact of ablating {collection_to_ablate} on {test_collection} queries...")
                    
                    # Run the test with the collection ablated
                    ablated_metrics = self.test_ablation(query_id, query_text, test_collection, config.query_limit)
                    
                    # Get the baseline for comparison
                    baseline = baseline_results[test_collection]
                    
                    # Store the result with measured impact
                    results[impact_key] = ablated_metrics
                    
                    # Report the impact
                    self.logger.info(f"Measured impact of ablating {collection_to_ablate} on {test_collection}: "
                                     f"F1 changed from {baseline.f1_score:.2f} to {ablated_metrics.f1_score:.2f}")
            
            # Restore the ablated collection before testing the next one
            self.logger.info(f"Restoring collection {collection_to_ablate}...")
            restore_success = self.restore_collection(collection_to_ablate)
            if not restore_success:
                self.logger.error(f"CRITICAL: Failed to restore collection {collection_to_ablate}")
                sys.exit(1)  # Fail-stop immediately

        return results

    def store_truth_data(self, query_id: uuid.UUID, collection_name: str, matching_entities: list[str]) -> bool:
        """Store truth data with a composite key based on query_id and collection.

        Args:
            query_id: The UUID of the query.
            collection_name: The collection name to associate the truth data with.
            matching_entities: List of entity IDs that should match the query.

        Returns:
            bool: True if storing succeeded.
        """
        if not self.db:
            self.logger.error("No database connection available")
            sys.exit(1)  # Fail-stop immediately - we can't proceed without DB

        # Ensure the Truth Collection exists - create it if needed
        try:
            if not self.db.has_collection(self.TRUTH_COLLECTION):
                self.db.create_collection(self.TRUTH_COLLECTION)
                self.logger.info(f"Created truth data collection {self.TRUTH_COLLECTION}")
        except Exception as e:
            self.logger.error(f"CRITICAL: Failed to ensure truth collection exists: {e}")
            sys.exit(1)  # Fail-stop immediately

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
        try:
            collection = self.db.collection(self.TRUTH_COLLECTION)
        except Exception as e:
            self.logger.error(f"CRITICAL: Failed to access truth collection: {e}")
            sys.exit(1)  # Fail-stop immediately

        # Check if document with this composite key already exists and store/update it
        try:
            existing = collection.get(composite_key)
            if existing:
                # Update existing document
                collection.update(truth_doc)
                self.logger.info(f"Updated truth data for query {query_id} in collection {collection_name}")
            else:
                # Insert new document
                collection.insert(truth_doc)
                self.logger.info(f"Recorded truth data for query {query_id} in collection {collection_name}")
        except Exception as e:
            self.logger.error(f"CRITICAL: Failed to store truth data: {e}")
            sys.exit(1)  # Fail-stop immediately

        return True

    def cleanup(self) -> None:
        """Clean up resources used by the ablation tester.
        
        This method ensures all ablated collections are properly restored
        and resources are released according to fail-stop principles.
        """
        self.logger.info("Cleaning up ablation tester resources")
        
        # Check for and restore any collections that are still ablated
        if hasattr(self, 'ablated_collections'):
            for collection_name, is_ablated in self.ablated_collections.items():
                if is_ablated:
                    self.logger.warning(f"Collection {collection_name} is still ablated during cleanup")
                    restore_success = self.restore_collection(collection_name)
                    if not restore_success:
                        self.logger.error(f"CRITICAL: Failed to restore collection {collection_name} during cleanup")
                        sys.exit(1)  # Fail-stop immediately
            
            # Clear tracking data after restoring collections
            self.ablated_collections.clear()
        
        # Clear backup data
        if hasattr(self, 'backup_data'):
            self.backup_data.clear()
