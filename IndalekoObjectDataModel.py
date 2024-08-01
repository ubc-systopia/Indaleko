'''
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
'''
import json
import jsonschema
import apischema
from datetime import datetime, UTC
from graphql import print_schema
from uuid import UUID
from typing import Annotated, List, Optional
from dataclasses import dataclass, field
from apischema.json_schema import deserialization_schema, serialization_schema
from apischema.graphql import graphql_schema
from icecream import ic

from IndalekoDataModel import IndalekoDataModel, IndalekoUUID
from IndalekoRecordDataModel import IndalekoRecordDataModel

class IndalekoObjectDataModel(IndalekoRecordDataModel):
    '''This is the data model for the Indaleko Object type.'''
    @dataclass
    class IndalekoObject:
        '''Define data format for the Indaleko Object.'''
        Record : IndalekoRecordDataModel.IndalekoRecord

        URI : Annotated[
            str,
            apischema.schema(description="The URI for the object."),
            apischema.metadata.required
        ]

        ObjectIdentifier : Annotated[
            UUID,
            apischema.schema(description="UUID representing this object."),
            apischema.metadata.required
        ]

        Timestamps : Annotated[
            List[IndalekoDataModel.Timestamp],
            apischema.schema(description="The timestamps for the object."),
            apischema.metadata.required
        ]

        Size : Annotated[
            int,
            apischema.schema(description="The size of the object in bytes.")
        ]

        SemanticAttributes : Annotated[
            Optional[List[IndalekoDataModel.SemanticAttribute]],
            apischema.schema(description="The semantic attributes for the object.")
        ] = field(default_factory=list)

        Label : Annotated[
            Optional[str],
            apischema.schema(description="The object label (like a file name).")
        ] = None

        LocalIdentifier : Annotated[
            Optional[str],
            apischema.schema(description="The local identifier used "\
                             "by the storage system to find this, such "\
                                "as a UUID or inode number."),
        ] = None


        @staticmethod
        def deserialize(data: dict) -> 'IndalekoObjectDataModel.IndalekoObject':
            '''Deserialize a dictionary to an object.'''
            return apischema.deserialize(IndalekoObjectDataModel.IndalekoObject,
                                         data,
                                         additional_properties=True)

        @staticmethod
        def serialize(data) -> dict:
            '''Serialize the object to a dictionary.'''
            ic(data)
            candidate = apischema.serialize(IndalekoObjectDataModel.IndalekoObject,
                                            data,
                                            additional_properties=True)
            return candidate



    @staticmethod
    def get_indaleko_object(object_identifier : UUID) -> 'IndalekoObjectDataModel.IndalekoObject':
        '''Return an Indaleko Object.'''
        return IndalekoObjectDataModel.IndalekoObject(
            Record=None,
            Label='Test Object',
            URI='http://www.example.com',
            ObjectIdentifier=IndalekoUUID(object_identifier, 'Test Object'),
            LocalIdentifier='1',
            Timestamps=[IndalekoDataModel.Timestamp(
                UUID('12345678-1234-5678-1234-567812345678'),
                datetime.now(UTC),
                'Test Timestamp')],
            Size=1024,
            SemanticAttributes=[IndalekoDataModel\
                                .get_semantic_attribute(\
                                    IndalekoUUID(UUID('12345678-1234-5678-1234-567812345678'),
                                                 'Test Attribute'))]
            )

    @staticmethod
    def get_queries() -> list:
        '''Return the queries for the Indaleko Object.'''
        return [IndalekoObjectDataModel.get_indaleko_object]

    @staticmethod
    def get_types() -> list:
        '''Return the types for the Indaleko Object.'''
        return [IndalekoObjectDataModel.IndalekoObject]

def main():
    '''Test code for IndalekoObjectDataModel.'''
    ic('GraphQL Schema:')
    ic(print_schema(graphql_schema(query=IndalekoObjectDataModel.get_queries(),
                                      types=IndalekoObjectDataModel.get_types())))
    unpack_schema = deserialization_schema(IndalekoObjectDataModel.IndalekoObject, additional_properties=True)
    pack_schema = serialization_schema(IndalekoObjectDataModel.IndalekoObject, additional_properties=True)
    json_unpack_schema = json.dumps(unpack_schema, indent=2)
    print(json_unpack_schema)
    json_pack_schema = json.dumps(pack_schema, indent=2)
    print(json_pack_schema)

    data_object = {
        "Record": {
            "Data": "xQL6xQL3eyJzdF9hdGltZSI6IDE2OTMyMjM0NTYuMzMzNDI4MSwgInN0X2F0aW1lX25zIjogMTY5MzIyMzQ1NjMzMzQyODEwMCwgInN0X2JpcnRodGltZSI6IDE2ODU4OTEyMjEuNTU5MTkxNywgInN0X2JpcnRodGltZV9ucyI6IDE2ODU4OTEyMjE1NTkxOTE3MDAsICJzdF9jdGltZSI6IDE2ODU4OTEyMjEuNTU5MTkxNywgInN0X2N0aW1lX25zIjogMTY4NTg5MTIyMTU1OTE5MTcwMCwgInN0X2RldiI6IDI3NTYzNDcwOTQ5NTU2NDk1OTksICJzdF9maWxlX2F0dHJpYnV0ZXMiOiAzMiwgInN0X2dpZCI6IDAsICJzdF9pbm8iOiAxMTI1ODk5OTEwMTE5ODMyLCAic3RfbW9kZSI6IDMzMjc5LCAic3RfbXRpbWUiOiAxNjg1ODkxMjIxLjU1OTcxNTcsICJzdF9tdGltZV9ucyI6IDE2ODU4OTEyMjE1NTk3MTU3MDAsICJzdF9ubGluayI6IDEsICJzdF9yZXBhcnNlX3RhZyI6IDAsICJzdF9zaXplIjogMTQxMDEyMCwgInN0X3VpZCI6IDAsICJOYW1lIjogInJ1ZnVzLTQuMS5leGUiLCAiUGF0aCI6ICJkOlxcZGlzdCIsICJVUkkiOiAiXFxcXD9cXFZvbHVtZXszMzk3ZDk3Yi0yY2E1LTExZWQtYjJmYy1iNDBlZGU5YTVhM2N9XFxkaXN0XFxydWZ1cy00LjEuZXhlIiwgIkluZGV4ZXIiOiAiMDc5M2I0ZDUtZTU0OS00Y2I2LTgxNzctMDIwYTczOGI2NmI3IiwgIlZvbHVtZSBHVUlEIjogIjMzOTdkOTdiLTJjYTUtMTFlZC1iMmZjLWI0MGVkZTlhNWEzYyIsICJPYmplY3RJZGVudGlmaWVyIjogIjJjNzNkNmU1LWVhYmEtNGYwYS1hY2YzLWUwMmM1MjlmMDk3YSJ9",
            "Attributes": {
                "st_atime": 1693223456.3334281,
                "st_atime_ns": 1693223456333428100,
                "st_birthtime": 1685891221.5591917,
                "st_birthtime_ns": 1685891221559191700,
                "st_ctime": 1685891221.5591917,
                "st_ctime_ns": 1685891221559191700,
                "st_dev": 2756347094955649599,
                "st_file_attributes": 32,
                "st_gid": 0,
                "st_ino": 1125899910119832,
                "st_mode": 33279,
                "st_mtime": 1685891221.5597157,
                "st_mtime_ns": 1685891221559715700,
                "st_nlink": 1, "st_reparse_tag": 0,
                "st_size": 1410120,
                "st_uid": 0,
                "Name": "rufus-4.1.exe",
                "Path": "d:\\dist",
                "URI": "\\\\?\\Volume{3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c}\\dist\\rufus-4.1.exe",
                "Indexer": "0793b4d5-e549-4cb6-8177-020a738b66b7",
                "Volume GUID": "3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c",
                "ObjectIdentifier": "2c73d6e5-eaba-4f0a-acf3-e02c529f097a"
            },
            "SourceIdentifier": {
                "Identifier": "429f1f3c-7a21-463f-b7aa-cd731bb202b1",
                "Version": "1.0", "Description": None
            },
            "Timestamp": "2024-07-30T23:38:48.319654+00:00"
        },
        "_key": "2c73d6e5-eaba-4f0a-acf3-e02c529f097a",
        "URI": "\\\\?\\Volume{3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c}\\dist\\rufus-4.1.exe",
        "ObjectIdentifier": "2c73d6e5-eaba-4f0a-acf3-e02c529f097a",
        "Timestamps": [
            {
                "Label": "6b3f16ec-52d2-4e9b-afd0-e02a875ec6e6",
                "Value": "2023-06-04T15:07:01.559192+00:00",
                "Description": "Created"
            },
            {
                "Label": "434f7ac1-f71a-4cea-a830-e2ea9a47db5a",
                "Value": "2023-06-04T15:07:01.559716+00:00",
                "Description": "Modified"
            },
            {
                "Label": "581b5332-4d37-49c7-892a-854824f5d66f",
                "Value": "2023-08-28T11:50:56.333428+00:00",
                "Description": "Accessed"
            },
            {
                "Label": "3bdc4130-774f-4e99-914e-0bec9ee47aab",
                "Value": "2023-06-04T15:07:01.559192+00:00",
                "Description": "Changed"
            }
        ],
        "Size": 1410120,
        "Machine": "2e169bb7-0024-4dc1-93dc-18b7d2d28190",
        "Volume": "3397d97b-2ca5-11ed-b2fc-b40ede9a5a3c",
        "UnixFileAttributes": "S_IFREG",
        "WindowsFileAttributes": "FILE_ATTRIBUTE_ARCHIVE",
        "SemanticAttributes" : [],
        "Label" : None,
        "LocalIdentifier" : None
    }
    indaleko_object = IndalekoObjectDataModel.IndalekoObject.deserialize(data_object)
    ic(indaleko_object)
    serialized_object = IndalekoObjectDataModel.IndalekoObject.serialize(indaleko_object)
    ic(serialized_object)

    try:
        jsonschema.validate(instance=data_object, schema=unpack_schema)
    except jsonschema.exceptions.ValidationError as error:
        print(f'Validation error: {error.message}')

    try:
        jsonschema.validate(instance=data_object, schema=pack_schema)
    except jsonschema.exceptions.ValidationError as error:
        print(f'Validation error: {error.message}')
if __name__ == '__main__':
    main()
