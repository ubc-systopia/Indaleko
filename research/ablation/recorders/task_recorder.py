"""Task activity recorder for ablation testing."""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from db.db_config import IndalekoDBConfig

from ..base import ISyntheticRecorder
from ..models.task_activity import TaskActivity


class TaskActivityRecorder(ISyntheticRecorder):
    """Synthetic recorder for task activity data.

    This recorder writes task activity data to the ArangoDB database
    and manages the ablation test collections.
    """

    # Collection name for task activity
    COLLECTION_NAME = "AblationTaskActivity"

    # Collection name for truth data
    TRUTH_COLLECTION = "AblationTruthData"

    def __init__(self):
        """Initialize the task activity recorder."""
        self.logger = logging.getLogger(__name__)
        self.db_config = None
        self.db = None
        self._setup_db_connection()

    def _setup_db_connection(self) -> bool:
        """Set up the database connection.

        Returns:
            bool: True if the connection was successful, False otherwise.
        """
        try:
            self.db_config = IndalekoDBConfig()
            self.db = self.db_config.get_arangodb()

            # Ensure collections exist
            self._ensure_collections_exist()

            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            return False

    def _ensure_collections_exist(self) -> None:
        """Ensure that the required collections exist in the database."""
        if not self.db:
            self.logger.error("No database connection available")
            return

        try:
            # Check if the main collection exists
            if not self.db.has_collection(self.COLLECTION_NAME):
                self.db.create_collection(self.COLLECTION_NAME)
                self.logger.info(f"Created collection {self.COLLECTION_NAME}")

            # Check if the truth collection exists
            if not self.db.has_collection(self.TRUTH_COLLECTION):
                self.db.create_collection(self.TRUTH_COLLECTION)
                self.logger.info(f"Created collection {self.TRUTH_COLLECTION}")
        except Exception as e:
            self.logger.error(f"Failed to ensure collections exist: {e}")
            raise

    def record(self, data: dict) -> bool:
        """Record task activity data to the database.

        Args:
            data: The task activity data to record.

        Returns:
            bool: True if recording was successful, False otherwise.
        """
        if not self.db:
            self.logger.error("No database connection available")
            return False

        try:
            # Convert to TaskActivity model for validation
            activity = TaskActivity(**data)

            # Convert to dict and ensure UUID objects are converted to strings
            activity_dict = activity.dict()
            # Convert any UUIDs, Enums, and datetimes to strings for JSON serialization
            for key, value in activity_dict.items():
                if isinstance(value, UUID):
                    activity_dict[key] = str(value)
                elif key == "activity_type" and hasattr(value, "name"):
                    # Handle ActivityType enum serialization
                    activity_dict[key] = value.name
                elif isinstance(value, datetime):
                    # Convert datetime to ISO format
                    activity_dict[key] = value.isoformat()

            # Get the collection
            collection = self.db.collection(self.COLLECTION_NAME)

            # Insert the document
            result = collection.insert(activity_dict)

            self.logger.info(f"Recorded task activity with _key: {result['_key']}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to record task activity: {e}")
            return False

    def record_batch(self, data_batch: list[dict[str, Any]]) -> bool:
        """Record a batch of task activity data to the database.

        Args:
            data_batch: List of task activity data to record.

        Returns:
            bool: True if recording was successful, False otherwise.
        """
        if not self.db:
            self.logger.error("No database connection available")
            return False

        try:
            # Get the collection
            collection = self.db.collection(self.COLLECTION_NAME)

            # Validate each document and prepare for insertion
            validated_data = []
            for data in data_batch:
                # Convert to TaskActivity model for validation
                activity = TaskActivity(**data)
                # Convert to dict and ensure UUID objects are converted to strings
                activity_dict = activity.dict()
                # Convert any UUIDs, Enums, and datetimes to strings for JSON serialization
                for key, value in activity_dict.items():
                    if isinstance(value, UUID):
                        activity_dict[key] = str(value)
                    elif key == "activity_type" and hasattr(value, "name"):
                        # Handle ActivityType enum serialization
                        activity_dict[key] = value.name
                    elif isinstance(value, datetime):
                        # Convert datetime to ISO format
                        activity_dict[key] = value.isoformat()
                
                # Set _key to match the entity ID if it exists
                if "id" in data:
                    # Use the ID as the document key for direct matching
                    activity_dict["_key"] = str(data["id"])
                elif "id" in activity_dict:
                    # Use the ID as the document key for direct matching
                    activity_dict["_key"] = activity_dict["id"]
                
                validated_data.append(activity_dict)

            # Insert the documents
            results = collection.insert_many(validated_data)

            self.logger.info(f"Recorded {len(results)} task activities in batch")
            return True
        except Exception as e:
            self.logger.error(f"Failed to record task activity batch: {e}")
            return False

    def record_truth_data(self, query_id: UUID, entity_ids: set[UUID]) -> bool:
        """Record truth data for a specific query.

        Args:
            query_id: The UUID of the query.
            entity_ids: The set of entity UUIDs that should match the query.

        Returns:
            bool: True if recording was successful, False otherwise.
        """
        if not self.db:
            self.logger.error("No database connection available")
            return False

        try:
            # Get the truth collection
            collection = self.db.collection(self.TRUTH_COLLECTION)

            # Create the truth document
            truth_doc = {
                "_key": str(query_id),
                "query_id": str(query_id),
                "matching_entities": [str(entity_id) for entity_id in entity_ids],
                "collection": self.COLLECTION_NAME,
            }

            # Check if a document with this query_id already exists
            existing = collection.get(str(query_id))
            if existing:
                # Update the existing document
                collection.update(truth_doc)
                self.logger.info(f"Updated truth data for query {query_id}")
            else:
                # Insert a new document
                collection.insert(truth_doc)
                self.logger.info(f"Recorded truth data for query {query_id}")

            return True
        except Exception as e:
            self.logger.error(f"Failed to record truth data: {e}")
            return False

    def delete_all(self) -> bool:
        """Delete all records created by this recorder.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        if not self.db:
            self.logger.error("No database connection available")
            return False

        try:
            # Delete all documents in the collection
            self.db.aql.execute(f"FOR doc IN {self.COLLECTION_NAME} REMOVE doc IN {self.COLLECTION_NAME}")

            # Count the documents to verify deletion
            count = self.count_records()

            if count == 0:
                self.logger.info(f"Successfully deleted all records from {self.COLLECTION_NAME}")
                return True
            else:
                self.logger.warning(f"Failed to delete all records: {count} records remain")
                return False
        except Exception as e:
            self.logger.error(f"Failed to delete records: {e}")
            return False

    def get_collection_name(self) -> str:
        """Get the name of the collection this recorder writes to.

        Returns:
            str: The collection name.
        """
        return self.COLLECTION_NAME

    def count_records(self) -> int:
        """Count the number of records in the collection.

        Returns:
            int: The record count.
        """
        if not self.db:
            self.logger.error("No database connection available")
            return 0

        try:
            # Count the documents in the collection
            result = self.db.aql.execute(f"RETURN LENGTH({self.COLLECTION_NAME})")

            # Extract the count from the cursor
            count = next(result)

            return count
        except Exception as e:
            self.logger.error(f"Failed to count records: {e}")
            return 0

    def get_record_by_id(self, record_id: UUID) -> dict[str, Any] | None:
        """Get a task activity record by its ID.

        Args:
            record_id: The UUID of the record to retrieve.

        Returns:
            Optional[Dict[str, Any]]: The record if found, None otherwise.
        """
        if not self.db:
            self.logger.error("No database connection available")
            return None

        try:
            # Get the collection
            collection = self.db.collection(self.COLLECTION_NAME)

            # Retrieve the document
            document = collection.get(str(record_id))

            return document
        except Exception as e:
            self.logger.error(f"Failed to get record by ID: {e}")
            return None

    def get_records_by_query(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get task activity records that match a query.

        This is a simplified implementation that uses AQL to search
        for task activities based on a keyword query.

        Args:
            query: The query string to search for.
            limit: The maximum number of records to return.

        Returns:
            List[Dict[str, Any]]: The matching records.
        """
        if not self.db:
            self.logger.error("No database connection available")
            return []

        try:
            # Convert query to lowercase for case-insensitive search
            query_lower = query.lower()

            # Execute AQL query to search for matching documents
            result_cursor = self.db.aql.execute(
                f"""
                FOR doc IN {self.COLLECTION_NAME}
                FILTER LOWER(doc.task_name) LIKE @query OR
                       LOWER(doc.application) LIKE @query OR
                       (doc.window_title != NULL AND LOWER(doc.window_title) LIKE @query) OR
                       (doc.user != NULL AND LOWER(doc.user) LIKE @query)
                LIMIT @limit
                RETURN doc
                """,
                bind_vars={"query": f"%{query_lower}%", "limit": limit},
            )

            # Convert cursor to list
            results = [doc for doc in result_cursor]

            return results
        except Exception as e:
            self.logger.error(f"Failed to get records by query: {e}")
            return []
