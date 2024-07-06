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

from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Dict, Any, Annotated, Optional
from uuid import UUID
from apischema import schema
from apischema.graphql import graphql_schema
from apischema.json_schema import deserialization_schema
from apischema.metadata import required
from graphql import print_schema

class IndalekoDataModel:
    '''This is the base class for the IndalekoDataModel'''

    @dataclass
    class SourceIdentifier:
        Identifier: Annotated[
            UUID,
            schema(description="The identifier of the source of the data."),
            required
            ]
        Version: Annotated[
            str,
            schema(description="The version of the source of the ,data."),
            required
            ]
        Description: Annotated[
            str,
            schema(description="A human readable description of the source of the data."),
            required
            ]

    @staticmethod
    def get_source_identifier(uuid : UUID) -> 'IndalekoDataModel.SourceIdentifier':
        '''Lookup a source identifier'''
        return IndalekoDataModel.SourceIdentifier(
            Identifier=uuid,
            Version='1.0',
            Description='This is a test record'
        )
    @dataclass
    class Timestamp:
        Label: Annotated[
            UUID,
            schema(description="UUID representing the semantic meaning of this timestamp."),
            required
        ]
        Value: Annotated[
            datetime,
            schema(description="Timestamp in ISO date and time format.", format="date-time"),
            required
        ]
        Description: Annotated[
            Optional[str],
            schema(description="Description of the timestamp.")
        ] = None

    @staticmethod
    def get_timestamp(uuid : UUID,
                      value : datetime = datetime.now(UTC),
                      description : str = 'Prototype description') -> 'IndalekoDataModel.Timestamp':
        '''Lookup a timestamp'''
        return IndalekoDataModel.Timestamp(
            Label=uuid,
            Value=value,
            Description=description
        )
    @dataclass
    class IndalekoUUID:
        UUID: Annotated[
            UUID,
            schema(description="A Universally Unique Identifier", format="uuid"),
            required
        ]

        Label: Annotated[
            str,
            schema(description="A human-readable label for the UUID.")
        ]

    @staticmethod
    def get_indaleko_uuid() -> 'IndalekoDataModel.IndalekoUUID':
        '''Lookup a UUID'''
        return IndalekoDataModel.IndalekoUUID(
            UUID=UUID('00000000-0000-0000-0000-000000000000'),
            Label='This is a dummy label.'
        )

    @dataclass
    class SemanticAttribute:
        '''
        A semantic attribute is something that relates to the semantics of
        the data itself.  This is an abstract model because I don't know what
        the meaning of the semantic attribute are - I just collect them. At some
        point we'll need to know what a semantic attribute represents for it to
        be useful, but indexing isn't about understanding, it's about collecting
        data.
        '''
        UUID: Annotated[
            'IndalekoDataModel.IndalekoUUID',
            schema(description="The UUID for this attribute.", format="uuid"),
            required
        ]
        Data : Annotated[
            str,
            schema(description="The data associated with this attribute."),
            required
        ]

    @staticmethod
    def get_semantic_attribute() -> 'IndalekoDataModel.SemanticAttribute':
        '''Lookup a semantic attribute'''
        return IndalekoDataModel.SemanticAttribute(
            UUID=UUID('00000000-0000-0000-0000-000000000000'),
            Data='This is a dummy label for the semantic attribute.'
        )

    @staticmethod
    def get_queries() -> list:
        '''Return the queries for the IndalekoDataModel'''
        return [IndalekoDataModel.get_source_identifier,
                IndalekoDataModel.get_timestamp,
                IndalekoDataModel.get_indaleko_uuid,
                IndalekoDataModel.get_semantic_attribute]

    @staticmethod
    def get_types() -> list:
        '''Return the types for the IndalekoDataModel'''
        return [IndalekoDataModel.SourceIdentifier,
                IndalekoDataModel.Timestamp,
                IndalekoDataModel.IndalekoUUID,
                IndalekoDataModel.SemanticAttribute]

def main():
    '''Test code for the IndalekoDataModel class'''
    print("This is the IndalekoDataModel module")
    print('graphql schema:')
    print(print_schema(graphql_schema(query=IndalekoDataModel.get_queries(),
                                      types=IndalekoDataModel.get_types())))

if __name__ == "__main__":
    main()
