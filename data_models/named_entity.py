"""
This module defines the data model for named entities.

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

import json
import os
import sys
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from data_models.location_data_model import LocationDataModel

# pylint: enable=wrong-import-position


class IndalekoNamedEntityType(str, Enum):
    person = "person"
    organization = "organization"
    location = "location"
    date = "date"
    event = "event"
    product = "product"
    item = "item"


class IndalekoNamedEntityDataModel(IndalekoBaseModel):
    name: str
    uuid: UUID = uuid4()
    category: IndalekoNamedEntityType
    description: str | None = None
    gis_location: LocationDataModel | None = None  # GIS location for places
    device_id: UUID | None = None  # Device identifier for things

    class Config:
        """Sample configuration data for the data model."""

        json_schema_extra = {
            "example": {
                "name": "Tony",
                "uuid": "981a3522-c394-40b0-a82c-a9d7fa1f7e01",
                "category": IndalekoNamedEntityType.person,
                "description": "The user",
            },
        }


class NamedEntityCollection(IndalekoBaseModel):
    entities: list[IndalekoNamedEntityDataModel]

    class Config:
        """Sample configuration data for the data model."""

        json_schema_extra = {
            "example": {
                "entities": [
                    IndalekoNamedEntityDataModel.Config.json_schema_extra["example"],
                ],
            },
        }


# Example usage
example_entities = NamedEntityCollection(
    entities=[
        IndalekoNamedEntityDataModel(
            name="Tony",
            category=IndalekoNamedEntityType.person,
            description="The user",
            uuid=UUID("981a3522-c394-40b0-a82c-a9d7fa1f7e01"),
        ),
        IndalekoNamedEntityDataModel(
            name="Paris",
            category=IndalekoNamedEntityType.location,
            description="Capital of France",
            gis_location=LocationDataModel(
                source="defined",
                timestamp=datetime.now(UTC),
                latitude=48.8566,
                longitude=2.3522,
            ),
        ),
        IndalekoNamedEntityDataModel(
            name="Laptop",
            category=IndalekoNamedEntityType.item,
            description="User's personal laptop",
            device_id="3dd1f5f6-1bd1-4822-864a-7470eeb8eebc",
        ),
    ],
)


def main():
    """Test code"""
    print(json.dumps(example_entities.model_json_schema(), indent=2))


if __name__ == "__main__":
    main()
