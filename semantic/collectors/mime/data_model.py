"""
This module defines the data model for the MIME type data collector.

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
import os
import sys
from uuid import UUID, uuid4

# third-party imports
from pydantic import Field, field_validator

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Indaleko imports
# pylint: disable=wrong-import-position
from semantic.data_models.base_data_model import BaseSemanticDataModel

# pylint: enable=wrong-import-position


class SemanticMimeDataModel(BaseSemanticDataModel):
    """
    This class defines the data model for file MIME type detection.

    It includes:
    - Content-based detected MIME type (e.g., "application/pdf", "image/jpeg")
    - Detection confidence level
    - Extension-based MIME type (for comparison)
    - Optional additional metadata (e.g., for specialized formats)
    """

    mime_data_id: UUID = Field(
        default_factory=uuid4,
        description="The unique identifier for the MIME type data record.",
    )

    mime_type: str = Field(
        ...,
        description="The detected MIME type based on content analysis.",
    )

    mime_type_from_extension: str = Field(
        None,
        description="The MIME type based on file extension (if available).",
    )

    confidence: float = Field(
        ...,
        description="Confidence level in the detected MIME type (0.0-1.0).",
        ge=0.0,
        le=1.0,
    )

    encoding: str = Field(
        None,
        description="Character encoding if detected (for text files).",
    )

    additional_metadata: dict = Field(
        default_factory=dict,
        description="Additional format-specific metadata.",
    )

    @classmethod
    @field_validator("mime_data_id")
    def validate_mime_data_id(cls, value):
        if not isinstance(value, UUID):
            raise ValueError("MIME data ID must be a UUID")
        return value

    @classmethod
    @field_validator("mime_type")
    def validate_mime_type(cls, value):
        if not value or not isinstance(value, str):
            raise ValueError("MIME type must be a non-empty string")
        # Basic validation of MIME type format
        if "/" not in value:
            raise ValueError("MIME type must be in format 'type/subtype'")
        return value

    @classmethod
    @field_validator("confidence")
    def validate_confidence(cls, value):
        if not 0.0 <= value <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return value

    @classmethod
    class Config:

        @staticmethod
        def schema_extra() -> dict:
            base_example = BaseSemanticDataModel.Config.json_schema_extra["example"]
            return {
                "example": {
                    **base_example,
                    "mime_data_id": "6a4c1af0-6d3f-4a2e-b8aa-2cef4dcb643c",
                    "mime_type": "application/pdf",
                    "mime_type_from_extension": "application/pdf",
                    "confidence": 0.95,
                    "encoding": None,
                    "additional_metadata": {"version": "1.7", "is_encrypted": False},
                },
            }

        json_schema_extra = {
            "example": {
                **BaseSemanticDataModel.Config.json_schema_extra["example"],
                "mime_data_id": "6a4c1af0-6d3f-4a2e-b8aa-2cef4dcb643c",
                "mime_type": "application/pdf",
                "mime_type_from_extension": "application/pdf",
                "confidence": 0.95,
                "encoding": None,
                "additional_metadata": {"version": "1.7", "is_encrypted": False},
            },
        }


def main():
    """Test code for the MIME type data model"""
    SemanticMimeDataModel.test_model_main()


if __name__ == "__main__":
    main()
