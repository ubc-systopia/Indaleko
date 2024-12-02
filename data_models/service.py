"""
This module defines the data model for the Indaleko services definition.

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

from typing import List, Union, Dict, Any
from pydantic import Field
from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from data_models import IndalekoRecordDataModel

# pylint: enable=wrong-import-position

class IndalekoServiceDataModel(IndalekoBaseModel):
    '''This is the data model for the Indaleko service definition.'''

    Record : IndalekoRecordDataModel = Field(None,
                                    title='Record',
                                    description='The record associated with the object.')

    Identifier : uuid.UUID = Field(None,
                                    title='Identifier',
                                    description='This is the UUID of the service provider.')

    Version : str = Field(None,
                          title='Version',
                          description='This is the version of the service provider.')

    Name : str = Field(None,
                       title='Name',
                       description='This is the name of the service provider.')

    Type : str = Field(None,
                       title='Type',
                       description='This is the type of service provider.')

    Description : str = Field(None,
                              title='Description',
                              description='This is the description of the service provider.')

    class Config:
        json_schema_extra = {
            "example": {
                "Record": IndalekoRecordDataModel.Config.json_schema_extra['example'],
                "Identifier": "123e4567-e89b-12d3-a456-426614174000",
                "Version": "1.0.0",
                "Name": "Indaleko",
                "Type": "Service",
                "Description": "This is the Indaleko service."
            }
        }

def main():
    '''This allows testing the service data model'''
    ic('Testing Service Data Model')
    IndalekoServiceDataModel.test_model_main()

if __name__ == '__main__':
    main()
