"""
This module defines the base data model used by the Indaleko collectors.

Indaleko Collector Data Model
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

from uuid import UUID, uuid4

from icecream import ic
from pydantic import BaseModel, Field


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from constants import IndalekoConstants


# pylint: enable=wrong-import-position


class IndalekoCollectorDataModel(BaseModel):
    """Defines the base data model for the storage collectors."""

    PlatformName: str | None = Field(
        None,
        title="PlatformName",
        description="The name of the platform (e.g., Linux, Windows, etc.)if any (default=None).",
    )

    ServiceRegistrationName: str = Field(
        ...,
        title="ServiceRegistrationName",
        description="The service name used when registeringthis collector in the database.",
    )

    ServiceFileName: str = Field(
        ...,
        title="ServiceFileName",
        description="The service name of the collectorfor file name generation.",
    )

    ServiceUUID: UUID = Field(
        ...,
        title="ServiceUUID",
        description="The UUID of the collector.",
    )

    ServiceVersion: str = Field(
        ...,
        title="CollectorVersion",
        description="The version of the collector.",
    )

    ServiceDescription: str = Field(
        ...,
        title="CollectorDescription",
        description="The description of the collector.",
    )

    ServiceType: str = Field(
        ...,
        title="CollectorType",
        description="The type of the collector.",
    )

    class Config:
        """Configuration for the base CLI data model."""

        json_schema_extra = {
            "example": {
                "PlatformName": "Linux",
                "ServiceRegistrationName": "Linux Local Collector",
                "ServiceFileName": "collector",
                "ServiceUUID": uuid4(),
                "ServiceVersion": "1.0",
                "ServiceDescription": "This service collects localfilesystem metadata of a Linux machine.",
                "ServiceType": IndalekoConstants.service_type_test,
            },
        }


def main() -> None:
    """Test code for the base CLI data model."""
    ic("Testing Collector Data Model")
    storage_collector_data = IndalekoCollectorDataModel(
        **IndalekoCollectorDataModel.Config.json_schema_extra["example"],
    )
    ic(storage_collector_data)
    ic(platform.system())


if __name__ == "__main__":
    main()
