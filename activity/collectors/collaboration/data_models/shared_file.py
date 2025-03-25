"""
This module defines the base data model for shared files
in collaboration data collectors and recorders.

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
import os
import sys

from pydantic import Field, HttpUrl
from typing import Optional

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.collaboration.data_models.collaboration_data_model \
    import BaseCollaborationDataModel

# pylint: enable=wrong-import-position


class SharedFileData(BaseCollaborationDataModel):
    filename: str = Field(..., description="The name of the file shared")
    url: HttpUrl = Field(..., description="The URL to access the file")
    size_bytes: Optional[int] = Field(None, description="Size of the file in bytes")
    content_type: Optional[str] = Field(None, description="MIME type of the file")

    class Config:
        @staticmethod
        def generate_example():
            """Generate an example for the data model"""
            example = BaseCollaborationDataModel.Config.json_schema_extra["example"]
            example["filename"] = "example.pdf"
            example["url"] = "https://cdn.discordapp.com/..."
            example["size_bytes"] = 1048576
            example["content_type"] = "application/pdf"
            return example

        json_schema_extra = {
            "example": generate_example()
        }

def main():
    """This allows testing the data model"""
    ic(SharedFileData.Config.json_schema_extra)
    SharedFileData.test_model_main()


if __name__ == "__main__":
    main()
