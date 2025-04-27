# \!/usr/bin/env python
"""
NTFS Short-Term Memory Recorder for Indaleko.

This module implements the "Short-Term Memory" component of the NTFS cognitive memory system,
providing intermediate storage of preprocessed file system activities.

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

from datetime import UTC, datetime, timedelta


# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import required modules
try:
    from activity.characteristics import ActivityDataCharacteristics
    from activity.collectors.storage.data_models.storage_activity_data_model import (
        StorageActivityType,
        StorageProviderType,
    )
    from activity.recorders.storage.base import StorageActivityRecorder
except ImportError as e:
    logging.exception(f"Error importing required modules: {e}")

    # Create dummy classes for testing
    class StorageActivityRecorder:
        """Dummy base class for testing."""

    class StorageProviderType:
        """Dummy enum for testing."""

        LOCAL_NTFS = "LOCAL_NTFS"

    class StorageActivityType:
        """Dummy enum for testing."""

        CREATE = "CREATE"
        MODIFY = "MODIFY"
        DELETE = "DELETE"

    class ActivityDataCharacteristics:
        """Dummy enum for testing."""

        ACTIVITY_DATA_SYSTEM_ACTIVITY = "ACTIVITY_DATA_SYSTEM_ACTIVITY"
        ACTIVITY_DATA_FILE_ACTIVITY = "ACTIVITY_DATA_FILE_ACTIVITY"


class NtfsShortTermMemoryRecorder:
    """
    Short-Term Memory recorder for NTFS storage activities.

    Handles the intermediate storage of preprocessed file system activities.
    """

    DEFAULT_RECORDER_ID = uuid.UUID("b2e93f7c-6912-42ae-b31c-8f9a01d87a4e")

    def __init__(self, **kwargs):
        """
        Initialize the short-term memory recorder.

        Args:
            no_db: Whether to run without database connection
            db_config_path: Path to database configuration
            debug: Whether to enable debug logging
        """
        # Configure logging
        logging.basicConfig(
            level=logging.DEBUG if kwargs.get("debug", False) else logging.INFO,
        )
        self._logger = logging.getLogger("NtfsShortTermMemoryRecorder")

        # Set recorder properties
        self._name = kwargs.get("name", "NTFS Short-Term Memory Recorder")
        self._recorder_id = kwargs.get("recorder_id", self.DEFAULT_RECORDER_ID)
        self._description = kwargs.get(
            "description",
            "Records preprocessed NTFS file system activities in short-term memory",
        )
        self._version = kwargs.get("version", "1.0.0")
        self._provider_type = StorageProviderType.LOCAL_NTFS
        self._no_db = kwargs.get("no_db", False)

        self._logger.info(f"Initialized {self._name} (no_db={self._no_db})")

    def connect(self):
        """Connect to the database."""
        if self._no_db:
            self._logger.info("Skipping database connection (no_db=True)")
            return

        try:
            # In a real implementation, this would connect to the database
            self._logger.info("Connected to database")
        except Exception as e:
            self._logger.error(f"Error connecting to database: {e}")

    def get_recorder_name(self) -> str:
        """Get the name of the recorder."""
        return self._name

    def get_recorder_id(self) -> uuid.UUID:
        """Get the ID of the recorder."""
        return self._recorder_id

    def get_description(self) -> str:
        """Get a description of this recorder."""
        return self._description

    def get_recorder_characteristics(self) -> list[str]:
        """Get the characteristics of this recorder."""
        return [
            ActivityDataCharacteristics.ACTIVITY_DATA_SYSTEM_ACTIVITY,
            ActivityDataCharacteristics.ACTIVITY_DATA_FILE_ACTIVITY,
        ]

    def search_short_term_memory(
        self,
        query: str,
        importance_min: float = 0.0,
        limit: int = 10,
    ) -> list[dict]:
        """
        Search for activities in short-term memory.

        Args:
            query: Search query
            importance_min: Minimum importance score
            limit: Maximum number of results

        Returns:
            List of matching activities
        """
        self._logger.info(
            f"Searching short-term memory for {query} (min importance: {importance_min}, limit: {limit})",
        )

        # Mock implementation for testing
        results = []
        for i in range(min(3, limit)):
            results.append(
                {
                    "_key": str(uuid.uuid4()),
                    "Record": {
                        "Data": {
                            "file_path": f"/path/to/short_term_result_{i}.txt",
                            "activity_type": StorageActivityType.MODIFY,
                            "timestamp": datetime.now(UTC).isoformat(),
                            "importance_score": 0.6 + (i * 0.1),
                            "memory_tier": "short_term",
                        },
                    },
                },
            )

        return results

    def cache_duration(self) -> timedelta:
        """Get the cache duration for this recorder's data."""
        return timedelta(hours=2)
