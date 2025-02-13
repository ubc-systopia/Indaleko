'''
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
'''
from datetime import datetime, timezone
import os
import sys
from uuid import UUID, uuid4

from typing import Literal, Optional

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from data_models.location_data_model import BaseLocationDataModel
# pylint: enable=wrong-import-position


class IndalekoNamedEntityDataModel(IndalekoBaseModel):
    name: str
    uuid: UUID = uuid4()
    category: Literal['person', 'place', 'thing']
    description: Optional[str] = None
    gis_location: Optional[BaseLocationDataModel] = None  # GIS location for places
    device_id: Optional[UUID] = None  # Device identifier for things


class NamedEntityCollection(IndalekoBaseModel):
    entities: list[IndalekoNamedEntityDataModel]


# Example usage
example_entities = NamedEntityCollection(entities=[
    IndalekoNamedEntityDataModel(
        name="Tony",
        category="person",
        description="The user",
        uuid=UUID("981a3522-c394-40b0-a82c-a9d7fa1f7e01")
    ),
    IndalekoNamedEntityDataModel(
        name="Paris",
        category="place",
        description="Capital of France",
        gis_location=BaseLocationDataModel(
            source='defined',
            timestamp=datetime.now(timezone.utc),
            latitude=48.8566,
            longitude=2.3522,
            )
        ),
    IndalekoNamedEntityDataModel(
        name="Laptop",
        category="thing",
        description="User's personal laptop",
        device_id="3dd1f5f6-1bd1-4822-864a-7470eeb8eebc"
    )
])

print(example_entities)
