"""
Example of a semantic extractor using the new registration service.

This file demonstrates how to create a MIME type extractor that
registers with the semantic registration service.

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
import logging
import os
import sys
import uuid

from typing import Any


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.record import IndalekoRecordDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from semantic.collectors.mime.mime_collector import IndalekoSemanticMimeType
from semantic.registration_service import IndalekoSemanticRegistrationService


# pylint: enable=wrong-import-position


def register_mime_extractor():
    """Register the MIME type extractor with the semantic registration service."""
    # Create a source identifier
    source_id = IndalekoSourceIdentifierDataModel(
        Identifier=uuid.UUID("12345678-1234-5678-1234-567812345678"),
        Version="1.0.0",
        Description="MIME Type Extractor",
    )

    # Create a record
    record = IndalekoRecordDataModel(
        SourceIdentifier=source_id,
        Timestamp=datetime.datetime.now(datetime.UTC),
        Attributes={},
        Data="",
    )

    # Create the registration service
    service = IndalekoSemanticRegistrationService()

    # Register the extractor
    extractor_data, collection = service.register_semantic_extractor(
        Identifier="12345678-1234-5678-1234-567812345678",
        Name="MIME Type Extractor",
        Description="Extracts MIME type information from files",
        Version="1.0.0",
        Record=record,
        SupportedMimeTypes=["*/*"],  # Supports all MIME types
        ResourceIntensity="low",
        ProcessingPriority=80,  # High priority since it's fast
        ExtractedAttributes=["mime:type", "mime:encoding", "mime:charset"],
    )

    return extractor_data, collection


def collect_mime_data(file_path: str) -> dict[str, Any]:
    """
    Collect MIME type data for a file.

    Args:
        file_path: Path to the file

    Returns:
        MIME type data
    """
    collector = IndalekoSemanticMimeType()
    return collector.process_file(file_path)


def main() -> None:
    """Example of using the semantic registration service."""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("MimeExtractorExample")

    # Check if the MIME type extractor is already registered
    service = IndalekoSemanticRegistrationService()
    extractor = service.lookup_provider_by_identifier(
        "12345678-1234-5678-1234-567812345678",
    )

    if extractor is None:
        logger.info("Registering MIME type extractor...")
        extractor_data, collection = register_mime_extractor()
        logger.info(f"Registered with collection: {collection.name}")
    else:
        logger.info("MIME type extractor already registered")

    # List supported MIME types
    mime_types = service.get_supported_mime_types()
    logger.info(f"Supported MIME types: {mime_types}")

    # Find extractors for a MIME type
    jpeg_extractors = service.find_extractors_for_mime_type("image/jpeg")
    logger.info(f"Found {len(jpeg_extractors)} extractors for image/jpeg")

    # Test the collector on a sample file if provided
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            logger.info(f"Collecting MIME data for {file_path}")
            mime_data = collect_mime_data(file_path)
            logger.info(f"MIME type: {mime_data.get('mime_type')}")
            logger.info(f"MIME encoding: {mime_data.get('mime_encoding')}")
        else:
            logger.error(f"File not found: {file_path}")


if __name__ == "__main__":
    main()
