"""
This module defines the platform definition use by the machine configuration data model.

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
from data_models.base import IndalekoBaseModel
from platforms.data_models import hardware, software

# pylint: enable=wrong-import-position


class MachinePlatform(IndalekoBaseModel):
    """Defines the platform (hardware and software) information"""

    Software: software.Software = Field(
        ...,
        title="Software",
        description="The software information for the machine.",
    )

    Hardware: hardware.Hardware = Field(
        ...,
        title="Hardware",
        description="The hardware information for the machine.",
    )

    class Config:
        """Configuration for the hardware data model"""

        json_schema_extra = {
            "example": {
                "Software": software.Software.Config.json_schema_extra["example"],
                "Hardware": hardware.Hardware.Config.json_schema_extra["example"],
            },
        }


def main():
    """Main function for the software data model"""
    ic("Testing Software Data Model")
    MachinePlatform.test_model_main()


if __name__ == "__main__":
    main()
