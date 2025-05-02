"""Store Metadata."""

import os
import sys
import uuid

from datetime import UTC, datetime
from pathlib import Path


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# ruff: noqa: S311,FBT001,FBT002

# pylint: disable=wrong-import-position

from activity.recorders.registration_service import IndalekoActivityDataRegistrationService
from data_models.record import IndalekoRecordDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from db.collection import IndalekoCollection
from db.i_collections import IndalekoCollections


# pylint: enable=wrong-import-position


class MetadataStorer:
    """MetadataStorer for moving the metadata dataset onto the Indaleko DB."""

    def __init__(self) -> None:
        """Initialize the metadata storer service."""
        self.activity_data_registrar = IndalekoActivityDataRegistrationService()


    def delete_records_from_collection(
            self,
            collections: IndalekoCollections,
            collection_name: str,
    ) -> None:
        """
        Deletes the records from the specified collection in IndalekoCollections.

        Args:
            collections (IndalekoCollections): the Indaldeko Collection to delete records from
            collection_name (str): the name of the collection.
        """
        collections.get_collection(collection_name).delete_collection(collection_name)

    def add_records_to_collection(
            self,
            collections: IndalekoCollections,
            collection_name: str,
            records: list,
            key_required: bool = False) -> None:
        """
        Adds each metadata into the specified collection.

        Args:
            collections (IndalekoCollections): the Indaldeko Collection to delete records from
            collection_name (str): the name of the collection
            records (list) : list of Records to store into the collection.
            key_required (bool): whether to add a key to the record or not.
        """
        for record in records:
            # Convert record to dictionary if it's not already
            if not isinstance(record, dict):
                if hasattr(record, 'dict'):
                    record = record.dict()
                elif hasattr(record, 'model_dump'):
                    record = record.model_dump()
                else:
                    # Try to convert to dict using Metadata helper
                    from data_generator.scripts.metadata.metadata import Metadata
                    record = Metadata.return_JSON(record)
                    
            # Ensure record is a dictionary before adding _key
            if isinstance(record, dict) and key_required:
                record["_key"] = str(uuid.uuid4())
            collections.get_collection(collection_name).insert(record)

    def register_activity_provider(
            self,
            collector_type: str,
            version:str = "1.0.0",
    ) -> IndalekoCollection:
        """
        Initializes a activity provider registerer for the specifitied collector.

        Args:
            collector_type (str): The type of collector to register.
            version (str): The version of the collector.
        """
        identifier = uuid.uuid4()
        source_identifier = IndalekoSourceIdentifierDataModel(
            Identifier=identifier,
            Version=version,
            Description=collector_type,
        )

        record_kwargs = {
            "Identifier" : str(identifier),
            "Version" : version,
            "Description" : collector_type,
            "Record" : IndalekoRecordDataModel(
                SourceIdentifier=source_identifier,
                Timestamp=datetime.now(UTC),
                Attributes={},
                Data="",
            ),
        }
        activity_registration_service, collection = self.activity_data_registrar.\
            register_provider(**record_kwargs)

        return activity_registration_service, collection

    def add_records_with_activity_provider(
            self,
            collection: IndalekoCollection,
            activity_contexts: dict,
    ) -> None:
        """
        Initializes a activity provider registerer for the specifitied collector.

        Args:
            collection (IndalekoCollection): The collection to add the records to.
            activity_contexts (dict): The activity contexts to add to the collection.
        """
        for activity in activity_contexts:
            collection.insert(activity)
