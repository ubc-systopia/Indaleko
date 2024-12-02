'''
This module defines the common database schema for Relationship Data.

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

from typing import Tuple, List

from icecream import ic
from pydantic import Field

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from data_models.timestamp import IndalekoTimestampDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.record import IndalekoRecordDataModel
from platforms.data_models.software import Software as software
from platforms.data_models.hardware import Hardware as hardware
# pylint: enable=wrong-import-position

class IndalekoRelationshipDataModel(IndalekoBaseModel):
    '''This is the definition of the relationship data model.'''
    Record : IndalekoRecordDataModel = Field(None,
                                    title='Record',
                                    description='The record associated with the object.')

    Objects : Tuple[str, str] = Field(None,
                                    title='Objects',
                                    description='The objects in the relationship.')

    Relationships : List[IndalekoSemanticAttributeDataModel] = Field(None,
                                    title='Relationship',
                                    description='The relationships between the objects.')

    class Config:
        '''Sample configuration data for the relationship model'''
        json_schema_extra = {
            "example" : {
                "Record" : IndalekoRecordDataModel.Config.json_schema_extra['example'],
                "Objects" : ('12345678-1234-5678-1234-567812345678', '12345678-1234-5678-1234-567812345678'),
                "Relationships" : [
                    IndalekoSemanticAttributeDataModel.Config.json_schema_extra['example'],
                    IndalekoSemanticAttributeDataModel.Config.json_schema_extra['example']
                ]
            }
        }

def main():
    '''This allows testing the data model.'''
    ic('Testing IndalekoRelationshipDataModel')
    IndalekoRelationshipDataModel().test_model_main()

if __name__ == '__main__':
    main()
