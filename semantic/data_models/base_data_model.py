'''
This module defines the base data model for semantic metadata recorders.

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

from typing import List
from datetime import datetime, timezone
from uuid import UUID

from icecream import ic
from pydantic import  Field, field_validator, AwareDatetime

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from data_models.record import IndalekoRecordDataModel
from data_models.base import IndalekoBaseModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.i_uuid import IndalekoUUIDDataModel
# pylint: enable=wrong-import-position


class BaseSemanticDataModel(IndalekoBaseModel):
    '''
    This class defines the common model used by semantic data providers in the
    Indaleko Project.

    The goal is to define a common structure that can be used to reason about
    the meaning of the information that the semantic data providers are
    collecting.

    By default, the semantic data framework will construct an index that
    includes all of the semantic fields that are defined by the semantic data
    providers.

    '''
    Record : IndalekoRecordDataModel = Field(...,
                                             title='Record',
                                             description='The record for the activity data.')

    Timestamp : AwareDatetime = \
        Field(...,
              title='Timestamp',
              description='The timestamp when the semantic data was collected.')

    ObjectIdentifier: UUID = Field(...,
                                   title = "ObjectIdentifier",
                                   description= "ObjectIdentifier of the original source file")

    RelatedObjects : List[UUID] = \
        Field(...,
              title='RelatedObjects',
              description='The UUIDs of storage objects related to this metadata.',
              min_items=1)

    SemanticAttributes : List[IndalekoSemanticAttributeDataModel] =\
        Field(...,
              title='SemanticAttributes',
              description='The semantic attributes captured by the activity data provider.',
              min_items=1)

    @classmethod
    @field_validator('timestamp', mode='before')
    def ensure_timezone(cls, value: datetime):
        '''Ensure that the timestamp is in explicit UTC timezone'''
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value


    class Config:
        '''Sample configuration data for the data model'''
        json_schema_extra = {
            "example": {
                "Record" : {
                    "SourceIdentifier" : {
                        "Identifier" : "50c37415-53ff-4e81-9a8b-00a6f0ad2310", # uuid
                        "Version" : "1.0",
                    },
                    "Timestamp" : "2023-09-21T10:29:59Z",
                    "Attributes" : {},
                    "Data" : "xAA="
                },
                "Timestamp": "2023-09-21T10:30:00Z",
                "ObjectIdentifier" : "5a833720-7293-47fe-b3b3-1296302956cd",
                "RelatedObjects" : [
                    "5a833720-7293-47fe-b3b3-1296302956cd",
                ],
                "SemanticAttributes" : [
                    {
                        "Identifier" :
                            IndalekoUUIDDataModel(
                                Identifier = 'b4a5a775-bba8-4697-91bf-4acf99927221',
                                Label = "File Type"
                            ).serialize(),
                        "Data" : "xB1hcHBsaWNhdGlvbi92bmQubXMtcG93ZXJwb2ludA=="
                    },
                    {
                        "Identifier" : 
                            IndalekoUUIDDataModel(
                                Identifier = 'af6eba9e-0993-4bab-a620-163d523e7850',
                                Label = "Languages"
                            ).serialize(),
                        "Data" : "xAJlbg=="
                    },
                ]
            }
        }

def main():
    '''This allows testing the data model'''
    ic(os.path.abspath(__file__))
    ic('Testing base_data_model.py')
    BaseSemanticDataModel.test_model_main()

if __name__ == '__main__':
    main()
