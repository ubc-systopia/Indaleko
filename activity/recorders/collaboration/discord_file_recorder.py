"""
This module implements a Discord file sharing recorder for Indaleko.

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
import uuid
from datetime import UTC, datetime
from typing import Any

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.collaboration.data_models.shared_file import SharedFileData
from activity.collectors.collaboration.discord.data_models.file_share_data_model import (
    DiscordDataModel,
)
from activity.collectors.collaboration.discord.discord_file_collector import (
    DiscordFileShareCollector,
)
from activity.data_model.activity import IndalekoActivityDataModel
from activity.recorders.base import RecorderBase
from activity.recorders.registration_service import (
    IndalekoActivityDataRegistrationService,
)
from data_models.i_uuid import IndalekoUUIDDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from db import IndalekoCollection, IndalekoDBConfig

# pylint: disable=wrong-import-position
from Indaleko import Indaleko

# pylint: enable=wrong-import-position


class DiscordFileShareRecorder(RecorderBase):
    """
    Discord file sharing recorder for Indaleko.

    This recorder processes and stores Discord file sharing data in the Indaleko database.
    It creates semantic attributes based on the shared file properties and maintains
    relationships between Discord CDN URLs and original filenames.
    """

    source_data = {
        "Identifier": uuid.UUID("e7d6c5b4-a3f2-10fd-9e8c-7b6a5d4c3f2e"),
        "Version": "1.0.0",
        "Description": "Discord File Share Recorder",
    }

    semantic_attributes_mapping = {
        "filename": "a7b8c9d0-e1f2-3a4b-5c6d-7e8f9a0b1c2d",
        "url": "b8c9d0e1-f2a3-4b5c-6d7e-8f9a0b1c2d3e",
        "message_id": "c9d0e1f2-a3b4-5c6d-7e8f-9a0b1c2d3e4f",
        "channel_id": "d0e1f2a3-b4c5-6d7e-8f9a-0b1c2d3e4f5a",
        "guild_id": "e1f2a3b4-c5d6-7e8f-9a0b-1c2d3e4f5a6b",
        "sender": "f2a3b4c5-d6e7-8f9a-0b1c-2d3e4f5a6b7c",
        "content_type": "a3b4c5d6-e7f8-9a0b-1c2d-3e4f5a6b7c8d",
        "size_bytes": "b4c5d6e7-f8a9-0b1c-2d3e-4f5a6b7c8d9e",
        "timestamp": "c5d6e7f8-a90b-1c2d-3e4f-5a6b7c8d9e0f",
    }

    def __init__(self, collector: DiscordFileShareCollector | None = None, **kwargs):
        """Initialize the Discord file sharing recorder"""
        # Initialize database connection
        self.db_config = IndalekoDBConfig()
        assert self.db_config is not None, "Failed to get the database configuration"

        # Initialize source identifier
        source_identifier = IndalekoSourceIdentifierDataModel(
            Identifier=self.source_data["Identifier"],
            Version=self.source_data["Version"],
            Description=self.source_data["Description"],
        )

        # Initialize record kwargs
        record_kwargs = {
            "Identifier": str(self.source_data["Identifier"]),
            "Version": self.source_data["Version"],
            "Description": self.source_data["Description"],
            "Record": IndalekoRecordDataModel(
                SourceIdentifier=source_identifier,
                Timestamp=datetime.now(UTC),
                Attributes={},
                Data="",
            ),
        }

        # Register with the provider registrar
        self.provider_registrar = IndalekoActivityDataRegistrationService()
        assert self.provider_registrar is not None, "Failed to get the provider registrar"

        collector_data = self.provider_registrar.lookup_provider_by_identifier(
            str(self.source_data["Identifier"]),
        )
        if collector_data is None:
            ic("Registering the provider")
            collector_data, collection = self.provider_registrar.register_provider(
                **record_kwargs,
            )
        else:
            ic("Provider already registered")
            collection = IndalekoActivityDataRegistrationService.lookup_activity_provider_collection(
                str(self.source_data["Identifier"]),
            )

        ic(collector_data)
        ic(collection)
        self.collector_data = collector_data
        self.collection = collection

        # Set up collector
        self.collector = collector

        # Set up logging
        self.logger = logging.getLogger("DiscordFileShareRecorder")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def get_recorder_name(self) -> str:
        """Get the name of the recorder"""
        return "discord_file_share_recorder"

    def get_recorder_id(self) -> uuid.UUID:
        """Get the ID of the recorder"""
        return self.source_data["Identifier"]

    def get_recorder_characteristics(self) -> list[ActivityDataCharacteristics]:
        """Get the characteristics of the recorder"""
        if self.collector:
            return self.collector.get_collector_characteristics()
        return [
            ActivityDataCharacteristics.ACTIVITY_DATA_FILE_SHARE,
            ActivityDataCharacteristics.ACTIVITY_DATA_COLLABORATION,
            ActivityDataCharacteristics.PROVIDER_COLLABORATION_DATA,
        ]

    def get_collector_class_model(self) -> dict[str, type]:
        """Get the class model for the collector"""
        return {"DiscordDataModel": DiscordDataModel, "SharedFileData": SharedFileData}

    def get_description(self) -> str:
        """Get the description of the recorder"""
        return self.source_data["Description"]

    def create_semantic_attributes(
        self,
        attachment: dict,
    ) -> list[IndalekoSemanticAttributeDataModel]:
        """
        Create semantic attributes from file attachment data.

        Args:
            attachment: The file attachment data

        Returns:
            List of semantic attributes
        """
        semantic_attributes = []

        # Map attachment fields to semantic attributes
        for field, uuid_value in self.semantic_attributes_mapping.items():
            if field in attachment and attachment[field] is not None:
                value = attachment[field]

                # Convert special types
                if isinstance(value, datetime):
                    value = value.isoformat()
                elif isinstance(value, list):
                    value = json.dumps(value)

                # Create the semantic attribute
                semantic_attributes.append(
                    IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=uuid_value,
                            Version="1",
                            Description=field,
                        ),
                        Data=str(value),
                    ),
                )

        return semantic_attributes

    def build_discord_file_activity_document(
        self,
        attachment: dict,
        semantic_attributes: list[IndalekoSemanticAttributeDataModel] | None = None,
    ) -> dict:
        """
        Build a document for storing in the database.

        Args:
            attachment: The file attachment data
            semantic_attributes: The semantic attributes

        Returns:
            Document for storage
        """
        if semantic_attributes is None:
            semantic_attributes = self.create_semantic_attributes(attachment)

        # Prepare the activity data
        timestamp = attachment.get("timestamp", datetime.now(UTC).isoformat())

        # Create the record
        record = IndalekoRecordDataModel(
            SourceIdentifier=self.source_data,
            Timestamp=timestamp,
            Data=Indaleko.encode_binary_data(attachment),
        )

        # Create the activity data model
        activity_data_args = {
            "Record": record,
            "Timestamp": timestamp,
            "SemanticAttributes": semantic_attributes,
        }

        activity_data = IndalekoActivityDataModel(**activity_data_args)

        # Convert to dictionary
        return json.loads(
            activity_data.model_dump_json(exclude_none=True, exclude_unset=True),
        )

    def store_attachment(self, attachment: dict) -> dict:
        """
        Store a file attachment in the database.

        Args:
            attachment: The file attachment data

        Returns:
            The stored document
        """
        # Create semantic attributes
        semantic_attributes = self.create_semantic_attributes(attachment)

        # Build document
        doc = self.build_discord_file_activity_document(
            attachment=attachment,
            semantic_attributes=semantic_attributes,
        )

        # Insert into collection
        result = self.collection.insert(doc)
        self.logger.info(
            f"Stored attachment: {attachment.get('filename')} (key: {result})",
        )

        return doc

    def process_data(self, data: Any) -> dict[str, Any]:
        """
        Process the data from the collector.

        Args:
            data: Data to process

        Returns:
            Processed data
        """
        return data

    def lookup_attachment_by_url(self, url: str) -> dict | None:
        """
        Look up an attachment by its URL.

        Args:
            url: The attachment URL

        Returns:
            The attachment data if found, None otherwise
        """
        assert isinstance(
            self.collection,
            IndalekoCollection,
        ), f"collection is not an IndalekoCollection {type(self.collection)}"

        # Query with URL filter
        query = """
            FOR doc IN @@collection
                FILTER doc.Record.Data LIKE @url
                SORT doc.Timestamp DESC
                LIMIT 1
                RETURN doc
        """
        bind_vars = {"@collection": self.collection.name, "url": f"%{url}%"}

        results = IndalekoDBConfig()._arangodb.aql.execute(query, bind_vars=bind_vars)
        entries = [entry for entry in results]

        if len(entries) == 0:
            return None

        # Decode the binary data
        doc = entries[0]
        attachment_data = Indaleko.decode_binary_data(doc["Record"]["Data"])
        return attachment_data

    def get_all_attachments(self, limit: int = 100) -> list[dict]:
        """
        Get all file attachments from the database.

        Args:
            limit: Maximum number of attachments to retrieve

        Returns:
            List of attachment data
        """
        assert isinstance(
            self.collection,
            IndalekoCollection,
        ), f"collection is not an IndalekoCollection {type(self.collection)}"

        query = """
            FOR doc IN @@collection
                SORT doc.Timestamp DESC
                LIMIT @limit
                RETURN doc
        """
        bind_vars = {"@collection": self.collection.name, "limit": limit}

        results = IndalekoDBConfig()._arangodb.aql.execute(query, bind_vars=bind_vars)
        entries = [entry for entry in results]

        # Decode the binary data for each entry
        attachments = []
        for doc in entries:
            try:
                attachment_data = Indaleko.decode_binary_data(doc["Record"]["Data"])
                attachments.append(attachment_data)
            except Exception as e:
                self.logger.error(f"Error decoding attachment data: {e}")

        return attachments

    def sync_attachments(self) -> int:
        """
        Sync file attachments from the collector to the database.

        Returns:
            Number of attachments synced
        """
        if not self.collector:
            self.logger.error("No collector available for syncing")
            return 0

        # Collect attachments from Discord
        attachments = self.collector.collect_data()

        # Store each attachment
        count = 0
        for attachment in attachments:
            # Check if attachment already exists in the database
            existing = self.lookup_attachment_by_url(attachment["url"])
            if not existing:
                self.store_attachment(attachment)
                count += 1

        self.logger.info(f"Synced {count} new attachments to database")
        return count

    def update_data(self) -> int:
        """
        Update data in the database by syncing new attachments.

        Returns:
            Number of attachments synced
        """
        return self.sync_attachments()

    def retrieve_attachments_by_filename(self, filename: str) -> list[dict]:
        """
        Retrieve attachments by original filename.

        Args:
            filename: The filename to search for

        Returns:
            List of matching attachments
        """
        assert isinstance(
            self.collection,
            IndalekoCollection,
        ), f"collection is not an IndalekoCollection {type(self.collection)}"

        # Query with filename filter
        query = """
            FOR doc IN @@collection
                FILTER doc.Record.Data LIKE @filename
                SORT doc.Timestamp DESC
                RETURN doc
        """
        bind_vars = {"@collection": self.collection.name, "filename": f"%{filename}%"}

        results = IndalekoDBConfig()._arangodb.aql.execute(query, bind_vars=bind_vars)
        entries = [entry for entry in results]

        # Decode the binary data for each entry
        attachments = []
        for doc in entries:
            try:
                attachment_data = Indaleko.decode_binary_data(doc["Record"]["Data"])
                attachments.append(attachment_data)
            except Exception as e:
                self.logger.error(f"Error decoding attachment data: {e}")

        return attachments

    def generate_filename_to_url_mapping(self) -> dict[str, list[str]]:
        """
        Generate a mapping from filenames to URLs.

        Returns:
            Dictionary mapping filenames to lists of URLs
        """
        # Get all attachments
        attachments = self.get_all_attachments(limit=1000)

        # Build the mapping
        mapping = {}
        for attachment in attachments:
            filename = attachment.get("filename")
            url = attachment.get("url")

            if filename and url:
                if filename not in mapping:
                    mapping[filename] = []
                mapping[filename].append(url)

        return mapping


def main():
    """Main function for testing the recorder"""
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    try:
        # Create the collector with a token file
        collector = DiscordFileShareCollector(token_file="./config/discord-token.json")

        # Create the recorder with the collector
        recorder = DiscordFileShareRecorder(collector=collector)

        # Sync attachments
        count = recorder.sync_attachments()
        print(f"\nSynced {count} new attachments to the database")

        # Get all attachments
        attachments = recorder.get_all_attachments(limit=10)
        print(f"\nRetrieved {len(attachments)} attachments from the database:")

        # Print attachment details
        for i, attachment in enumerate(attachments[:5]):
            print(f"\nAttachment {i+1}:")
            print(f"  Filename: {attachment.get('filename')}")
            print(f"  URL: {attachment.get('url')}")
            print(f"  From: {attachment.get('sender', 'Unknown')}")

        # Generate filename to URL mapping
        mapping = recorder.generate_filename_to_url_mapping()
        print("\nFilename to URL mapping:")
        for filename, urls in list(mapping.items())[:5]:
            print(f"  {filename}: {len(urls)} URLs")

    except Exception as e:
        logging.exception(f"Error in main: {e}")


if __name__ == "__main__":
    main()
