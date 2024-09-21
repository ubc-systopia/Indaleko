'''
This module defines the data model for the tile tracker location
activity data provider.

Project Indaleko
Copyright (C) 2024 Tony Mason

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
import os
import sys

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

from activity.providers.location.data_models.location_data_model import BaseLocationDataModel

class TileLocationDataModel(BaseLocationDataModel):
    tile_id: str = Field(..., description="Unique identifier for the Tile device")
    customer_name: Optional[str] = Field(None, description="Custom name of the Tile device (e.g., 'keys', 'backpack')")
    proximity: Optional[bool] = Field(None, description="Indicates if the Tile is in proximity (True if within range)")
    battery_level: Optional[float] = Field(None, description="Battery level of the Tile device as a percentage")
    ring_state: Optional[str] = Field(None, description="The current ring state (e.g., 'ringing', 'silent')")
    connection_status: Optional[str] = Field(None, description="Status of connection (e.g., 'connected', 'disconnected')")
    last_seen: Optional[datetime] = Field(None, description="Timestamp of the last interaction with the Tile device")
    last_location: Optional[dict] = Field(
        None, description="The last location data containing detailed information"
    )
    type: Optional[str] = Field(None, description="Type of Tile device (e.g., 'Mate', 'Pro', etc.)")
    owner_id: Optional[str] = Field(None, description="User or account ID of the Tile's owner")

    class Config:
        json_schema_extra = {
            "example": {
                "latitude": 49.2827,
                "longitude": -123.1207,
                "altitude": 70.0,
                "accuracy": 5.0,
                "heading": 270.0,
                "speed": 10.5,
                "timestamp": "2023-09-21T10:30:00Z",
                "source": "Tile",
                "tile_id": "12345abcde",
                "name": "backpack",
                "timestamp": "2023-09-21T12:00:00Z",
                "proximity": True,
                "battery_level": 85.0,
                "ring_state": "silent",
                "connection_status": "connected",
                "last_seen": "2023-09-21T11:59:00Z",
                "last_location": {
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "accuracy": 5.0,
                    "timestamp": "2023-09-21T11:55:00Z"
                },
                "type": "Mate",
                "owner_id": "user123"
            }
        }

    def serialize(self):
        '''Serialize the data model'''
        return self.dict()

    @staticmethod
    def deserialize(data):
        '''Deserialize the data model'''
        return TileLocationDataModel(**data)


def main():
    '''This allows testing the data model'''
    data = TileLocationDataModel(
        **TileLocationDataModel.Config.json_schema_extra['example']
    )
    ic(data)
    ic(data.json())
    ic(dir(data))
    ic(type(data.json()))
    ic(data.dict())
    serial_data = data.serialize()
    data_check = TileLocationDataModel.deserialize(serial_data)
    assert data_check == data
    ic(TileLocationDataModel.schema_json())

if __name__ == '__main__':
    main()
