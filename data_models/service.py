"""
This module defines the data model for the Indaleko services definition.

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
from data_models import IndalekoRecordDataModel
from data_models.service_identifier import IndalekoServiceIdentifierDataModel

# pylint: enable=wrong-import-position

class IndalekoServiceDataModel(IndalekoServiceIdentifierDataModel):
    '''This is the data model for the Indaleko service definition.'''

    Record : IndalekoRecordDataModel = Field(None,
                                    title='Record',
                                    description='The record associated with the object.')


    class Config:
        json_schema_extra = {
            "example": {
                "Record": IndalekoRecordDataModel.Config.json_schema_extra['example'],
                **IndalekoServiceIdentifierDataModel.Config.json_schema_extra['example']
            }
        }

def main():
    '''This allows testing the service data model'''
    ic('Testing Service Data Model')
    ic(IndalekoServiceDataModel.Config.json_schema_extra['example'])
    # IndalekoServiceDataModel.test_model_main()

if __name__ == '__main__':
    main()
