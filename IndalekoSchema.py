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
import uuid

import apischema
import graphql
import jsonschema

from IndalekoDataModel import IndalekoDataModel

class IndalekoSchema:
    '''This is the base class for schema within Indaleko'''

    template = {
            "$schema": "https://json-schema.org/draft/2020-12/schema#",
            "$id": "https://fsgeek.ca/indaleko/schema/record.json",
            "title": "Indaleko Record Schema",
            "description": "Schema for the JSON representation of an abstract record within Indaleko.",
            "type": "object",
        }

    def __init__(self):
        '''Initialize the schema'''
        self.base_type = IndalekoDataModel.SourceIdentifier
        self.schema = self.get_schema()

    def check_against_schema(self, data: dict) -> bool:
        '''Check the data against the schema'''
        assert isinstance(data, dict), 'data must be a dictionary'
        assert isinstance(self.schema, IndalekoSchema), 'schema must be a dictionary'
        try:
            jsonschema.validate(data, self.schema)
            return True
        except jsonschema.exceptions.ValidationError as error:
            print(f"Validation error: {error}")
            return False

    def is_valid_record(self, indaleko_record : dict) -> bool:
        '''Check if the record is valid'''
        assert isinstance(indaleko_record, dict), 'indaleko_record must be a dictionary'
        return self.check_against_schema(indaleko_record)

    def is_valid_schema(self) -> bool:
        '''Given a dict representing a schema, determine if it is a valid schema.'''
        valid = False
        try:
            jsonschema.Draft202012Validator.check_schema(self.schema)
            valid = True
        except jsonschema.exceptions.Schema as e:
            print(f'Schema Validation Error: {e}')
        return valid

    @staticmethod
    def get_record(identifier : uuid.UUID = None) -> IndalekoDataModel.SourceIdentifier:
        '''Return info on the source identifier'''
        record = IndalekoDataModel.SourceIdentifier(
            Identifier=identifier,
            Version='1.0',
            Description='This is a test record'
        )
        return record

    @staticmethod
    def get_records() -> list[IndalekoDataModel.SourceIdentifier]:
        '''Return all records'''
        return [IndalekoSchema.get_record() for _ in range(10)]

    @staticmethod
    def get_graphql_schema():
        '''Return the GraphQL schema for the Record collection.'''
        return apischema.graphql.graphql_schema(
            query=[IndalekoSchema.get_record],
            types=[IndalekoDataModel.SourceIdentifier]
        )

    def get_schema(self : 'IndalekoSchema') -> dict:
        '''Return the JSON schema for the Indaleko Record'''
        schema_dict = self.template.copy()
        schema_dict['rule'] = apischema.json_schema.deserialization_schema(self.base_type)
        return schema_dict

def main():
    '''Test code for IndalekoSchema.'''
    indaleko_schema = IndalekoSchema()
    if indaleko_schema.is_valid_schema():
        print('Schema is valid.')
    print('JSON Schema:')
    print(json.dumps(indaleko_schema.get_schema(), indent=4))
    print('GraphQL Schema:')
    print(graphql.print_schema(indaleko_schema.get_graphql_schema()))

if __name__ == "__main__":
    main()
