"""
This implements a semantic extractor for detecting MIME types from file content.

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
import logging
import mimetypes
import os
import sys
import unittest
import uuid

from datetime import UTC, datetime

# third-party imports
from typing import Any

import magic

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Indaleko imports
# pylint: disable=wrong-import-position
import semantic.recorders.mime.characteristics as MimeDataCharacteristics

from data_models.i_object import IndalekoObjectDataModel
from data_models.i_uuid import IndalekoUUIDDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from semantic.characteristics import SemanticDataCharacteristics
from semantic.collectors.mime.data_model import SemanticMimeDataModel
from semantic.collectors.semantic_collector import SemanticCollector


# pylint: enable=wrong-import-position


class IndalekoSemanticMimeType(SemanticCollector):
    """This class implements a semantic collector for detecting file MIME types from content."""

    def __init__(self, **kwargs) -> None:
        """Initialize the semantic MIME type detector."""
        self._name = "Content-Based MIME Type Detector"
        self._provider_id = uuid.UUID("8d7c1e9f-6a3b-4f7d-9e2c-5a1b8d6f3c4e")
        self._mime_cache = {}  # Cache of detected MIME types by file_path
        self._object_cache = {}  # Cache of objects by their identifiers
        self._mime_magic = magic.Magic(mime=True)

        # Initialize mimetypes database
        mimetypes.init()

        # Process any additional arguments
        for key, value in kwargs.items():
            setattr(self, f"_{key}", value)

        # Make sure we have a name and provider_id
        if not hasattr(self, "_name") and not hasattr(self, "_provider_id"):
            raise ValueError(
                "The name or provider_id must be provided for the semantic MIME type detector.",
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

    def detect_mime_type(self, file_path: str) -> dict[str, Any]:
        """
        Detect the MIME type of a file based on its content.

        Args:
            file_path (str): Path to the file

        Returns:
            Dict[str, Any]: Dictionary with MIME type information
        """
        # Check if we already have the MIME type cached
        if file_path in self._mime_cache:
            return self._mime_cache[file_path]

        # Get file extension and guess MIME type from it
        ext_mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

        # Use libmagic to detect MIME type from content
        try:
            content_mime_type = self._mime_magic.from_file(file_path)
            confidence = 0.9  # Default high confidence for libmagic
        except Exception as e:
            logging.warning(f"Error detecting MIME type for {file_path}: {e}")
            content_mime_type = "application/octet-stream"
            confidence = 0.5

        # Check for text files and detect encoding
        encoding = None
        additional_metadata = {}

        # For text files, try to detect encoding
        if content_mime_type.startswith("text/"):
            try:
                import chardet

                with open(file_path, "rb") as f:
                    raw_data = f.read(4096)  # Read a chunk to detect encoding
                    result = chardet.detect(raw_data)
                    encoding = result["encoding"]
                    additional_metadata["charset_confidence"] = result["confidence"]
            except ImportError:
                logging.info(
                    "chardet module not available, skipping encoding detection",
                )
            except Exception as e:
                logging.warning(f"Error detecting encoding for {file_path}: {e}")

        # For specific file types, add additional metadata
        if content_mime_type == "application/pdf":
            try:
                # Try to extract PDF version
                with open(file_path, "rb") as f:
                    header = f.read(1024).decode("latin-1", errors="ignore")
                    if "%PDF-" in header:
                        version = header.split("%PDF-")[1].split("\n")[0].strip()
                        additional_metadata["version"] = version
            except Exception as e:
                logging.warning(f"Error extracting PDF metadata for {file_path}: {e}")

        # Store category information
        if content_mime_type.startswith("text/"):
            additional_metadata["category"] = "text"
        elif content_mime_type.startswith("image/"):
            additional_metadata["category"] = "image"
        elif content_mime_type.startswith("audio/"):
            additional_metadata["category"] = "audio"
        elif content_mime_type.startswith("video/"):
            additional_metadata["category"] = "video"
        elif content_mime_type.startswith("application/"):
            additional_metadata["category"] = "application"

        # Check if extension and content MIME types match
        if ext_mime_type == content_mime_type:
            # Increase confidence if extension matches content type
            confidence = min(confidence + 0.05, 1.0)
        else:
            # Slightly decrease confidence if they don't match
            confidence = max(confidence - 0.1, 0.5)

        result = {
            "mime_type": content_mime_type,
            "mime_type_from_extension": ext_mime_type,
            "confidence": confidence,
            "encoding": encoding,
            "additional_metadata": additional_metadata,
        }

        # Cache the result
        self._mime_cache[file_path] = result

        return result

    def create_mime_record(
        self,
        file_path: str,
        object_id: uuid.UUID,
    ) -> SemanticMimeDataModel:
        """
        Create a MIME type record for a file.

        Args:
            file_path (str): Path to the file
            object_id (uuid.UUID): UUID of the object

        Returns:
            SemanticMimeDataModel: MIME type data model
        """
        # Detect MIME type
        mime_data = self.detect_mime_type(file_path)

        # Create semantic attributes
        semantic_attributes = []

        # Add primary MIME type attribute
        semantic_attributes.append(
            IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=MimeDataCharacteristics.SEMANTIC_MIME_TYPE,
                    Label="MIME Type",
                ),
                Data=mime_data["mime_type"],
            ),
        )

        # Add extension-based MIME type attribute
        if mime_data["mime_type_from_extension"]:
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=MimeDataCharacteristics.SEMANTIC_MIME_TYPE_FROM_EXTENSION,
                        Label="Extension MIME Type",
                    ),
                    Data=mime_data["mime_type_from_extension"],
                ),
            )

        # Add confidence attribute
        semantic_attributes.append(
            IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=MimeDataCharacteristics.SEMANTIC_MIME_CONFIDENCE,
                    Label="Detection Confidence",
                ),
                Data=str(mime_data["confidence"]),
            ),
        )

        # Add encoding attribute if available
        if mime_data["encoding"]:
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=MimeDataCharacteristics.SEMANTIC_MIME_ENCODING,
                        Label="Text Encoding",
                    ),
                    Data=mime_data["encoding"],
                ),
            )

        # Add category-specific attributes
        category = mime_data["additional_metadata"].get("category")
        if category == "text":
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=MimeDataCharacteristics.SEMANTIC_MIME_IS_TEXT,
                        Label="Is Text",
                    ),
                    Data="true",
                ),
            )
        elif category == "image":
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=MimeDataCharacteristics.SEMANTIC_MIME_IS_IMAGE,
                        Label="Is Image",
                    ),
                    Data="true",
                ),
            )
        elif category == "audio":
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=MimeDataCharacteristics.SEMANTIC_MIME_IS_AUDIO,
                        Label="Is Audio",
                    ),
                    Data="true",
                ),
            )
        elif category == "video":
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=MimeDataCharacteristics.SEMANTIC_MIME_IS_VIDEO,
                        Label="Is Video",
                    ),
                    Data="true",
                ),
            )
        elif category == "application":
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=MimeDataCharacteristics.SEMANTIC_MIME_IS_APPLICATION,
                        Label="Is Application",
                    ),
                    Data="true",
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

        # Create MIME data model
        return SemanticMimeDataModel(
            Record=record,
            Timestamp=datetime.now(UTC),
            ObjectIdentifier=object_id,
            RelatedObjects=[object_id],
            SemanticAttributes=semantic_attributes,
            mime_data_id=uuid.uuid4(),
            mime_type=mime_data["mime_type"],
            mime_type_from_extension=mime_data["mime_type_from_extension"],
            confidence=mime_data["confidence"],
            encoding=mime_data["encoding"],
            additional_metadata=mime_data["additional_metadata"],
        )

    def get_mime_type_for_file(
        self,
        file_path: str,
        object_id: str | uuid.UUID,
    ) -> dict[str, Any]:
        """
        Get MIME type for a file and create a semantic data record.

        Args:
            file_path (str): Path to the file
            object_id (Union[str, uuid.UUID]): UUID of the object

        Returns:
            Dict[str, Any]: Dictionary containing the MIME type and metadata
        """
        # Convert string UUID to UUID object if needed
        if isinstance(object_id, str):
            object_id = uuid.UUID(object_id)

        # Create MIME type record
        mime_model = self.create_mime_record(file_path, object_id)

        # Return as dictionary
        return mime_model.model_dump()

    def get_collector_characteristics(self) -> list[SemanticDataCharacteristics]:
        """Get the characteristics of the collector."""
        return [
            SemanticDataCharacteristics.SEMANTIC_DATA_FILE_TYPE,
            MimeDataCharacteristics.SEMANTIC_MIME_TYPE,
            MimeDataCharacteristics.SEMANTIC_MIME_TYPE_FROM_EXTENSION,
            MimeDataCharacteristics.SEMANTIC_MIME_CONFIDENCE,
            MimeDataCharacteristics.SEMANTIC_MIME_ENCODING,
            MimeDataCharacteristics.SEMANTIC_MIME_IS_TEXT,
            MimeDataCharacteristics.SEMANTIC_MIME_IS_IMAGE,
            MimeDataCharacteristics.SEMANTIC_MIME_IS_AUDIO,
            MimeDataCharacteristics.SEMANTIC_MIME_IS_VIDEO,
            MimeDataCharacteristics.SEMANTIC_MIME_IS_APPLICATION,
            MimeDataCharacteristics.SEMANTIC_MIME_IS_CONTAINER,
            MimeDataCharacteristics.SEMANTIC_MIME_IS_COMPRESSED,
            MimeDataCharacteristics.SEMANTIC_MIME_IS_ENCRYPTED,
        ]

    def get_collector_name(self) -> str:
        """Get the name of the collector."""
        return self._name

    def get_collector_id(self) -> uuid.UUID:
        """Get the ID of the collector."""
        return self._provider_id

    def retrieve_data(self, data_id: str) -> dict:
        """
        Retrieve semantic MIME type data for a specific identifier.

        Args:
            data_id (str): The identifier of the data to retrieve

        Returns:
            Dict: The semantic MIME type data
        """
        # TODO: Implement retrieving from a persistent store
        # For now, just return an error indicating this needs to be implemented
        raise NotImplementedError(
            "Retrieving data by ID is not yet implemented. "
            "Use get_mime_type_for_file() to detect MIME type for a specific file.",
        )

    def get_collector_description(self) -> str:
        """Get the description of the collector."""
        return """This collector detects MIME types of files based on content analysis:
        - Uses libmagic for content-based detection
        - Compares against extension-based MIME type
        - Provides confidence levels for detections
        - Detects encoding for text files
        - Classifies files into categories (text, image, audio, video, application)
        - Extracts format-specific metadata where possible"""

    def get_json_schema(self) -> dict:
        """Get the JSON schema for the collector."""
        return {
            "type": "object",
            "properties": {
                "mime_type": {
                    "type": "string",
                    "description": "Content-based MIME type",
                },
                "mime_type_from_extension": {
                    "type": "string",
                    "description": "Extension-based MIME type",
                },
                "confidence": {
                    "type": "number",
                    "description": "Detection confidence (0.0-1.0)",
                },
                "encoding": {
                    "type": "string",
                    "description": "Character encoding (for text files)",
                },
                "additional_metadata": {
                    "type": "object",
                    "description": "Format-specific metadata",
                },
            },
            "required": ["mime_type", "confidence"],
        }


# Unit tests
class TestMimeTypeDetector(unittest.TestCase):
    def setUp(self) -> None:
        # Create test files of different types
        with open("test_text.txt", "w", encoding="utf-8") as f:
            f.write("This is a plain text file for testing MIME type detection.")

        with open("test_html.html", "w", encoding="utf-8") as f:
            f.write(
                "<html><head><title>Test</title></head><body><h1>Test HTML</h1></body></html>",
            )

        # Create a small binary file
        with open("test_binary.bin", "wb") as f:
            f.write(b"\x00\x01\x02\x03\x04")

    def tearDown(self) -> None:
        # Clean up test files
        for filename in ["test_text.txt", "test_html.html", "test_binary.bin"]:
            if os.path.exists(filename):
                os.remove(filename)

    def test_mime_detection(self) -> None:
        """Test MIME type detection."""
        detector = IndalekoSemanticMimeType()

        # Test text file
        text_mime = detector.detect_mime_type("test_text.txt")
        assert text_mime["mime_type"].startswith("text/")
        assert text_mime["mime_type_from_extension"] == "text/plain"

        # Test HTML file
        html_mime = detector.detect_mime_type("test_html.html")
        assert html_mime["mime_type"].startswith("text/html") or html_mime["mime_type"] == "text/plain"  # Some magic implementations detect HTML as plain text
        assert html_mime["mime_type_from_extension"] == "text/html"

        # Test binary file
        binary_mime = detector.detect_mime_type("test_binary.bin")
        assert binary_mime["mime_type"].startswith("application/") or binary_mime["mime_type"] == "text/plain"  # Small binary files might be detected as text

    def test_collector_initialization(self) -> None:
        """Test collector initialization."""
        detector = IndalekoSemanticMimeType()
        assert detector.get_collector_name() == "Content-Based MIME Type Detector"
        assert detector.get_collector_id() == uuid.UUID("8d7c1e9f-6a3b-4f7d-9e2c-5a1b8d6f3c4e")

        # Test with custom name and provider_id
        custom_detector = IndalekoSemanticMimeType(
            name="Custom MIME Detector",
            provider_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        )
        assert custom_detector._name == "Custom MIME Detector"
        assert custom_detector._provider_id == uuid.UUID("22222222-2222-2222-2222-222222222222")


if __name__ == "__main__":
    unittest.main()

# Example usage
if __name__ == "__main__":
    test_file_path = "example_file.txt"  # Replace with your file path
    detector = IndalekoSemanticMimeType()
    mime_info = detector.detect_mime_type(test_file_path)
    ic(f"MIME Type: {mime_info['mime_type']}")
    ic(f"Confidence: {mime_info['confidence']}")
    if mime_info["encoding"]:
        ic(f"Encoding: {mime_info['encoding']}")
