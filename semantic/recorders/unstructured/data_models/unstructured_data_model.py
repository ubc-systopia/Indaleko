'''
This module defines the data model for the tile tracker location
activity data provider.

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
import os
import sys

from pydantic import  Field, field_validator, AwareDatetime
from typing import Optional
from datetime import datetime, timezone
from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

from semantic.data_models.base_data_model import BaseSemanticDataModel
from activity.collectors.location.data_models.location_data_model import BaseLocationDataModel

class TileLocationDataModel(BaseLocationDataModel):
    '''
    This class defines the data model for the Tile-based location activity data
    provider.  Fields visible from the data provider are:
        'accuracy', # already in base class
        'altitude', # already in base class
        'archetype',
        'as_dict',  # returns data back as a dictionary
        'async_history', # method for retrieving historical data (Tile Premium feature)
        'async_update', # method for updating the Tile device data?
        'dead', # boolean indicating if the Tile device is dead
        'firmware_version', # version of the firmware
        'hardware_version', # version of the hardware
        'kind', # kind of Tile device.  Only things observed are TILE and PHONE
        'last_timestamp', # last time the Tile device was seen - maps to base class
        'latitude', # already in base class
        'longitude', # already in base class
        'lost', # boolean indicating if the Tile device is lost
        'lost_timestamp', # timestamp when the Tile device was lost
        'name', # user defined name for the Tile device
        'ring_state', # current ring state
        'uuid', # unique identifier for the Tile device: note, this isn't a UUID.
        'visible', # boolean indicating if the Tile device is visible (in app?)
        'voip_state' # state of the voip connection (only seen 'OFFLINE')
    '''
    tile_id: str = Field(..., description="Unique identifier for the Tile device")
    archetype : Optional[str] = Field(None, description="Archetype of the Tile device")
    dead : bool = Field(False, description="Boolean indicating if the Tile device is dead")
    firmware_version: Optional[str] = Field(None, description="Version of the firmware")
    hardware_version: Optional[str] = Field(None, description="Version of the hardware")
    kind: Optional[str] = Field(None, description="Kind of Tile device")
    lost: bool = Field(False, description="Boolean indicating if the Tile device is lost")
    lost_timestamp: Optional[AwareDatetime] = Field(None, description="Timestamp when the Tile device was lost")
    name : str = Field(..., description="User defined name for the Tile device")
    ring_state: Optional[str] = Field(None, description="Current ring state")
    visible: bool = Field(False, description="Boolean indicating if the Tile device is visible")
    voip_state: Optional[str] = Field(None, description="State of the voip connection")
    email : str = Field(..., description="Email address associated with the Tile device")

    @field_validator('lost_timestamp', mode='before')
    def ensure_timezone(cls, value: datetime):
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value



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
                "archetype": "BACKPACK",
                "dead": False,
                "firmware_version": "05.03.07.0",
                "hardware_version": "08.03",
                "kind": "TILE",
                "lost": False,
                "lost_timestamp": "1970-01-01T00:00:00Z",
                "name": "Backpack",
                "ring_state": "STOPPED",
                "tile_id" : "77736942235f491e",
                "visible": True,
                "voip_state": "OFFLINE",
                "email": "aki@null.com"
            }
        }


def main():
    '''This allows testing the data model'''
    TileLocationDataModel.test_model_main()

    
if __name__ == '__main__':
    main()
