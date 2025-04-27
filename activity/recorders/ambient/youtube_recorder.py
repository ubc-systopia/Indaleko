"""
YouTube activity recorder for the Indaleko project.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import logging
import os
import sys
import uuid

from datetime import UTC, datetime
from typing import Any


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from Indaleko import Indaleko
from activity.characteristics import ActivityCharacteristics
from activity.collectors.ambient.media.youtube_collector import YouTubeActivityCollector
from activity.collectors.ambient.media.youtube_data_model import YouTubeVideoActivity
from activity.recorders.base import RecorderBase


# pylint: enable=wrong-import-position

# Set up logging
logger = logging.getLogger(__name__)


class YouTubeActivityRecorder(RecorderBase):
    """
    YouTube activity recorder for storing activity data in Indaleko.

    This recorder takes YouTube video watch activities collected by
    the YouTubeActivityCollector and stores them in the Indaleko
    database. It supports multi-dimensional classification of activities,
    allowing for rich semantic understanding of user behavior.
    """

    def __init__(self, **kwargs):
        """
        Initialize the YouTube activity recorder.

        Args:
            collector (YouTubeActivityCollector, optional): The collector to use
            collection_name (str, optional): Name of the collection to store data in
            name (str, optional): Custom name for the recorder
            recorder_id (uuid.UUID, optional): Custom recorder ID
        """
        self._name = kwargs.get("name", "YouTube Activity Recorder")
        self._recorder_id = kwargs.get(
            "recorder_id",
            uuid.UUID("8b9c0d1e-2f3a-4b5c-6d7e-8f9a0b1c2d3e"),
        )

        # Storage parameters
        self._collection_name = kwargs.get("collection_name", "YouTubeActivity")

        # Collector reference
        self._collector = kwargs.get("collector")

        # Initialize database connection
        self._db = Indaleko()
        try:
            self._db.connect()
            self._collection = self._db.get_collection(self._collection_name)
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            self._collection = None

        # Last update timestamp
        self._last_update = None

        # Description
        self._description = "Stores YouTube video watch activity data in Indaleko"

    def get_recorder_characteristics(self) -> ActivityCharacteristics:
        """Return the characteristics of this recorder."""
        return ActivityCharacteristics(
            collector_type="ambient",
            data_category="media",
            data_sources=["youtube"],
            semantic_attributes=["MediaType", "Platform", "ContentConsumption"],
            related_objects=["YoutubeChannel", "YoutubeVideo"],
            requires_authentication=True,
        )

    def get_recorder_name(self) -> str:
        """Return the name of this recorder."""
        return self._name

    def get_recorder_id(self) -> uuid.UUID:
        """Return the recorder ID."""
        return self._recorder_id

    def get_collector_class_model(self) -> type:
        """Return the collector class model."""
        return YouTubeActivityCollector

    def get_cursor(self) -> str | None:
        """
        Return a cursor for resuming data storage.

        Returns:
            Optional[str]: A cursor string or None if no cursor is available
        """
        if self._collector:
            return self._collector.get_cursor()
        return None

    def cache_duration(self) -> int:
        """
        Return the recommended cache duration in seconds.

        Returns:
            int: Recommended cache duration in seconds
        """
        if self._collector:
            return self._collector.cache_duration()
        return 3600  # 1 hour default

    def get_description(self) -> str:
        """
        Return a human-readable description of this recorder.

        Returns:
            str: Recorder description
        """
        return self._description

    def get_json_schema(self) -> dict[str, Any]:
        """
        Return the JSON schema for YouTube activity data.

        Returns:
            Dict[str, Any]: JSON schema
        """
        return YouTubeVideoActivity.schema()

    def process_data(
        self,
        activities: list[YouTubeVideoActivity],
    ) -> list[dict[str, Any]]:
        """
        Process activity data before storage.

        This method converts YouTubeVideoActivity objects to ArangoDB-compatible
        documents, adding necessary database fields and formatting.

        Args:
            activities (List[YouTubeVideoActivity]): YouTube activity objects

        Returns:
            List[Dict[str, Any]]: Processed documents ready for storage
        """
        processed_docs = []

        for activity in activities:
            try:
                # Build ArangoDB document
                doc = activity.build_arangodb_doc()

                # Add additional database metadata
                doc["_created"] = datetime.now(UTC).isoformat()
                doc["_collector"] = "YouTubeActivityCollector"
                doc["_recorder"] = self._name

                processed_docs.append(doc)

            except Exception as e:
                logger.error(f"Error processing activity data: {e}")
                continue

        return processed_docs

    def store_activities(self, activities: list[YouTubeVideoActivity]) -> bool:
        """
        Store YouTube activity data in the database.

        Args:
            activities (List[YouTubeVideoActivity]): Activities to store

        Returns:
            bool: True if successful, False otherwise
        """
        if not self._collection:
            logger.error("Database collection not available")
            return False

        if not activities:
            logger.info("No activities to store")
            return True

        try:
            # Process activities into database documents
            docs = self.process_data(activities)

            # Store in database
            result = self._collection.import_documents(
                docs,
                on_duplicate="update",  # Update if duplicate found
            )

            # Update timestamp
            self._last_update = datetime.now(UTC)

            logger.info(f"Stored {len(docs)} YouTube activities")
            return True

        except Exception as e:
            logger.error(f"Error storing YouTube activities: {e}")
            return False

    def store_data(
        self,
        data: list[YouTubeVideoActivity] | YouTubeVideoActivity,
    ) -> bool:
        """
        Store activity data.

        This is a generic interface that delegates to store_activities.

        Args:
            data: Activity data to store

        Returns:
            bool: True if successful, False otherwise
        """
        if isinstance(data, list):
            return self.store_activities(data)
        elif isinstance(data, YouTubeVideoActivity):
            return self.store_activities([data])
        else:
            logger.error(f"Unsupported data type: {type(data)}")
            return False

    def update_data(
        self,
        data: list[YouTubeVideoActivity] | YouTubeVideoActivity,
    ) -> bool:
        """
        Update existing activity data.

        For YouTube activities, this is the same as store_data with on_duplicate="update".

        Args:
            data: Activity data to update

        Returns:
            bool: True if successful, False otherwise
        """
        return self.store_data(data)

    def get_latest_db_update(self) -> datetime | None:
        """
        Get the timestamp of the latest database update.

        Returns:
            Optional[datetime]: Latest update timestamp or None
        """
        return self._last_update

    def collect_and_store(self) -> bool:
        """
        Convenience method to collect data from collector and store it.

        Returns:
            bool: True if successful, False otherwise
        """
        if not self._collector:
            logger.error("No collector configured")
            return False

        try:
            # Collect data
            self._collector.collect_data()

            # Get and store activities
            activities = self._collector.get_activities()
            return self.store_activities(activities)

        except Exception as e:
            logger.error(f"Error in collect_and_store: {e}")
            return False


def main():
    """Test the YouTube activity recorder."""
    # This is just a simple test
    collector = YouTubeActivityCollector()
    recorder = YouTubeActivityRecorder(collector=collector)

    print(f"Recorder: {recorder.get_recorder_name()}")
    print(f"Recorder ID: {recorder.get_recorder_id()}")
    print(f"Description: {recorder.get_description()}")

    # Real test would require API credentials
    # success = recorder.collect_and_store()
    # print(f"Collect and store result: {success}")


if __name__ == "__main__":
    main()
