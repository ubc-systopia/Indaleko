"""
This module defines the data model for the indaleko record type.

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
from datetime import UTC, datetime
from pathlib import Path
from textwrap import dedent

from pydantic import AwareDatetime, Field, field_validator

# > from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from utils.misc.data_management import encode_binary_data


# pylint: enable=wrong-import-position


class IndalekoRecordDataModel(IndalekoBaseModel):
    """This class defines the Record data model for Indaleko."""

    SourceIdentifier: IndalekoSourceIdentifierDataModel = Field(
        ...,
        title="SourceIdentifier",
        description="The source identifier for the record (e.g., for provenance).",
    )

    Timestamp: AwareDatetime = Field(
        datetime.now(UTC),
        title="Timestamp",
        description="Record creation timestamp.",
    )

    Data: str = Field(
        default=encode_binary_data(b""),
        title="Data",
        description=dedent(
            "The raw (uninterpreted) data from the original source, "
            "encoded as a UUENCODED binary string.\n"
            "This field is opaque and must be treated as a single blob.\n"
            "Do not index, parse, or reference any sub-fields "
            "within Data (e.g., Record.Data.*).\n"
            "Use dedicated model fields or metadata instead.",
        ),
    )

    @field_validator("Timestamp", mode="before")
    @classmethod
    def ensure_timezone(cls, value: datetime) -> datetime:
        """
        Ensure that the timestamp is timezone-aware.
        """
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value

    class Config:
        """Sample configuration data for the data model."""

        json_schema_extra = {
            "example": {
                "SourceIdentifier": {
                    "Identifier": "429f1f3c-7a21-463f-b7aa-cd731bb202b1",
                    "Version": "1.0",
                },
                "Timestamp": "2024-07-30T23:38:48.319654+00:00",
                "Data": "xQL6xQL3eyJzdF9hdGltZSI6IDE2OTMyMjM0NTYuMzMzNDI4MSwgInN0X2F"
                "0aW1lX25zIjogMTY5MzIyMzQ1NjMzMzQyODEwMCwgInN0X2JpcnRodGltZSI6IDE2OD"
                "U4OTEyMjEuNTU5MTkxNywgInN0X2JpcnRodGltZV9ucyI6IDE2ODU4OTEyMjE1NTkxOT"
                "E3MDAsICJzdF9jdGltZSI6IDE2ODU4OTEyMjEuNTU5MTkxNywgInN0X2N0aW1lX25zIj"
                "ogMTY4NTg5MTIyMTU1OTE5MTcwMCwgInN0X2RldiI6IDI3NTYzNDcwOTQ5NTU2NDk1OT"
                "ksICJzdF9maWxlX2F0dHJpYnV0ZXMiOiAzMiwgInN0X2dpZCI6IDAsICJzdF9pbm8iOi"
                "AxMTI1ODk5OTEwMTE5ODMyLCAic3RfbW9kZSI6IDMzMjc5LCAic3RfbXRpbWUiOiAxNj"
                "g1ODkxMjIxLjU1OTcxNTcsICJzdF9tdGltZV9ucyI6IDE2ODU4OTEyMjE1NTk3MTU3MD"
                "AsICJzdF9ubGluayI6IDEsICJzdF9yZXBhcnNlX3RhZyI6IDAsICJzdF9zaXplIjogMT"
                "QxMDEyMCwgInN0X3VpZCI6IDAsICJOYW1lIjogInJ1ZnVzLTQuMS5leGUiLCAiUGF0aC"
                "I6ICJkOlxcZGlzdCIsICJVUkkiOiAiXFxcXD9cXFZvbHVtZXszMzk3ZDk3Yi0yY2E1LT"
                "ExZWQtYjJmYy1iNDBlZGU5YTVhM2N9XFxkaXN0XFxydWZ1cy00LjEuZXhlIiwgIkluZG"
                "V4ZXIiOiAiMDc5M2I0ZDUtZTU0OS00Y2I2LTgxNzctMDIwYTczOGI2NmI3IiwgIlZvbH"
                "VtZSBHVUlEIjogIjMzOTdkOTdiLTJjYTUtMTFlZC1iMmZjLWI0MGVkZTlhNWEzYyIsIC"
                "JPYmplY3RJZGVudGlmaWVyIjogIjJjNzNkNmU1LWVhYmEtNGYwYS1hY2YzLWUwMmM1Mj"
                "lmMDk3YSJ9",
            },
        }


def main():
    """This allows testing the data model"""
    IndalekoRecordDataModel.test_model_main()


if __name__ == "__main__":
    main()
