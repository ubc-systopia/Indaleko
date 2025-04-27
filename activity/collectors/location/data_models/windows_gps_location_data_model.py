"""
This module defines the data model for the Windows GPS based location
activity data provider.

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

from pydantic import AwareDatetime, Field, field_validator


# from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.location.data_models.windows_gps_satellite_data import (
    WindowsGPSLocationSatelliteDataModel,
)
from data_models.location_data_model import BaseLocationDataModel


# pylint: enable=wrong-import-position


class WindowsGPSLocationDataModel(BaseLocationDataModel):
    """This is the data model for the Windows GPS location service."""

    altitude_accuracy: float | None = Field(
        None,
        description="Accuracy of altitude measurement",
    )
    is_remote_source: bool | None = Field(
        None,
        description="Is the source remote?",
    )
    point: str | None = Field(
        None,
        description="A string representation of the point data",
    )
    position_source: str | None = Field(
        None,
        description="The source of the position data",
    )
    position_source_timestamp: AwareDatetime | None = Field(
        None,
        description="Timestamp of the position source",
    )
    satellite_data: WindowsGPSLocationSatelliteDataModel | None = Field(
        None,
        description="Details about satellite data used for the position",
    )
    civic_address: str | None = Field(
        None,
        description="Civic address for the location, if available",
    )
    venue_data: str | None = Field(
        None,
        description="Details about the venue data for the location, if available",
    )

    @field_validator("position_source_timestamp", mode="before")
    def ensure_timezone(cls, value: datetime):
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        assert isinstance(value, datetime)
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value

    class Config:
        @staticmethod
        def generate_example():
            """Generate an example for the data model"""
            example = BaseLocationDataModel.Config.json_schema_extra["example"]
            example["altitude_accuracy"] = 2.0
            example["is_remote_source"] = False
            example["point"] = "POINT(49.2827 -123.1207)"
            example["position_source"] = "GPS"
            example["position_source_timestamp"] = "2023-09-21T10:31:00Z"
            example["satellite_data"] = WindowsGPSLocationSatelliteDataModel.Config.json_schema_extra["example"]
            example["civic_address"] = None
            example["venue_data"] = None
            return example

        json_schema_extra = {
            "example": generate_example(),
        }


def main():
    """This allows testing the data model"""
    WindowsGPSLocationDataModel.test_model_main()


if __name__ == "__main__":
    main()
