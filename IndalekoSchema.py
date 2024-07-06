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
import jsonschema
import jsonschema.exceptions

from datetime import datetime
from apischema.graphql import graphql_schema
from graphql import print_schema

from IndalekoDataModel import IndalekoDataModel

class IndalekoSchema:
    '''This is the base class for schema within Indaleko'''

    template = {
            "$schema": "https://json-schema.org/draft/2020-12/schema#",
            "$id": "https://fsgeek.ca/indaleko/schema/record.json",
            "title": "Indaleko Schema",
            "description": "Schema for the JSON representation of an abstract record within Indaleko.",
            "type": "object",
        }

    def __init__(self):
        '''Initialize the schema'''
        if not hasattr(self, 'data_model'):
            self.data_model = IndalekoDataModel()
        if not hasattr(self, 'base_type'):
            self.base_type = IndalekoDataModel.SourceIdentifier
        if not hasattr(self, 'schema'):
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
        '''Is the schema assocated with this object valid?'''
        return IndalekoSchema.is_valid_schema_dict(self.schema)

    @staticmethod
    def is_valid_schema_dict(schema_dict : dict) -> bool:
        '''Given a dict representing a schema, determine if it is a valid schema.'''
        valid = False
        try:
            jsonschema.Draft202012Validator.check_schema(schema_dict)
            valid = True
        except jsonschema.exceptions.SchemaError as e:
            print(f'Schema Validation Error: {e}')
        return valid

    @staticmethod
    def get_source_identifier(identifier : uuid.UUID = None) -> IndalekoDataModel.SourceIdentifier:
        '''Return info on the source identifier'''
        record = IndalekoDataModel.SourceIdentifier(
            Identifier=identifier,
            Version='1.0',
            Description='This is a test record'
        )
        return record

    @staticmethod
    def get_indaleko_uuid(label : str = None, uuid : uuid.UUID = None) -> IndalekoDataModel.IndalekoUUID:
        '''Return a UUID'''
        indaleko_uuid = IndalekoDataModel.IndalekoUUID(
            UUID=uuid,
            Label=label
        )
        return indaleko_uuid

    @staticmethod
    def get_semantic_attribute(uuid : IndalekoDataModel.IndalekoUUID = None, data : str = None) -> IndalekoDataModel.SemanticAttribute:
        '''Return a semantic attribute'''
        semantic_attribute = IndalekoDataModel.SemanticAttribute(
            UUID=uuid,
            Data=data
        )
        return semantic_attribute

    @staticmethod
    def get_timestamp(label : uuid.UUID = None, value : datetime = None, description : str = None) -> IndalekoDataModel.Timestamp:
        '''Return a timestamp'''
        record = IndalekoDataModel.Timestamp(
            Label=label,
            Value=value,
            Description=description
        )
        return record

    def get_graphql_schema(self):
        '''Return the GraphQL schema for the Record collection.'''
        return graphql_schema(
            query=self.data_model.get_queries(),
            types=self.data_model.get_types()
        )

    def get_old_schema(self : 'IndalekoSchema') -> dict:
        '''There was no old schema for the base class.'''
        return self.get_schema()

    def get_schema(self : 'IndalekoSchema') -> dict:
        '''Return the JSON schema for the Indaleko Record'''
        schema_dict = self.template.copy()
        schema_dict['rule'] = apischema.json_schema.deserialization_schema(self.base_type)
        return schema_dict

    def print_graphql_schema(self, **kwargs) -> str:
        '''Return the GraphQL schema for the schema.'''
        return print_schema(graphql_schema(**kwargs))

    def schema_detail(self, **kwargs) -> None:
        '''Provide a basic function to check the schema detail.'''
        assert self.is_valid_schema_dict(self.get_old_schema()), 'Old schema is not valid.'
        print('Old schema is valid.')
        print('Old Schema:')
        print(json.dumps(self.get_old_schema(), indent=4))
        print('New Schema:')
        assert self.is_valid_schema(), 'New schema is not valid.'
        print('New schema is valid')
        print(json.dumps(self.get_schema(), indent=4))
        print('GraphQL Schema:')
        print(self.print_graphql_schema(**kwargs))



def main():
    '''Test code for IndalekoSchema.'''
    indaleko_schema = IndalekoSchema()
    indaleko_schema.schema_detail(query=IndalekoDataModel.get_queries(),
                                  types=IndalekoDataModel.get_types())

if __name__ == "__main__":
    main()
