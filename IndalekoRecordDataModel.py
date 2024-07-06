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

from apischema import schema
from apischema.graphql import graphql_schema
from apischema.metadata import required
from graphql import print_schema
import jsonschema
from jsonschema import validate, Draft202012Validator, exceptions

from IndalekoDataModel import IndalekoDataModel

class IndalekoRecordDataModel(IndalekoDataModel):

    @dataclass
    class IndalekoRecord:
        '''Define data format for the Indaleko Record.'''
        SourceIdentifier: Annotated[IndalekoDataModel.SourceIdentifier,
                                    schema(description="The source identifier for the data."),
                                    required]
        Timestamp: Annotated[datetime,
                             schema(description="The timestamp of when this record was created."),
                             required]
        Attributes: Annotated[
            Dict[str, Any],
            schema(description="The attributes extracted from the source data."),
            required] = field(default_factory=dict)
        Data: Annotated[
            str,
             schema(description="The raw (uninterpreted) data from the source."),
             required] = field(default=None)

    @staticmethod
    def get_indaleko_record() -> 'IndalekoRecordDataModel.IndalekoRecord':
        '''Return an Indaleko Record.'''
        return IndalekoRecordDataModel.IndalekoRecord(
            SourceIdentifier=IndalekoDataModel.get_source_identifier(UUID('12345678-1234-5678-1234-567812345678')),
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
    print('GraphQL Schema:')
    print(print_schema(graphql_schema(query=IndalekoRecordDataModel.get_queries(),
                                      types=IndalekoRecordDataModel.get_types())))

if __name__ == "__main__":
    main()
