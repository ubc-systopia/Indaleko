"""
This module defines a recorder for IP-based location data.

It registers the IPLocation collector as an activity data provider,
builds and inserts location activity documents into its ArangoDB collection.
"""
import uuid
from datetime import datetime
from typing import Any, Dict, List, Union

from activity.recorders.location.location_data_recorder import BaseLocationDataRecorder
from activity.recorders.registration_service import IndalekoActivityDataRegistrationService
from activity.collectors.location.ip_location import IPLocation
from activity.collectors.location.data_models.ip_location_data_model import IPLocationDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from data_models.i_uuid import IndalekoUUIDDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from activity.semantic_attributes import KnownSemanticAttributes
from utils.misc.data_management import decode_binary_data


class IPLocationRecorder(BaseLocationDataRecorder):
    """Recorder for IP-based location data."""

    identifier = uuid.UUID("82ae879d-7280-4b5a-a98a-5ebc1bf61bbc")
    version = "1.0.0"
    description = "IP Location Recorder"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Instantiate the IP location collector
        self.provider = IPLocation()
        # Prepare source identifier for registration
        source_id = IndalekoSourceIdentifierDataModel(
            Identifier=self.identifier,
            Version=self.version,
            Description=self.description,
        )
        # Registration payload: empty record to create collection
        record_kwargs = {
            "Identifier": str(self.identifier),
            "Version": self.version,
            "Description": self.description,
            "Record": IndalekoRecordDataModel(
                SourceIdentifier=source_id,
                Timestamp=datetime.now(),
                Attributes={},
                Data="",
            ),
        }
        # Register or lookup provider
        registrar = IndalekoActivityDataRegistrationService()
        existing = registrar.lookup_provider_by_identifier(str(self.identifier))
        if existing is None:
            self.collector_data, self.collection = registrar.register_provider(**record_kwargs)
        else:
            self.collector_data = existing
            self.collection = IndalekoActivityDataRegistrationService.lookup_activity_provider_collection(
                str(self.identifier)
            )

    def get_recorder_characteristics(self) -> List[Any]:
        return self.provider.get_collector_characteristics()

    def get_recorder_name(self) -> str:
        return "ip_location"

    def get_collector_class_model(self) -> Dict[str, type]:
        return {"IPLocation": IPLocationDataModel}

    def get_recorder_id(self) -> uuid.UUID:
        return self.identifier

    def process_data(self, data: Any) -> Dict[str, Any]:
        # The collector returns a dict of the serialized data
        return data if isinstance(data, dict) else data.serialize()

    def store_data(self, data: Dict[str, Any]) -> None:
        # Data persistence handled in update_data via ArangoDB insert
        pass

    def update_data(self) -> Union[IPLocationDataModel, None]:
        """Collect new data, compare to last DB entry, and insert if changed."""
        # Trigger collector to gather latest IP location
        self.provider.collect_data()
        # Retrieve last in-memory record
        raw = self.provider.retrieve_data(self.identifier)
        if not raw:
            return None
        # Build data model instance
        model = IPLocationDataModel(**raw)
        # Compare to last stored data
        last = self.get_latest_db_update()
        if not self.has_data_changed(model, last):
            return last
        # Prepare semantic attributes
        ksa = KnownSemanticAttributes
        sem_attrs = [
            IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=ksa.ACTIVITY_DATA_LOCATION_LATITUDE,
                    Version="1",
                    Description="Latitude",
                ),
                Value=model.Location.latitude,
            ),
            IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=ksa.ACTIVITY_DATA_LOCATION_LONGITUDE,
                    Version="1",
                    Description="Longitude",
                ),
                Value=model.Location.longitude,
            ),
            IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=ksa.ACTIVITY_DATA_LOCATION_ACCURACY,
                    Version="1",
                    Description="Accuracy",
                ),
                Value=model.Location.accuracy,
            ),
        ]
        # Build and insert activity document
        source_id = IndalekoSourceIdentifierDataModel(
            Identifier=self.identifier,
            Version=self.version,
            Description=self.description,
        )
        doc = BaseLocationDataRecorder.build_location_activity_document(
            source_data=source_id,
            location_data=model,
            semantic_attributes=sem_attrs,
        )
        self.collection.insert(doc)
        return model

    def get_latest_db_update(self) -> Union[IPLocationDataModel, None]:
        """Fetch and deserialize the latest stored activity document."""
        entry = BaseLocationDataRecorder.get_latest_db_update_dict(self.collection)
        if entry is None:
            return None
        data = decode_binary_data(entry["Record"]["Data"])
        # Clean out None values
        cleaned = {k: v for k, v in data.items() if v is not None}
        return IPLocationDataModel.deserialize(cleaned)