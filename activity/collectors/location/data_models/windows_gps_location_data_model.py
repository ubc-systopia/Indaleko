'''
This module defines the data model for the Windows GPS based location
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

from pydantic import Field, field_validator, AwareDatetime
from typing import Optional
from datetime import datetime, timezone


# from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.location_data_model import BaseLocationDataModel
from activity.collectors.location.data_models.windows_gps_satellite_data\
     import WindowsGPSLocationSatelliteDataModel
# pylint: enable=wrong-import-position


class WindowsGPSLocationDataModel(BaseLocationDataModel):
    '''This is the data model for the Windows GPS location service.'''
    altitude_accuracy: Optional[float] = Field(None, description="Accuracy of altitude measurement")
    is_remote_source: Optional[bool] = Field(None, description="Is the source remote?")
    point: Optional[str] = Field(None, description="A string representation of the point data")
    position_source: Optional[str] = Field(None, description="The source of the position data")
    position_source_timestamp: Optional[AwareDatetime] = Field(None, description="Timestamp of the position source")
    satellite_data: Optional[WindowsGPSLocationSatelliteDataModel] = Field(
        None,
        description="Details about satellite data used for the position"
    )
    civic_address: Optional[str] = Field(None, description="Civic address for the location, if available")
    venue_data: Optional[str] = Field(None, description="Details about the venue data for the location, if available")

    @field_validator('position_source_timestamp', mode='before')
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
                "altitude_accuracy": 2.0,
                "heading": 90.0,
                "speed": 10.0,
                "source": "GPS",
                "timestamp": "2023-09-21T10:30:00Z",
                "is_remote_source": False,
                "point": "POINT(49.2827 -123.1207)",
                "position_source": "GPS",
                "position_source_timestamp": "2023-09-21T10:31:00Z",
                "satellite_data": WindowsGPSLocationSatelliteDataModel.Config.json_schema_extra['example'],
                "civic_address": None,
                "venue_data": None,
            },
            "new_example": {
                'accuracy': 209.0,
                'altitude': 0.0,
                'altitude_accuracy': None,
                'civic_address': None,
                'heading': None,
                'is_remote_source': False,
                'latitude': 49.28042203230194,
                'longitude': -123.12734913090786,
                'point': 'POINT(49.28042203230194 -123.12734913090786)',
                'position_source': 'GPS',
                'position_source_timestamp': '2024-09-27T00:04:29.060275Z',
                'satellite_data': {
                    'geometric_dilution_of_precision': None,
                    'horizontal_dilution_of_precision': None,
                    'position_dilution_of_precision': None,
                    'time_dilution_of_precision': None,
                    'vertical_dilution_of_precision': None
                },
                'source': 'GPS',
                'speed': None,
                'timestamp': '2024-09-27T00:04:29.060275Z',
                'venue_data': None
            }
        }


def main():
    '''This allows testing the data model'''
    WindowsGPSLocationDataModel.test_model_main()


if __name__ == '__main__':
    main()
