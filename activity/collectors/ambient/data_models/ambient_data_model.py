"""
Indaleko Ambient Data Model.

This module defines the base data model for ambient data collectors
and recorders.

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
from activity.data_model.activity import IndalekoActivityDataModel


# pylint: enable=wrong-import-position


class BaseAmbientConditionDataModel(IndalekoActivityDataModel):
    """This is the base data model for ambient condition data."""

    source: str = Field(
        ...,
        description="Source of the location data, e.g., 'Sensor', 'Music App', etc.",
    )

    class Config:
        """Sample configuration for the data model."""

        @staticmethod
        def generate_example() -> str:
            """Generate an example for the data model."""
            example = IndalekoActivityDataModel.Config.json_schema_extra["example"]
            example["source"] = "Spotify"
            return example

        json_schema_extra = {  # noqa: RUF012
            # Note: this example
            "example": generate_example(),
        }

def main() -> None:
    """This allows testing the data model."""
    BaseAmbientConditionDataModel.test_model_main()


if __name__ == "__main__":
    main()
