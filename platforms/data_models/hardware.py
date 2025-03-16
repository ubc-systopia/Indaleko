"""
This module defines the database schema for the MachineConfig collection.

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
from typing import Optional

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel

# pylint: enable=wrong-import-position


class Hardware(IndalekoBaseModel):
    """Defines the machine Hardware information"""

    CPU: str = Field(..., title="CPU", description="Processor Architecture.")

    Version: str = Field(..., title="Version", description="Version of the processor.")

    Cores: Optional[int] = Field(
        None, title="Cores", description="Number of cores on the processor."
    )

    Threads: Optional[int] = Field(
        None, title="Threads", description="Number of threads on the processor."
    )

    class Config:
        """Configuration for the hardware data model"""

        json_schema_extra = {
            "example": {
                "CPU": "x86_64",
                "Version": "Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz",
                "Cores": 4,
                "Threads": 8,
            }
        }


def main():
    """Main function for the software data model"""
    ic("Testing Software Data Model")
    Hardware.test_model_main()


if __name__ == "__main__":
    main()
