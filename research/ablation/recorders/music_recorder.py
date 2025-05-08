"""Music activity recorder for ablation testing."""

import logging
from typing import Any
from uuid import UUID

from ..base import ISyntheticRecorder

# Import database configuration
try:
    from db.db_collections import IndalekoDBCollections
    from db.db_config import IndalekoDBConfig
except ImportError:
    logging.warning("IndalekoDBConfig not available - using mock implementation")

    # Mock implementation for testing without database
    class IndalekoDBConfig:
        def __init__(self):
            pass

        def get_arangodb(self):
            return None

    class IndalekoDBCollections:
        Indaleko_Ablation_Music_Activity_Collection = "AblationMusicActivity"
        Indaleko_Ablation_Query_Truth_Collection = "AblationQueryTruth"


class MusicActivityRecorder(ISyntheticRecorder):
    """Synthetic recorder for music activity."""

    def __init__(self):
        """Initialize the music activity recorder."""
        try:
            self.db_config = IndalekoDBConfig()
            self.db = self.db_config.get_arangodb()
            self.collection = self.db.collection(IndalekoDBCollections.Indaleko_Ablation_Music_Activity_Collection)
            self.truth_collection = self.db.collection(IndalekoDBCollections.Indaleko_Ablation_Query_Truth_Collection)
        except Exception as e:
            logging.exception(f"Failed to connect to database: {e}")
            self.db = None
            self.collection = None
            self.truth_collection = None

    def record(self, data: dict) -> bool:
        """Record music activity data to the database.

        Args:
            data: The music activity data to record.

        Returns:
            bool: True if recording was successful, False otherwise.
        """
        if self.db is None or self.collection is None:
            logging.error("Database connection not available")
            return False

        try:
            # Ensure the data has the right format for the database by using json serialization
            # This handles complex types like UUIDs and datetimes automatically
            import json

            from pydantic import BaseModel

            if isinstance(data, BaseModel):
                # If it's a Pydantic model, use model_dump_json to ensure proper serialization
                processed_data = json.loads(data.model_dump_json())
            elif isinstance(data, dict):
                # For regular dictionaries, we need to ensure all values are serializable
                # First convert to JSON string and then back to dict to handle UUIDs, etc.
                processed_data = json.loads(json.dumps(data, default=str))
            else:
                processed_data = data

            # Insert the data into the database
            self.collection.insert(processed_data)
            logging.info(f"Recorded music activity with ID {processed_data.get('id')}")
            return True
        except Exception as e:
            logging.exception(f"Failed to record music activity: {e}")
            return False

    def record_truth_data(self, query_id: UUID, entity_ids: set[UUID]) -> bool:
        """Record truth data for a music-related query.

        Args:
            query_id: The UUID of the query.
            entity_ids: The set of entity UUIDs that should match the query.

        Returns:
            bool: True if recording was successful, False otherwise.
        """
        if self.db is None or self.truth_collection is None:
            logging.error("Database connection not available")
            return False

        try:
            # Create the truth data document
            truth_data = {
                "_key": query_id,  # Will be converted to string by json serialization
                "query_id": query_id,
                "entity_ids": list(entity_ids),  # Convert set to list for serialization
                "collection": IndalekoDBCollections.Indaleko_Ablation_Music_Activity_Collection,
                "activity_type": "music",
            }

            # Use json serialization to handle UUID objects
            import json

            processed_data = json.loads(json.dumps(truth_data, default=str))

            # Insert the truth data into the database
            self.truth_collection.insert(processed_data)
            logging.info(f"Recorded truth data for query {query_id} with {len(entity_ids)} matching entities")
            return True
        except Exception as e:
            logging.exception(f"Failed to record truth data: {e}")
            return False

    def record_batch(self, data_batch: list[dict[str, Any]]) -> bool:
        """Record a batch of music activity data to the database.

        Args:
            data_batch: List of music activity data to record.

        Returns:
            bool: True if recording was successful, False otherwise.
        """
        if self.db is None or self.collection is None:
            logging.error("Database connection not available")
            return False

        try:
            # Insert each item in the batch
            for data in data_batch:
                # Just use record method to ensure consistent serialization
                success = self.record(data)
                if not success:
                    raise ValueError("Failed to record item in batch")

            logging.info(f"Recorded batch of {len(data_batch)} music activities")
            return True
        except Exception as e:
            logging.exception(f"Failed to record music activity batch: {e}")
            return False

    def delete_all(self) -> bool:
        """Delete all music activity records.

        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        if self.db is None:
            logging.error("Database connection not available")
            return False

        try:
            # Delete all documents in the collection
            aql_query = f"""
            FOR doc IN {IndalekoDBCollections.Indaleko_Ablation_Music_Activity_Collection}
            REMOVE doc IN {IndalekoDBCollections.Indaleko_Ablation_Music_Activity_Collection}
            """
            self.db.aql.execute(aql_query)

            logging.info("Deleted all music activity records")
            return True
        except Exception as e:
            logging.exception(f"Failed to delete music activity records: {e}")
            return False

    def get_collection_name(self) -> str:
        """Get the name of the collection this recorder writes to.

        Returns:
            str: The collection name.
        """
        return IndalekoDBCollections.Indaleko_Ablation_Music_Activity_Collection

    def count_records(self) -> int:
        """Count the number of music activity records in the collection.

        Returns:
            int: The record count.
        """
        if self.db is None:
            logging.error("Database connection not available")
            return 0

        try:
            # Count documents in the collection
            aql_query = f"""
            RETURN LENGTH({IndalekoDBCollections.Indaleko_Ablation_Music_Activity_Collection})
            """
            cursor = self.db.aql.execute(aql_query)
            count = next(cursor)

            logging.info(f"Counted {count} music activity records")
            return count
        except Exception as e:
            logging.exception(f"Failed to count music activity records: {e}")
            return 0
