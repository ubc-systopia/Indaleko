"""This module contains the NTFS storage activity data recorder."""

import os
import sys

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.storage.ntfs.ntfs_collector_v2 import NtfsStorageActivityCollectorV2
from activity.recorders.base import RecorderBase
from activity.recorders.registration_service import (
    IndalekoActivityDataRegistrationService,
)
from activity.recorders.storage.data_models.storage_activity import (
    IndalekoStorageActivityDataModel,
)
from data_models.record import IndalekoRecordDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from db.db_config import IndalekoDBConfig


# pylint: enable=wrong-import-position

KnownStorageActivityAttributes = {
    "LocalIdentifier": "The identifier of the object in the NTFS storage system.",
    "ParentIdentifier": "The identifier of the parent object in the NTFS storage system.",
    "FileName": "The name of the file in the NTFS storage system.",
}

class NTFSStorageActivityRecorder(RecorderBase):
    """Recorder for NTFS storage activity."""

    semantic_attributes_supported = {  # noqa: RUF012

    }

    identifier = UUID("d9218f19-335a-4fdb-9456-425b92fee063")
    version = "1.0.0"
    description = "NTFS storage activity recorder."

    def __init__(self, *args: dict[str, object], **kwargs: dict) -> None:
        """Initialize the NTFS storage activity recorder."""
        super().__init__(*args, **kwargs)
        ic("Past the super() call")
        self._collector = kwargs.get("collector")
        if not hasattr(self, "_collection"):
            self._collection = kwargs.get("collection")
        if self._collector is not None and not isinstance(self._collector, RecorderBase):
            raise TypeError(f"provider is not a StorageActivityCollector {type(self._collector)}")
        self._db_config = IndalekoDBConfig()
        ic("Past the db config call")
        if self._db_config is None:
            raise RuntimeError("Database configuration is not set.")
        source_identifier = IndalekoSourceIdentifierDataModel(
            Identifier=self.identifier,
            Version=self.version,
            Description=self.description,
        )
        record_kwargs = {
            "Identifier": str(self.identifier),
            "Version": self.version,
            "Description": self.description,
            "Record": IndalekoRecordDataModel(
                SourceIdentifier=source_identifier,
                Timestamp=datetime.now(UTC),
            ),
        }
        ic("record_kwargs:", record_kwargs)
        self._provider_registrar = IndalekoActivityDataRegistrationService()
        ic("Past the provider registrar call")
        if self._provider_registrar is None:
            raise RuntimeError("Failed to get the provider registrar")
        collector_data = self._provider_registrar.lookup_provider_by_identifier(
            str(self.identifier),
        )
        ic("lookup_provider_by_identifier:", collector_data)
        if collector_data is None:
            ic("No collector data found, registering new provider")
            self._collector_data, self._collection = (
                self._provider_registrar.register_provider(
                    **record_kwargs,
                )
            )
            ic("Registered new provider:", self._collector_data, self._collection)
        else:
            self._collection = (
                IndalekoActivityDataRegistrationService.lookup_activity_provider_collection(
                    str(self.identifier),
                )
            )
            ic("Looked up collection: ", self._collection.collection_name)
        # H A C K - this should be done in the registration service
        if self._db_config.db.collection(self._collection.collection_name) is None: # type: ignore  # noqa: PGH003
            ic("Collection does not exist, creating it")
            self._db_config.db.create_collection( # type: ignore  # noqa: PGH003
                self._collection.collection_name,
                schema=IndalekoStorageActivityDataModel.get_arangodb_schema(),
            )
        else:
            ic(f"Collection {self._collection.collection_name} exists, using it")
        self._collector_data = collector_data
        self.collector_model = NtfsStorageActivityCollectorV2
        self.provider = self._collector

    def get_recorder_characteristics(self) -> list[ActivityDataCharacteristics]:
        """Return the characteristics of the NTFS storage activity recorder."""
        return self._collector.get_characteristics() # type: ignore  # noqa: PGH003

    def get_recorder_name(self) -> str:
        """Return the name of the recorder."""
        return "NTFSStorageActivityRecorder"

    def get_collector_class_model(self) -> dict[str, type]:
        """Return the collector class model."""
        return {"collector": NtfsStorageActivityCollectorV2}

    def get_recorder_id(self) -> UUID:
        """Return the unique identifier for the recorder."""
        return self.identifier

    def get_cursor(self, activity_context: UUID) -> UUID:
        """Return a cursor for the given activity context."""
        # For NTFS, the cursor could be the last processed record's UUID
        # Here, just return the activity_context as a placeholder
        return activity_context

    def cache_duration(self) -> timedelta:
        """Return the cache duration for the recorder."""
        # Cache for 10 minutes by default
        return timedelta(minutes=10)

    def get_description(self) -> str:
        """Return the description of the recorder."""
        return self.description

    def get_json_schema(self) -> dict:
        """Return a JSON schema describing the NTFS activity data."""
        return {
            "type": "object",
            "properties": {
            "LocalIdentifier": {"type": "string"},
            "ParentIdentifier": {"type": "string"},
            "FileName": {"type": "string"},
            "Timestamp": {"type": "string", "format": "date-time"},
            },
            "required": ["LocalIdentifier", "FileName", "Timestamp"],
        }

    def process_data(self, data: object) -> dict[str, object]:
        """Process raw data and return a dictionary suitable for storage."""
        # Assume data is a dict-like object from the collector
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        processed = {
            "LocalIdentifier": data.get("LocalIdentifier"),
            "ParentIdentifier": data.get("ParentIdentifier"),
            "FileName": data.get("FileName"),
            "Timestamp": data.get("Timestamp", datetime.now(UTC).isoformat()),
        }
        return processed

    def store_data(self, data: dict[str, object]) -> None:
        """Store the processed data in the database."""
        # This is a placeholder for actual DB storage logic
        # For demonstration, just print or log the data
        print(f"Storing data: {data}")

    def update_data(self) -> None:
        """Update the recorder's data from the collector."""
        if self._collector is None:
            raise RuntimeError("No collector available for update")
        collected_data = self._collector.collect()
        processed = self.process_data(collected_data)
        self.store_data(processed)

    def get_latest_db_update(self) -> dict[str, object]:
        """Retrieve the latest update from the database."""
        # Placeholder: In a real implementation, query the DB
        # Here, return a dummy record
        return {
            "LocalIdentifier": "dummy_id",
            "ParentIdentifier": "dummy_parent",
            "FileName": "dummy.txt",
            "Timestamp": datetime.now(UTC).isoformat(),
        }


def main() -> None:
    """Main entry point for the NTFS storage activity recorder."""
    recorder = NTFSStorageActivityRecorder()
    ic(recorder.get_description())

if __name__ == "__main__":
    main()
