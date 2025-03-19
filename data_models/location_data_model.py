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

from typing import Optional
from datetime import datetime, timezone

from pydantic import Field, field_validator, AwareDatetime

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.data_model.activity import IndalekoActivityDataModel
from data_models.base import IndalekoBaseModel
# pylint: enable=wrong-import-position


class LocationDataModel(IndalekoBaseModel):
    latitude: float = Field(..., description="Latitude coordinate of the location")
    longitude: float = Field(..., description="Longitude coordinate of the location")
    altitude: Optional[float] = Field(
        None, description="Altitude of the location, if available"
    )
    accuracy: Optional[float] = Field(None, description="Accuracy of the location data")
    heading: Optional[float] = Field(None, description="Heading/direction of movement")
    speed: Optional[float] = Field(None, description="Speed of movement")
    timestamp: AwareDatetime = Field(
        ..., description="Timestamp when the location was recorded"
    )
    source: str = Field(
        ..., description="Source of the location data, e.g., 'GPS', 'IP', etc."
    )

    class Config:
        '''Sample configuration for the data model'''
        json_schema_extra = {
            "example": {
                "latitude": 49.2827,
                "longitude": -123.1207,
                "altitude": 70.0,
                "accuracy": 5.0,
                "heading": 270.0,
                "speed": 10.5,
                "timestamp": "2023-09-21T10:30:00Z",
                "source": "GPS",
            }
        }


class BaseLocationDataModel(IndalekoActivityDataModel):

    Location: LocationDataModel = Field(
        ...,
        title="Location",
        description="The location data."
    )

    @classmethod
    @field_validator("timestamp", mode="before")
    def ensure_timezone(cls, value: datetime):
        """Ensure that the timestamp is in explicit UTC timezone"""
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value

    class Config:

        @staticmethod
        def generate_example():
            """Generate an example for the data model"""
            example = IndalekoActivityDataModel.Config.json_schema_extra["example"]
            example["Location"] = LocationDataModel.Config.json_schema_extra["example"]
            return example

        json_schema_extra = {
            "example": generate_example(),
        }


def main():
    """This allows testing the data model"""
    LocationDataModel.test_model_main()
    BaseLocationDataModel.test_model_main()


if __name__ == "__main__":
    main()
