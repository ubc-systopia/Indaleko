
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

from typing import Union, Any
from pydantic import Field

# from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel  # noqa: E402
from data_models.db_index import IndalekoCollectionIndexDataModel  # noqa: E402
# pylint: enable=wrong-import-position


class IndalekoCollectionMetadataDataModel(IndalekoBaseModel):
    '''
    This class defines the data model for the Indaleko collection metadata.
    '''

    key: str = Field(
        ...,
        title='Name',
        description='The name of the collection we are describing'
    )

    Description: Union[str, None] = Field(
        ...,
        title='Description',
        description='This describes the basic purpose of the collection'
    )

    QueryGuidelines: Union[list[str], None] = Field(
        ...,
        Name='QueryGuidelines',
        description='Guidelines for querying this collection',
    )

    Schema: dict[str, Any] = Field(
        ...,
        Name='Schema',
        description='The schema for the collection',
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
    def deserialize(data: Union[dict[str, str], str]) -> 'IndalekoCollectionMetadataDataModel':
        '''Deserialize the data model from a dictionary.'''
        if isinstance(data, str):
            data = json.loads(data)
        elif not isinstance(data, dict):
            raise ValueError(f"Expected str or dict, got {type(data)}")
        if '_key' in data and 'key' not in data:  # Pydantic doesn't allow _key, ArangoDB uses it.
            data['key'] = data['_key']
            del data['_key']
        return IndalekoCollectionMetadataDataModel(**data)

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
                "QueryGuidelines": "Please use the primary key for queries",
                "Schema": IndalekoCollectionIndexDataModel.Config.json_schema_extra,
            }
        }


def main():
    '''This allows testing the data model.'''
    IndalekoCollectionMetadataDataModel.test_model_main()


if __name__ == '__main__':
    main()
