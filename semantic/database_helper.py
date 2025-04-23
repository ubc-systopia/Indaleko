"""
Database helper functions for semantic processing.

This module provides functions to interact with the ArangoDB database
for semantic metadata extraction.

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
import socket
import uuid
from datetime import UTC, datetime
from typing import Any

from db.db_collections import IndalekoDBCollections

# Import Indaleko database components
from db.db_config import IndalekoDBConfig
from db.i_collections import IndalekoCollections

# Set up logging
logger = logging.getLogger("semantic.database")


class SemanticDatabaseHelper:
    """Helper class for semantic processing database operations."""

    def __init__(self, config: dict[str, Any]):
        """Initialize the database helper with configuration."""
        self.config = config
        self.db = None
        self.connected = False
        self.collections = None
        self.hostname = socket.gethostname()

    def connect(self) -> bool:
        """Connect to the ArangoDB database."""
        if self.connected:
            return True

        try:
            # Create connection
            db_config = IndalekoDBConfig()
            self.db = db_config._arangodb

            # Initialize collections with view skipping for better performance
            self.collections = IndalekoCollections(skip_views=True)

            # Verify connection
            self.db.version()

            self.connected = True
            logger.info("Connected to database")
            return True
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            self.connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from the database."""
        self.connected = False
        self.collections = None
        self.db = None
        logger.debug("Disconnected from database")

    def get_files_for_processing(
        self, extractor_type: str, batch_size: int, state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Get a batch of files from the database that need semantic processing.

        Args:
            extractor_type: Type of extractor ("mime" or "checksum")
            batch_size: Number of files to retrieve
            state: Current processing state

        Returns:
            List of files with their paths and object IDs
        """
        if not self.connected and not self.connect():
            logger.error("Cannot get files: Not connected to database")
            return []

        # Get the last processed file ID from state
        last_file_id = state["extractors"].get(extractor_type, {}).get("last_file_id")

        try:
            # Get the appropriate semantic collection based on extractor type
            semantic_collection_name = None

            if extractor_type == "mime":
                semantic_collection_name = IndalekoDBCollections.Indaleko_Semantic_MIME
                semantic_attribute_id = uuid.UUID(
                    "8a7b9678-f2c5-4e3a-9a8b-cc8c2e626374",
                )  # Mime type attribute
            elif extractor_type == "checksum":
                semantic_collection_name = (
                    IndalekoDBCollections.Indaleko_Semantic_Checksum
                )
                semantic_attribute_id = uuid.UUID(
                    "c4e2d558-6a13-4734-9e19-5fe3c8a2c355",
                )  # Checksum attribute (MD5)
            else:
                logger.error(f"Unknown extractor type: {extractor_type}")
                return []

            # Construct AQL query to find files that:
            # 1. Are on the local machine (use hostname to match)
            # 2. Don't have the semantic attribute already, or it's older than X days
            # 3. Are of file types we're interested in based on config
            # 4. Are accessible (have a path that exists)

            # Get file extensions to include from config
            file_extensions = self.config["extractors"][extractor_type].get(
                "file_extensions", ["*"],
            )

            # If extensions include "*", we process all files
            process_all_extensions = "*" in file_extensions

            # Convert extensions to AQL filter format
            extension_filter = ""
            if not process_all_extensions:
                extension_conditions = []
                for ext in file_extensions:
                    if not ext.startswith("."):
                        ext = f".{ext}"
                    extension_conditions.append(
                        f'LIKE(LOWER(obj.Record.Attributes.URI), "%{ext}")',
                    )

                if extension_conditions:
                    extension_filter = f"AND ({' OR '.join(extension_conditions)})"

            # Build query for files without semantic attribute
            # Note: This is a simplified query - in production, you would add
            # more sophisticated filtering based on all relevant criteria
            aql_query = f"""
            FOR obj IN @@collection
                FILTER obj.Record != null
                AND obj.Record.Attributes != null
                AND obj.Record.Attributes.URI != null
                AND obj.Record.Attributes.HostMachine != null
                AND obj.Record.Attributes.HostMachine.Machine == @hostname
                {extension_filter}

                LET has_attribute = (
                    FOR attr IN @@semantic_collection
                        FILTER attr.ObjectID == obj._key
                        RETURN 1
                )

                FILTER LENGTH(has_attribute) == 0

                SORT obj._key
                LIMIT @batch_size

                RETURN {{
                    "object_id": obj._key,
                    "path": obj.Record.Attributes.URI,
                    "last_modified": obj.Record.Attributes.LastModifiedTime
                }}
            """

            # Execute query
            bind_vars = {
                "@collection": IndalekoDBCollections.Indaleko_Object_Collection,
                "@semantic_collection": semantic_collection_name,
                "hostname": self.hostname,
                "batch_size": batch_size,
            }

            cursor = self.db.aql.execute(aql_query, bind_vars=bind_vars)
            results = [doc for doc in cursor]

            # Filter results to only include files that exist on disk
            filtered_results = []
            for file_info in results:
                file_path = file_info.get("path")
                if file_path and os.path.exists(file_path):
                    filtered_results.append(file_info)
                else:
                    logger.debug(f"Skipping non-existent file: {file_path}")

            logger.info(
                f"Found {len(filtered_results)} files for {extractor_type} processing",
            )
            return filtered_results

        except Exception as e:
            logger.error(f"Error retrieving files for {extractor_type} processing: {e}")
            return []

    def store_mime_type_data(self, object_id: str, mime_data: dict[str, Any]) -> bool:
        """
        Store MIME type data in the database.

        Args:
            object_id: Object ID of the file
            mime_data: MIME type data to store

        Returns:
            True if successful, False otherwise
        """
        if not self.connected and not self.connect():
            logger.error("Cannot store MIME data: Not connected to database")
            return False

        try:
            # Get the appropriate collection
            collection_name = IndalekoDBCollections.Indaleko_Semantic_MIME
            collection = self.collections.get_collection(collection_name)

            # Create document
            document = {
                "_key": str(uuid.uuid4()),
                "ObjectID": object_id,
                "MimeType": mime_data.get("mime_type", "application/octet-stream"),
                "Encoding": mime_data.get("encoding", "binary"),
                "Category": mime_data.get("category", "unknown"),
                "Confidence": mime_data.get("confidence", 1.0),
                "ExtensionMatch": mime_data.get("extension_match", False),
                "ProcessedTimestamp": datetime.now(UTC).isoformat(),
            }

            # Insert document
            collection._arangodb_collection.insert(document)
            logger.debug(f"Stored MIME data for object {object_id}")
            return True

        except Exception as e:
            logger.error(f"Error storing MIME data for object {object_id}: {e}")
            return False

    def store_checksum_data(
        self, object_id: str, checksum_data: dict[str, Any],
    ) -> bool:
        """
        Store checksum data in the database.

        Args:
            object_id: Object ID of the file
            checksum_data: Checksum data to store

        Returns:
            True if successful, False otherwise
        """
        if not self.connected and not self.connect():
            logger.error("Cannot store checksum data: Not connected to database")
            return False

        try:
            # Get the appropriate collection
            collection_name = IndalekoDBCollections.Indaleko_Semantic_Checksum
            collection = self.collections.get_collection(collection_name)

            # Create document
            document = {
                "_key": str(uuid.uuid4()),
                "ObjectID": object_id,
                "MD5": checksum_data.get("MD5", ""),
                "SHA1": checksum_data.get("SHA1", ""),
                "SHA256": checksum_data.get("SHA256", ""),
                "SHA512": checksum_data.get("SHA512", ""),
                "Dropbox": checksum_data.get("Dropbox", ""),
                "ProcessedTimestamp": datetime.now(UTC).isoformat(),
            }

            # Insert document
            collection._arangodb_collection.insert(document)
            logger.debug(f"Stored checksum data for object {object_id}")
            return True

        except Exception as e:
            logger.error(f"Error storing checksum data for object {object_id}: {e}")
            return False
