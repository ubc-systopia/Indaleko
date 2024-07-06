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

from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, List
from uuid import UUID

from graphql import print_schema
from apischema.graphql import graphql_schema
from apischema.metadata import required
from apischema import schema

from IndalekoDataModel import IndalekoDataModel
from IndalekoRecordDataModel import IndalekoRecordDataModel

class IndalekoActivityDataProviderDataModel(IndalekoRecordDataModel):
    '''This is the data model for the activity data providers.'''

    @dataclass
    class ActivityDataProviderEntity:
        '''This is the data model for the activity data provider entity.'''

        Label : Annotated[
            IndalekoDataModel.IndalekoUUID,
            schema(description="The UUID representing the semantic meaning of this entity."),
            required
        ]

        Value : Annotated[
            IndalekoDataModel.IndalekoUUID,
            schema(description="The UUID corresponding to this entity."),
            required
        ]

        Description : Annotated[
            str,
            schema(description="A human readable description of the entity."),
        ]


    @dataclass
    class ActivityDataProvider:
        '''This is the data model for the activity data provider.'''

        ActivityDataIdentifer: Annotated[
            IndalekoDataModel.IndalekoUUID,
            required
        ]

        ActivityProviderIdentifier : Annotated[
            IndalekoDataModel.IndalekoUUID,
            required
        ]

        Timestamps: List[IndalekoDataModel.Timestamp]

        ActivityType : Annotated[
            IndalekoDataModel.IndalekoUUID,
            required
        ]

        DataVersion : Annotated[
            str,
            schema(description="The version of the activity data."),
        ]

        Entities : List['IndalekoActivityDataProviderDataModel.ActivityDataProviderEntity']

        Active : Annotated[
            bool,
            schema(description="Is this activity data provider entity active?"),
            required
        ]

def get_activity_data_provider(activity_data_provider_id : UUID) -> IndalekoActivityDataProviderDataModel.ActivityDataProvider:
    '''Look up an activity data provider.'''
    indaleko_activity_data_provider = IndalekoActivityDataProviderDataModel.ActivityDataProvider(
        ActivityDataIdentifer=IndalekoDataModel.IndalekoUUID(
            UUID=UUID('00000000-0000-0000-0000-000000000000'),
            Label='Activity Data Identifier'
        ),
        ActivityProviderIdentifier=IndalekoDataModel.IndalekoUUID(
            UUID=activity_data_provider_id,
            Label='Activity Provider Identifier'
        ),
        Timestamps=[IndalekoDataModel.Timestamp(
            Label=UUID('00000000-0000-0000-0000-000000000000'),
            Value=datetime.now())
        ],
        ActivityType=IndalekoDataModel.IndalekoUUID(
            UUID=UUID('00000000-0000-0000-0000-000000000000'),
            Label='Activity Type Identifier'),
        DataVersion='1.0.0',
        Entities=[IndalekoActivityDataProviderDataModel.ActivityDataProviderEntity(
            Label=IndalekoDataModel.IndalekoUUID(
                UUID=UUID('00000000-0000-0000-0000-000000000000'),
                Label='Entity Label'
            ),
            Value=IndalekoDataModel.IndalekoUUID(
                UUID=UUID('00000000-0000-0000-0000-000000000000'),
                Label='Entity Value'
            ),
            Description='Entity Description'
        )],
        Active=True
    )
    return indaleko_activity_data_provider


def main():
    '''Test code for IndalekoObjectDataModel.'''
    print('GraphQL Schema:')
    print(print_schema(graphql_schema(
        query=[get_activity_data_provider],
        types=[IndalekoActivityDataProviderDataModel.ActivityDataProvider]))
    )

if __name__ == '__main__':
    main()
