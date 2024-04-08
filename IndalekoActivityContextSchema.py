'''
This module defines the database schema for Activity Context Information.

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

class IndalekoActivityContextSchema(IndalekoRecordSchema):
    '''Define the schema for use with the ActivityContext collection.'''

    @staticmethod
    def get_schema():
        activity_data_provider_schema = {
            '''
            This schema relates to the machine configuration collection,
            which captures meta-data about the machine where the data was indexed.
            '''
            "$schema": "https://json-schema.org/draft/2020-12/schema#",
            "$id": "https://activitycontext.work/schema/ActivityContext.json",
            "title": "Data source schema",
            "description": "This schema describes information about activity provider.",
            "type": "object",
            "rule" : {
                "ActivityContextIdentifier" : {
                    "type" : "string",
                    "description" : "UUID of this activity data.",
                    "format": "uuid",
                },
                "Timestamps" : {
                    "type" : "array",
                    "properties" : {
                        "Label" : {
                            "type" : "string",
                            "description" : "UUID representing the semantic meaning of this timestamp.",
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
                "DataVersion" : {
                    "type" : "string",
                    "description" : "Version of the activity data.",
                },
                "required" : ["ActivityContextIdentifier",
                              "ActivityType"],
            }
        }
        assert 'Record' not in activity_data_provider_schema['rule'], \
            'Record should not be in activity registration schema.'
        activity_data_provider_schema['rule']['Record'] = IndalekoRecordSchema.get_schema()
        activity_data_provider_schema['rule']['required'].append('Record')
        return activity_data_provider_schema


def main():
    '''Test the IndalekoActivityContextSchema class.'''
    if IndalekoActivityContextSchema.is_valid_schema(IndalekoActivityContextSchema.get_schema()):
        print('IndalekoActivityContextSchema is a valid schema.')
    else:
        print('IndalekoActivityContextSchema is not a valid schema.')
    print(json.dumps(IndalekoActivityContextSchema.get_schema(), indent=4))

if __name__ == '__main__':
    main()
