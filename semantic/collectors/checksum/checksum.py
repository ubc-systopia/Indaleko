"""
This implements a semantic extractor for calculating multiple checksums for files

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

# standard imports
import hashlib
import logging
import mmap
import os
import sys
import unittest
import uuid
from datetime import UTC, datetime

# third-party imports
# explicit imports
from typing import Any

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Indaleko imports
# pylint: disable=wrong-import-position
import semantic.recorders.checksum.characteristics as ChecksumDataCharacteristics
from data_models.i_object import IndalekoObjectDataModel
from data_models.i_uuid import IndalekoUUIDDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from semantic.characteristics import SemanticDataCharacteristics
from semantic.collectors.checksum.data_model import SemanticChecksumDataModel
from semantic.collectors.semantic_collector import SemanticCollector

# pylint: enable=wrong-import-position


class IndalekoSemanticChecksums(SemanticCollector):
    """This class defines the semantic file checksums collector for the Indaleko project."""

    def __init__(self, **kwargs):
        """Initialize the semantic file checksums collector"""
        self._name = "Semantic File Checksums"
        self._provider_id = uuid.UUID("de7ff1c7-2550-4cb3-9538-775f9464746e")
        self._checksums_cache = {}  # Cache of computed checksums by file_path
        self._object_cache = {}  # Cache of objects by their identifiers

        # Process any additional arguments
        for key, value in kwargs.items():
            setattr(self, f"_{key}", value)

        # Make sure we have a name and provider_id
        if not hasattr(self, "_name") and not hasattr(self, "_provider_id"):
            raise ValueError(
                "The name or provider_id must be provided for the semantic file checksums collector.",
            )

    def lookup_object(self, object_id: str) -> IndalekoObjectDataModel | None:
        """
        Lookup an object by its identifier.

        Args:
            object_id (str): The identifier of the object to look up

        Returns:
            Optional[IndalekoObjectDataModel]: The object if found, None otherwise
        """
        # Check if we have it in the cache
        if object_id in self._object_cache:
            return self._object_cache[object_id]

        # TODO: Implement lookup from database or other source
        logging.warning(
            f"Object with ID {object_id} not found in cache and database lookup not implemented",
        )
        return None

    def compute_checksums_for_file(self, file_path: str) -> dict[str, str]:
        """
        Compute checksums for a file.

        Args:
            file_path (str): Path to the file

        Returns:
            Dict[str, str]: Dictionary of checksums with algorithm as key
        """
        # Check if we already have the checksums cached
        if file_path in self._checksums_cache:
            return self._checksums_cache[file_path]

        # Compute checksums
        checksums = compute_checksums(file_path)

        # Cache the result
        self._checksums_cache[file_path] = checksums

        return checksums

    def create_checksum_record(
        self,
        file_path: str,
        object_id: uuid.UUID,
    ) -> SemanticChecksumDataModel:
        """
        Create a checksum record for a file.

        Args:
            file_path (str): Path to the file
            object_id (uuid.UUID): UUID of the object

        Returns:
            SemanticChecksumDataModel: Checksum data model
        """
        # Compute checksums
        checksums = self.compute_checksums_for_file(file_path)

        # Create semantic attributes
        semantic_attributes = []

        # Add attribute for each checksum type
        attribute_map = {
            "MD5": ChecksumDataCharacteristics.SEMANTIC_CHECKSUM_MD5,
            "SHA1": ChecksumDataCharacteristics.SEMANTIC_CHECKSUM_SHA1,
            "SHA256": ChecksumDataCharacteristics.SEMANTIC_CHECKSUM_SHA256,
            "SHA512": ChecksumDataCharacteristics.SEMANTIC_CHECKSUM_SHA512,
            "Dropbox": ChecksumDataCharacteristics.SEMANTIC_CHECKSUM_DROPBOX_SHA2,
        }

        for algo, checksum in checksums.items():
            uuid_obj = attribute_map.get(algo)
            if uuid_obj:
                semantic_attributes.append(
                    IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=uuid_obj,
                            Label=f"{algo} Checksum",
                        ),
                        Data=checksum,
                    ),
                )

        # Create record
        record = IndalekoRecordDataModel(
            SourceIdentifier=IndalekoSourceIdentifierDataModel(
                Identifier=str(self._provider_id),
                Version="1.0",
            ),
            Timestamp=datetime.now(UTC),
            Attributes={},
            Data="",
        )

        # Create checksum data model
        return SemanticChecksumDataModel(
            Record=record,
            Timestamp=datetime.now(UTC),
            ObjectIdentifier=object_id,
            RelatedObjects=[object_id],
            SemanticAttributes=semantic_attributes,
            checksum_data_id=uuid.uuid4(),
            md5_checksum=checksums["MD5"],
            sha1_checksum=checksums["SHA1"],
            sha256_checksum=checksums["SHA256"],
            sha512_checksum=checksums["SHA512"],
            dropbox_checksum=checksums["Dropbox"],
        )

    def get_checksums_for_file(
        self,
        file_path: str,
        object_id: str | uuid.UUID,
    ) -> dict[str, Any]:
        """
        Get checksums for a file and create a semantic data record.

        Args:
            file_path (str): Path to the file
            object_id (Union[str, uuid.UUID]): UUID of the object

        Returns:
            Dict[str, Any]: Dictionary containing the checksums and metadata
        """
        # Convert string UUID to UUID object if needed
        if isinstance(object_id, str):
            object_id = uuid.UUID(object_id)

        # Create checksum record
        checksum_model = self.create_checksum_record(file_path, object_id)

        # Return as dictionary
        return checksum_model.model_dump()

    def get_collector_characteristics(self) -> list[SemanticDataCharacteristics]:
        """Get the characteristics of the collector"""
        return [
            SemanticDataCharacteristics.SEMANTIC_DATA_CHECKSUMS,
            ChecksumDataCharacteristics.SEMANTIC_CHECKSUM_MD5,
            ChecksumDataCharacteristics.SEMANTIC_CHECKSUM_SHA1,
            ChecksumDataCharacteristics.SEMANTIC_CHECKSUM_SHA256,
            ChecksumDataCharacteristics.SEMANTIC_CHECKSUM_SHA512,
            ChecksumDataCharacteristics.SEMANTIC_CHECKSUM_DROPBOX_SHA2,
        ]

    def get_collector_name(self) -> str:
        """Get the name of the collector"""
        return self._name

    def get_collector_id(self) -> uuid.UUID:
        """Get the ID of the collector"""
        return self._provider_id

    def retrieve_data(self, data_id: str) -> dict:
        """
        Retrieve semantic checksum data for a specific identifier.

        Args:
            data_id (str): The identifier of the data to retrieve

        Returns:
            Dict: The semantic checksum data
        """
        # TODO: Implement retrieving from a persistent store
        # For now, just return an error indicating this needs to be implemented
        raise NotImplementedError(
            "Retrieving data by ID is not yet implemented. "
            "Use get_checksums_for_file() to compute checksums for a specific file.",
        )

    def get_collector_description(self) -> str:
        """Get the description of the collector"""
        return """This collector computes and provides multiple checksums for files:
        - MD5: Fast but collision-prone hash
        - SHA1: Widely used but no longer cryptographically secure
        - SHA256: Strong cryptographic hash
        - SHA512: Very strong cryptographic hash with higher security margin
        - Dropbox Content Hash: Special hash used by Dropbox for content addressing"""

    def get_json_schema(self) -> dict:
        """Get the JSON schema for the collector"""
        return {
            "type": "object",
            "properties": {
                "MD5": {"type": "string", "description": "MD5 hash (32 characters)"},
                "SHA1": {"type": "string", "description": "SHA1 hash (40 characters)"},
                "SHA256": {
                    "type": "string",
                    "description": "SHA256 hash (64 characters)",
                },
                "SHA512": {
                    "type": "string",
                    "description": "SHA512 hash (128 characters)",
                },
                "Dropbox": {
                    "type": "string",
                    "description": "Dropbox content hash (64 characters)",
                },
            },
            "required": ["MD5", "SHA1", "SHA256", "SHA512", "Dropbox"],
        }


# Define Dropbox checksum
class DropboxChecksum:
    """
    Implementation of Dropbox's content-hash algorithm

    This is a special hash algorithm used by Dropbox for content addressing.
    The algorithm works as follows:
    1. Split the file into 4MB blocks
    2. Compute SHA256 hash for each block
    3. Concatenate all block hashes
    4. Compute a final SHA256 hash of the concatenated hashes
    """

    def __init__(self):
        self.block_hashes = []

    def update(self, data):
        # Compute SHA256 hash of each 4MB block
        sha256 = hashlib.sha256()
        sha256.update(data)
        self.block_hashes.append(sha256.digest())

    def digest(self):
        # Concatenate all block hashes and compute final SHA256 hash
        final_sha256 = hashlib.sha256()
        final_sha256.update(b"".join(self.block_hashes))
        return final_sha256.hexdigest()


# Define chunk size and threshold for mmap usage
CHUNK_SIZE = 4 * 1024 * 1024  # 4MB per chunk
MMAP_THRESHOLD = 16 * 1024 * 1024  # 16MB file size threshold


def compute_checksums(file_path):
    """
    Compute multiple checksums for a file in a single pass.

    This function computes MD5, SHA1, SHA256, SHA512, and Dropbox content hash
    for a file in a single pass through the data. It uses memory mapping
    for large files to improve performance.

    Args:
        file_path (str): Path to the file

    Returns:
        Dict[str, str]: Dictionary of checksums with algorithm as key
    """
    # Initialize checksum calculators
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    sha512 = hashlib.sha512()
    dropbox = DropboxChecksum()

    file_size = os.path.getsize(file_path)

    if file_size < MMAP_THRESHOLD:
        # For small files, read the entire file at once
        with open(file_path, "rb") as f:
            data = f.read()
            md5.update(data)
            sha1.update(data)
            sha256.update(data)
            sha512.update(data)
            dropbox.update(data)
    else:
        # For large files, use memory mapping and process chunks
        with open(file_path, "rb") as f:
            # Use mmap for memory-efficient processing of large files
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                for offset in range(0, file_size, CHUNK_SIZE):
                    chunk = mmapped_file[offset : offset + min(CHUNK_SIZE, file_size - offset)]
                    md5.update(chunk)
                    sha1.update(chunk)
                    sha256.update(chunk)
                    sha512.update(chunk)
                    dropbox.update(chunk)

    # Get digests for each checksum
    md5_hash = md5.hexdigest()
    sha1_hash = sha1.hexdigest()
    sha256_hash = sha256.hexdigest()
    sha512_hash = sha512.hexdigest()
    dropbox_hash = dropbox.digest()

    return {
        "MD5": md5_hash,
        "SHA1": sha1_hash,
        "SHA256": sha256_hash,
        "SHA512": sha512_hash,
        "Dropbox": dropbox_hash,
    }


# Unit tests
class TestChecksum(unittest.TestCase):
    def setUp(self):
        # Create test files
        with open("test_file_1.txt", "w", encoding="utf-8") as f:
            f.write("Hello World!")
        with open("test_file_2.txt", "wb") as f:
            f.write(b"A" * 4 * 1024 * 1024)  # 4MB of 'A'

    def tearDown(self):
        # Clean up test files
        os.remove("test_file_1.txt")
        os.remove("test_file_2.txt")

    def test_small_file_checksums(self):
        """Test small file operations"""
        # Compute the checksums and verify they match the expected format
        checksums = compute_checksums("test_file_1.txt")

        # Verify the checksums are the correct length and format
        self.assertEqual(len(checksums["MD5"]), 32)
        self.assertEqual(len(checksums["SHA1"]), 40)
        self.assertEqual(len(checksums["SHA256"]), 64)
        self.assertEqual(len(checksums["SHA512"]), 128)
        self.assertEqual(len(checksums["Dropbox"]), 64)

        # Verify they're valid hex strings
        for algo, checksum in checksums.items():
            self.assertTrue(
                all(c in "0123456789abcdefABCDEF" for c in checksum),
                f"Checksum for {algo} is not a valid hex string: {checksum}",
            )

    def test_large_file_checksums(self):
        """Test large file operations"""
        checksums = compute_checksums("test_file_2.txt")
        self.assertEqual(
            len(checksums["Dropbox"]),
            64,
        )  # SHA-256 hash length in hex is 64 characters
        self.assertEqual(
            len(checksums["SHA512"]),
            128,
        )  # SHA-512 hash length in hex is 128 characters

    def test_collector_initialization(self):
        """Test collector initialization"""
        collector = IndalekoSemanticChecksums()
        self.assertEqual(collector.get_collector_name(), "Semantic File Checksums")
        self.assertEqual(
            collector.get_collector_id(),
            uuid.UUID("de7ff1c7-2550-4cb3-9538-775f9464746e"),
        )

        # Test with custom name and provider_id
        custom_collector = IndalekoSemanticChecksums(
            name="Custom Checksum Collector",
            provider_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        )
        self.assertEqual(custom_collector._name, "Custom Checksum Collector")
        self.assertEqual(
            custom_collector._provider_id,
            uuid.UUID("11111111-1111-1111-1111-111111111111"),
        )


if __name__ == "__main__":
    unittest.main()

# Example usage
if __name__ == "__main__":
    test_file_path = "example_file.txt"  # Replace with your file path
    for algo, checksum in compute_checksums(test_file_path).items():
        ic(f"{algo}: {checksum}")
