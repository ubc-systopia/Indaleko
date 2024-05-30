'''
This module defines the database schema for Activity Providers.

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

from IndalekoRecordSchema import IndalekoRecordSchema

class IndalekoActivityProviderSchema(IndalekoRecordSchema):
    '''Define the schema for use with the ActivityProvider collection.'''

    @staticmethod
    def get_schema():
        activity_data_provider_schema = {
            '''
            This schema relates to the machine configuration collection,
            which captures meta-data about the machine where the data was indexed.
            '''
            "$schema": "https://json-schema.org/draft/2020-12/schema#",
            "$id": "https://activitycontext.work/schema/activityprovider.json",
            "title": "Data source schema",
            "description": "This schema describes information about activity provider.",
            "type": "object",
            "rule" : {
                "ActivityDataIdentifier" : {
                    "type" : "string",
                    "description" : "UUID of this activity data.",
                    "format": "uuid",
                },
                "ActivityProviderIdentifier" : {
                    "type" : "string",
                    "description" : "UUID of the activity provider.",
                    "format": "uuid",
                },
                "Timestamps" : {
                    "type" : "array",
                    "properties" : {
                        "Label" : {
                            "type" : "string",
                            "description" :
                            "UUID representing the semantic meaning of this timestamp.",
                            "format": "uuid",
                        },
                        "Value" : {
                            "type" : "string",
                            "description" : "Timestamp in ISO date and time format.",
                            "format" : "date-time",
                        },
                        "Description" : {
                            "type" : "string",
                            "description" : "Description of the timestamp.",
                        },
                    },
                    "required" : [
                        "Label",
                        "Value"
                    ],
                    "description" : "List of timestamps with UUID-based semantic meanings associated with this object."
                },
                "ActivityType" : {
                    "type" : "string",
                    "description" : "UUID identifying the type of activity.",
                    "format": "uuid",
                },
                "DataVersion" : {
                    "type" : "string",
                    "description" : "Version of the activity data.",
                },
                "Entities" : {
                    "type" : "array",
                    "properties" : {
                        "Label" : {
                            "type" : "string",
                            "description" : "UUID representing the semantic meaning of this entity.",
                            "format": "uuid",
                        },
                        "Value" : {
                            "type" : "string",
                            "description" : "UUID representing the entity.",
                            "format" : "uuid",
                        },
                        "Description" : {
                            "type" : "string",
                            "description" : "Description of the entity.",
                        },
                    },
                    "required" : [
                        "Label",
                        "Value"
                    ],
                    "description" : "List of users associated with this object."
                },
                "Active" : bool,
                "required" : ["ActivityDataIdentifier",
                              "ActivityProviderIdentifier",
                              "ActivityType",
                              "Active"],
            }
        }
        assert 'Record' not in activity_data_provider_schema['rule'], \
            'Record should not be in activity registration schema.'
        activity_data_provider_schema['rule']['Record'] = IndalekoRecordSchema.get_schema()
        activity_data_provider_schema['rule']['required'].append('Record')
        return activity_data_provider_schema


def main():
    '''Test the IndalekoActivityProviderSchema class.'''
    if IndalekoActivityProviderSchema.is_valid_schema(IndalekoActivityProviderSchema.get_schema()):
        print('IndalekoActivityProviderSchema is a valid schema.')
    else:
        print('IndalekoActivityProviderSchema is not a valid schema.')
    print(json.dumps(IndalekoActivityProviderSchema.get_schema(), indent=4))

if __name__ == '__main__':
    main()
