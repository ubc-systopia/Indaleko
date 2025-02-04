"""
This module defines the base data model for the Indaleko related data models.

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
import json
import uuid

from typing import Dict, Any, Type, TypeVar

from pydantic import BaseModel
from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

T = TypeVar('T', bound='IndalekoBaseModel')


class IndalekoBaseModel(BaseModel):
    '''
    This expands upon the base model and provides common methods that we use in meshing the
    Pydanic data model with ArangoDB and our usuage model.
    '''
    def serialize(self) -> Dict[str, Any]:
        '''Serialize the object to a dictionary'''
        return self.model_dump(exclude_unset=True, exclude_none=True)

    @classmethod
    def deserialize(cls: Type[T], data: Dict[str, Any]) -> T:
        '''Deserialize the object from a dictionary'''
        if isinstance(data, str):
            return cls(**json.loads(data))
        elif isinstance(data, dict):
            return cls(**data)
        else:
            raise ValueError(f"Expected str or dict, got {type(data)}")

    @classmethod
    def get_json_example(cls: Type[T]) -> dict:
        '''This will return a JSON compatible encoding as a python dictionary'''
        return json.loads(cls(**cls.Config.json_schema_extra['example']).model_dump_json())

    @classmethod
    def get_example(cls: Type[T]) -> T:
        return cls(**cls.get_json_example())

    @classmethod
    def build_arangodb_doc(cls: Type[T], _key: uuid.UUID = uuid.uuid4()) -> dict:
        '''
        Builds a dictionary that can be used to insert the data into ArangoDB.
        If a key is provided, it will be used, otherwise a random UUID is generated.
        '''
        ic(type(cls))
        data = json.loads(cls.model_dump_json())
        assert '_key' not in data, f"Key already exists in data: {data}"
        data['_key'] = str(_key)
        return json.dumps(data)

    @classmethod
    def get_json_schema(cls: Type[T]) -> dict:
        '''Returns the JSON schema for the data model in Python dictionary format.'''
        return cls.get_example().model_json_schema()

    @classmethod
    def get_arangodb_schema(cls: Type[T]) -> dict:
        '''Returns the JSON schema for the data model in the format required by ArangoDB'''
        return {
            "message": "Unfortunately, your data did not conform to the schema.",
            "level": "strict",
            "type": "json",
            "rule": cls.get_json_schema()
        }

    @classmethod
    def test_model_main(cls: Type[T]) -> None:
        '''This function can be used to do basic testing of the data model.'''
        data = cls.get_example()
        ic(data)
        ic(dir(data))
        print(data.model_dump_json(indent=2, exclude_unset=True, exclude_none=True))
        serial_data = data.serialize()
        data_check = cls.deserialize(serial_data)
        assert data_check == data
        ic(cls.get_arangodb_schema())


def main():
    '''This allows testing the data model.'''
    ic('Currently no test code for IndalekoBaseModel')


if __name__ == '__main__':
    main()
