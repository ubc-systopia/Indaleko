"""
Truth data tracker for the ablation study framework.

This module provides functionality for tracking which records should match
each query, enabling precise calculation of precision, recall, and F1 metrics.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Union

try:
    from db.db_config import IndalekoDBConfig
except ImportError:
    # Mock implementation for standalone testing
    class IndalekoDBConfig:
        """Mock DB config for standalone testing."""

        def get_arangodb(self):
            """Get a mock ArangoDB connection."""
            return MockArangoDB()

class MockArangoDB:
    """Mock ArangoDB for standalone testing."""

    def __init__(self):
        """Initialize the mock database."""
        self.collections = {}
        self.aql = self

    def execute(self, query, bind_vars=None):
        """Execute a mock AQL query."""
        return []

    def create_collection(self, name):
        """Create a mock collection."""
        self.collections[name] = []
        return {"name": name}

    def collection(self, name):
        """Get a mock collection."""
        if name not in self.collections:
            self.collections[name] = []
        return MockCollection(self.collections[name])

class MockCollection:
    """Mock collection for standalone testing."""

    def __init__(self, data):
        """Initialize the mock collection."""
        self.data = data

    def insert(self, document):
        """Insert a document into the mock collection."""
        self.data.append(document)
        return {"_id": str(uuid.uuid4())}


class TruthDataTracker:
    """Tracker for query truth data.

    This class tracks which records should match each query,
    enabling precise calculation of precision, recall, and F1 metrics.
    """

    def __init__(self, collection_name: str = "AblationQueryTruth"):
        """Initialize the truth data tracker.

        Args:
            collection_name: Name of the collection to store truth data in
        """
        self.collection_name = collection_name
        self.logger = logging.getLogger(__name__)

        try:
            self.db_config = IndalekoDBConfig()
            self.db = self.db_config.get_arangodb()

            # Create the truth data collection if it doesn't exist
            collections = self.db.collections()
            collection_names = [c["name"] for c in collections]

            if self.collection_name not in collection_names:
                self.db.create_collection(self.collection_name)
        except Exception as e:
            self.logger.error(f"Error connecting to database: {e}")
            self.db = None

    def record_query_truth(self, query_id: str, matching_ids: List[str],
                          activity_type: str, query_text: str,
                          query_components: Optional[Dict[str, Any]] = None) -> str:
        """Record the truth data for a query.

        Args:
            query_id: The identifier for the query
            matching_ids: List of identifiers for records that should match
            activity_type: The type of activity the query targets
            query_text: The natural language query
            query_components: Optional dictionary of query components

        Returns:
            Identifier for the created truth record
        """
        if not query_components:
            query_components = {}

        truth_record = {
            "_key": query_id,
            "query_id": query_id,
            "query_text": query_text,
            "activity_type": activity_type,
            "matching_ids": matching_ids,
            "components": query_components,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        try:
            if self.db:
                collection = self.db.collection(self.collection_name)
                result = collection.insert(truth_record)
                return result["_id"]
            else:
                self.logger.warning("Database not available, truth data not recorded")
                return query_id
        except Exception as e:
            self.logger.error(f"Error recording truth data: {e}")
            return query_id

    def get_matching_ids(self, query_id: str) -> List[str]:
        """Get the identifiers that should match a query.

        Args:
            query_id: The identifier for the query

        Returns:
            List of identifiers for records that should match
        """
        try:
            if self.db:
                query = f"""
                FOR doc IN {self.collection_name}
                FILTER doc.query_id == @query_id
                LIMIT 1
                RETURN doc.matching_ids
                """

                cursor = self.db.aql.execute(query, bind_vars={"query_id": query_id})
                results = list(cursor)

                if results:
                    return results[0]

            return []
        except Exception as e:
            self.logger.error(f"Error getting matching IDs: {e}")
            return []

    def get_truth_record(self, query_id: str) -> Optional[Dict[str, Any]]:
        """Get the complete truth record for a query.

        Args:
            query_id: The identifier for the query

        Returns:
            Truth record dictionary if found, None otherwise
        """
        try:
            if self.db:
                query = f"""
                FOR doc IN {self.collection_name}
                FILTER doc.query_id == @query_id
                LIMIT 1
                RETURN doc
                """

                cursor = self.db.aql.execute(query, bind_vars={"query_id": query_id})
                results = list(cursor)

                if results:
                    return results[0]

            return None
        except Exception as e:
            self.logger.error(f"Error getting truth record: {e}")
            return None

    def calculate_metrics(self, query_id: str, result_ids: List[str]) -> Dict[str, float]:
        """Calculate precision, recall, and F1 for query results.

        Args:
            query_id: The identifier for the query
            result_ids: List of identifiers returned by the query

        Returns:
            Dictionary with precision, recall, and F1 scores
        """
        truth_ids = set(self.get_matching_ids(query_id))
        result_ids_set = set(result_ids)

        # Calculate true positives, false positives, and false negatives
        true_positives = len(truth_ids.intersection(result_ids_set))
        false_positives = len(result_ids_set - truth_ids)
        false_negatives = len(truth_ids - result_ids_set)

        # Calculate precision, recall, and F1
        precision = true_positives / (true_positives + false_positives) if true_positives + false_positives > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if true_positives + false_negatives > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "truth_count": len(truth_ids),
            "result_count": len(result_ids_set)
        }

    def save_truth_data(self, output_path: Path) -> None:
        """Save all truth data to a file.

        Args:
            output_path: Path to save the truth data to
        """
        try:
            if self.db:
                query = f"""
                FOR doc IN {self.collection_name}
                RETURN doc
                """

                cursor = self.db.aql.execute(query)
                results = list(cursor)

                with open(output_path, 'w') as f:
                    json.dump(results, f, indent=2)
            else:
                self.logger.warning("Database not available, truth data not saved")
        except Exception as e:
            self.logger.error(f"Error saving truth data: {e}")

    def load_truth_data(self, input_path: Path) -> None:
        """Load truth data from a file.

        Args:
            input_path: Path to load the truth data from
        """
        try:
            if self.db:
                with open(input_path, 'r') as f:
                    truth_data = json.load(f)

                collection = self.db.collection(self.collection_name)

                for record in truth_data:
                    # Convert _key to string if it's not already
                    if "_key" in record and not isinstance(record["_key"], str):
                        record["_key"] = str(record["_key"])

                    try:
                        collection.insert(record)
                    except Exception as e:
                        self.logger.error(f"Error inserting truth record: {e}")
            else:
                self.logger.warning("Database not available, truth data not loaded")
        except Exception as e:
            self.logger.error(f"Error loading truth data: {e}")

    def clear_truth_data(self) -> None:
        """Clear all truth data from the collection."""
        try:
            if self.db:
                query = f"""
                FOR doc IN {self.collection_name}
                REMOVE doc IN {self.collection_name}
                """

                self.db.aql.execute(query)
            else:
                self.logger.warning("Database not available, truth data not cleared")
        except Exception as e:
            self.logger.error(f"Error clearing truth data: {e}")

    def get_all_query_ids(self) -> List[str]:
        """Get all query IDs in the truth data.

        Returns:
            List of query IDs
        """
        try:
            if self.db:
                query = f"""
                FOR doc IN {self.collection_name}
                RETURN doc.query_id
                """

                cursor = self.db.aql.execute(query)
                return list(cursor)
            else:
                self.logger.warning("Database not available, cannot get query IDs")
                return []
        except Exception as e:
            self.logger.error(f"Error getting query IDs: {e}")
            return []
