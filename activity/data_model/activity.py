"""
This module defines the common data model for activity data providers
in the Indaleko project.

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

from datetime import datetime
from typing import List
from pydantic import Field

# from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
# pylint: enable=wrong-import-position


class IndalekoActivityDataModel(IndalekoBaseModel):
    '''
    This class defines the common model used by activity data providers in the
    Indaleko Project.

    The goal is to define a common structure that can be used to reason about
    the meaning of the information that the activity data providers are
    collecting.

    By default, the activity data framework will construct an index that
    includes all of the semantic fields that are defined by the activity data
    providers.

    '''
    Record : IndalekoRecordDataModel = Field(...,
                                             title='Record',
                                             description='The record for the activity data.')

    Timestamp : datetime = Field(...,
                            title='Timestamp',
                            description='The timestamp when the activity data was collected.')

    SemanticAttributes : List[IndalekoSemanticAttributeDataModel] \
        = Field(...,
                title='SemanticAttributes',
                description='The semantic attributes captured by the activity data provider.')

    class Config:
        '''Sample configuration data for the data model.'''
        json_schema_extra = {
            "example": {
                "Record": IndalekoRecordDataModel.get_json_example(),
                "Timestamp": "2024-01-01T00:00:00Z",
                "SemanticAttributes": [IndalekoSemanticAttributeDataModel.get_json_example()],
            }
        }


def main():
    '''This allows testing the data model'''
    IndalekoActivityDataModel.test_model_main()

if __name__ == '__main__':
    main()
