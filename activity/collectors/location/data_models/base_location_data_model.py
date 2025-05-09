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

from pydantic import Field

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.data_model.activity import IndalekoActivityDataModel
from data_models.location_data_model import LocationDataModel

# pylint: enable=wrong-import-position


class BaseLocationDataModel(IndalekoActivityDataModel):
    Location: LocationDataModel = Field(
        ...,
        title="Location",
        description="The location data.",
    )

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
    BaseLocationDataModel.test_model_main()


if __name__ == "__main__":
    main()
