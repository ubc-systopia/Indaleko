"""
This module defines the base data model used by the
Indaleko activity collectors.

Indaleko Storage Collector Data Model
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
import platform
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
from constants import IndalekoConstants
from data_models.collector import IndalekoCollectorDataModel

# pylint: enable=wrong-import-position


class IndalekoActivityCollectorDataModel(IndalekoCollectorDataModel):
    """WIP"""

    ServiceType: str = Field(
        IndalekoConstants.service_type_activity_data_collector,
        title="CollectorType",
        description="The type of the collector. (default is"
        f"{IndalekoConstants.service_type_activity_data_collector})",
    )

    class Config:
        """Configuration for the activity collector data model."""

        @staticmethod
        def get_example():
            """Get an example of the activity collector data model."""
            example = IndalekoCollectorDataModel.Config.json_schema_extra["example"].copy()
            example["ServiceType"] = IndalekoConstants.service_type_activity_data_collector
            return example

        json_schema_extra = {
            "example": get_example(),
        }


def main():
    """Test code for the activity collector data model"""
    ic("Testing Indaleko Activity Collector Data Model")
    activity_collector_data = IndalekoActivityCollectorDataModel(
        **IndalekoActivityCollectorDataModel.Config.json_schema_extra["example"],
    )
    ic(activity_collector_data)
    ic(platform.system())
    print(activity_collector_data.model_dump(exclude_unset=True, exclude_defaults=True))
    print(activity_collector_data.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
