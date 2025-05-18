"""NTFS storage activity data models for Indaleko.

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

from pathlib import Path

from pydantic import Field

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from activity.recorders.storage.data_models.storage_activity import (
    IndalekoStorageActivityDataModel,
)


# pylint: enable=wrong-import-position

class NTFSStorageActivityDataModel(IndalekoStorageActivityDataModel):
    """Defines the data model for NTFS storage activity."""

    LocalIdentifier: int = Field(
        ...,
        title="LocalIdentifier",
        description="""
            The identifier of the object in the NTFS storage system.
            This is used to track the object in the NTFS storage system.
            """,
    )

    ParentIdentifier: int = Field(
        ...,
        title="ParentIdentifier",
        description="""
            The identifier of the parent object in the NTFS storage system.
            This is used to track the parent object in the NTFS storage system.
            """,
    )

    FileName: str = Field(
        ...,
        title="FileName",
        description="The name of the file in the NTFS storage system."
    )

    class Config: # type: ignore  # noqa: PGH003
        """Pydantic configuration."""
        @staticmethod
        def get_example() -> dict[str, object]:
            """Get an example of the data model."""
            example = IndalekoStorageActivityDataModel.Config.json_schema_extra["example"]
            example.update({
                "LocalIdentifier": 123456789,
                "ParentIdentifier": 987654321,
                "FileName": "example.txt",
            })
            return example

        json_schema_extra = {  # noqa: RUF012
            "example": get_example(),
        }


def main() -> None:
    """Main function for testing."""
    NTFSStorageActivityDataModel.test_model_main() # type: ignore  # noqa: PGH003

if __name__ == "__main__":
    main()
