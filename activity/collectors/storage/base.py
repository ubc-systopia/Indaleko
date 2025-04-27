"""
Base class for storage activity collectors in Indaleko.

This module provides a standardized base class for
implementing storage activity
collectors across different storage providers (NTFS, Dropbox, OneDrive, etc.).

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

import json
import logging
import os
import socket
import sys
import uuid

from abc import abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.base import CollectorBase
from activity.collectors.storage.data_models.storage_activity_data_model import (
    BaseStorageActivityData,
    StorageActivityData,
    StorageActivityMetadata,
    StorageActivityType,
    StorageProviderType,
)
from data_models.timestamp import IndalekoTimestampDataModel


# pylint: enable=wrong-import-position


class StorageActivityCollector(CollectorBase):
    """
    Base class for all storage activity collectors.

    This class provides common functionality for collecting storage activities
    across different storage providers. Specific providers should extend this
    class and implement the provider-specific logic.
    """

    def __init__(self, **kwargs):
        """
        Initialize the storage activity collector.

        Args:
            name: Name of the collector
            provider_id: UUID of the provider
            provider_type: Type of storage provider
            version: Version of the collector
            description: Description of the collector
            max_history_days: Maximum number of days to retrieve history for
            user_id: User ID for authentication (if applicable)
            debug: Enable debug logging
        """
        # Basic configuration
        self._name = kwargs.get("name", "Storage Activity Collector")
        self._provider_id = kwargs.get(
            "provider_id",
            uuid.UUID("59f3a2d8-8e31-4cb5-9e89-f516ea9d3c77"),
        )
        self._provider_type = kwargs.get("provider_type", StorageProviderType.OTHER)
        self._version = kwargs.get("version", "1.0.0")
        self._description = kwargs.get("description", "Collects storage activities")

        # Configuration
        self._max_history_days = kwargs.get("max_history_days", 30)
        self._user_id = kwargs.get("user_id", None)
        self._debug = kwargs.get("debug", False)
        self._machine_name = kwargs.get("machine_name", socket.gethostname())

        # Data structures
        self._activities = []
        self._storage_location = kwargs.get("storage_location", None)

        # Output path for storing collected data
        self._output_path = kwargs.get("output_path", None)

        # Metadata
        self._metadata = StorageActivityMetadata(
            provider_type=self._provider_type,
            provider_name=self._name,
            source_machine=self._machine_name,
            storage_location=self._storage_location,
        )

        # Setup logging
        self._logger = logging.getLogger(f"{self._name}")

        # Map of activity types to handler methods
        self._activity_handlers = {}

    def generate_collector_file_name(self: "StorageActivityCollector", **kwargs) -> str:
        """Generate a file name for the storage activity data collector"""
        if "platform" not in kwargs:
            kwargs["platform"] = self.collector_data.PlatformName
        if "collector_name" not in kwargs:
            kwargs["collector_name"] = self.collector_data.ServiceRegistrationFileName
        if "machine_id" not in kwargs:
            if not hasattr(self, "machine_id"):
                ic(f"type(cls): {type(self)}")
                ic(f"dir(cls): {dir(self)}")
            kwargs["machine_id"] = self.machine_id  # must be there!
        assert "machine_id" in kwargs, "machine_id must be specified"
        return BaseStorageCollector.__generate_collector_file_name(**kwargs)

    @staticmethod
    def __generate_collector_file_name(**kwargs) -> str:
        """This will generate a file name for the collector output file."""
        # platform : str, target_dir : str = None, suffix : str = None) -> str:
        assert "collector_name" in kwargs, "collector_name must be specified"
        platform = None
        if "platform" in kwargs:
            if not isinstance(kwargs["platform"], str):
                raise ValueError("platform must be a string")
            platform = kwargs["platform"].replace("-", "_")
        collector_name = kwargs.get("collector_name", "unknown_collector").replace(
            "-",
            "_",
        )
        if not isinstance(collector_name, str):
            raise ValueError("collector_name must be a string")
        machine_id = kwargs.get("machine_id", None)
        storage_description = None
        if "storage_description" in kwargs:
            storage_description = str(uuid.UUID(kwargs["storage_description"]).hex)
        timestamp = kwargs.get(
            "timestamp",
            datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
        assert isinstance(timestamp, str), "timestamp must be a string"
        target_dir = indaleko_default_data_dir
        if "target_dir" in kwargs:
            target_dir = kwargs["target_dir"]
        suffix = kwargs.get("suffix", BaseStorageCollector.default_file_suffix)
        kwargs = {
            "service": collector_name,
            "timestamp": timestamp,
        }
        if platform:
            kwargs["platform"] = platform
        if machine_id is not None:
            kwargs["machine"] = machine_id
        if storage_description is not None:
            kwargs["storage"] = storage_description
        kwargs["suffix"] = suffix
        name = generate_file_name(**kwargs)
        return os.path.join(target_dir, name)

    def add_activity(self, activity: BaseStorageActivityData) -> None:
        """
        Add an activity to the collection.

        Args:
            activity: The activity to add
        """
        self._activities.append(activity)
        self._metadata.activity_count += 1

    def get_activities(
        self,
        filters: dict | None = None,
    ) -> list[BaseStorageActivityData]:
        """
        Get collected activities, optionally filtered.

        Args:
            filters: Dictionary of filters to apply

        Returns:
            List of activities
        """
        if not filters:
            return self._activities

        results = []
        for activity in self._activities:
            match = True
            for key, value in filters.items():
                if hasattr(activity, key) and getattr(activity, key) != value:
                    match = False
                    break
            if match:
                results.append(activity)

        return results

    def clear_activities(self) -> None:
        """Clear all collected activities."""
        self._activities = []
        self._metadata.activity_count = 0

    def get_activity_by_id(
        self,
        activity_id: uuid.UUID,
    ) -> BaseStorageActivityData | None:
        """
        Get an activity by its ID.

        Args:
            activity_id: The activity ID to look for

        Returns:
            The activity if found, None otherwise
        """
        for activity in self._activities:
            if activity.activity_id == activity_id:
                return activity
        return None

    def get_activities_by_type(
        self,
        activity_type: StorageActivityType,
    ) -> list[BaseStorageActivityData]:
        """
        Get activities of a specific type.

        Args:
            activity_type: Type of activities to get

        Returns:
            List of activities of the specified type
        """
        return [a for a in self._activities if a.activity_type == activity_type]

    def get_activities_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> list[BaseStorageActivityData]:
        """
        Get activities within a time range.

        Args:
            start_time: Start of the time range
            end_time: End of the time range

        Returns:
            List of activities within the time range
        """
        return [a for a in self._activities if start_time <= a.timestamp <= end_time]

    # Implement CollectorBase abstract methods
    def get_collector_characteristics(self) -> list[ActivityDataCharacteristics]:
        """Get the characteristics of this collector."""
        return [
            ActivityDataCharacteristics.ACTIVITY_DATA_SYSTEM_ACTIVITY,
            ActivityDataCharacteristics.ACTIVITY_DATA_FILE_ACTIVITY,
        ]

    def get_collector_name(self) -> str:
        """Get the name of the collector."""
        return self._name

    def get_provider_id(self) -> uuid.UUID:
        """Get the ID of the collector."""
        return self._provider_id

    def get_provider_type(self) -> StorageProviderType:
        """Get the type of storage provider."""
        return self._provider_type

    def retrieve_data(self, data_id: uuid.UUID) -> dict:
        """
        Retrieve data for a specific ID.

        Args:
            data_id: The ID to retrieve data for

        Returns:
            The requested data
        """
        activity = self.get_activity_by_id(data_id)
        if activity:
            return activity.model_dump()
        return {}

    def get_cursor(self, activity_context: uuid.UUID) -> uuid.UUID:
        """
        Get a cursor for the provided activity context.

        Args:
            activity_context: The activity context

        Returns:
            A cursor UUID
        """
        # In this simple implementation, just return a new UUID
        return uuid.uuid4()

    def cache_duration(self) -> timedelta:
        """
        Get the cache duration for this collector's data.

        Returns:
            The cache duration
        """
        return timedelta(minutes=30)

    def get_description(self) -> str:
        """
        Get a description of this collector.

        Returns:
            The collector description
        """
        return self._description

    def get_json_schema(self) -> dict:
        """
        Get the JSON schema for this collector's data.

        Returns:
            The JSON schema
        """
        return StorageActivityData.model_json_schema()

    @abstractmethod
    def collect_data(self) -> None:
        """Collect storage activity data."""

    def process_data(self, data: Any) -> dict[str, Any]:
        """
        Process the collected data.

        Args:
            data: Data to process

        Returns:
            Processed data
        """
        # Create a StorageActivityData object with metadata and activities
        activity_data = StorageActivityData(
            metadata=self._metadata,
            activities=self._activities,
            Timestamp=IndalekoTimestampDataModel(),
        )
        return activity_data.model_dump()

    def store_data(self, data: dict[str, Any]) -> None:
        """
        Store the processed data.

        Args:
            data: Processed data to store
        """
        # This is a collector, not a recorder.
        # Storage is handled by the recorder.

    def save_activities_to_file(self) -> str | None:
        """
        Save collected activities to a file.

        Returns:
            Path to the saved file, or None if no file was saved
        """
        if not self._activities:
            self._logger.warning("No activities to save")
            return None

        if not self._output_path:
            self._logger.warning(
                "No output path specified, activities not saved to file",
            )
            return None

        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self._output_path), exist_ok=True)

            # Write to file using JSONL format (one JSON object per line)
            with open(self._output_path, "w", encoding="utf-8") as f:
                # First write the metadata as a single line
                metadata = {
                    "record_type": "metadata",
                    "collector_metadata": (self._metadata.model_dump() if self._metadata else {}),
                    "timestamp": datetime.now(UTC).isoformat(),
                    "collector_name": self._name,
                    "total_activities": len(self._activities),
                }
                f.write(json.dumps(metadata, default=str) + "\n")

                # Then write each activity as a separate line
                for activity in self._activities:
                    activity_data = activity.model_dump()
                    activity_data["record_type"] = "activity"  # Add record type for easier parsing
                    f.write(json.dumps(activity_data, default=str) + "\n")

            self._logger.info(
                f"Saved {len(self._activities)} activities to {self._output_path}",
            )
            return self._output_path
        except Exception as e:
            self._logger.error(f"Error saving activities to file: {e}")
            return None


class WindowsStorageActivityCollector(StorageActivityCollector):
    """
    Base class for Windows-specific storage activity collectors.

    This class extends the StorageActivityCollector to provide Windows-specific
    functionality, such as volume GUID mapping and Windows API access.
    """

    def __init__(self, **kwargs):
        """
        Initialize the Windows storage activity collector.

        Args:
            machine_config: The machine configuration
            use_volume_guids: Whether to use volume GUIDs for stable paths
        """
        super().__init__(**kwargs)

        # Windows-specific configuration
        self._machine_config = kwargs.get("machine_config", None)
        self._use_volume_guids = kwargs.get("use_volume_guids", True)

        # Check for Windows machine config
        if self._machine_config is None:
            self._logger.warning("No machine configuration provided")

    def get_volume_guid_path(self, volume: str) -> str:
        """
        Get the volume GUID path for a volume.

        Args:
            volume: Volume to get GUID path for (e.g., "C:")

        Returns:
            The volume GUID path
        """
        if not volume:
            self._logger.error("No volume provided")
            return volume

        # If it's already a volume GUID path, return it
        if volume.startswith("\\\\?\\Volume{"):
            return volume

        # Extract drive letter
        if ":" in volume:
            drive_letter = volume[0].upper()
        else:
            drive_letter = volume.upper()

        # Use machine config to get GUID if available
        if self._machine_config and hasattr(
            self._machine_config,
            "map_drive_letter_to_volume_guid",
        ):
            try:
                guid = self.map_drive_letter_to_volume_guid(drive_letter)
                if guid:
                    guid_path = f"\\\\?\\Volume{{{guid}}}\\"
                    self._logger.info(
                        f"Mapped drive {drive_letter}: to volume GUID path: {guid_path}",
                    )
                    return guid_path
                else:
                    self._logger.warning(
                        f"Could not map drive {drive_letter}: to a volume GUID",
                    )
            except Exception as e:
                self._logger.error(f"Error mapping drive to GUID: {e}")

        # Fall back to standard path
        std_path = f"\\\\?\\{volume}\\"
        self._logger.info(f"Using standard path for volume {volume}: {std_path}")
        return std_path

    def map_drive_letter_to_volume_guid(self, drive_letter: str) -> str | None:
        """
        Map a drive letter to a volume GUID.

        Args:
            drive_letter: The drive letter to map

        Returns:
            The volume GUID if found, None otherwise
        """
        if not self._machine_config:
            self._logger.error("No machine configuration available")
            return None

        # Make sure the drive letter is just a single character
        if len(drive_letter) > 1:
            drive_letter = drive_letter[0]

        self._logger.debug(
            f"Attempting to map drive letter {drive_letter} to volume GUID",
        )

        # Use the machine config to map the drive letter
        try:
            if hasattr(self._machine_config, "map_drive_letter_to_volume_guid"):
                # Get the volume info from machine config
                if hasattr(self._machine_config, "get_volume_info") and self._debug:
                    volume_info = self._machine_config.get_volume_info()
                    self._logger.debug(
                        f"Volume info from machine config: {volume_info}",
                    )

                # Map drive letter to GUID
                guid = self._machine_config.map_drive_letter_to_volume_guid(
                    drive_letter,
                )

                if guid:
                    self._logger.debug(
                        f"Successfully mapped drive {drive_letter} to GUID {guid}",
                    )
                else:
                    self._logger.warning(
                        f"Drive letter {drive_letter} not found in machine configuration",
                    )

                return guid
            else:
                self._logger.error(
                    "Machine config does not have map_drive_letter_to_volume_guid method",
                )
        except Exception as e:
            self._logger.error(f"Error mapping drive letter to GUID: {e}")

        return None
