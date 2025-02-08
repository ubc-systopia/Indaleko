
"""
This module defines the collection metadata data model for Indaleko.

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
import json
import os
import sys

from typing import Union
from pydantic import Field, BaseModel
from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel  # noqa: E402
# pylint: enable=wrong-import-position


class IndexMetadata(BaseModel):
    '''
    This class defines the data model for Arango index metadata used
    with collections in Indaleko.
    '''
    Name: str
    Type: str
    Fields: list[str]
    Unique: bool
    Sparse: bool
    Deduplicate: bool


class IndalekoCollectionMetadataDatamodel(IndalekoBaseModel):
    '''
    This class defines the data model for the Indaleko collection metadata.
    '''

    key: str = Field(
        ...,
        title='Name',
        description='The name of the collection we are describing'
    )

    Description: str = Field(
        ...,
        title='Description',
        description='This describes the basic purpose of the collection'
    )

    RelevantQueries: list[str] = Field(
        ...,
        Name='RelevantQueries',
        description='Example queries that are relevant to this collection',
    )

    PrimaryKeys: list[str] = Field(
        ...,
        Name='PrimaryKeys',
        description='The primary keys for this collection',
    )

    IndexedFields: list[IndexMetadata] = Field(
        ...,
        Name='IndexedFields',
        description='The fields that are indexed for this collection',
    )

    QueryGuidelines: Union[str, None] = Field(
        ...,
        Name='QueryGuidelines',
        description='Guidelines for querying this collection',
    )

    def serialize(self) -> dict[str, str]:
        '''Serialize the data model to a dictionary.'''
        data = json.loads(
            self.model_dump_json(
                exclude_unset=True,
                exclude_none=True
            )
        )
        if '_key' not in data and 'key' in data:
            data['_key'] = data['key']
            del data['key']
        return data

    @staticmethod
    def deserialize(data: Union[dict[str, str], str]) -> 'IndalekoCollectionMetadataDatamodel':
        '''Deserialize the data model from a dictionary.'''
        if isinstance(data, str):
            data = json.loads(data)
        elif not isinstance(data, dict):
            raise ValueError(f"Expected str or dict, got {type(data)}")
        if '_key' in data and 'key' not in data:  # Pydantic doesn't allow _key, ArangoDB uses it.
            data['key'] = data['_key']
            del data['_key']
        return IndalekoCollectionMetadataDatamodel(**data)

    class Config:
        '''Sample configuration data for the data model.'''
        json_schema_extra = {
            "example": {
                "key": "IndalekoCollectionMetadata",
                "Description": "This collection contains metadata about collections",
                "RelevantQueries": [
                    "FOR doc IN IndalekoCollectionMetadata FILTER doc.Name "
                    "== 'IndalekoCollectionMetadata' RETURN doc",
                ],
                "PrimaryKeys": [
                    "_key"
                ],
                "IndexedFields": [],
                "QueryGuidelines": "Please use the primary key for queries"
            }
        }


def main():
    '''This allows testing the data model.'''
    IndalekoCollectionMetadataDatamodel.test_model_main()


if __name__ == '__main__':
    main()
