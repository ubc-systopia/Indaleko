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

from datetime import datetime
import json
from uuid import UUID

from apischema.graphql import graphql_schema
from graphql import print_schema

from IndalekoRecordDataModel import IndalekoRecordDataModel
from IndalekoSchema import IndalekoSchema

class IndalekoRecordSchema(IndalekoSchema):
    '''
    This is the schema for the Indaleko Record. Note that it is inherited and
    merged by other classes that derive from this base type.
    '''
    def __init__(self):
        '''Initialize the schema.'''
        if not hasattr(self, 'base_type'):
            self.base_type = IndalekoRecordDataModel.IndalekoRecord
        super().__init__()

    @staticmethod
    def get_old_schema():
        """
        Return the schema for data managed by this class.
        """
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema#",
            "$id": "https://fsgeek.ca/indaleko/schema/record.json",
            "title": "Indaleko Record Schema",
            "description": "Schema for the JSON representation of an abstract record within Indaleko.",
            "type": "object",
            "rule" : {
                "type" : "object",
                "properties": {
                    "Source Identifier": {
                        "type" : "object",
                        "properties" : {
                            "Identifier" : {
                                "type" : "string",
                                "description" : "The identifier of the source of the data.",
                                "format" : "uuid",
                            },
                            "Version" : {
                                "type" : "string",
                                "description" : "The version of the source of the data.",
                            },
                            "Description" : {
                                "type" : "string",
                                "description" : "A human readable description of the source of the data.",
                            }
                        },
                        "required" : ["Identifier", "Version"],
                    },
                    "Timestamp": {
                        "type" : "string",
                        "description" : "The timestamp of when this record was created.",
                        "format" : "date-time",
                    },
                    "Attributes" : {
                        "type" : "object",
                        "description" : "The attributes extracted from the source data.",
                    },
                    "Data" : {
                        "type" : "string",
                        "description" : "The raw (uninterpreted) data from the source.",
                    }
                },
                "required": ["Source Identifier", "Timestamp", "Attributes", "Data"]
            }
        }

    @staticmethod
    def get_record(identifier : UUID = None) -> 'IndalekoRecordDataModel.IndalekoRecord':
        '''Return the record with the given ID.'''
        return IndalekoRecordDataModel.IndalekoRecord(
            SourceIdentifier = IndalekoRecordDataModel.SourceIdentifier(
                Identifier = identifier,
                Version = '1.0',
                Description = 'Test Source'
            ),
            Timestamp = datetime.now(),
            Attributes={},
            Data='Sample Data'
        )

    @staticmethod
    def get_records() -> list[IndalekoRecordDataModel.IndalekoRecord]:
        '''Return all records.'''
        return [IndalekoRecordDataModel.IndalekoRecord(
            SourceIdentifier = IndalekoRecordDataModel.SourceIdentifier(
                Identifier = UUID('12345678-1234-5678-1234-567812345678'),
                Version = '1.0',
                Description = 'Test Source'
            ),
            Timestamp = datetime.now(),
            Attributes={},
            Data='Sample Data'
        )]

    @staticmethod
    def get_graphql_schema():
        '''Return the GraphQL schema for the record.'''
        gql_schema = graphql_schema(
            query=[IndalekoRecordSchema.get_record, IndalekoRecordSchema.get_records],
            types=[IndalekoRecordDataModel.SourceIdentifier, IndalekoRecordDataModel.IndalekoRecord])
        return gql_schema



def main():
    '''Test code for IndalekoRecordSchema.'''
    test_schema = IndalekoRecordSchema()
    if test_schema.is_valid_schema():
        print('Schema is valid.')
    print(json.dumps(test_schema.get_old_schema(), indent=4))
    print(json.dumps(test_schema.get_schema(), indent=4))
    print('GraphQL Schema:')
    print(print_schema(test_schema.get_graphql_schema()))

if __name__ == "__main__":
    main()
