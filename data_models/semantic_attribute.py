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

from typing import Any
from pydantic import Field

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from data_models.i_uuid import IndalekoUUIDDataModel
# pylint: enable=wrong-import-position

class IndalekoSemanticAttributeDataModel(IndalekoBaseModel):
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
    Identifier : IndalekoUUIDDataModel =\
          Field(...,
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
                "Identifier": IndalekoUUIDDataModel.get_json_example(),
                "Data": "foo.lua"
            }
        }



def main():
    '''This allows testing the data model'''
    IndalekoSemanticAttributeDataModel.test_model_main()

if __name__ == '__main__':
    main()
