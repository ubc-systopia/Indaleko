"""
This module defines the collection metadata data model for Indaleko.

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

from typing import Union

# from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel  # noqa: E402

# pylint: enable=wrong-import-position


class IndalekoCollectionIndexDataModel(IndalekoBaseModel):
    """
    This class defines the data model for Arango index metadata used
    with collections in Indaleko.
    """

    Name: str
    Type: str
    Fields: list[str]
    Unique: Union[bool, None] = None
    Sparse: Union[bool, None] = None
    Deduplicate: Union[bool, None] = None

    class Config:
        """
        This class defines the configuration for the data model.
        """

        json_schema_extra = {
            "example": {
                "Name": "primary",
                "Type": "persistent",
                "Fields": ["_key"],
                "Unique": True,
                "Sparse": False,
                "Deduplicate": True,
            }
        }


def main():
    """This allows testing the data model."""
    IndalekoCollectionIndexDataModel.test_model_main()


if __name__ == "__main__":
    main()
