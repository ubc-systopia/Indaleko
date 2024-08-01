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

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Annotated
from uuid import UUID
from icecream import ic

from apischema import schema, deserialize, serialize
from apischema.graphql import graphql_schema
from apischema.metadata import required
from apischema.json_schema import deserialization_schema, serialization_schema
from graphql import print_schema

from IndalekoDataModel import IndalekoDataModel

class IndalekoRecordDataModel:

    @dataclass
    class IndalekoRecord:
        '''Define data format for the Indaleko Record.'''
        SourceIdentifier: Annotated[IndalekoDataModel.SourceIdentifier,
                                    schema(description="The source identifier for the data."),
                                    required]
        Timestamp: Annotated[datetime,
                             schema(description="The timestamp of when this record was created."),
                             required] = field(default_factory=datetime.now)
        Attributes: Annotated[
            Dict[str, Any],
            schema(description="The attributes extracted from the source data."),
            required] = field(default_factory=dict)
        Data: Annotated[
            str,
             schema(description="The raw (uninterpreted) data from the source."),
             required] = field(default_factory=dict)

        @staticmethod
        def deserialize(data: Dict[str, Any]) -> 'IndalekoRecordDataModel.IndalekoRecord':
            '''Deserialize a dictionary to an object.'''
            return deserialize(IndalekoRecordDataModel.IndalekoRecord, data, additional_properties=True)

        @staticmethod
        def serialize(data) -> Dict[str, Any]:
            '''Serialize the object to a dictionary.'''
            return serialize(IndalekoRecordDataModel.IndalekoRecord, data)

    @staticmethod
    def get_indaleko_record() -> 'IndalekoRecordDataModel.IndalekoRecord':
        '''Return an Indaleko Record.'''
        return IndalekoRecordDataModel.IndalekoRecord(
            SourceIdentifier=IndalekoDataModel.\
                get_source_identifier(UUID('12345678-1234-5678-1234-567812345678')),
            Timestamp=datetime.now(),
            Attributes={'test': 'test'},
            Data='This is a test record'
        )

    @staticmethod
    def get_queries() -> list:
        '''Return the queries for the Indaleko Record.'''
        return [IndalekoRecordDataModel.get_indaleko_record]

    @staticmethod
    def get_types() -> list:
        '''Return the types for the Indaleko Record.'''
        return [IndalekoRecordDataModel.IndalekoRecord]

def main():
    '''Test code for IndalekoRecordDataModel.'''
    ic('GraphQL Schema:')
    ic(print_schema(graphql_schema(query=IndalekoRecordDataModel.get_queries(),
                                      types=IndalekoRecordDataModel.get_types())))
    ic(deserialization_schema(IndalekoRecordDataModel.IndalekoRecord))
    ic(serialization_schema(IndalekoRecordDataModel.IndalekoRecord))

if __name__ == "__main__":
    main()
