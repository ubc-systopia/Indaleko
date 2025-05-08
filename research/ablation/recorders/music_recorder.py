"""Music activity recorder for ablation testing."""

import logging
from uuid import UUID

from ..base import ISyntheticRecorder

# Dummy import for database config - will be replaced with actual implementation
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
        Indaleko_Activities_Collection = "Activities"
        Indaleko_Truth_Data_Collection = "TruthData"


class MusicActivityRecorder(ISyntheticRecorder):
    """Synthetic recorder for music activity."""

    def __init__(self):
        """Initialize the music activity recorder."""
        try:
            self.db_config = IndalekoDBConfig()
            self.db = self.db_config.get_arangodb()
            self.collection = self.db.collection(IndalekoDBCollections.Indaleko_Activities_Collection)
            self.truth_collection = self.db.collection(IndalekoDBCollections.Indaleko_Truth_Data_Collection)
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
            # Ensure the data has the right format for the database
            # In a real implementation, we would perform validation and conversion here

            # Insert the data into the database
            self.collection.insert(data)
            logging.info(f"Recorded music activity with ID {data.get('id')}")
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
            # Convert UUIDs to strings for database storage
            entity_ids_str = [str(entity_id) for entity_id in entity_ids]

            # Create the truth data document
            truth_data = {
                "_key": str(query_id),
                "query_id": str(query_id),
                "entity_ids": entity_ids_str,
                "collection": IndalekoDBCollections.Indaleko_Activities_Collection,
                "activity_type": "music",
            }

            # Insert the truth data into the database
            self.truth_collection.insert(truth_data)
            logging.info(f"Recorded truth data for query {query_id} with {len(entity_ids)} matching entities")
            return True
        except Exception as e:
            logging.exception(f"Failed to record truth data: {e}")
            return False
