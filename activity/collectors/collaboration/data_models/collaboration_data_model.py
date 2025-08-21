"""
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

from icecream import ic
from pydantic import Field


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.data_model.activity import IndalekoActivityDataModel


# pylint: enable=wrong-import-position


class BaseCollaborationDataModel(IndalekoActivityDataModel):
    """This is the base data model for the collaboration data."""

    CollaborationType: str = Field(
        ...,
        title="CollaborationType",
        description="The type of collaboration (e-mail, file sharing, messaging, etc.)",
    )

    class Config:
        """Sample configuration for the data model."""

        @staticmethod
        def generate_example():
            """Generate an example for the data model."""
            example = IndalekoActivityDataModel.Config.json_schema_extra["example"]
            example["CollaborationType"] = "file sharing"
            return example

        json_schema_extra = {
            # Note: this example
            "example": generate_example(),
        }


def main() -> None:
    """This allows testing the data model."""
    ic(BaseCollaborationDataModel.Config.json_schema_extra)
    BaseCollaborationDataModel.test_model_main()


if __name__ == "__main__":
    main()
