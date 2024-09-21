'''
This module defines the data model for location services.

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

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import json
from icecream import ic


class BaseLocationDataModel(BaseModel):
    latitude: float = Field(..., description="Latitude coordinate of the location")
    longitude: float = Field(..., description="Longitude coordinate of the location")
    altitude: Optional[float] = Field(None, description="Altitude of the location, if available")
    accuracy: Optional[float] = Field(None, description="Accuracy of the location data")
    heading: Optional[float] = Field(None, description="Heading/direction of movement")
    speed: Optional[float] = Field(None, description="Speed of movement")
    timestamp: datetime = Field(..., description="Timestamp when the location was recorded")
    source: str = Field(..., description="Source of the location data, e.g., 'GPS', 'IP', etc.")

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
                "source": "GPS"
            }
        }

def main():
    '''This allows testing the data model'''
    data = BaseLocationDataModel(
        latitude=49.2827,
        longitude=-123.1207,
        altitude=70.0,
        accuracy=5.0,
        heading=270.0,
        speed=10.5,
        timestamp="2023-09-21T10:30:00Z",
        source="GPS"
    )
    ic(data)
    ic(data.json())
    ic(type(data.json()))
    # print(json.dumps(data.json(), indent=2))


if __name__ == '__main__':
    main()

