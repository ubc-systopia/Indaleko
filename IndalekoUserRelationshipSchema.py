'''
This module defines the schema for the Indaleko User Relationship data.

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
from jsonschema import validate, exceptions

from IndalekoRecordSchema import IndalekoRecordSchema

class IndalekoUserRelationshipSchema(IndalekoRecordSchema):
    '''Define the schema for use with the Relationship collection.'''

    @staticmethod
    def get_old_schema():
        relationship_schema =  {
            "$schema": "https://json-schema.org/draft/2020-12/schema#",
            "$id" : "https://activitycontext.work/schema/indaleko-user-relationship.json",
            "title" : "Indaleko User Relationship Schema",
            "description" : "Schema for the JSON representation of an Indaleko User Relationship, which is used for identifying related user identities.",
            "type" : "object",
            "rule" : {
                "properties" : {
                    "Identity1" : {
                        "type" : "string",
                        "format" : "uuid",
                        "description" : "The Indaleko UUID for the first user identity in the relationship.",
                    },
                    "Identity2" : {
                        "type" : "string",
                        "format" : "uuid",
                        "description" : "The Indaleko UUID for the second user identity in the relationship.",
                    },
                    "Metadata" :  {
                        "type" : "array",
                        "items" : {
                            "type" : "object",
                            "properties" : {
                                "UUID" : {
                                    "type" : "string",
                                    "format" : "uuid",
                                    "description" : "The UUID for this metadata.",
                                },
                                "Data" : {
                                    "type" : "string",
                                    "description" : "The data associated with this metadata.",
                                },
                            },
                            "required" : ["UUID", "Data"],
                        },
                        "description" : "Optional metadata associated with this relationship.",
                    },
                },
                "required" : ["Object1", "Object2"],
            },
        }
        assert 'Record' not in relationship_schema, 'Record must not be specified.'
        relationship_schema['rule']['properties']['Record'] = \
            IndalekoRecordSchema().get_json_schema()['rule']
        relationship_schema['rule']['required'].append('Record')
        return relationship_schema

    @staticmethod
    def is_valid_relationship(indaleko_relationship : dict) -> bool:
        '''Given a dict, determine if it is a valid Indaleko Relationship.'''
        assert isinstance(indaleko_relationship, dict), 'relationship must be a dict'
        valid = False
        try:
            validate(instance=indaleko_relationship,
                     schema=IndalekoUserRelationshipSchema().get_json_schema())
            valid = True
        except exceptions.ValidationError as error:
            print(f'Validation error: {error.message}')
        return valid


def main():
    """Test the IndalekoMachineConfigSchema class."""
    if IndalekoUserRelationshipSchema.is_valid_json_schema_dict(IndalekoUserRelationshipSchema().get_json_schema()):
        print('Schema is valid.')
    print(json.dumps(IndalekoUserRelationshipSchema().get_json_schema(), indent=4))

if __name__ == "__main__":
    main()
