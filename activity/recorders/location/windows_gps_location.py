"""
This module acquires Windows GPS data and records it.

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

import os
import sys
import uuid

from datetime import UTC, datetime
from pathlib import Path

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.known_semantic_attributes import KnownSemanticAttributes
from activity.collectors.location.data_models.windows_gps_location_data_model import (
    WindowsGPSLocationDataModel,
)
from activity.collectors.location.windows_gps_location import WindowsGPSLocation
from activity.recorders.location.location_data_recorder import BaseLocationDataRecorder

# > from activity.registration import IndalekoActivityDataRegistration
from activity.recorders.registration_service import (
    IndalekoActivityDataRegistrationService,
)
from data_models.i_uuid import IndalekoUUIDDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from db.db_config import IndalekoDBConfig
from utils.misc.data_management import decode_binary_data


# pylint: enable=wrong-import-position


class WindowsGPSLocationRecorder(BaseLocationDataRecorder):
    """Windows GPS Location Recorder."""

    identifier = uuid.UUID("7e85669b-ecc7-4d57-8b51-8d325ea84930")
    version = "1.0.0"
    description = "Windows GPS Location Recorder"

    def __init__(self, **kwargs: dict) -> None:
        """Initialize the Windows GPS Location Recorder."""
        super().__init__(**kwargs)
        self.min_movement_change_required = kwargs.get(
            "min_movement_change_required",
            self.default_min_movement_change_required,
        )
        self.max_time_between_updates = kwargs.get(
            "max_time_between_updates",
            self.default_max_time_between_updates,
        )
        self.db_config = IndalekoDBConfig()
        if self.db_config is None:
            raise RuntimeError("Failed to get the database configuration")
        source_identifier = IndalekoSourceIdentifierDataModel(
            Identifier=self.identifier,
            Version=self.version,
            Description=self.description,
        )
        ic(source_identifier.serialize())
        record_kwargs = {
            "Identifier": str(self.identifier),
            "Version": self.version,
            "Description": self.description,
            "Record": IndalekoRecordDataModel(
                SourceIdentifier=source_identifier,
                Timestamp=datetime.now(UTC),
                Data="",
            ),
        }
        self.provider_registrar = IndalekoActivityDataRegistrationService()
        if self.provider_registrar is None:
            raise RuntimeError("Failed to get the provider registrar")
        collector_data = self.provider_registrar.lookup_provider_by_identifier(
            str(self.identifier),
        )
        if collector_data is None:
            ic("Registering the provider")
            collector_data, collection = self.provider_registrar.register_provider(
                **record_kwargs,
            )
        else:
            ic("Provider already registered")
            collection = IndalekoActivityDataRegistrationService.lookup_activity_provider_collection(
                str(self.identifier),
            )
        ic(collection)
        self.collector_data = collector_data
        self.collector = WindowsGPSLocation()
        self.provider = self.collector
        self.collection = collection

    def get_latest_db_update(self) -> WindowsGPSLocationDataModel | None:
        """Get the latest update from the database."""
        doc = BaseLocationDataRecorder.get_latest_db_update_dict(self.collection)
        if doc is None:
            ic("No data found in the database")
            return None
        if "Record" not in doc:
            ic("No Record found in the document")
            return None
        if "Data" not in doc["Record"]:
            ic("No Data found in the Record")
            return None
        data = decode_binary_data(doc["Record"]["Data"])
        cleaned_data = {key: value for key, value in data.items() if value is not None}
        location_data = WindowsGPSLocationDataModel.deserialize(cleaned_data)
        ic(location_data)
        return location_data

    def update_data(self) -> WindowsGPSLocationDataModel | None:
        """Update the data in the database."""
        ksa = KnownSemanticAttributes
        current_data: WindowsGPSLocationDataModel = WindowsGPSLocation().get_coords()
        ic(current_data)
        if not isinstance(current_data, WindowsGPSLocationDataModel):
            raise TypeError(
                f"current_data is not a WindowsGPSLocationDataModel {type(current_data)}",
            )
        latest_db_data = self.get_latest_db_update()
        if not self.has_data_changed(current_data, latest_db_data):
            ic("Data has not changed, return last DB record")
            return latest_db_data
        # the data has changed enough for us to record it.
        ic("Data has changed, record in the database")
        source_identifier = IndalekoSourceIdentifierDataModel(
            Identifier=self.identifier,
            Version=self.version,
            Description=self.description,
        )
        semantic_attributes = [
            IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=ksa.ACTIVITY_DATA_LOCATION_LATITUDE,
                    Label="Latitude",
                ),
                Value=current_data.Location.latitude,  # pylint: disable=no-member
            ),
            IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=ksa.ACTIVITY_DATA_LOCATION_LONGITUDE,
                    Label="Longitude",
                ),
                Value=current_data.Location.longitude,  # pylint: disable=no-member
            ),
            IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=ksa.ACTIVITY_DATA_LOCATION_ACCURACY,  # pylint: disable=no-member
                    Label="1",
                ),
                Value=current_data.Location.accuracy,  # pylint: disable=no-member
            ),
        ]
        doc = BaseLocationDataRecorder.build_location_activity_document(
            source_data=source_identifier,
            location_data=current_data,
            semantic_attributes=semantic_attributes,
        )
        self.collection.insert(doc)
        return current_data

    def get_recorder_characteristics(self) -> list[ActivityDataCharacteristics]:
        """Retrieve the characteristics of the recorder.

        Returns:
        -------
        dict
            A dictionary containing the characteristics of the recorder.
        """
        return self.collector.get_collector_characteristics()

    def get_recorder_name(self) -> str:
        """Get the name of the recorder."""
        return "windows_gps_location"

    def get_collector_class_model(self) -> dict[str, type]:
        """Get the class models for the collector(s) used by this recorder."""
        return {"WindowsGPSLocation": WindowsGPSLocationDataModel}

    def get_recorder_id(self) -> uuid.UUID:
        """Get the UUID for the recorder."""
        return self.identifier

    def process_data(self, data: WindowsGPSLocationDataModel) -> WindowsGPSLocationDataModel:
        """Process the collected data."""
        return data

    def get_description(self) -> str:
        """Get the description of the recorder."""
        return self.provider.get_description()

    def store_data(
        self,
        data: WindowsGPSLocationDataModel | list[WindowsGPSLocationDataModel],
    ) -> None:
        """Store the processed data."""
        ksa = KnownSemanticAttributes
        if not isinstance(data, WindowsGPSLocationDataModel):
            raise TypeError(f"current_data is not a WindowsGPSLocationDataModel {type(data)}")
        ic(type(data))
        latest_db_data = self.get_latest_db_update()
        if not self.has_data_changed(data, latest_db_data):
            ic("Data has not changed, return last DB record")
            return latest_db_data
        # the data has changed enough for us to record it.
        ic("Data has changed, record in the database")
        source_identifier = IndalekoSourceIdentifierDataModel(
            Identifier=self.identifier,
            Version=self.version,
            Description=self.description,
        )
        semantic_attributes = [
            IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=ksa.ACTIVITY_DATA_LOCATION_LATITUDE,  # pylint: disable=no-member
                    Label="Latitude",
                ),
                Value=data.latitude,
            ),
            IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=ksa.ACTIVITY_DATA_LOCATION_LONGITUDE,  # pylint: disable=no-member
                    Label="Longitude",
                ),
                Value=data.longitude,
            ),
            IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=ksa.ACTIVITY_DATA_LOCATION_ACCURACY,  # pylint: disable=no-member
                    Label="Accuracy",
                ),
                Value=data.accuracy,
            ),
        ]
        ic(type(data))
        doc = BaseLocationDataRecorder.build_location_activity_document(
            source_data=source_identifier,
            location_data=data,
            semantic_attributes=semantic_attributes,
        )
        self.collection.insert(doc)
        return None


def main() -> None:
    """Main entry point for the Windows GPS Location Recorder."""
    ic("Starting Windows GPS Location Recorder")
    recorder = WindowsGPSLocationRecorder()
    recorder.update_data()
    latest = recorder.get_latest_db_update()
    ic(latest)
    if latest is None:
        ic("No data found in the database")
        return
    ic(recorder.get_description())
    ic("Finished Windows GPS Location Recorder")
    ic(recorder.get_recorder_characteristics())


if __name__ == "__main__":
    main()
