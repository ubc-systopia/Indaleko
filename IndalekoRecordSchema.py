'''
This module defines the database schema for any database record conforming to
the Indaleko Record requirements.
'''
import json
import jsonschema
from jsonschema import validate, Draft202012Validator, exceptions

class IndalekoRecordSchema:
    '''
    This is the schema for the Indaleko Record. Note that it is inherited and
    merged by other classes that derive from this base type.
    '''
    @staticmethod
    def check_against_schema(data : dict, schema : dict) -> bool:
        '''Given a dict, determine if it conforms to the given schema.'''
        assert isinstance(data, dict), 'data must be a dict'
        assert isinstance(schema, dict), 'schema must be a dict'
        valid = False
        try:
            validate(instance=data, schema=IndalekoRecordSchema.get_schema())
            valid = True
        except jsonschema.exceptions.ValidationError as error:
            print(f'Validation error: {error.message}')
        return valid

    @staticmethod
    def is_valid_record(indaleko_record : dict) -> bool:
        '''Given a dict, determine if it is a valid Indaleko Record.'''
        assert isinstance(indaleko_record, dict), 'record must be a dict'
        valid = False
        try:
            validate(instance=indaleko_record, schema=IndalekoRecordSchema.get_schema())
            valid = True
        except jsonschema.exceptions.ValidationError as error:
            print(f'Validation error: {error.message}')
        return valid

    @staticmethod
    def is_valid_schema(schema : dict) -> bool:
        '''Given a dict representing a schema, determine if it is a valid schema.'''
        valid = False
        try:
            Draft202012Validator.check_schema(schema)
            valid = True
        except exceptions.Schema as e:
            print(f'Schema Validation Error: {e}')

        return valid

    @staticmethod
    def get_schema():
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

def main():
    '''Test code for IndalekoRecordSchema.'''
    if IndalekoRecordSchema.is_valid_schema(IndalekoRecordSchema.get_schema()):
        print('Schema is valid.')
    print(json.dumps(IndalekoRecordSchema.get_schema(), indent=4))

if __name__ == "__main__":
    main()
