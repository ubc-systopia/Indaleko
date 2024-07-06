'''
This module defines the common database schema for Activity Data.

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

from datetime import datetime
from uuid import UUID

from apischema.graphql import graphql_schema
from graphql import print_schema

from IndalekoRecordSchema import IndalekoRecordSchema
from IndalekoActivityDataModel import IndalekoActivityDataModel
from IndalekoDataModel import IndalekoDataModel

class IndalekoActivityDataSchema(IndalekoRecordSchema):
    '''Schema defintion for activity data.'''

    @staticmethod
    def get_old_schema():
        activity_data_schema = {
            '''
            This schema relates to the activity data that is collected by
            the activity provider(s). This schema is used as a base from which
            we can derive more specific schemas for different types of activity
            data.
            '''
            "$schema": "https://json-schema.org/draft/2020-12/schema#",
            "$id": "https://activitycontext.work/schema/activitydata.json",
            "title": "Activity Data schema",
            "description": "This schema describes information about activity data.",
            "type": "object",
            "rule" : {
                "ActivityDataIdentifier" : {
                    "type" : "string",
                    "description" : "UUID of this activity data.",
                    "format": "uuid",
                },
                "CollectionTimestamp" : {
                    "type" : "string",
                    "description" : "Timestamp when the data was collected.",
                    "format": "date-time",
                },
                "ActivityTimestamps" : {
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
                            "description" : "Timestamp value.",
                            "format": "date-time",
                        },
                    },
                    "required" : ["Label", "Value"],
                },
                "required" : ["ActivityDataIdentifier","CollectionTimestamp"],
            },
        }
        assert 'Record' not in activity_data_schema['rule'], \
            'Record should not be in activity data schema.'
        activity_data_schema['rule']['Record'] = IndalekoRecordSchema.get_old_schema()
        activity_data_schema['rule']['required'].append('Record')
        return activity_data_schema

    @staticmethod
    def get_activity_data(identifier : IndalekoDataModel.IndalekoUUID)\
        -> IndalekoActivityDataModel.ActivityData:
        '''Given an identifier, return an activity data.'''
        indaleko_activity_data = IndalekoActivityDataModel.ActivityData(
            ActivityDataIdentifier=identifier,
            CollectionTimestamp=datetime.now(),
            ActivityTimestamps=[
                IndalekoDataModel.Timestamp(
                    Label=IndalekoDataModel.IndalekoUUID(
                        UUID=UUID('00000000-0000-0000-0000-000000000000'),
                        Label='Activity Timestamp'
                    ),
                    Value=datetime.now()
                )
            ]
        )
        return indaleko_activity_data

def main():
    '''Test the IndalekoActivityDataSchema class.'''
    activity_data = IndalekoActivityDataSchema()
    assert IndalekoActivityDataSchema.is_valid_schema_dict(activity_data.get_old_schema())
    print('Old ActivityData schema is valid')
    print('Old Schema:')
    print(json.dumps(activity_data.get_old_schema(), indent=4))
    assert activity_data.is_valid_schema()
    print('New ActivityData schema is valid')
    print('New Schema:')
    print(json.dumps(activity_data.get_schema(), indent=4))
    print('GraphQL Schema:')
    print(print_schema(graphql_schema(
        query=[IndalekoActivityDataSchema.get_activity_data],
        types=[IndalekoActivityDataModel.ActivityData])))

if __name__ == '__main__':
    main()
