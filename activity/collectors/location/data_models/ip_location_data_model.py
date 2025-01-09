'''
This module defines the data model for the ip location
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

from pydantic import BaseModel, Field
from typing import Optional, Union
from ipaddress import IPv4Address, IPv6Address
from datetime import datetime
from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

from activity.collectors.location.data_models.location_data_model import BaseLocationDataModel

class IPLocationDataModel(BaseLocationDataModel):
    '''This is the data model for the ip location service.'''
    ip_address: Union[IPv4Address, IPv6Address] = Field(..., description="The public facing IP address for the device")
    city: Optional[str] = Field(None, description="City inferred from the IP address")
    country: Optional[str] = Field(None, description="Country inferred from the IP address")
    country_code: Optional[str] = Field(None, description="ISO country code inferred from the IP address")
    region: Optional[str] = Field(None, description="Region or state inferred from the IP address")
    region_name: Optional[str] = Field(None, description="Full name of the region or state")
    postal_code: Optional[str] = Field(None, description="Postal or ZIP code inferred from the IP address")
    isp: Optional[str] = Field(None, description="Internet Service Provider associated with the IP address")
    org: Optional[str] = Field(None, description="Organization associated with the IP address")
    as_name: Optional[str] = Field(None, description="Autonomous System (AS) associated with the IP address")
    timezone: Optional[str] = Field(None, description="Timezone of the inferred location")


    class Config:
        json_schema_extra = {
            "example": {
                "latitude": 49.2827,
                "longitude": -123.1207,
                "altitude": 70.0,
                "accuracy": 5.0,
                "heading": 90.0,
                "speed": 10.0,
                "timestamp": "2023-09-21T10:30:00Z",
                "source": "IP",
                "ip_address": "1.1.1.1",
                "city": "Sydney",
                "country": "Australia",
                "country_code": "AU",
                "region": "NSW",
                "region_name": "New South Wales",
                "postal_code": "2000",
                "isp": "Cloudflare",
                "org": "Cloudflare",
                "as_name": "AS13335 Cloudflare, Inc.",
                "timezone": "Australia/Sydney",
            }
        }


def main():
    '''This allows testing the data model'''
    data = IPLocationDataModel(
        **IPLocationDataModel.Config.json_schema_extra['example']
    )
    ic(data)
    serial_data = data.serialize()
    data_check = IPLocationDataModel.deserialize(serial_data)
    assert data_check == data
    ic(IPLocationDataModel.get_arangodb_schema())

if __name__ == '__main__':
    main()
