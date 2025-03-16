"""
This module defines the data model for the user identity information.

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

from typing import List, Union

from pydantic import Field
from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from data_models.identity_domain import IndalekoIdentityDomainDataModel
from data_models.i_uuid import IndalekoUUIDDataModel

# pylint: enable=wrong-import-position


class IndalekoUserDataModel(IndalekoBaseModel):
    """
    This class defines the data model for the User data information.
    """

    Identifier: IndalekoUUIDDataModel = Field(
        None,
        title="Identifier",
        description="The UUID assigned to this user.",
        example="12345678-1234-5678-1234-567812345678",
    )

    Domains: List[IndalekoIdentityDomainDataModel] = Field(
        None,
        title="Domains",
        description="The identity domains having an association to this user.",
    )

    Description: Union[str, None] = Field(
        None,
        title="Description",
        description="Description of the user.",
        examples=["Aki", None],
    )

    class Config:
        """
        This class defines configuration data for the data model.
        """

        json_schema_extra = {
            "example": {
                "Identifier": IndalekoUUIDDataModel.Config.json_schema_extra["example"],
                "Domains": [
                    IndalekoIdentityDomainDataModel.Config.json_schema_extra["example"]
                ],
                "Description": "Human readable label for this user.",
            }
        }


def main():
    """This allows testing the data model"""
    ic("Testing the UserDataModel")
    IndalekoUserDataModel.test_model_main()


if __name__ == "__main__":
    main()
