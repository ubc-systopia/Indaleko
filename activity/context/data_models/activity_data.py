"""
This module defines the activity data model used within the activity data
context data model.

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
import uuid

from pydantic import Field

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel

# pylint: enable=wrong-import-position


class ActivityDataModel(IndalekoBaseModel):
    """
    This class defines the combination of the provider and the provider
    reference (UUID) for the activity data. Note: we don't assume we capture
    the activity data here, though the data model does permit it.
    """

    Provider: uuid.UUID = Field(
        ...,
        title="Provider",
        description="The provider of the activity data.",
    )
    ProviderReference: uuid.UUID = Field(
        ...,
        title="ProviderReference",
        description="The provider reference for the activity data.",
    )
    ProviderData: str | None = Field(
        None,
        title="ProviderData",
        description="The provider data (if any).",
    )
    ProviderAttributes: dict[str, str] | None = Field(
        None,
        title="ProviderAttributes",
        description="The provider attributes (if any).",
    )

    class Config:
        """
        Configuration for the class.
        """

        json_schema_extra = {
            "example": {
                "Provider": "00000000-0000-0000-0000-000000000000",
                "ProviderReference": "00000000-0000-0000-0000-000000000000",
                "ProviderData": "Some data",
                "ProviderAttributes": {"key1": "value1", "key2": "value2"},
            },
        }


def main():
    """Test code for IndalekoActivityDataModel."""
    ActivityDataModel.test_model_main()


if __name__ == "__main__":
    main()
