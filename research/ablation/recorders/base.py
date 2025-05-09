"""Base implementation for ablation activity recorders."""

import json
import logging
import sys
from uuid import UUID

from db.db_config import IndalekoDBConfig

from ..base import ISyntheticRecorder


class BaseActivityRecorder(ISyntheticRecorder):
    """Base class for synthetic activity recorders.

    This recorder provides common functionality for writing activity data 
    to the ArangoDB database and managing ablation test collections.
    """

    # Collection name for activity data
    COLLECTION_NAME: str | None = None

    # Collection name for truth data
    TRUTH_COLLECTION: str | None = None

    # Activity model class - must be set by subclasses
    ActivityClass: type = None

    def __init__(self):
        """Initialize the activity recorder."""
        self.logger = logging.getLogger(__name__)
        self.db_config = None
        self.db = None
        self._setup_db_connection()

    def _setup_db_connection(self) -> bool:
        """Set up the database connection.

        Returns:
            bool: True if the connection was successful, False otherwise.
        """
        self.db_config = IndalekoDBConfig()
        self.db = self.db_config.get_arangodb()

        # Ensure collections exist
        self._ensure_collections_exist()

        return True

    def _ensure_collections_exist(self) -> None:
        """Ensure that the required collections exist in the database."""
        if not self.db:
            self.logger.critical("No database connection available")
            sys.exit(1)

        # Check if the main collection exists
        if not self.db.has_collection(self.COLLECTION_NAME):
            self.db.create_collection(self.COLLECTION_NAME)
            self.logger.info(f"Created collection {self.COLLECTION_NAME}")

        # Check if the truth collection exists
        if not self.db.has_collection(self.TRUTH_COLLECTION):
            self.db.create_collection(self.TRUTH_COLLECTION)
            self.logger.info(f"Created collection {self.TRUTH_COLLECTION}")

    def record(self, data: dict) -> bool:
        """Record activity data to the database.

        Args:
            data: The activity data to record.

        Returns:
            bool: True if recording was successful, False otherwise.
        """
        if not self.db:
            self.logger.critical("No database connection available")
            sys.exit(1)

        # Convert to ActivityClass model for validation and serialization
        activity_dict = json.loads(self.ActivityClass(**data).model_dump_json())

        # Get the collection
        collection = self.db.collection(self.COLLECTION_NAME)

        # Insert the document
        result = collection.insert(activity_dict)

        self.logger.info(f"Recorded activity with _key: {result['_key']}")
        return True

    def record_batch(self, data_batch: list[dict[str, object]]) -> bool:
        """Record a batch of activity data to the database.

        Args:
            data_batch: List of activity data to record.

        Returns:
            bool: True if recording was successful, False otherwise.
        """
        if not self.db:
            self.logger.critical("No database connection available")
            sys.exit(1)

        # Get the collection
        collection = self.db.collection(self.COLLECTION_NAME)

        # Validate each document and prepare for insertion
        validated_data = []
        for data in data_batch:
            # Convert to ActivityClass model for validation
            activity_dict = json.loads(self.ActivityClass(**data).model_dump_json())

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
        self.logger.debug("Results of batch insert: %s", results)

        # Explicitly check if all documents were inserted successfully
        if not results or len(results) != len(validated_data):
            self.logger.error(
                "Batch insert failed: Expected %s documents, but only %s were inserted",
                len(validated_data),
                len(results) if results else 0,
            )
            return False
        self.logger.info(
            f"Recorded {len(validated_data)} activities in batch (collection {collection.name})"
        )
        return True

    def record_truth_data(self, query_id: UUID, entity_ids: set[UUID]) -> bool:
        """Record truth data for a specific query.

        Args:
            query_id: The UUID of the query.
            entity_ids: The set of entity UUIDs that should match the query.

        Returns:
            bool: True if recording was successful, False otherwise.
        """
        if not self.db:
            self.logger.critical("No database connection available")
            sys.exit(1)

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

    def delete_all(self) -> bool:
        """Delete all records created by this recorder.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        if not self.db:
            self.logger.critical("No database connection available")
            sys.exit(1)

        # Delete all documents in the collection
        self.db.aql.execute(f"FOR doc IN {self.COLLECTION_NAME} REMOVE doc IN {self.COLLECTION_NAME}")

        # Count the documents to verify deletion
        count = self.count_records()

        if count == 0:
            self.logger.info(f"Successfully deleted all records from {self.COLLECTION_NAME}")
            return True
        else:
            self.logger.critical(f"Failed to delete all records: {count} records remain in collection {self.COLLECTION_NAME}")
            sys.exit(1)

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
            self.logger.critical("No database connection available")
            sys.exit(1)

        # Count the documents in the collection
        result = self.db.aql.execute(f"RETURN LENGTH({self.COLLECTION_NAME})")

        # Extract the count from the cursor
        count = next(result)

        return count

    def get_record_by_id(self, record_id: UUID) -> dict[str, object] | None:
        """Get an activity record by its ID.

        Args:
            record_id: The UUID of the record to retrieve.

        Returns:
            Optional[Dict[str, object]]: The record if found, None otherwise.
        """
        if not self.db:
            self.logger.critical("No database connection available")
            sys.exit(1)

        # Retrieve the document
        document = self.db.collection(self.COLLECTION_NAME).get(str(record_id))

        return document