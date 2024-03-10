'''
This module defines the database schema for the ActivityRegistration collection.

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

class IndalekoActivityRegistrationSchema(IndalekoRecordSchema):
    '''Define the schema for use with the ActivityRegistration collection.'''

    @staticmethod
    def get_schema():
        activity_registration_schema = {
            '''
            This schema relates to the machine configuration collection,
            which captures meta-data about the machine where the data was indexed.
            '''
            "$schema": "https://json-schema.org/draft/2020-12/schema#",
            "$id": "https://activitycontext.work/schema/activityregistration.json",
            "title": "Data source schema",
            "description": "This schema describes information about activity provider.",
            "type": "object",
            "rule" : {
                "ActivityProvider" : {
                    "type" : "string",
                    "properties" : {
                        "Identifier" : {
                            "type" : "string",
                            "description" : "UUID representing the activity provider.",
                            "format": "uuid",
                        },
                        "Version" : {
                            "type" : "string",
                            "description" : "Version of the activity provider.",
                        },
                        "Description" : {
                            "type" : "string",
                            "description" : "Description of the activity provider.",
                        },
                    },
                    "required" : ["Identifier"],
                },
                "ActivityCollection" : {
                    "type" : "string",
                    "description" : "Unique name of the collection where the activity data is stored.",
                },
                "required" : ["ActivityProvider", "ActivityCollection"],
            }
        }
        assert 'Record' not in activity_registration_schema['rule'], \
            'Record should not be in activity registration schema.'
        activity_registration_schema['rule']['Record'] = IndalekoRecordSchema.get_schema()
        activity_registration_schema['rule']['required'].append('Record')
        return activity_registration_schema


def main():
    '''Test the IndalekoActivityRegistrationSchema class.'''
    if IndalekoActivityRegistrationSchema.is_valid_schema(IndalekoActivityRegistrationSchema.get_schema()):
        print('IndalekoActivityRegistrationSchema is a valid schema.')
    print(json.dumps(IndalekoActivityRegistrationSchema.get_schema(), indent=4))

if __name__ == '__main__':
    main()
