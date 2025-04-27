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

from pydantic import BaseModel, Field


# from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
# pylint: enable=wrong-import-position


class WindowsGPSLocationSatelliteDataModel(BaseModel):
    geometric_dilution_of_precision: float | None = Field(
        None,
        description="Geometric dilution of precision",
    )
    horizontal_dilution_of_precision: float | None = Field(
        None,
        description="Horizontal dilution of precision",
    )
    vertical_dilution_of_precision: float | None = Field(
        None,
        description="Vertical dilution of precision",
    )
    position_dilution_of_precision: float | None = Field(
        None,
        description="Position dilution of precision",
    )
    time_dilution_of_precision: float | None = Field(
        None,
        description="Time dilution of precision",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "geometric_dilution_of_precision": 1.0,
                "horizontal_dilution_of_precision": 1.0,
                "vertical_dilution_of_precision": 1.0,
                "position_dilution_of_precision": 1.0,
                "time_dilution_of_precision": 1.0,
            },
        }


def main():
    """This allows testing the data model."""
    WindowsGPSLocationSatelliteDataModel.test_model_main()


if __name__ == "__main__":
    main()
