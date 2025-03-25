"""
This module defines the data model for the checksum data collector.

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


class SemanticChecksumDataModel(BaseSemanticDataModel):
    """
    This class defines the data model for the file checksum semantic data.
    """

    checksum_data_id: UUID = Field(
        default_factory=uuid4,
        description="The unique identifier for the checksum data record.",
    )
    md5_checksum: str = Field(..., description="The MD5 checksum for the file.")
    sha1_checksum: str = Field(..., description="The SHA1 checksum for the file.")
    sha256_checksum: str = Field(..., description="The SHA256 checksum for the file.")
    dropbox_checksum: str = Field(..., description="The Dropbox checksum for the file.")

    @classmethod
    @field_validator("checksum_data_id")
    def validate_checksum_data_id(cls, value):
        if not isinstance(value, UUID):
            raise ValueError("Checksum data ID must be a UUID")
        return value

    @classmethod
    @field_validator("md5_checksum")
    def validate_md5_checksum(cls, value):
        if len(value) != 32:
            raise ValueError("MD5 checksum must be 32 characters long")
        if not all(c in "0123456789abcdefABCDEF" for c in value):
            raise ValueError("MD5 checksum must be a valid hexadecimal string")
        return value

    @classmethod
    @field_validator("sha1_checksum")
    def validate_sha1_checksum(cls, value):
        if len(value) != 40:
            raise ValueError("SHA1 checksum must be 40 characters long")
        if not all(c in "0123456789abcdefABCDEF" for c in value):
            raise ValueError("SHA1 checksum must be a valid hexadecimal string")
        return value

    @classmethod
    @field_validator("sha256_checksum")
    def validate_sha256_checksum(cls, value):
        if len(value) != 64:
            raise ValueError("SHA256 checksum must be 64 characters long")
        if not all(c in "0123456789abcdefABCDEF" for c in value):
            raise ValueError("SHA256 checksum must be a valid hexadecimal string")
        return value

    @classmethod
    @field_validator("dropbox_checksum")
    def validate_dropbox_checksum(cls, value):
        if len(value) != 64:
            raise ValueError("Dropbox checksum must be 64 characters long")
        if not all(c in "0123456789abcdefABCDEF" for c in value):
            raise ValueError("Dropbox checksum must be a valid hexadecimal string")
        return value

    @classmethod
    class Config:

        @staticmethod
        def schema_extra() -> dict:
            base_example = BaseSemanticDataModel.Config.json_schema_extra["example"]
            return {
                "example": {
                    **base_example,
                    "checksum_data_id": "123e4567-e89b-12d3-a456-426614174000",
                    "md5_checksum": "d41d8cd98f00b204e9800998ecf8427e",
                    "sha1_checksum": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
                    "sha256_checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "dropbox_checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                }
            }

        json_schema_extra = {
            "example": {
                **BaseSemanticDataModel.Config.json_schema_extra["example"],
                "checksum_data_id": "123e4567-e89b-12d3-a456-426614174000",
                "md5_checksum": "d41d8cd98f00b204e9800998ecf8427e",
                "sha1_checksum": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
                "sha256_checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "dropbox_checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            }
        }


def main():
    """Test code for the checksum data model"""
    SemanticChecksumDataModel.test_model_main()


if __name__ == "__main__":
    main()
