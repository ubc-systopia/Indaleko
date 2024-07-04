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
import json
from typing import Dict, Any, Annotated
from uuid import UUID

from apischema import schema
from apischema.graphql import graphql_schema
from apischema.json_schema import deserialization_schema
from apischema.metadata import required
from graphql import print_schema
import jsonschema
from jsonschema import validate, Draft202012Validator, exceptions

from IndalekoDataModel import IndalekoDataModel

class IndalekoRecordDataModel(IndalekoDataModel):

    @dataclass
    class SourceIdentifier(IndalekoDataModel.SourceIdentifier):
        '''Define the source identifier for the Indaleko Record.'''
        pass

    @dataclass
    class IndalekoRecord:
        '''Define data format for the Indaleko Record.'''
        SourceIdentifier: Annotated['IndalekoRecordDataModel.SourceIdentifier',
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

def get_record() -> IndalekoRecordDataModel.IndalekoRecord:
    '''Return a record'''
    record = IndalekoRecordDataModel.IndalekoRecord(
        SourceIdentifier=IndalekoDataModel.SourceIdentifier(
            Identifier=UUID('12345678-1234-5678-1234-567812345678'),
            Version='1.0',
            Description='This is a test record'
        ),
        Timestamp=datetime.now(),
        Attributes={'Test': 'Test'},
        Data='This is a test data record'
    )
    return record

def main():
    '''Test code for IndalekoRecordDataModel.'''
    print('GraphQL Schema:')
    print(print_schema(graphql_schema(query=[get_record], types=[IndalekoRecordDataModel.IndalekoRecord])))

if __name__ == "__main__":
    main()
