'''
This defines the Indaleko User schema.

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
import jsonschema
from jsonschema import validate

from IndalekoUserDataModel import IndalekoUserDataModel
from IndalekoRecordSchema import IndalekoRecordSchema

class IndalekoUserSchema(IndalekoRecordSchema):
    '''This class defines the schema for Indaleko Users.'''

    def __init__(self):
        '''Initialize the schema.'''
        if not hasattr(self, 'data_model'):
            self.data_model = IndalekoUserDataModel()
        if not hasattr(self, 'base_type'):
            self.base_type = IndalekoUserDataModel.UserData
        super().__init__()

    @staticmethod
    def get_old_schema():
        services_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema#",
            "$id": "https://activitycontext.work/schema/user.json",
            "title": "Service provider schema",
            "description":
            "This schema describes information about user identity within the Indaleko system.",
            "type": "object",
            "rule" : {
                "properties": {
                    "Identifier": {
                        "description": "This is the UUID of the Indaleko User.",
                        "type": "string",
                        "format": "uuid"
                    },
                    "Domain" : {
                        "description" : "This is the domain in which this user is defined.",
                        "type" : "string",
                        "format" : "uuid",
                    },
                },
                "required": ["Identifier", "Domain"],
            }
        }
        assert 'Record' not in \
            services_schema['rule']['properties'], 'Record must not be specified.'
        services_schema['rule']['properties']['Record'] = \
            IndalekoRecordSchema.get_old_schema()['rule']
        services_schema['rule']['required'].append('Record')
        return services_schema

def main():
    '''Test code for IndalekoUserSchema.'''
    if IndalekoUserSchema.is_valid_schema(IndalekoUserSchema.get_old_schema()):
        print('Schema is valid.')
    print(json.dumps(IndalekoUserSchema.get_old_schema(), indent=4))

if __name__ == "__main__":
    main()
