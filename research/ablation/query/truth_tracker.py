"""
Truth tracker for the ablation study framework.

This module provides functionality for tracking which records should match
each query, enabling precise calculation of precision, recall, and F1 metrics.
"""

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from db.db_collections import IndalekoDBCollections
from db.db_config import IndalekoDBConfig

from ..models.activity import ActivityType


class TruthTracker:
    """Tracker for query truth data.

    This class tracks which records should match each query,
    enabling precise calculation of precision, recall, and F1 metrics.
    """

    def __init__(self):
        """Initialize the truth data tracker."""
        self.logger = logging.getLogger(__name__)

        # Set up database connection
        try:
            self.db_config = IndalekoDBConfig()
            self.db = self.db_config.get_arangodb()
        except Exception as e:
            self.logger.error(f"FATAL: Failed to connect to database: {e}")
            # Database connection is required, so this is always a fatal error
            raise RuntimeError(f"Database connection is required. Error: {e}") from e

    def get_matching_ids(self, query_text: str, activity_types: list[ActivityType] | None = None) -> list[str]:
        """Get the document IDs that should match a query.

        Args:
            query_text: The natural language query
            activity_types: Optional list of activity types targeted by the query

        Returns:
            List of document IDs that should match the query
        """
        self.logger.info(f"Getting matching IDs for query: {query_text}")

        # Fetch matching IDs from the query truth collection
        try:
            # Convert activity types to strings if provided
            activity_type_strings = None
            if activity_types:
                activity_type_strings = [at.name for at in activity_types]

            # Build query conditions
            conditions = ["doc.query_text == @query_text"]
            bind_vars = {"query_text": query_text}

            if activity_type_strings:
                # Check if any of the provided activity types are in the query's activity_types array
                conditions.append("LENGTH(INTERSECTION(doc.activity_types, @activity_types)) > 0")
                bind_vars["activity_types"] = activity_type_strings

            # Construct and execute AQL query
            aql = f"""
            FOR doc IN {IndalekoDBCollections.Indaleko_Ablation_Query_Truth_Collection}
            FILTER {" AND ".join(conditions)}
            LIMIT 1
            RETURN doc.matching_ids
            """

            cursor = self.db.aql.execute(aql, bind_vars=bind_vars)
            results = list(cursor)

            if results and results[0]:
                return results[0]

            # If no exact match, try a looser match on query text
            # This handles minor variations in query text that might occur
            aql = f"""
            FOR doc IN {IndalekoDBCollections.Indaleko_Ablation_Query_Truth_Collection}
            FILTER LIKE(doc.query_text, CONCAT('%', @query_core, '%'), true)
            SORT LENGTH(doc.query_text) ASC
            LIMIT 1
            RETURN doc.matching_ids
            """

            # Extract core terms from the query (to handle minor variations)
            query_terms = query_text.lower().split()
            core_terms = [term for term in query_terms if len(term) > 3]
            query_core = " ".join(core_terms[:3]) if len(core_terms) >= 3 else query_text

            cursor = self.db.aql.execute(aql, bind_vars={"query_core": query_core})
            results = list(cursor)

            if results and results[0]:
                return results[0]

            # If still no match found, log a warning and return empty list
            self.logger.warning(f"No matching IDs found for query: {query_text}")
            return []

        except Exception as e:
            self.logger.error(f"Error getting matching IDs: {e}")
            return []

    def record_query_truth(
        self,
        query_id: str,
        matching_ids: list[str],
        query_text: str,
        activity_types: list[str],
        difficulty: str = "medium",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Record truth data for a query.

        Args:
            query_id: The UUID of the query
            matching_ids: List of document IDs that should match the query
            query_text: The natural language query
            activity_types: List of activity types targeted by the query
            difficulty: Difficulty level of the query (easy, medium, hard)
            metadata: Optional additional metadata for the query

        Returns:
            True if the truth data was successfully recorded, False otherwise
        """
        self.logger.info(f"Recording truth data for query: {query_text}")

        if not metadata:
            metadata = {}

        try:
            # Convert UUID to string if needed
            query_id_str = str(query_id) if isinstance(query_id, uuid.UUID) else query_id

            # Prepare document
            doc = {
                "_key": query_id_str,
                "query_id": query_id_str,
                "query_text": query_text,
                "matching_ids": matching_ids,
                "activity_types": activity_types,
                "created_at": datetime.now(UTC).isoformat(),
                "synthetic": True,  # Currently all our test data is synthetic
                "difficulty": difficulty,
                "metadata": metadata,
            }

            # Insert into the database
            collection = self.db.collection(IndalekoDBCollections.Indaleko_Ablation_Query_Truth_Collection)
            result = collection.insert(doc)

            return bool(result)

        except Exception as e:
            self.logger.error(f"Error recording query truth data: {e}")
            return False

    def get_truth_record(self, query_id: str) -> dict[str, Any] | None:
        """Get the complete truth record for a query.

        Args:
            query_id: The UUID of the query

        Returns:
            Dictionary containing the truth record, or None if not found
        """
        try:
            # Convert UUID to string if needed
            query_id_str = str(query_id) if isinstance(query_id, uuid.UUID) else query_id

            # Query the database
            aql = f"""
            FOR doc IN {IndalekoDBCollections.Indaleko_Ablation_Query_Truth_Collection}
            FILTER doc.query_id == @query_id
            LIMIT 1
            RETURN doc
            """

            cursor = self.db.aql.execute(aql, bind_vars={"query_id": query_id_str})
            results = list(cursor)

            if results:
                return results[0]

            self.logger.warning(f"No truth record found for query ID: {query_id}")
            return None

        except Exception as e:
            self.logger.error(f"Error getting truth record: {e}")
            return None

    def get_all_query_truth(self) -> list[dict[str, Any]]:
        """Get all query truth records.

        Returns:
            List of all query truth records
        """
        try:
            aql = f"""
            FOR doc IN {IndalekoDBCollections.Indaleko_Ablation_Query_Truth_Collection}
            RETURN doc
            """

            cursor = self.db.aql.execute(aql)
            return list(cursor)

        except Exception as e:
            self.logger.error(f"Error getting all query truth records: {e}")
            return []

    def save_to_file(self, file_path: Path) -> bool:
        """Save all query truth records to a file.

        Args:
            file_path: Path to save the records to

        Returns:
            True if the records were successfully saved, False otherwise
        """
        try:
            records = self.get_all_query_truth()

            # Create parent directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to file
            with open(file_path, "w") as f:
                json.dump(records, f, indent=2)

            self.logger.info(f"Saved {len(records)} query truth records to {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving query truth records to file: {e}")
            return False

    def load_from_file(self, file_path: Path) -> bool:
        """Load query truth records from a file.

        Args:
            file_path: Path to load the records from

        Returns:
            True if the records were successfully loaded, False otherwise
        """
        try:
            # Read from file
            with open(file_path) as f:
                records = json.load(f)

            # Get collection
            collection = self.db.collection(IndalekoDBCollections.Indaleko_Ablation_Query_Truth_Collection)

            # Import records
            count = 0
            for record in records:
                try:
                    collection.insert(record, overwrite=True)
                    count += 1
                except Exception as e:
                    self.logger.error(f"Error inserting record: {e}")

            self.logger.info(f"Loaded {count} query truth records from {file_path}")
            return count > 0

        except Exception as e:
            self.logger.error(f"Error loading query truth records from file: {e}")
            return False

    def clear_all_records(self) -> bool:
        """Clear all query truth records from the database.

        Returns:
            True if the records were successfully cleared, False otherwise
        """
        try:
            aql = f"""
            FOR doc IN {IndalekoDBCollections.Indaleko_Ablation_Query_Truth_Collection}
            REMOVE doc IN {IndalekoDBCollections.Indaleko_Ablation_Query_Truth_Collection}
            """

            self.db.aql.execute(aql)
            self.logger.info("Cleared all query truth records")
            return True

        except Exception as e:
            self.logger.error(f"Error clearing query truth records: {e}")
            return False

    def get_activity_type_distribution(self) -> dict[str, int]:
        """Get the distribution of activity types across all truth records.

        Returns:
            Dictionary mapping activity type to count
        """
        try:
            aql = f"""
            FOR doc IN {IndalekoDBCollections.Indaleko_Ablation_Query_Truth_Collection}
            FOR activity_type IN doc.activity_types
            COLLECT type = activity_type WITH COUNT INTO count
            RETURN {{
                activity_type: type,
                count: count
            }}
            """

            cursor = self.db.aql.execute(aql)
            results = list(cursor)

            distribution = {}
            for result in results:
                distribution[result["activity_type"]] = result["count"]

            return distribution

        except Exception as e:
            self.logger.error(f"Error getting activity type distribution: {e}")
            return {}
