'''
This module defines the captured data model used as part of the machine configuration data model.

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

from datetime import datetime, timezone
from typing import Union
from uuid import UUID

from icecream import ic
from pydantic import Field, field_validator, AwareDatetime

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
# pylint: enable=wrong-import-position

class Captured(IndalekoBaseModel):
    '''Defines the Captured Machine configuration information'''
    Label : UUID = Field(...,
                         title='Label',
                         description='UUID representing the semantic meaning of this timestamp.')

    Value : AwareDatetime = Field(...,
                                  title='Value',
                                  description='The timestamp of when this record was created.')

    @field_validator('Value', mode='before')
    @classmethod
    def ensure_timezone(cls, value : Union[datetime, str]) -> datetime:
        '''Ensure the timezone is set to UTC'''
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value

    class Config:
        '''Configuration for the captured data model'''
        json_schema_extra = {
            'example': {
                'Label': '3fa85f64-5717-4562-b3fc-2c963f66afa6',
                'Value': '2024-01-01T12:00:00Z'
            }
        }

def main():
    '''Main function for the software data model'''
    ic('Testing Software Data Model')
    Captured.test_model_main()

if __name__ == '__main__':
    main()
