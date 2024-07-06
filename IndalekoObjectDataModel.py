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
import apischema
from datetime import datetime, UTC
from graphql import print_schema
from uuid import UUID
from typing import Annotated, List
from dataclasses import dataclass
from apischema.graphql import graphql_schema


from IndalekoDataModel import IndalekoDataModel
from IndalekoRecordDataModel import IndalekoRecordDataModel

class IndalekoObjectDataModel(IndalekoRecordDataModel):
    '''This is the data model for the Indaleko Object type.'''
    @dataclass
    class IndalekoObject:
        Label : Annotated[
            str,
            apischema.schema(description="The object label (like a file name).")
        ]

        URI : Annotated[
            str,
            apischema.schema(description="The URI for the object."),
            apischema.metadata.required
        ]

        ObjectIdentifier : IndalekoDataModel.IndalekoUUID

        LocalIdentifier : Annotated[
            str,
            apischema.schema(description="The local identifier used "\
                             "by the storage system to find this, such "\
                                "as a UUID or inode number."),
        ]

        Timestamps : Annotated[
            List[IndalekoDataModel.Timestamp],
            apischema.schema(description="The timestamps for the object."),
            apischema.metadata.required
        ]

        Size : Annotated[
            int,
            apischema.schema(description="The size of the object in bytes."),
            apischema.metadata.required
        ]

        RawData : Annotated[
            str,
            apischema.schema(description="The raw data for the object.",
                             encoding="base64",
                             media_type="application/octet-stream"),
        ]

        SemanticAttributes : Annotated[
            List[IndalekoDataModel.SemanticAttribute],
            apischema.schema(description="The semantic attributes for the object."),
        ]

    @staticmethod
    def get_indaleko_object() -> 'IndalekoObjectDataModel.IndalekoObject':
        '''Return an Indaleko Object.'''
        return IndalekoObjectDataModel.IndalekoObject(
            Label='Test Object',
            URI='http://www.example.com',
            ObjectIdentifier=IndalekoDataModel.IndalekoUUID(UUID('12345678-1234-5678-1234-567812345678'), 'Test Object'),
            LocalIdentifier='12345678-1234-5678-1234-567812345678',
            Timestamps=[IndalekoDataModel.Timestamp(
                UUID('12345678-1234-5678-1234-567812345678'),
                datetime.now(UTC),
                'Test Timestamp')],
            Size=1024,
            RawData='This is a test object.',
            SemanticAttributes=[IndalekoDataModel.get_semantic_attribute()]
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
    print('GraphQL Schema:')
    print(print_schema(graphql_schema(query=IndalekoObjectDataModel.get_queries(),
                                      types=IndalekoObjectDataModel.get_types())))

if __name__ == '__main__':
    main()
