"""
This module implements an Outlook email file sharing recorder for Indaleko.

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
from pathlib import Path
from typing import Any

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.collaboration.data_models.email_file_share import (
    EmailFileShareCollaborationDataModel as EmailFileShareData,
)
from activity.collectors.collaboration.data_models.shared_file import SharedFileData
from activity.collectors.collaboration.outlook.outlook_file_collector import (
    OutlookFileShareCollector,
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


class OutlookFileShareRecorder(RecorderBase):
    """
    Outlook file sharing recorder for Indaleko.

    This recorder processes and stores Outlook email file sharing data in the Indaleko database.
    It creates semantic attributes based on the shared file properties and tracks relationships
    between files shared via email.
    """

    source_data = {
        "Identifier": uuid.UUID("98765432-abcd-ef12-3456-7890abcdef12"),
        "Version": "1.0.0",
        "Description": "Outlook File Share Recorder",
    }

    semantic_attributes_mapping = {
        "filename": "a7b8c9d0-e1f2-3a4b-5c6d-7e8f9a0b1c2d",
        "url": "b8c9d0e1-f2a3-4b5c-6d7e-8f9a0b1c2d3e",
        "email_id": "c9d0e1f2-a3b4-5c6d-7e8f-9a0b1c2d3e4f",
        "subject": "d0e1f2a3-b4c5-6d7e-8f9a-0b1c2d3e4f5a",
        "sender": "e1f2a3b4-c5d6-7e8f-9a0b-1c2d3e4f5a6b",
        "recipients": "f2a3b4c5-d6e7-8f9a-0b1c-2d3e4f5a6b7c",
        "content_type": "a3b4c5d6-e7f8-9a0b-1c2d-3e4f5a6b7c8d",
        "size": "b4c5d6e7-f8a9-0b1c-2d3e-4f5a6b7c8d9e",
        "timestamp": "c5d6e7f8-a90b-1c2d-3e4f-5a6b7c8d9e0f",
        "file_share_type": "d6e7f8a9-0b1c-2d3e-4f5a-6b7c8d9e0f1a",
    }

    def __init__(
        self,
        collector: OutlookFileShareCollector | None = None,
        data_dir: str = "./outlook_data",
        **kwargs,
    ):
        """
        Initialize the Outlook file sharing recorder.

        Args:
            collector: The Outlook file collector
            data_dir: Directory to store data files
            **kwargs: Additional arguments
        """
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

        # Directory for data storage
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Set up logging
        self.logger = logging.getLogger("OutlookFileShareRecorder")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # Track processed file shares
        self.processed_ids = set()

    def get_recorder_name(self) -> str:
        """Get the name of the recorder"""
        return "outlook_file_share_recorder"

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
        return {
            "EmailFileShareData": EmailFileShareData,
            "SharedFileData": SharedFileData,
        }

    def get_description(self) -> str:
        """Get the description of the recorder"""
        return self.source_data["Description"]

    def create_semantic_attributes(
        self,
        file_share: dict,
    ) -> list[IndalekoSemanticAttributeDataModel]:
        """
        Create semantic attributes from file share data.

        Args:
            file_share: The file share data

        Returns:
            List of semantic attributes
        """
        semantic_attributes = []

        # Build a flattened dictionary from the file share data
        flat_data = {
            "filename": file_share.get("filename"),
            "url": file_share.get("url"),
            "email_id": file_share.get("email_id"),
            "subject": file_share.get("subject"),
            "sender": file_share.get("sender"),
            "recipients": ",".join(file_share.get("recipients", [])),
            "content_type": file_share.get("content_type"),
            "size": file_share.get("size"),
            "timestamp": file_share.get("timestamp"),
            "file_share_type": file_share.get("attachment_type"),
        }

        # Map flattened data to semantic attributes
        for field, uuid_value in self.semantic_attributes_mapping.items():
            if field in flat_data and flat_data[field] is not None:
                value = flat_data[field]

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

    def build_email_file_share_document(
        self,
        file_share: dict,
        semantic_attributes: list[IndalekoSemanticAttributeDataModel] | None = None,
    ) -> dict:
        """
        Build a document for storing in the database.

        Args:
            file_share: The file share data
            semantic_attributes: The semantic attributes

        Returns:
            Document for storage
        """
        if semantic_attributes is None:
            semantic_attributes = self.create_semantic_attributes(file_share)

        # Prepare the timestamp
        timestamp = file_share.get("timestamp", datetime.now(UTC).isoformat())

        # Create the record
        record = IndalekoRecordDataModel(
            SourceIdentifier=self.source_data,
            Timestamp=timestamp,
            Data=Indaleko.encode_binary_data(file_share),
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

    def store_file_share(self, file_share: dict) -> dict | None:
        """
        Store a file share in the database.

        Args:
            file_share: The file share data

        Returns:
            The stored document if successful, None otherwise
        """
        try:
            # Generate a unique ID if not present
            if "id" not in file_share:
                file_share["id"] = str(uuid.uuid4())

            # Skip if already processed
            if file_share["id"] in self.processed_ids:
                self.logger.info(
                    f"Skipping already processed file share: {file_share.get('filename')}",
                )
                return None

            # Create semantic attributes
            semantic_attributes = self.create_semantic_attributes(file_share)

            # Build document
            doc = self.build_email_file_share_document(
                file_share=file_share,
                semantic_attributes=semantic_attributes,
            )

            # Insert into collection
            result = self.collection.insert(doc)
            self.logger.info(
                f"Stored file share: {file_share.get('filename')} (key: {result})",
            )

            # Mark as processed
            self.processed_ids.add(file_share["id"])

            return doc
        except Exception as e:
            self.logger.error(
                f"Error storing file share {file_share.get('filename')}: {e}",
            )
            return None

    def process_email_data(self, email_data: dict) -> list[dict]:
        """
        Process email data and store file shares.

        Args:
            email_data: Email data including attachments

        Returns:
            List of stored documents
        """
        try:
            results = []

            # Extract relevant fields
            email_id = email_data.get("emailId")
            subject = email_data.get("subject")
            sender = email_data.get("senderEmailAddress")
            recipients = email_data.get("recipientEmailAddresses", [])
            timestamp = email_data.get(
                "timestamp",
                datetime.now(UTC).isoformat(),
            )
            attachments = email_data.get("attachments", [])

            # Process each attachment
            for attachment in attachments:
                file_share = {
                    "email_id": email_id,
                    "subject": subject,
                    "sender": sender,
                    "recipients": recipients,
                    "timestamp": timestamp,
                    "filename": attachment.get("fileName"),
                    "attachment_type": attachment.get("attachmentType"),
                    "content_type": attachment.get("contentType"),
                    "size": attachment.get("size"),
                    "url": attachment.get("url"),
                    "id": attachment.get("id", str(uuid.uuid4())),
                }

                # Store the file share
                result = self.store_file_share(file_share)
                if result:
                    results.append(result)

            return results
        except Exception as e:
            self.logger.error(f"Error processing email data: {e}")
            return []

    def process_data(self, data: Any) -> dict[str, Any]:
        """
        Process the data from the collector.

        Args:
            data: Data to process

        Returns:
            Processed data
        """
        # Process email data if it's a dictionary with attachments
        if isinstance(data, dict) and "attachments" in data:
            return self.process_email_data(data)

        # Process a single file share
        if isinstance(data, dict) and "filename" in data:
            result = self.store_file_share(data)
            return result if result else {}

        return {}

    def lookup_file_by_url(self, url: str) -> dict | None:
        """
        Look up a file by its URL.

        Args:
            url: The file URL

        Returns:
            The file data if found, None otherwise
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
        file_data = Indaleko.decode_binary_data(doc["Record"]["Data"])
        return file_data

    def lookup_file_by_filename(self, filename: str) -> list[dict]:
        """
        Look up files by filename.

        Args:
            filename: The filename to search for

        Returns:
            List of matching file data
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
        files = []
        for doc in entries:
            try:
                file_data = Indaleko.decode_binary_data(doc["Record"]["Data"])
                files.append(file_data)
            except Exception as e:
                self.logger.error(f"Error decoding file data: {e}")

        return files

    def lookup_files_by_sender(self, sender: str) -> list[dict]:
        """
        Look up files by sender email.

        Args:
            sender: The sender email to search for

        Returns:
            List of matching file data
        """
        assert isinstance(
            self.collection,
            IndalekoCollection,
        ), f"collection is not an IndalekoCollection {type(self.collection)}"

        # Query with sender filter
        query = """
            FOR doc IN @@collection
                FILTER doc.Record.Data LIKE @sender
                SORT doc.Timestamp DESC
                RETURN doc
        """
        bind_vars = {"@collection": self.collection.name, "sender": f"%{sender}%"}

        results = IndalekoDBConfig()._arangodb.aql.execute(query, bind_vars=bind_vars)
        entries = [entry for entry in results]

        # Decode the binary data for each entry
        files = []
        for doc in entries:
            try:
                file_data = Indaleko.decode_binary_data(doc["Record"]["Data"])
                files.append(file_data)
            except Exception as e:
                self.logger.error(f"Error decoding file data: {e}")

        return files

    def get_all_file_shares(self, limit: int = 100) -> list[dict]:
        """
        Get all file shares from the database.

        Args:
            limit: Maximum number of file shares to retrieve

        Returns:
            List of file share data
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
        file_shares = []
        for doc in entries:
            try:
                file_data = Indaleko.decode_binary_data(doc["Record"]["Data"])
                file_shares.append(file_data)
            except Exception as e:
                self.logger.error(f"Error decoding file data: {e}")

        return file_shares

    def start_collector(self) -> None:
        """Start the collector to begin receiving data."""
        if not self.collector:
            self.logger.error("No collector available to start")
            return

        try:
            # Start the collector
            self.collector.collect_data()
            self.logger.info("Collector started successfully")
        except Exception as e:
            self.logger.error(f"Error starting collector: {e}")

    def sync_from_collector(self) -> int:
        """
        Sync file shares from the collector to the database.

        Returns:
            Number of file shares synced
        """
        if not self.collector:
            self.logger.error("No collector available for syncing")
            return 0

        # Get all file shares from the collector
        file_shares = self.collector.get_file_shares()

        # Process each file share
        count = 0
        for file_share in file_shares:
            # Store the file share
            result = self.store_file_share(file_share)
            if result:
                count += 1

        self.logger.info(f"Synced {count} file shares from collector")
        return count

    def scan_data_directory(self) -> int:
        """
        Scan the data directory for JSON files and import them.

        Returns:
            Number of file shares imported
        """
        count = 0

        # Find all JSON files in the data directory
        json_files = list(self.data_dir.glob("*.json"))
        self.logger.info(f"Found {len(json_files)} JSON files in {self.data_dir}")

        # Process each file
        for json_file in json_files:
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)

                # Process the data
                results = self.process_email_data(data)
                count += len(results)

                # Optionally, move the file to a processed directory
                processed_dir = self.data_dir / "processed"
                processed_dir.mkdir(exist_ok=True)
                json_file.rename(processed_dir / json_file.name)

            except Exception as e:
                self.logger.error(f"Error processing {json_file}: {e}")

        self.logger.info(f"Imported {count} file shares from JSON files")
        return count

    def update_data(self) -> int:
        """
        Update data by syncing from collector and scanning data directory.

        Returns:
            Total number of file shares updated
        """
        count = 0

        # Sync from collector if available
        if self.collector:
            count += self.sync_from_collector()

        # Scan data directory
        count += self.scan_data_directory()

        return count


def main():
    """Main function for testing the recorder"""
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    try:
        # Create a test directory
        data_dir = Path("./outlook_test_data")
        data_dir.mkdir(exist_ok=True)

        # Create a sample data file
        sample_data = {
            "emailId": "AAMkADRmMDExYzA3LThhYzgtNDRlOS1iMmJmLWNkYWM0ZjQ2ZmFkZQBGAAAAAADJRNbJqN3oQqtchVY9fVDoBwDtROOF92eoRKmzSJJuTTKdAAAAAAEJAADtROOF92eoRKmzSJJuTTKdAAFvmujTAAA=",
            "subject": "Project files for review",
            "senderEmailAddress": "sender@example.com",
            "recipientEmailAddresses": [
                "recipient1@example.com",
                "recipient2@example.com",
            ],
            "timestamp": datetime.now(UTC).isoformat(),
            "attachments": [
                {
                    "fileName": "report.docx",
                    "attachmentType": "regular",
                    "contentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "size": 54321,
                    "id": "AAMkADRmMDExYzA3LThhYzgtNDRlOS1iMmJmLWNkYWM0ZjQ2ZmFkZQBGAAAAAADJRNbJqN3oQqtchVY9fVDoBwDtROOF92eoRKmzSJJuTTKdAAAAAAEJAADtROOF92eoRKmzSJJuTTKdAAFvmujTAAABEgAQAJ9cMJD03UZAi9/kR2Xcioo=",
                },
                {
                    "fileName": "data.xlsx",
                    "attachmentType": "onedrive",
                    "contentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "size": 12345,
                    "url": "https://1drv.ms/x/s!AkP8HPJpsdfW98765gKJYT",
                },
            ],
        }

        # Save sample data to a file
        sample_file = data_dir / "sample_email_data.json"
        with open(sample_file, "w", encoding="utf-8") as f:
            json.dump(sample_data, f, indent=2, default=str)

        print(f"Created sample data file: {sample_file}")

        # Initialize recorder
        recorder = OutlookFileShareRecorder(data_dir=str(data_dir))

        # Process the data directory
        count = recorder.scan_data_directory()
        print(f"Imported {count} file shares")

        # Retrieve file shares
        file_shares = recorder.get_all_file_shares()
        print(f"\nRetrieved {len(file_shares)} file shares from database:")

        for i, file_share in enumerate(file_shares):
            print(f"\nFile Share {i+1}:")
            print(f"  Filename: {file_share.get('filename')}")
            print(f"  Type: {file_share.get('attachment_type')}")
            print(f"  Sender: {file_share.get('sender')}")
            print(f"  Recipients: {', '.join(file_share.get('recipients', []))}")

        # Test lookup by filename
        docx_files = recorder.lookup_file_by_filename("report.docx")
        print(f"\nFound {len(docx_files)} files matching 'report.docx'")

        # Test lookup by sender
        sender_files = recorder.lookup_files_by_sender("sender@example.com")
        print(f"Found {len(sender_files)} files from sender@example.com")

        print("\nOutlook file share recorder test completed successfully")

    except Exception as e:
        logging.exception(f"Error in main: {e}")


if __name__ == "__main__":
    main()
