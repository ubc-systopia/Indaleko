'''
This module defines the schema for the Indaleko Relationship data.
'''
import json
from jsonschema import validate, exceptions

from IndalekoRecordSchema import IndalekoRecordSchema

class IndalekoRelationshipSchema(IndalekoRecordSchema):
    '''Define the schema for use with the Relationship collection.'''

    @staticmethod
    def get_schema():
        relationship_schema =  {
            "$schema": "https://json-schema.org/draft/2020-12/schema#",
            "$id" : "https://activitycontext.work/schema/indaleko-relationship.json",
            "title" : "Indaleko Relationship Schema",
            "description" : "Schema for the JSON representation of an Indaleko Relationship, which is used for identifying related objects.",
            "type" : "object",
            "rule" : {
                "properties" : {
                    "object1" : {
                        "type" : "string",
                        "format" : "uuid",
                        "description" : "The Indaleko UUID for the first object in the relationship.",
                    },
                    "object2" : {
                        "type" : "string",
                        "format" : "uuid",
                        "description" : "The Indaleko UUID for the second object in the relationship.",
                    },
                    "relationship" : {
                        "type" : "string",
                        "description" : "The UUID specifying the specific relationship between the two objects.",
                        "format" : "uuid",
                    },
                    "metadata" :  {
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
                "required" : ["object1", "object2" , "relationship"],
            },
        }
        assert 'Record' not in relationship_schema, 'Record must not be specified.'
        relationship_schema['rule']['properties']['Record'] = IndalekoRecordSchema.get_schema()['rule']
        relationship_schema['rule']['required'].append('Record')
        return relationship_schema

    @staticmethod
    def is_valid_relationship(indaleko_relationship : dict) -> bool:
        '''Given a dict, determine if it is a valid Indaleko Relationship.'''
        assert isinstance(indaleko_relationship, dict), 'relationship must be a dict'
        valid = False
        try:
            validate(instance=indaleko_relationship, schema=IndalekoRelationshipSchema.get_schema())
            valid = True
        except exceptions.ValidationError as error:
            print(f'Validation error: {error.message}')
        return valid


def main():
    """Test the IndalekoMachineConfigSchema class."""
    if IndalekoRelationshipSchema.is_valid_schema(IndalekoRelationshipSchema.get_schema()):
        print('Schema is valid.')
    print(json.dumps(IndalekoRelationshipSchema.get_schema(), indent=4))

if __name__ == "__main__":
    main()
