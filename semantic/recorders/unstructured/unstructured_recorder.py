#!/usr/bin/env python3
"""
Indaleko Project - Unstructured Semantic Recorder

This module implements a recorder for semantic metadata extracted with unstructured.io.
It stores the extracted data in ArangoDB following the Indaleko recorder pattern
and supports performance monitoring.

Note: Semantic extractors should only run on machines where data is physically
stored. Storage recorders should add device-file relationships (UUID:
f3dde8a2-cff5-41b9-bd00-0f41330895e1) between files and the machines
where they're stored.

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
import sys
import time
import uuid
from datetime import UTC, datetime
from typing import Any

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from data_models.base import IndalekoBaseModel
from data_models.i_uuid import IndalekoUUIDDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from db.db_config import IndalekoDBConfig
from Indaleko import Indaleko
from semantic.characteristics import SemanticDataCharacteristics
from semantic.collectors.semantic_attributes import *  # Import all semantic attribute UUIDs
from semantic.collectors.unstructured.data_models.embedded import (
    UnstructuredEmbeddedDataModel,
)
from semantic.collectors.unstructured.unstructured_collector import (
    UnstructuredCollector,
)
from semantic.performance_monitor import (
    SemanticExtractorPerformance,
    monitor_semantic_extraction,
)
from semantic.recorders.base import SemanticRecorderBase
from utils.misc.data_management import encode_binary_data


class UnstructuredRecorder(SemanticRecorderBase):
    """
    Recorder for semantic metadata extraction using unstructured.io.

    This recorder stores semantic metadata extracted with unstructured.io in ArangoDB.
    It follows the Indaleko recorder pattern and integrates with the performance
    monitoring framework.
    """

    # Constants for the recorder
    RECORDER_ID = uuid.UUID("6dbcf86e-c1a5-4aed-94c1-7f87d8cc2d1d")
    RECORDER_NAME = "Unstructured.io Semantic Recorder"
    DESCRIPTION = "Stores semantic content extracted by unstructured.io"
    COLLECTION_NAME = "SemanticContent"

    # Class-level mapping of attribute labels to UUIDs
    attribute_map = {
        # File attributes
        "filetype": SEM_FILETYPE,
        "filename": SEM_FILENAME,
        "last_modified": SEM_LAST_MODIFIED,
        "page_number": SEM_PAGE_NUMBER,
        "language": SEM_LANGUAGE,
        # Element types
        "Title": SEM_TITLE,
        "Text": SEM_TEXT,
        "UncategorizedText": SEM_UNCATEGORIZEDTEXT,
        "NarrativeText": SEM_NARRATIVETEXT,
        "BulletedText": SEM_BULLETEDTEXT,
        "Paragraph": SEM_PARAGRAPH,
        "Abstract": SEM_ABSTRACT,
        "Threading": SEM_THREADING,
        "Form": SEM_FORM,
        "FieldName": SEM_FIELDNAME,
        "Value": SEM_VALUE,
        "Link": SEM_LINK,
        "CompositeElement": SEM_COMPOSITEELEMENT,
        "Image": SEM_IMAGE,
        "Picture": SEM_PICTURE,
        "FigureCaption": SEM_FIGURECAPTION,
        "Figure": SEM_FIGURE,
        "Caption": SEM_CAPTION,
        "List": SEM_LIST,
        "ListItem": SEM_LISTITEM,
        "ListItemOther": SEM_LISTITEMOTHER,
        "Checked": SEM_CHECKED,
        "Unchecked": SEM_UNCHECKED,
        "CheckboxChecked": SEM_CHECKBOXCHECKED,
        "CheckboxUnchecked": SEM_CHECKBOXUNCHECKED,
        "RadioButtonChecked": SEM_RADIOBUTTONCHECKED,
        "RadioButtonUnchecked": SEM_RADIOBUTTONUNCHECKED,
        "Address": SEM_ADDRESS,
        "EmailAddress": SEM_EMAILADDRESS,
        "PageBreak": SEM_PAGEBREAK,
        "Formula": SEM_FORMULA,
        "Table": SEM_TABLE,
        "Header": SEM_HEADER,
        "Headline": SEM_HEADLINE,
        "SubHeadline": SEM_SUBHEADLINE,
        "PageHeader": SEM_PAGEHEADER,
        "SectionHeader": SEM_SECTIONHEADER,
        "Footer": SEM_FOOTER,
        "Footnote": SEM_FOOTNOTE,
        "PageFooter": SEM_PAGEFOOTER,
        "PageNumber": SEM_PAGENUMBER,
        "CodeSnippet": SEM_CODESNIPPET,
        "FormKeysValues": SEM_FORMKEYSVALUES,
    }

    def __init__(self, **kwargs):
        """
        Initialize the UnstructuredRecorder.

        Args:
            collector (UnstructuredCollector, optional): Collector instance to use
            collection_name (str, optional): Name of the collection to store data in
            recorder_id (uuid.UUID, optional): Override the default recorder ID
            recorder_name (str, optional): Override the default recorder name
            db_config (IndalekoDBConfig, optional): Database configuration
            skip_db_connection (bool, optional): Skip connecting to the database
            enable_performance_monitoring (bool, optional): Enable performance monitoring
        """
        # Basic recorder information
        self._name = kwargs.get("recorder_name", self.RECORDER_NAME)
        self._recorder_id = kwargs.get("recorder_id", self.RECORDER_ID)
        self._description = self.DESCRIPTION

        # Collection configuration
        self._collection_name = kwargs.get("collection_name", self.COLLECTION_NAME)

        # Performance monitoring
        self._perf_monitor = SemanticExtractorPerformance()
        self._enable_monitoring = kwargs.get("enable_performance_monitoring", True)
        if self._enable_monitoring:
            self._perf_monitor.enable()

        # Database connection
        self._skip_db_connection = kwargs.get("skip_db_connection", False)
        self._db_config = kwargs.get("db_config")
        self._db = None
        self._collection = None

        if not self._skip_db_connection:
            self._initialize_db()

        # Collector instance
        self._collector = kwargs.get("collector")

        # Set up logging
        self._logger = logging.getLogger(f"{self.__class__.__name__}")
        self._logger.setLevel(logging.INFO)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)

            # Add file handler
            log_dir = os.path.join(Indaleko.default_data_dir, "logs")
            os.makedirs(log_dir, exist_ok=True)
            file_handler = logging.FileHandler(
                os.path.join(
                    log_dir,
                    f"unstructured_recorder_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                ),
            )
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

        # Latest update tracking
        self._latest_update = None

    def _initialize_db(self):
        """Initialize database connection and create collection if needed."""
        try:
            if self._db_config is None:
                self._db_config = IndalekoDBConfig()

            # Connect to the database
            self._db = Indaleko()
            self._db.connect(db_config=self._db_config)

            # Get or create collection using IndalekoCollections centralized mechanism
            try:
                from db.i_collections import IndalekoCollections

                self._logger.info(f"Getting collection {self._collection_name}")
                self._collection = IndalekoCollections.get_collection(
                    self._collection_name,
                )
                self._logger.info(f"Retrieved collection {self._collection_name}")
            except Exception as collection_error:
                self._logger.error(f"Error getting collection: {collection_error}")
                raise

            self._logger.info(
                f"Connected to database, using collection {self._collection_name}",
            )
        except Exception as e:
            self._logger.error(f"Error initializing database: {e!s}")
            raise

    def get_recorder_characteristics(self) -> SemanticDataCharacteristics:
        """
        Get the characteristics of the recorder.

        Returns:
            SemanticDataCharacteristics: Characteristics of the recorder
        """
        characteristics = SemanticDataCharacteristics()
        characteristics.set_name(self._name)
        characteristics.set_provider_id(self._recorder_id)
        return characteristics

    def get_recorder_name(self) -> str:
        """
        Get the name of the recorder.

        Returns:
            str: Name of the recorder
        """
        return self._name

    def get_recorder_id(self) -> uuid.UUID:
        """
        Get the ID for the recorder.

        Returns:
            uuid.UUID: ID for the recorder
        """
        return self._recorder_id

    def get_collector_class_model(self) -> type:
        """
        Get the type of collector this recorder works with.

        Returns:
            Type: Type of collector
        """
        return UnstructuredCollector

    def get_description(self) -> str:
        """
        Get a description of the recorder.

        Returns:
            str: Description of the recorder
        """
        return self._description

    def get_cursor(self) -> Any:
        """
        Get a cursor for the recorded data.

        Returns:
            Any: Cursor for the recorded data
        """
        return self._latest_update

    def cache_duration(self) -> int:
        """
        Get the cache duration for the recorded data.

        Returns:
            int: Cache duration in seconds
        """
        return 3600  # 1 hour

    def get_json_schema(self) -> dict[str, Any]:
        """
        Get the JSON schema for the recorded data.

        Returns:
            Dict[str, Any]: JSON schema
        """
        return UnstructuredEmbeddedDataModel.model_json_schema()

    @monitor_semantic_extraction(extractor_name="UnstructuredRecorder.process_data")
    def process_data(self, raw_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Process raw data for storage.

        Args:
            raw_data: Raw data to process

        Returns:
            List[Dict[str, Any]]: Processed data
        """
        return raw_data

    @monitor_semantic_extraction(extractor_name="UnstructuredRecorder.store_data")
    def store_data(self, data: list[dict[str, Any]]) -> bool:
        """
        Store processed data in the database.

        Args:
            data: Processed data to store

        Returns:
            bool: True if successful, False otherwise
        """
        if self._skip_db_connection:
            self._logger.warning("Database connection skipped, not storing data")
            return False

        if self._collection is None:
            self._logger.error("Database collection not initialized")
            return False

        total_items = len(data)
        stored_count = 0
        self._logger.info(f"Storing {total_items} semantic data items")

        try:
            start_time = time.time()

            for item in data:
                # Create semantic database model
                semantic_model = self._create_semantic_model(item)

                # Store in database
                if semantic_model:
                    doc_id = self._collection.insert_document(
                        semantic_model.build_arangodb_doc(),
                    )
                    self._logger.debug(f"Stored document with ID: {doc_id}")
                    stored_count += 1

            end_time = time.time()
            elapsed_time = end_time - start_time

            self._logger.info(
                f"Stored {stored_count}/{total_items} items in {elapsed_time:.2f} seconds",
            )

            # Update latest update timestamp
            self._latest_update = datetime.now(UTC)

            return stored_count > 0

        except Exception as e:
            self._logger.error(f"Error storing data: {e!s}", exc_info=True)
            return False

    def update_data(self, data: list[dict[str, Any]]) -> bool:
        """
        Update existing data in the database.

        Args:
            data: Data to update

        Returns:
            bool: True if successful, False otherwise
        """
        # This implementation is similar to store_data, but with update logic
        if self._skip_db_connection:
            self._logger.warning("Database connection skipped, not updating data")
            return False

        if self._collection is None:
            self._logger.error("Database collection not initialized")
            return False

        total_items = len(data)
        updated_count = 0
        self._logger.info(f"Updating {total_items} semantic data items")

        try:
            start_time = time.time()

            for item in data:
                # Create semantic database model
                semantic_model = self._create_semantic_model(item)

                if not semantic_model:
                    continue

                # Check if document exists
                object_id = str(item.get("ObjectIdentifier", ""))
                query = f"FOR doc IN {self._collection_name} FILTER doc.ObjectIdentifier == @id RETURN doc._key"
                cursor = self._db.db.aql.execute(query, bind_vars={"id": object_id})

                doc_keys = [doc for doc in cursor]

                if doc_keys:
                    # Update existing document
                    doc_key = doc_keys[0]
                    arangodb_doc = semantic_model.build_arangodb_doc()
                    arangodb_doc["_key"] = doc_key
                    self._collection.update_document(doc_key, arangodb_doc)
                    self._logger.debug(f"Updated document with key: {doc_key}")
                else:
                    # Insert new document
                    doc_id = self._collection.insert_document(
                        semantic_model.build_arangodb_doc(),
                    )
                    self._logger.debug(f"Inserted document with ID: {doc_id}")

                updated_count += 1

            end_time = time.time()
            elapsed_time = end_time - start_time

            self._logger.info(
                f"Updated {updated_count}/{total_items} items in {elapsed_time:.2f} seconds",
            )

            # Update latest update timestamp
            self._latest_update = datetime.now(UTC)

            return updated_count > 0

        except Exception as e:
            self._logger.error(f"Error updating data: {e!s}", exc_info=True)
            return False

    def get_latest_db_update(self) -> datetime | None:
        """
        Get the latest database update timestamp.

        Returns:
            Optional[datetime]: Latest update timestamp, or None if not available
        """
        return self._latest_update

    @monitor_semantic_extraction(
        extractor_name="UnstructuredRecorder._create_semantic_model",
    )
    def _create_semantic_model(
        self,
        item: dict[str, Any],
    ) -> IndalekoBaseModel | None:
        """
        Create a semantic database model from unstructured data.

        Args:
            item: Unstructured data item

        Returns:
            Optional[IndalekoBaseModel]: Semantic database model, or None if creation failed
        """
        try:
            # Extract basic information
            object_id = item.get("ObjectIdentifier")
            if not object_id:
                self._logger.warning("Item missing ObjectIdentifier, skipping")
                return None

            # Create record for raw data
            raw_data = json.dumps(item)
            record = IndalekoRecordDataModel(
                SourceIdentifier={
                    "Identifier": str(self._recorder_id),
                    "Version": "1.0",
                },
                Data=encode_binary_data(raw_data.encode("utf-8")),
            )

            # Extract semantic attributes
            semantic_attributes = self._extract_semantic_attributes(item)

            # Create semantic model
            from semantic.data_models.base_data_model import BaseSemanticDataModel

            semantic_model = BaseSemanticDataModel(
                Record=record,
                Timestamp=datetime.now(UTC).isoformat(),
                ObjectIdentifier=uuid.UUID(object_id),
                RelatedObjects=[uuid.UUID(object_id)],
                SemanticAttributes=semantic_attributes,
            )

            return semantic_model

        except Exception as e:
            self._logger.error(
                f"Error creating semantic model: {e!s}",
                exc_info=True,
            )
            return None

    def _extract_semantic_attributes(
        self,
        item: dict[str, Any],
    ) -> list[IndalekoSemanticAttributeDataModel]:
        """
        Extract semantic attributes from unstructured data.

        Args:
            item: Unstructured data item

        Returns:
            List[IndalekoSemanticAttributeDataModel]: Extracted semantic attributes
        """
        attributes = []

        # Extract file metadata
        if "LocalPath" in item:
            filename = os.path.basename(item["LocalPath"])
            attributes.append(self._create_attribute("filename", filename))

        # Extract timestamp
        if "ModificationTimestamp" in item:
            attributes.append(
                self._create_attribute("last_modified", item["ModificationTimestamp"]),
            )

        # Extract unstructured elements
        elements = item.get("Unstructured", [])
        languages = set()

        for element in elements:
            # Extract element text by type
            element_type = element.get("type")
            text = element.get("text", "")

            if element_type and text and element_type in self.attribute_map:
                attributes.append(self._create_attribute(element_type, text))

            # Extract metadata
            metadata = element.get("metadata", {})

            # Extract file type
            if "filetype" in metadata:
                filetype = metadata["filetype"]
                attributes.append(self._create_attribute("filetype", filetype))

            # Extract languages
            if "languages" in metadata:
                element_languages = metadata["languages"]
                languages.update(element_languages)

            # Extract page numbers
            if "page_number" in metadata:
                page_number = metadata["page_number"]
                attributes.append(self._create_attribute("page_number", page_number))

        # Add language attributes
        for language in languages:
            attributes.append(self._create_attribute("language", language))

        return attributes

    def _create_attribute(
        self,
        attr_type: str,
        value: Any,
    ) -> IndalekoSemanticAttributeDataModel:
        """
        Create a semantic attribute with the given type and value.

        Args:
            attr_type: Type of attribute
            value: Value of attribute

        Returns:
            IndalekoSemanticAttributeDataModel: Created attribute
        """
        # Get UUID for attribute type
        uuid_value = self.attribute_map.get(attr_type, SEM_UNUSED)

        # Create UUID data model
        identifier = IndalekoUUIDDataModel(Identifier=uuid_value, Label=attr_type)

        # Create semantic attribute
        return IndalekoSemanticAttributeDataModel(Identifier=identifier, Value=value)


def main():
    """Main function for testing the UnstructuredRecorder."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Indaleko Unstructured Semantic Recorder",
    )
    parser.add_argument(
        "--input",
        help="Input JSON file with data from UnstructuredCollector",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Skip database connection",
    )
    parser.add_argument(
        "--collection",
        default="SemanticContent",
        help="Collection name for storage",
    )

    args = parser.parse_args()

    if not args.input:
        print("Error: Input file not specified. Use --input to specify the data file.")
        return

    # Load data from file
    try:
        with open(args.input) as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading input file: {e!s}")
        return

    # Create recorder
    recorder = UnstructuredRecorder(
        collection_name=args.collection,
        skip_db_connection=args.skip_db,
        enable_performance_monitoring=True,
    )

    # Process and store data
    if isinstance(data, list):
        processed_data = recorder.process_data(data)
        if args.skip_db:
            print(f"Processed {len(processed_data)} items (database storage skipped)")
        else:
            success = recorder.store_data(processed_data)
            print(
                f"Stored {len(processed_data)} items: {'Success' if success else 'Failed'}",
            )
    else:
        print("Error: Input data is not a list")

    # Print performance statistics
    print("Performance statistics:")
    print(json.dumps(recorder._perf_monitor.get_statistics(), indent=2))


if __name__ == "__main__":
    main()
