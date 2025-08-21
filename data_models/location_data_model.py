"""
This module defines the data model for location services.

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
from typing import ClassVar

from pydantic import AwareDatetime, Field, field_validator


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from activity.data_model.activity import IndalekoActivityDataModel
from data_models.base import IndalekoBaseModel


# pylint: enable=wrong-import-position


class LocationDataModel(IndalekoBaseModel):
    """This is the data model for location services."""

    latitude: float = Field(..., description="Latitude coordinate of the location")
    longitude: float = Field(..., description="Longitude coordinate of the location")
    altitude: float | None = Field(
        None,
        description="Altitude of the location, if available",
    )
    accuracy: float | None = Field(None, description="Accuracy of the location data")
    heading: float | None = Field(None, description="Heading/direction of movement")
    speed: float | None = Field(None, description="Speed of movement")
    timestamp: AwareDatetime = Field(
        ...,
        description="Timestamp when the location was recorded",
    )
    source: str = Field(
        ...,
        description="Source of the location data, e.g., 'GPS', 'IP', etc.",
    )

    class Config:
        """Sample configuration for the data model."""

        json_schema_extra = {  # noqa: RUF012
            "example": {
                "latitude": 49.2827,
                "longitude": -123.1207,
                "altitude": 70.0,
                "accuracy": 5.0,
                "heading": 270.0,
                "speed": 10.5,
                "timestamp": "2023-09-21T10:30:00Z",
                "source": "GPS",
            },
        }


class BaseLocationDataModel(IndalekoActivityDataModel):
    """This is the base data model for location services."""

    Location: LocationDataModel = Field(
        ...,
        title="Location",
        description="The location data.",
    )

    @classmethod
    @field_validator("timestamp", mode="before")
    def ensure_timezone(cls, value: datetime) -> datetime:
        """Ensure that the timestamp is in explicit UTC timezone."""
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value

    class Config:  # type: ignore  # noqa: PGH003
        """Sample configuration for the data model."""

        frozen = True  # Make the model immutable

        @staticmethod
        def generate_example() -> dict:
            """Generate an example for the data model."""
            # Return a new dict each time to avoid mutation issues
            example = dict(IndalekoActivityDataModel.Config.json_schema_extra["example"])
            example["Location"] = dict(LocationDataModel.Config.json_schema_extra["example"])
            return example

        json_schema_extra: ClassVar = {
            "example": generate_example(),
        }


def main() -> None:
    """This allows testing the data model."""
    LocationDataModel.test_model_main()
    BaseLocationDataModel.test_model_main()


if __name__ == "__main__":
    main()
