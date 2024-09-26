"""
This module defines the data model for the activity data provider registration
system.

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
"""

import os
import sys
import uuid

from typing import Dict, Any, Union

from datetime import datetime
from pydantic import BaseModel, Field
from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.indaleko_source_identifier_data_model import IndalekoSourceIdentifierDataModel
from data_models.indaleko_record_data_model import IndalekoRecordDataModel

# pylint: enable=wrong-import-position

class IndalekoActivityDataProviderRegistrationDataModel(BaseModel):
    '''
    This class defines the activity data provider registration for the
    Indaleko system.
    '''
    Identifier : uuid.UUID = Field(...,
                              title='Identifier',
                              description='The UUID for the activity data provider.')

    Version : str = Field(...,
                           title='Version',
                           description='The version of the activity data provider.')

    Description : str = Field(...,
                                title='Description',
                                description='A description of the activity data provider.')

    Record : IndalekoRecordDataModel = Field(...,
                                            title='Record',
                                            description='Standard data record format.')

    class Config:
        '''Sample configuration data for the data model.'''
        json_schema_extra = {
            "example": {
                "Identifier": {
                    "Identifier": "429f1f3c-7a21-463f-b7aa-cd731bb202b1",
                    "Version": "1.0",
                },
                "Version": "1.0",
                "Description": "This is a sample activity data provider registration.",
                "Record": IndalekoRecordDataModel.Config.json_schema_extra['example'],
            }
        }

    def serialize(self) -> Dict[str, Any]:
        '''Serialize the object to a dictionary'''
        return self.model_dump(exclude_unset=True)

    @staticmethod
    def deserialize(data : Dict[str, Any]) -> \
        'IndalekoActivityDataProviderRegistrationDataModel':
        '''Deserialize the object from a dictionary'''
        if isinstance(data, str):
            return IndalekoActivityDataProviderRegistrationDataModel.parse_raw(data)
        elif isinstance(data, dict):
            return IndalekoActivityDataProviderRegistrationDataModel(**data)
        else:
            raise ValueError(f"Expected str or dict, got {type(data)}")

def main():
    '''This allows testing the data model.'''
    data = IndalekoActivityDataProviderRegistrationDataModel(
        **IndalekoActivityDataProviderRegistrationDataModel.Config.json_schema_extra['example']
    )
    ic(data)
    serial_data = data.serialize()
    ic(type(serial_data))
    ic(serial_data)
    data_check = IndalekoActivityDataProviderRegistrationDataModel.deserialize(serial_data)
    assert data_check == data
    ic(IndalekoActivityDataProviderRegistrationDataModel.model_json_schema())

if __name__ == '__main__':
    main()
