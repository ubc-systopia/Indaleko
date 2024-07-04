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
from datetime import datetime
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

    @dataclass
    class SemanticAttribute:
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


def get_record()-> IndalekoDataModel.SourceIdentifier:
    '''Return a record'''
    record = IndalekoDataModel.SourceIdentifier(
        Identifier=UUID('12345678-1234-5678-1234-567812345678'),
        Version='1.0',
        Description='This is a test record'
    )
    return record

def get_timestamp() -> IndalekoDataModel.Timestamp:
    '''Return a timestamp'''
    timestamp = IndalekoDataModel.Timestamp(
        Label=UUID('12345678-1234-5678-1234-567812345678'),
        Value=datetime.now(),
        Description='This is a test timestamp'
    )
    return timestamp

def main():
    '''Test code for the IndalekoDataModel class'''
    print("This is the IndalekoDataModel module")
    print('graphql schema:')
    print(print_schema(graphql_schema(query=[get_record, get_timestamp],
                                      types=[IndalekoDataModel.SourceIdentifier,
                                             IndalekoDataModel.Timestamp])))

if __name__ == "__main__":
    main()
