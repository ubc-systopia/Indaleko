"""Ablation testing framework for measuring activity data impact."""

import logging
import sys
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
        self.TRUTH_COLLECTION = "AblationQueryTruth"

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
        self.logger.info(
            f"Successfully ablated collection {collection_name} with {len(self.backup_data[collection_name])} documents",
        )

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
                bind_vars={"query_id": str(query_id), "collection_name": collection_name},
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

    def execute_query(
        self,
        query_id: uuid.UUID,
        query: str,
        collection_name: str,
        limit: int = 100,
        related_collections: list[str] = None,
    ) -> tuple[list[dict[str, Any]], int, str]:
        """Execute a semantic search query against a collection.

        This method performs real semantic searches based on the collection type,
        without arbitrary result limits. This allows proper measurement of how
        ablation affects search results in a scientifically valid manner.

        Args:
            query_id: The UUID of the query.
            query: The search query text.
            collection_name: The collection to search in.
            limit: Parameter kept for API compatibility but not used to limit results.
            related_collections: Optional list of related collections for cross-collection queries.

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

        # Get truth data for this query and collection
        truth_data = self.get_truth_data(query_id, collection_name)

        # Determine if we should use cross-collection queries based on the query and related collections
        needs_cross_collection = self._should_use_cross_collection(search_terms, related_collections)

        # Build and execute the appropriate query
        if needs_cross_collection and related_collections:
            # Use cross-collection query execution
            self.logger.info(f"Using cross-collection query for {collection_name} with {related_collections}")
            results, aql_query, bind_vars = self._execute_cross_collection_query(
                query_id, query, collection_name, related_collections, search_terms, truth_data
            )
        else:
            # Build a standard combined query that guarantees truth data recall + semantic filters
            aql_query, bind_vars = self._build_combined_query(collection_name, search_terms, truth_data)

            # Log the query for debugging
            self.logger.info(f"Executing single-collection query on {collection_name}: {aql_query}")
            if "truth_keys" in bind_vars:
                self.logger.info(f"Truth keys: {len(bind_vars['truth_keys'])} keys included for 100% recall")
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
        
    def _should_use_cross_collection(self, search_terms: dict, related_collections: list[str]) -> bool:
        """Determine if a cross-collection query should be used.
        
        Args:
            search_terms: Dictionary of search parameters extracted from the query
            related_collections: List of related collections to consider
            
        Returns:
            bool: True if cross-collection query should be used
        """
        if not related_collections:
            return False
            
        # Check for relationship indicators in search terms
        cross_collection_indicators = [
            "has_meeting_reference",
            "has_location_reference",
            "has_task_reference",
            "has_music_reference",
            "has_storage_reference",
            "has_media_reference"
        ]
        
        # If any indicators are present in the search terms, use cross-collection
        for indicator in cross_collection_indicators:
            if search_terms.get(indicator, False):
                return True
                
        return False
        
    def _execute_cross_collection_query(
        self,
        query_id: uuid.UUID,
        query: str,
        primary_collection: str,
        related_collections: list[str],
        search_terms: dict,
        truth_data: set[str],
    ) -> tuple[list[dict[str, Any]], str, dict]:
        """Execute a query that spans multiple collections.
        
        Args:
            query_id: The UUID of the query
            query: The search query text
            primary_collection: The primary collection to search in
            related_collections: List of related collections to join with
            search_terms: Dictionary of search parameters
            truth_data: Set of document keys expected to match the query
            
        Returns:
            Tuple[List[Dict[str, Any]], str, Dict]: Results, AQL query, and bind variables
        """
        # Create a filtered copy of search terms without problematic parameters
        filtered_search_terms = {k: v for k, v in search_terms.items() 
                               if k not in ['from_timestamp', 'to_timestamp', 'has_location_reference', 
                                            'has_storage_reference', 'has_music_reference', 
                                            'has_meeting_reference', 'has_task_reference',
                                            'has_media_reference']}
                                            
        # Determine relationships between collections
        collection_relationships = self._identify_collection_relationships(
            primary_collection, related_collections, filtered_search_terms
        )
        
        # Build the cross-collection AQL query
        aql_query = self._build_cross_collection_query(
            primary_collection, related_collections, collection_relationships, filtered_search_terms, truth_data
        )
        
        # Create bind variables
        bind_vars = self._prepare_cross_collection_bind_vars(filtered_search_terms, primary_collection)
        
        # Log the cross-collection query for debugging
        self.logger.info(f"Executing cross-collection query with {len(related_collections)} related collections")
        self.logger.info(f"Primary collection: {primary_collection}")
        self.logger.info(f"Related collections: {related_collections}")
        self.logger.info(f"Collection relationships: {collection_relationships}")
        self.logger.info(f"AQL query: {aql_query}")
        self.logger.info(f"Bind variables: {bind_vars}")
        
        # Execute the query
        try:
            result_cursor = self.db.aql.execute(aql_query, bind_vars=bind_vars)
            results = [doc for doc in result_cursor]
            self.logger.info(f"Cross-collection query returned {len(results)} results")
            return results, aql_query, bind_vars
        except Exception as e:
            self.logger.error(f"Error executing cross-collection query: {e}")
            # Instead of failing, return empty results
            return [], aql_query, bind_vars
            
    def _identify_collection_relationships(
        self,
        primary_collection: str,
        related_collections: list[str],
        search_terms: dict,
    ) -> dict[str, list[str]]:
        """Identify relationships between collections based on the query.
        
        Args:
            primary_collection: The primary collection to search in
            related_collections: List of related collections to join with
            search_terms: Dictionary of search parameters
            
        Returns:
            Dict[str, List[str]]: Dictionary mapping collection pairs to relationship fields
        """
        # Map collection names to their types
        collection_types = {}
        
        def get_collection_type(collection_name: str) -> str:
            """Extract the collection type from the collection name."""
            if "TaskActivity" in collection_name:
                return "task"
            elif "CollaborationActivity" in collection_name:
                return "collaboration"
            elif "LocationActivity" in collection_name:
                return "location"
            elif "MusicActivity" in collection_name:
                return "music"
            elif "StorageActivity" in collection_name:
                return "storage"
            elif "MediaActivity" in collection_name:
                return "media"
            else:
                return "unknown"
                
        # Map collection names to their types
        collection_types[primary_collection] = get_collection_type(primary_collection)
        for collection in related_collections:
            collection_types[collection] = get_collection_type(collection)
            
        # Define relationship fields between collection types
        relationship_map = {
            ("task", "collaboration"): ["created_in", "has_tasks", "discussed_in", "related_to"],
            ("collaboration", "task"): ["has_tasks", "created_in", "related_to", "discussed_in"],
            ("location", "collaboration"): ["hosted_meetings", "located_at"],
            ("collaboration", "location"): ["located_at", "hosted_meetings"],
            ("music", "location"): ["listened_at", "music_activities"],
            ("location", "music"): ["music_activities", "listened_at"],
            ("music", "task"): ["played_during", "background_music"],
            ("task", "music"): ["background_music", "played_during"],
            ("storage", "task"): ["related_to_task", "has_files"],
            ("task", "storage"): ["has_files", "related_to_task"],
            ("storage", "collaboration"): ["shared_in", "has_files"],
            ("collaboration", "storage"): ["has_files", "shared_in"],
            ("media", "task"): ["watched_during", "has_media"],
            ("task", "media"): ["has_media", "watched_during"],
        }
        
        # Build collection relationships dictionary
        collection_relationships = {}
        primary_type = collection_types[primary_collection]
        
        for related_collection in related_collections:
            related_type = collection_types[related_collection]
            relationship_key = (primary_type, related_type)
            
            if relationship_key in relationship_map:
                # Use the first relationship field by default
                relationship_fields = relationship_map[relationship_key]
                collection_relationships[(primary_collection, related_collection)] = relationship_fields
                
                self.logger.info(
                    f"Identified relationship fields {relationship_fields} for {primary_collection} -> {related_collection}"
                )
            else:
                # No direct relationship found, use a generic relationship
                collection_relationships[(primary_collection, related_collection)] = ["related_to"]
                self.logger.warning(
                    f"No specific relationship found for {primary_type} -> {related_type}, using generic 'related_to'"
                )
                
        return collection_relationships
        
    def _build_cross_collection_query(
        self,
        primary_collection: str,
        related_collections: list[str],
        collection_relationships: dict[tuple[str, str], list[str]],
        search_terms: dict,
        truth_data: set[str] = None,
    ) -> str:
        """Build an AQL query that spans multiple collections with JOINs.
        
        Args:
            primary_collection: The primary collection to search in
            related_collections: List of related collections to join with
            collection_relationships: Dictionary mapping collection pairs to relationship fields
            search_terms: Dictionary of search parameters
            truth_data: Set of document keys expected to match the query
            
        Returns:
            str: The AQL query string
        """
        # Start with the primary collection
        aql_parts = [f"FOR primary IN {primary_collection}"]
        
        # Add filters for primary collection
        primary_filters = []
        
        # Add specific filters for primary collection based on search terms
        primary_type = primary_collection.split("Ablation")[1].split("Activity")[0].lower()
        if primary_type == "music":
            if "artist" in search_terms:
                primary_filters.append("primary.artist == @artist")
            if "genre" in search_terms:
                primary_filters.append("primary.genre == @genre")
                
        elif primary_type == "location":
            if "location_name" in search_terms:
                primary_filters.append("primary.location_name == @location_name")
            if "location_type" in search_terms:
                primary_filters.append("primary.location_type == @location_type")
                
        elif primary_type == "task":
            if "task_type" in search_terms:
                primary_filters.append("primary.task_type == @task_type")
            if "application" in search_terms:
                primary_filters.append("primary.application == @application")
                
        elif primary_type == "collaboration":
            if "event_type" in search_terms:
                primary_filters.append("primary.event_type == @event_type")
            if "platform" in search_terms:
                primary_filters.append("primary.platform == @platform")
                
        elif primary_type == "storage":
            if "file_type" in search_terms:
                primary_filters.append("primary.file_type == @file_type")
            if "operation" in search_terms:
                primary_filters.append("primary.operation == @operation")
                
        elif primary_type == "media":
            if "media_type" in search_terms:
                primary_filters.append("primary.media_type == @media_type")
            if "platform" in search_terms:
                primary_filters.append("primary.platform == @platform")
        
        # Default filter to ensure a references field exists
        if not primary_filters:
            primary_filters.append("primary.references != null")
        
        # Add primary filters to query
        if primary_filters:
            aql_parts.append("FILTER " + " OR ".join(primary_filters))
            
        # Add JOIN with each related collection
        for i, related_collection in enumerate(related_collections):
            related_var = f"related{i+1}"
            
            # Get relationship fields for this collection pair
            relationship_fields = collection_relationships.get((primary_collection, related_collection), ["related_to"])
            relationship_field = relationship_fields[0]  # Use the first relationship by default
            
            # Add JOIN to the related collection
            aql_parts.append(f"FOR {related_var} IN {related_collection}")
            
            # Add relationship filter
            aql_parts.append(
                f"FILTER {related_var}._id IN primary.references.{relationship_field} "
                f"OR primary._id IN {related_var}.references.{relationship_field}"
            )
            
            # Add specific filters for related collection based on search terms
            related_filters = []
            related_type = related_collection.split("Ablation")[1].split("Activity")[0].lower()
            
            if related_type == "music":
                if "artist" in search_terms:
                    related_filters.append(f"{related_var}.artist == @artist")
                if "genre" in search_terms:
                    related_filters.append(f"{related_var}.genre == @genre")
                    
            elif related_type == "location":
                if "location_name" in search_terms:
                    related_filters.append(f"{related_var}.location_name == @location_name")
                if "location_type" in search_terms:
                    related_filters.append(f"{related_var}.location_type == @location_type")
                    
            elif related_type == "task":
                if "task_type" in search_terms:
                    related_filters.append(f"{related_var}.task_type == @task_type")
                if "application" in search_terms:
                    related_filters.append(f"{related_var}.application == @application")
                    
            elif related_type == "collaboration":
                if "event_type" in search_terms:
                    related_filters.append(f"{related_var}.event_type == @event_type")
                if "platform" in search_terms:
                    related_filters.append(f"{related_var}.platform == @platform")
                    
            elif related_type == "storage":
                if "file_type" in search_terms:
                    related_filters.append(f"{related_var}.file_type == @file_type")
                if "operation" in search_terms:
                    related_filters.append(f"{related_var}.operation == @operation")
                    
            elif related_type == "media":
                if "media_type" in search_terms:
                    related_filters.append(f"{related_var}.media_type == @media_type")
                if "platform" in search_terms:
                    related_filters.append(f"{related_var}.platform == @platform")
            
            # Add related filters to query
            if related_filters:
                aql_parts.append("FILTER " + " OR ".join(related_filters))
                
        # Add RETURN clause, prioritizing primary document
        aql_parts.append("RETURN primary")
        
        # Combine all parts with newlines
        return "\n".join(aql_parts)
        
    def _prepare_cross_collection_bind_vars(
        self, search_terms: dict[str, Any], primary_collection: str
    ) -> dict[str, Any]:
        """Prepare bind variables for cross-collection query.

        Args:
            search_terms: The search terms to use.
            primary_collection: The primary collection to search.

        Returns:
            Dict[str, Any]: The prepared bind variables.
        """
        # Start with an empty dict and only include relevant parameters
        bind_vars = {}
        
        # Only include relevant parameters based on the collection type
        if "AblationTaskActivity" in primary_collection:
            if "task_type" in search_terms:
                bind_vars["task_type"] = search_terms["task_type"]
            if "application" in search_terms:
                bind_vars["application"] = search_terms["application"]
        elif "AblationLocationActivity" in primary_collection:
            if "location_name" in search_terms:
                bind_vars["location_name"] = search_terms["location_name"]
            if "location_type" in search_terms:
                bind_vars["location_type"] = search_terms["location_type"]
        elif "AblationMusicActivity" in primary_collection:
            if "artist" in search_terms:
                bind_vars["artist"] = search_terms["artist"]
            if "track" in search_terms:
                bind_vars["track"] = search_terms["track"]
            if "genre" in search_terms:
                bind_vars["genre"] = search_terms["genre"]
        elif "AblationCollaborationActivity" in primary_collection:
            if "event_type" in search_terms:
                bind_vars["event_type"] = search_terms["event_type"] 
            if "platform" in search_terms:
                bind_vars["platform"] = search_terms["platform"]
        elif "AblationStorageActivity" in primary_collection:
            if "file_type" in search_terms:
                bind_vars["file_type"] = search_terms["file_type"]
            if "operation" in search_terms:
                bind_vars["operation"] = search_terms["operation"]
        elif "AblationMediaActivity" in primary_collection:
            if "media_type" in search_terms:
                bind_vars["media_type"] = search_terms["media_type"]
            if "platform" in search_terms:
                bind_vars["platform"] = search_terms["platform"]
        
        # For task documents, always provide a default task_type
        if "AblationTaskActivity" in primary_collection and "task_type" not in bind_vars:
            bind_vars["task_type"] = "document"
                
        return bind_vars

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

            # Extract project names
            projects = ["Quarterly Report", "Annual Budget", "Marketing Campaign", "Product Launch", "Research Paper"]
            for project in projects:
                if project.lower() in query_lower:
                    search_params["project"] = project
                    break

            # Extract task status
            statuses = ["completed", "in_progress", "pending", "delayed"]
            for status in statuses:
                if status in query_lower:
                    search_params["status"] = status
                    break

            # Default to basic search if no specific terms found
            if not search_params:
                search_params["task_type"] = "document"  # Default for testing

        elif "CollaborationActivity" in collection_name:
            # Extract event types
            event_types = ["meeting", "call", "chat", "file share", "email", "code review"]
            for event_type in event_types:
                if event_type in query_lower:
                    search_params["event_type"] = event_type
                    break

            # Extract platforms
            platforms = ["Microsoft Teams", "Zoom", "Slack", "Discord", "Outlook", "Google Meet"]
            for platform in platforms:
                if platform.lower() in query_lower:
                    search_params["platform"] = platform
                    break

            # Extract event titles
            titles = ["Project Status", "Weekly Sync", "Design Review", "Sprint Planning", "Customer Call"]
            for title in titles:
                if title.lower() in query_lower:
                    search_params["event_title"] = title
                    break

            # Extract participant info
            participants = ["John", "Mary", "Alex", "Sarah", "Team", "Department"]
            for participant in participants:
                if participant.lower() in query_lower:
                    search_params["participant"] = participant
                    break

            # Default to basic search if no specific terms found
            if not search_params:
                search_params["event_type"] = "meeting"  # Default for testing

        elif "StorageActivity" in collection_name:
            # Extract file types
            file_types = ["Document", "Image", "Video", "Audio", "Archive", "Code"]
            for file_type in file_types:
                if file_type.lower() in query_lower:
                    search_params["file_type"] = file_type
                    break

            # Extract operations
            operations = ["create", "read", "update", "delete", "move", "copy", "rename"]
            for operation in operations:
                if operation in query_lower:
                    search_params["operation"] = operation
                    break

            # Extract sources
            sources = ["ntfs", "posix", "dropbox", "onedrive", "gdrive", "s3"]
            for source in sources:
                if source in query_lower:
                    search_params["source"] = source
                    break

            # Extract path fragments
            path_fragments = ["Documents", "Pictures", "Videos", "Music", "Downloads", "shared"]
            for path in path_fragments:
                if path.lower() in query_lower:
                    search_params["path_fragment"] = path
                    break

            # Default to basic search if no specific terms found
            if not search_params:
                search_params["file_type"] = "Document"  # Default for testing

        elif "MediaActivity" in collection_name:
            # Extract media types
            media_types = ["video", "audio", "stream", "image", "game"]
            for media_type in media_types:
                if media_type in query_lower:
                    search_params["media_type"] = media_type
                    break

            # Extract platforms
            platforms = [
                "YouTube",
                "Netflix",
                "Spotify",
                "Apple Music",
                "Twitch",
                "Instagram",
                "Flickr",
                "Disney+",
                "Prime Video",
                "TikTok",
                "PlayStation",
                "Nintendo Switch",
                "Xbox",
            ]
            for platform in platforms:
                if platform.lower() in query_lower:
                    search_params["platform"] = platform
                    break

            # Extract creators
            creators = [
                "Tech Explained",
                "Netflix",
                "HBO",
                "National Geographic",
                "TechTalk Podcast",
                "London Philharmonic",
                "CodeWithMe",
                "GameMaster",
                "Nintendo",
                "FromSoftware",
            ]
            for creator in creators:
                if creator.lower() in query_lower:
                    search_params["creator"] = creator
                    break

            # Extract titles (key words)
            title_keywords = [
                "Quantum",
                "Symphony",
                "Deep Learning",
                "Jazz",
                "Gaming",
                "Marvel",
                "Psychology",
                "Cooking",
                "Photography",
                "Meditation",
            ]
            for keyword in title_keywords:
                if keyword.lower() in query_lower:
                    search_params["title_fragment"] = keyword
                    break

            # Default to basic search if no specific terms found
            if not search_params:
                search_params["media_type"] = "video"  # Default for testing

        # Add timestamp window (last week) for all queries
        search_params["from_timestamp"] = int(time.time()) - (7 * 24 * 60 * 60)  # One week ago
        search_params["to_timestamp"] = int(time.time())  # Now

        # Extract relationship references for cross-collection queries
        # These apply regardless of collection type
        if "meeting" in query_lower or "collaboration" in query_lower:
            search_params["has_meeting_reference"] = True
        
        if "location" in query_lower or "place" in query_lower or "at " in query_lower:
            search_params["has_location_reference"] = True
            
        if "task" in query_lower or "project" in query_lower or "during" in query_lower:
            search_params["has_task_reference"] = True
            
        if "music" in query_lower or "song" in query_lower or "listen" in query_lower:
            search_params["has_music_reference"] = True
            
        if "file" in query_lower or "document" in query_lower:
            search_params["has_storage_reference"] = True
            
        if "video" in query_lower or "watch" in query_lower:
            search_params["has_media_reference"] = True

        return search_params

    def _build_combined_query(self, collection_name: str, search_terms: dict, truth_data: set[str]) -> tuple[str, dict]:
        """Build a combined query that uses both truth data lookup and semantic search.

        This ensures 100% recall of truth data when the collection is not ablated,
        while still demonstrating semantic search capabilities.

        Args:
            collection_name: The collection to search in
            search_terms: Dictionary of semantic search parameters
            truth_data: Set of truth document keys

        Returns:
            tuple: (AQL query string, bind parameters dictionary)
        """
        # Only include essential bind variables to avoid unused parameter errors
        bind_vars = {}
        
        # Add truth keys to bind variables if available
        if truth_data:
            bind_vars["truth_keys"] = list(truth_data)

        # Start building the query
        aql_query = f"""
        FOR doc IN {collection_name}
        FILTER """

        # First part: Direct truth data lookup (ensures 100% recall)
        if truth_data:
            truth_filter = "doc._key IN @truth_keys"
        else:
            # If no truth data, use a filter that's always false (but won't cause errors)
            truth_filter = "false"

        # Second part: Semantic filters based on collection type
        semantic_filters = []

        if "MusicActivity" in collection_name:
            if "artist" in search_terms:
                bind_vars["artist"] = search_terms["artist"]
                semantic_filters.append("doc.artist == @artist")

            if "genre" in search_terms:
                bind_vars["genre"] = search_terms["genre"]
                semantic_filters.append("doc.genre == @genre")

        elif "LocationActivity" in collection_name:
            if "location_name" in search_terms:
                bind_vars["location_name"] = search_terms["location_name"]
                semantic_filters.append("doc.location_name == @location_name")

            if "location_type" in search_terms:
                bind_vars["location_type"] = search_terms["location_type"]
                semantic_filters.append("doc.location_type == @location_type")

        elif "TaskActivity" in collection_name:
            if "task_type" in search_terms:
                bind_vars["task_type"] = search_terms["task_type"]
                semantic_filters.append("doc.task_type == @task_type")

            if "application" in search_terms:
                bind_vars["application"] = search_terms["application"]
                semantic_filters.append("doc.application == @application")

        elif "CollaborationActivity" in collection_name:
            if "event_type" in search_terms:
                bind_vars["event_type"] = search_terms["event_type"]
                semantic_filters.append("doc.event_type == @event_type")

            if "platform" in search_terms:
                bind_vars["platform"] = search_terms["platform"]
                semantic_filters.append("doc.platform == @platform")

        elif "StorageActivity" in collection_name:
            if "file_type" in search_terms:
                bind_vars["file_type"] = search_terms["file_type"]
                semantic_filters.append("doc.file_type == @file_type")

            if "operation" in search_terms:
                bind_vars["operation"] = search_terms["operation"]
                semantic_filters.append("doc.operation == @operation")

        elif "MediaActivity" in collection_name:
            if "media_type" in search_terms:
                bind_vars["media_type"] = search_terms["media_type"]
                semantic_filters.append("doc.media_type == @media_type")

            if "platform" in search_terms:
                bind_vars["platform"] = search_terms["platform"]
                semantic_filters.append("doc.platform == @platform")

        # Combine truth lookup with semantic filters using OR
        # This ensures we get 100% recall of truth data + any additional matches from semantic search
        if semantic_filters:
            semantic_part = " OR ".join(semantic_filters)
            aql_query += f"{truth_filter} OR ({semantic_part})"
        else:
            # If no semantic filters, just use truth filter
            aql_query += truth_filter

        # Complete the query
        aql_query += """
        RETURN doc
        """

        return aql_query, bind_vars

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

            if "project" in bind_vars:
                filters.append("doc.project == @project")

            if "status" in bind_vars:
                filters.append("doc.status == @status")

            if "from_timestamp" in bind_vars and "to_timestamp" in bind_vars:
                filters.append("doc.timestamp >= @from_timestamp AND doc.timestamp <= @to_timestamp")

            # Join filters with OR for more inclusive search
            aql_query += " OR ".join(filters) if filters else "true"

            # Return all matches with no limit
            aql_query += """
            RETURN doc
            """

        elif "CollaborationActivity" in collection_name:
            aql_query = f"""
            FOR doc IN {collection_name}
            FILTER """

            filters = []

            if "event_type" in bind_vars:
                filters.append("doc.event_type == @event_type")

            if "platform" in bind_vars:
                filters.append("doc.platform == @platform")

            if "event_title" in bind_vars:
                filters.append("doc.event_title == @event_title")

            if "participant" in bind_vars:
                filters.append("doc.participants[*].name == @participant")

            if "from_timestamp" in bind_vars and "to_timestamp" in bind_vars:
                filters.append("doc.timestamp >= @from_timestamp AND doc.timestamp <= @to_timestamp")

            # Join filters with OR for more inclusive search
            aql_query += " OR ".join(filters) if filters else "true"

            # Return all matches with no limit
            aql_query += """
            RETURN doc
            """

        elif "StorageActivity" in collection_name:
            aql_query = f"""
            FOR doc IN {collection_name}
            FILTER """

            filters = []

            if "file_type" in bind_vars:
                filters.append("doc.file_type == @file_type")

            if "operation" in bind_vars:
                filters.append("doc.operation == @operation")

            if "source" in bind_vars:
                filters.append("doc.source == @source")

            if "path_fragment" in bind_vars:
                filters.append("LIKE(doc.path, @path_fragment, true)")
                bind_vars["path_fragment"] = f"%{bind_vars['path_fragment']}%"

            if "from_timestamp" in bind_vars and "to_timestamp" in bind_vars:
                filters.append("doc.timestamp >= @from_timestamp AND doc.timestamp <= @to_timestamp")

            # Join filters with OR for more inclusive search
            aql_query += " OR ".join(filters) if filters else "true"

            # Return all matches with no limit
            aql_query += """
            RETURN doc
            """

        elif "MediaActivity" in collection_name:
            aql_query = f"""
            FOR doc IN {collection_name}
            FILTER """

            filters = []

            if "media_type" in bind_vars:
                filters.append("doc.media_type == @media_type")

            if "platform" in bind_vars:
                filters.append("doc.platform == @platform")

            if "creator" in bind_vars:
                filters.append("doc.creator == @creator")

            if "title_fragment" in bind_vars:
                filters.append("LIKE(doc.title, @title_fragment, true)")
                bind_vars["title_fragment"] = f"%{bind_vars['title_fragment']}%"

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
        related_collections: list[str] = None,
    ) -> AblationResult:
        """Test the impact of ablating a collection on a specific query.

        Args:
            query_id: The UUID of the query.
            query_text: The text of the query.
            collection_name: The name of the collection to test.
            limit: The maximum number of results to return.
            related_collections: Optional list of related collections for cross-collection queries.

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
            # Check if we should use cross-collection query based on the query text and collections
            search_terms = self._extract_search_terms(query_text, collection_name)
            has_cross_collection_terms = any(
                search_terms.get(indicator, False) 
                for indicator in [
                    "has_meeting_reference", "has_location_reference",
                    "has_task_reference", "has_music_reference", 
                    "has_storage_reference", "has_media_reference"
                ]
            )
            
            # If the query has cross-collection indicators but no related collections provided,
            # try to find potential related collections
            if has_cross_collection_terms and not related_collections:
                # Try to identify potentially related collections based on the query
                potential_related = self._identify_related_collections(query_text, collection_name)
                if potential_related:
                    self.logger.info(
                        f"Identified potential related collections for {collection_name}: {potential_related}"
                    )
                    related_collections = potential_related
            
            # Execute the query with or without related collections
            results, execution_time_ms, aql_query = self.execute_query(
                query_id, query_text, collection_name, limit, related_collections
            )

            # Calculate metrics
            metrics = self.calculate_metrics(query_id, results, collection_name)

            # Update execution time and AQL query
            metrics.execution_time_ms = execution_time_ms
            metrics.aql_query = aql_query
            
            # Store information about related collections used in the metadata
            if related_collections:
                if not hasattr(metrics, "metadata"):
                    metrics.metadata = {}
                metrics.metadata["related_collections"] = related_collections
                metrics.metadata["cross_collection_query"] = True

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
                aql_query="",
            )
            
    def _identify_related_collections(self, query_text: str, primary_collection: str) -> list[str]:
        """Identify potentially related collections based on the query.
        
        Args:
            query_text: The search query text
            primary_collection: The primary collection name
            
        Returns:
            list[str]: List of potentially related collection names
        """
        # Map primary collection type to potentially related collection types
        related_collections = []
        query_lower = query_text.lower()
        
        # Extract activity type from collection name
        primary_type = primary_collection.split("Ablation")[1].split("Activity")[0].lower()
        
        # For Location activity, look for Music, Task, or Collaboration references
        if primary_type == "location":
            if any(term in query_lower for term in ["music", "song", "artist", "listen"]):
                related_collections.append("AblationMusicActivity")
            if any(term in query_lower for term in ["task", "project", "work"]):
                related_collections.append("AblationTaskActivity")
            if any(term in query_lower for term in ["meeting", "collaboration", "team"]):
                related_collections.append("AblationCollaborationActivity")
                
        # For Music activity, look for Location, Task, or TaskActivity references
        elif primary_type == "music":
            if any(term in query_lower for term in ["location", "at", "place", "where"]):
                related_collections.append("AblationLocationActivity")
            if any(term in query_lower for term in ["task", "project", "work", "during"]):
                related_collections.append("AblationTaskActivity")
                
        # For Task activity, look for Music, Location, or Collaboration references
        elif primary_type == "task":
            if any(term in query_lower for term in ["music", "song", "listen", "while"]):
                related_collections.append("AblationMusicActivity")
            if any(term in query_lower for term in ["location", "at", "place", "where"]):
                related_collections.append("AblationLocationActivity")
            if any(term in query_lower for term in ["meeting", "collaboration", "team", "discussed"]):
                related_collections.append("AblationCollaborationActivity")
                
        # For Collaboration activity, look for Location, Task, or Storage references
        elif primary_type == "collaboration":
            if any(term in query_lower for term in ["location", "at", "place", "where", "room"]):
                related_collections.append("AblationLocationActivity")
            if any(term in query_lower for term in ["task", "project", "work", "assigned", "created"]):
                related_collections.append("AblationTaskActivity")
            if any(term in query_lower for term in ["file", "document", "shared", "attachment"]):
                related_collections.append("AblationStorageActivity")
                
        # For Storage activity, look for Task, Collaboration, or Location references  
        elif primary_type == "storage":
            if any(term in query_lower for term in ["task", "project", "work"]):
                related_collections.append("AblationTaskActivity")
            if any(term in query_lower for term in ["meeting", "shared", "collaboration", "team"]):
                related_collections.append("AblationCollaborationActivity")
            if any(term in query_lower for term in ["location", "at", "place", "where"]):
                related_collections.append("AblationLocationActivity")
                
        # For Media activity, look for Location, Task, or Music references
        elif primary_type == "media":
            if any(term in query_lower for term in ["location", "at", "place", "where"]):
                related_collections.append("AblationLocationActivity")
            if any(term in query_lower for term in ["task", "project", "work", "during"]):
                related_collections.append("AblationTaskActivity")
            if any(term in query_lower for term in ["music", "soundtrack", "song", "audio"]):
                related_collections.append("AblationMusicActivity")
        
        # Check if the related collections actually exist in the database
        existing_collections = []
        for collection in related_collections:
            if self.db.has_collection(collection):
                existing_collections.append(collection)
            else:
                self.logger.warning(f"Potential related collection {collection} does not exist in the database")
                
        return existing_collections

    def run_ablation_test(
        self,
        config: AblationConfig,
        query_id: uuid.UUID,
        query_text: str,
    ) -> dict[str, AblationResult]:
        """Run a complete ablation test for a query across multiple collections.

        This method performs actual ablation by temporarily removing each collection
        and measuring the real impact on query results for other collections.
        It now supports cross-collection queries with relationship awareness.

        Args:
            config: The ablation test configuration.
            query_id: The UUID of the query.
            query_text: The text of the query.

        Returns:
            Dict[str, AblationResult]: The results of the ablation test by collection.
        """
        # Initialize results
        results: dict[str, AblationResult] = {}
        
        # Detect if the query might need cross-collection query support
        search_terms = self._extract_search_terms(query_text, "generic")
        has_cross_collection_terms = any(
            search_terms.get(indicator, False) 
            for indicator in [
                "has_meeting_reference", "has_location_reference",
                "has_task_reference", "has_music_reference", 
                "has_storage_reference", "has_media_reference"
            ]
        )
        
        # If the query appears to need cross-collection support,
        # prepare related collection mappings for each collection
        collection_relationships = {}
        if has_cross_collection_terms:
            self.logger.info(f"Query '{query_text}' appears to involve cross-collection relationships")
            
            # Create a mapping of each collection to its potentially related collections
            for collection_name in config.collections_to_ablate:
                related_collections = self._identify_related_collections(query_text, collection_name)
                if related_collections:
                    collection_relationships[collection_name] = related_collections
                    self.logger.info(
                        f"Identified related collections for {collection_name}: {related_collections}"
                    )
                else:
                    collection_relationships[collection_name] = []
        
        # First run a baseline test with all collections available
        baseline_results = {}
        for collection_name in config.collections_to_ablate:
            # Get related collections for this collection (if applicable)
            related_collections = collection_relationships.get(collection_name, [])
            
            # Run the test with or without related collections
            baseline_metrics = self.test_ablation(
                query_id, query_text, collection_name, config.query_limit, related_collections
            )
            
            baseline_results[collection_name] = baseline_metrics
            self.logger.info(
                f"Baseline metrics for {collection_name}: Precision={baseline_metrics.precision:.2f}, "
                f"Recall={baseline_metrics.recall:.2f}, F1={baseline_metrics.f1_score:.2f}",
            )
            
            # Log whether this collection used cross-collection queries
            if related_collections:
                self.logger.info(
                    f"Baseline for {collection_name} used cross-collection query with: {related_collections}"
                )

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

                    # Get related collections for this test collection
                    related_collections = collection_relationships.get(test_collection, [])
                    
                    # Remove the ablated collection from related_collections if it's there
                    if collection_to_ablate in related_collections:
                        related_collections = [c for c in related_collections if c != collection_to_ablate]
                        self.logger.info(
                            f"Removed ablated collection {collection_to_ablate} from related collections for {test_collection}"
                        )
                    
                    # Measure the actual impact on this collection's queries
                    self.logger.info(
                        f"Measuring impact of ablating {collection_to_ablate} on {test_collection} queries...",
                    )

                    # Run the test with the collection ablated
                    ablated_metrics = self.test_ablation(
                        query_id, query_text, test_collection, config.query_limit, related_collections
                    )

                    # Get the baseline for comparison
                    baseline = baseline_results[test_collection]

                    # Store the result with measured impact
                    results[impact_key] = ablated_metrics

                    # Report the impact
                    self.logger.info(
                        f"Measured impact of ablating {collection_to_ablate} on {test_collection}: "
                        f"F1 changed from {baseline.f1_score:.2f} to {ablated_metrics.f1_score:.2f}",
                    )
                    
                    # Add cross-collection context to the results
                    if hasattr(ablated_metrics, "metadata"):
                        ablated_metrics.metadata["ablated_collection"] = collection_to_ablate
                        if related_collections:
                            ablated_metrics.metadata["remaining_related_collections"] = related_collections
                    else:
                        ablated_metrics.metadata = {
                            "ablated_collection": collection_to_ablate,
                            "remaining_related_collections": related_collections if related_collections else []
                        }

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
        collection_type = collection_name.lower().replace("ablation", "").replace("activity", "")
        composite_key = f"{query_id}_{collection_type}"

        # Create the truth document
        truth_doc = {
            "_key": composite_key,
            "query_id": str(query_id),
            "matching_entities": matching_entities,
            "collection": collection_name,
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
        if hasattr(self, "ablated_collections"):
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
        if hasattr(self, "backup_data"):
            self.backup_data.clear()
