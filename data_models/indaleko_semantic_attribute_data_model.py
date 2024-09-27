"""
This module defines the database schema for any database record conforming to
the Indaleko Record requirements.

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

from typing import Any

from pydantic import BaseModel, Field
from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

from data_models.indaleko_uuid_data_model import IndalekoUUIDDataModel


class IndalekoSemanticAttributeDataModel(BaseModel):
    '''
    This class defines the UUID data model for Indaleko.

    A "semantic attribute" is a top level concept of something that has a
    semantic meaning within the Indaleko system.  For example, this might be the
    name of the file, or the user that created the file, or notable elements
    from contents of the file.

    The UUID should be unique to the type of semantic attribute, so that records
    with the same UUID can infer the relationship based upon that semantic
    attribute.  For example, if the semantic attribute is the name of the file,
    then all records with the same UUID give the same meaning to that field.  In
    this way, we allow Indaleko to index these values without understanding the
    meaning of them.
    '''
    Identifier : IndalekoUUIDDataModel = Field(...,
                                   title='Identifier',
                                   description='The UUID specific to this type of semantic attribute.',
                                    example='12345678-1234-5678-1234-567812345678')
    Data : Any = Field(...,
                       title='Data',
                       description='The data associated with this semantic attribute.')

    class Config:
        '''Sample configuration data for the data model'''
        json_schema_extra = {
            "example": {
                "Identifier": "12345678-1234-5678-1234-567812345678",
                "Data": "foo.lua"
            }
        }

    def serialize(self):
        '''Serialize the data model'''
        return self.model_dump(exclude_unset=True)

    @staticmethod
    def deserialize(data):
        '''Deserialize the data model'''
        # if type(data['Identifier']) == str:
        #    data['Identifier'] = IndalekoUUIDDataModel.deserialize(eval(data['Identifier']))
        #assert isinstance(data['Identifier'], IndalekoUUIDDataModel),\
        #    f"Expected IndalekoUUIDDataModel, got {type(data['Identifier'])}"
        return IndalekoSemanticAttributeDataModel(**data)

def main():
    '''This allows testing the data model'''
    data = IndalekoSemanticAttributeDataModel(
            Identifier=IndalekoUUIDDataModel(
                Identifier=uuid.uuid4(),
                Label='This is a sample IndalekoUUID.'),
            Data='foo.lua'
    )
    ic(data)
    ic(data.json())
    ic(data.dict())
    serial_data = data.serialize()
    ic(type(serial_data))
    ic(serial_data)
    data_check = IndalekoSemanticAttributeDataModel.deserialize(serial_data)
    assert data_check == data
    ic(IndalekoSemanticAttributeDataModel.schema_json())

if __name__ == '__main__':
    main()
