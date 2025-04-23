"""
Template base class for Indaleko activity recorders.

This module provides a template class with sensible defaults to simplify
the implementation of new activity recorders.

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

import datetime
import json
import logging
import os
import sys
import uuid
from abc import abstractmethod
from typing import Any

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from activity.characteristics import ActivityDataCharacteristics
from activity.recorders.base import RecorderBase
from activity.recorders.registration_service import (
    IndalekoActivityDataRegistrationService,
)
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from data_models.timestamp import IndalekoTimestamp

# pylint: disable=wrong-import-position
from Indaleko import Indaleko

# pylint: enable=wrong-import-position


class TemplateRecorder(RecorderBase):
    """
    Template base class for Indaleko activity recorders.

    This class provides implementations for common recorder functionality
    with sensible defaults. Subclasses only need to implement a few key methods
    to create a fully functional recorder.

    Required overrides:
    - collect_and_process_data()
    - get_collector_class_model()
    - get_json_schema()

    Useful methods to override if needed:
    - build_activity_document()
    - get_semantic_attributes()
    - get_source_identifier_tags()
    """

    # Default cache duration (1 hour)
    DEFAULT_CACHE_DURATION = datetime.timedelta(hours=1)

    # Default description template
    DEFAULT_DESCRIPTION_TEMPLATE = "{name} records {activity_type} data"

    def __init__(self, **kwargs):
        """
        Initialize the recorder with sensible defaults.

        Args:
            name: Name of the recorder
            recorder_id: UUID of the recorder
            version: Version string
            description: Description of the recorder
            collection_name: Name of the collection to store data in
            db_config_path: Path to database configuration file
            auto_connect: Whether to connect to the database automatically
            register_service: Whether to register with the service manager
            characteristics: List of activity data characteristics
            activity_type: Type of activity (used in description)
            provider_type: Type of data provider
            provider_subtype: Subtype of data provider
            tags: Tags for this recorder
            logger_name: Custom logger name
        """
        # Basic configuration with defaults
        self._name = kwargs.get("name", self.__class__.__name__)
        self._recorder_id = kwargs.get("recorder_id", uuid.uuid4())
        self._version = kwargs.get("version", "1.0.0")
        activity_type = kwargs.get("activity_type", "activity")
        self._description = kwargs.get(
            "description",
            self.DEFAULT_DESCRIPTION_TEMPLATE.format(
                name=self._name, activity_type=activity_type,
            ),
        )

        # Storage configuration
        self._collection_name = kwargs.get(
            "collection_name", f"{self.__class__.__name__}Data",
        )
        self._db_config_path = kwargs.get("db_config_path", None)

        # Service configuration
        self._provider_type = kwargs.get("provider_type", "Activity")
        self._provider_subtype = kwargs.get(
            "provider_subtype", activity_type.capitalize(),
        )
        self._tags = kwargs.get("tags", [activity_type.lower()])

        # Activity characteristics
        self._characteristics = kwargs.get(
            "characteristics",
            [
                ActivityDataCharacteristics.ACTIVITY_DATA_ACTIVITY,
            ],
        )

        # Setup logging
        logger_name = kwargs.get("logger_name", f"Indaleko.{self.__class__.__name__}")
        self._logger = logging.getLogger(logger_name)

        # Database connection
        self._db = None
        self._collection = None

        # Connect to database if auto_connect is True
        if kwargs.get("auto_connect", True):
            self._connect_to_db()

        # Register with activity service manager if specified
        self._register_enabled = kwargs.get("register_service", True)
        if self._register_enabled:
            self._register_with_service_manager()

    def _connect_to_db(self):
        """Connect to the Indaleko database."""
        try:
            # Create Indaleko instance and connect to database
            self._db = Indaleko()

            # If db_config_path is provided, use it
            if self._db_config_path:
                self._db.db_config_path = self._db_config_path

            # Connect to database
            self._db.connect()

            # Get or create collection
            # Try to get the collection from the central registry
            from db.i_collections import IndalekoCollections

            try:
                # Check if collection exists in registry
                collection_obj = IndalekoCollections.get_collection(
                    self._collection_name,
                )
                self._collection = collection_obj._arangodb_collection
                self._logger.info(f"Using existing collection {self._collection_name}")
            except ValueError:
                # If not in registry, use dynamic registration service
                self._logger.info(
                    f"Collection {self._collection_name} not found in registry",
                )

                # Get or create the registration service for activity data
                from activity.registration_service import ActivityRegistrationService

                registration_service = ActivityRegistrationService()

                # Register this collection with a generated UUID for consistency
                import hashlib

                # Generate deterministic UUID from collection name
                name_hash = hashlib.md5(self._collection_name.encode()).hexdigest()
                provider_id = str(uuid.UUID(name_hash))

                # Create provider collection
                provider_collection = registration_service.lookup_provider_collection(
                    provider_id,
                )
                if provider_collection is None:
                    self._logger.info(
                        f"Creating collection for {self._collection_name} via registration service",
                    )
                    provider_collection = (
                        registration_service.create_provider_collection(
                            identifier=provider_id,
                            schema=None,  # No schema validation for now
                            edge=False,
                        )
                    )

                self._collection = provider_collection.collection

            self._logger.info(
                f"Connected to database, collection: {self._collection_name}",
            )
        except Exception as e:
            self._logger.error(f"Error connecting to database: {e}")
            raise

    def _register_with_service_manager(self) -> None:
        """Register the recorder with the activity service manager."""
        try:
            # Create source identifier
            source_identifier = self._get_source_identifier()

            # Create record for registration
            record = IndalekoRecordDataModel(
                SourceIdentifier=source_identifier,
                Timestamp=datetime.datetime.now(datetime.UTC),
                Attributes={},
                Data="",
            )

            # Get source identifiers and schema identifiers
            source_ids, schema_ids = self._get_source_identifier_tags()

            # Prepare registration data
            registration_kwargs = {
                "Identifier": str(self._recorder_id),
                "Name": self._name,
                "Description": self._description,
                "Version": self._version,
                "Record": record,
                "DataProvider": self._name,
                "DataProviderType": self._provider_type,
                "DataProviderSubType": self._provider_subtype,
                "DataProviderURL": "",
                "DataProviderCollectionName": self._collection_name,
                "DataFormat": "JSON",
                "DataFormatVersion": "1.0",
                "DataAccess": "Read",
                "DataAccessURL": "",
                "CreateCollection": True,
                "SourceIdentifiers": source_ids,
                "SchemaIdentifiers": schema_ids,
                "Tags": self._tags,
            }

            # Register with service manager
            try:
                service = IndalekoActivityDataRegistrationService()
                service.register_provider(**registration_kwargs)

                self._logger.info(
                    f"Registered recorder with service manager: {self._recorder_id}",
                )
            except Exception as e:
                self._logger.error(f"Error registering with service manager: {e}")

        except Exception as e:
            self._logger.error(f"Error creating registration data: {e}")

    def _get_source_identifier(self) -> IndalekoSourceIdentifierDataModel:
        """Get the source identifier for this recorder."""
        return IndalekoSourceIdentifierDataModel(
            Identifier=self._recorder_id,
            Version=self._version,
            Description=self._description,
        )

    def _get_source_identifier_tags(self) -> tuple[list[str], list[str]]:
        """
        Get source identifier UUIDs and schema identifier UUIDs.

        Returns:
            Tuple of (source_ids, schema_ids)
        """
        # Default implementation returns empty lists
        # Subclasses should override this to provide specific UUIDs
        source_ids = []
        schema_ids = []

        return source_ids, schema_ids

    def build_activity_document(
        self,
        activity_data: Any,
        semantic_attributes: list[IndalekoSemanticAttributeDataModel] | None = None,
    ) -> dict:
        """
        Build a document for storing an activity in the database.

        Args:
            activity_data: The activity data to store
            semantic_attributes: Optional list of semantic attributes

        Returns:
            Document for the database
        """
        # Ensure we have semantic attributes
        if semantic_attributes is None:
            semantic_attributes = self.get_semantic_attributes(activity_data)

        # Create source identifier
        source_id = self._get_source_identifier()

        # Create a timestamp
        timestamp = IndalekoTimestamp()

        # Convert activity data to dictionary if needed
        if hasattr(activity_data, "model_dump"):
            activity_data_dict = activity_data.model_dump()
        elif isinstance(activity_data, dict):
            activity_data_dict = activity_data
        else:
            # Try to convert to JSON and back to dict
            activity_data_dict = json.loads(json.dumps(activity_data, default=str))

        # Create the record with Indaleko's expected structure
        record = IndalekoRecordDataModel(
            RecordType=self._provider_subtype,
            Data=activity_data_dict,
            SourceIdentifier=source_id,
            Timestamp=timestamp,
            SemanticAttributes=semantic_attributes,
        )

        return record.model_dump()

    def get_semantic_attributes(
        self, activity_data: Any,
    ) -> list[IndalekoSemanticAttributeDataModel]:
        """
        Get semantic attributes for the given activity data.

        Args:
            activity_data: Activity data to extract attributes from

        Returns:
            List of semantic attributes
        """
        # Default implementation returns empty list
        # Subclasses should override this to provide specific attributes
        return []

    @abstractmethod
    def collect_and_process_data(self) -> list[Any]:
        """
        Collect and process data from the source.

        This method should handle collecting data from the source and
        processing it into a format ready for storage.

        Returns:
            List of processed data items
        """

    def update_data(self) -> None:
        """
        Update the data in the database.

        This method collects new data and stores it in the database.
        """
        try:
            # Collect and process data
            data_items = self.collect_and_process_data()

            # Store each data item
            stored_count = 0
            for item in data_items:
                self.store_data(item)
                stored_count += 1

            self._logger.info(f"Updated {stored_count} items in the database")
        except Exception as e:
            self._logger.error(f"Error updating data: {e}")

    def store_data(self, data: Any) -> None:
        """
        Store the processed data in the database.

        Args:
            data: Data to store
        """
        try:
            # Build the document
            document = self.build_activity_document(data)

            # Store in database
            self._collection.add_document(document)

            self._logger.debug(f"Stored data item: {document.get('_key', 'unknown')}")
        except Exception as e:
            self._logger.error(f"Error storing data: {e}")

    def process_data(self, data: Any) -> dict[str, Any]:
        """
        Process the collected data.

        Args:
            data: Raw data to process

        Returns:
            Processed data
        """
        # Default implementation just converts to dict
        if hasattr(data, "model_dump"):
            return data.model_dump()
        elif isinstance(data, dict):
            return data
        else:
            # Try to convert to JSON and back to dict
            return json.loads(json.dumps(data, default=str))

    def get_recorder_characteristics(self) -> list[ActivityDataCharacteristics]:
        """Get the characteristics of this recorder."""
        return self._characteristics

    def get_recorder_name(self) -> str:
        """Get the name of the recorder."""
        return self._name

    def get_recorder_id(self) -> uuid.UUID:
        """Get the ID of the recorder."""
        return self._recorder_id

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

    def cache_duration(self) -> datetime.timedelta:
        """
        Get the cache duration for this recorder's data.

        Returns:
            The cache duration
        """
        return self.DEFAULT_CACHE_DURATION

    def get_description(self) -> str:
        """
        Get a description of this recorder.

        Returns:
            The recorder description
        """
        return self._description

    def get_latest_db_update(self) -> dict[str, Any]:
        """
        Get the latest data update from the database.

        Returns:
            The latest update information
        """
        if not self._collection:
            return {}

        try:
            # Query for the most recent activity
            query = """
                FOR doc IN @@collection
                SORT doc.Record.Timestamp DESC
                LIMIT 1
                RETURN doc
            """

            # Execute query
            cursor = self._db.db.aql.execute(
                query, bind_vars={"@collection": self._collection_name},
            )

            # Return the first result, or empty dict if no results
            try:
                return next(cursor)
            except StopIteration:
                return {}
        except Exception as e:
            self._logger.error(f"Error getting latest database update: {e}")
            return {}


def main():
    """Test the template recorder."""
    logging.basicConfig(level=logging.INFO)

    # Cannot instantiate this class directly since it has abstract methods
    print("TemplateRecorder provides a base implementation with sensible defaults.")
    print("Extend this class to create your own recorders with minimal code.")


if __name__ == "__main__":
    main()
