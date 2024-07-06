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
from datetime import datetime
from uuid import UUID
from typing import Annotated, List
from dataclasses import dataclass

from graphql import print_schema
from apischema import schema
from apischema.graphql import graphql_schema
from apischema.metadata import required


from IndalekoDataModel import IndalekoDataModel
from IndalekoRecordDataModel import IndalekoRecordDataModel

class IndalekoActivityDataProviderRegistrationDataModel(IndalekoRecordDataModel):
    '''This is the data model Activity Provider Registration.'''

    @dataclass
    class ActivityProviderInformation:
        '''
        This defines the data model for activity provider information.
        '''
        Identifier : Annotated[
            IndalekoDataModel.IndalekoUUID,
            required
        ]

        Version : Annotated[
            str,
            schema(description="Version of the activity provider.")
        ]

        Description : Annotated[
            str,
            schema(description="Description of the activity provider.")
        ]

    @staticmethod
    def get_activity_provider_information() -> 'IndalekoActivityDataProviderRegistrationDataModel.ActivityProviderInformation':
        '''Return the activity provider information.'''
        return IndalekoActivityDataProviderRegistrationDataModel.ActivityProviderInformation(
            Identifier=IndalekoDataModel.get_source_identifier(UUID('12345678-1234-5678-1234-567812345678')),
            Version='1.0',
            Description='This is a test record'
        )

    @dataclass
    class ActivityProvider:
        '''
        This defines the data model for activity data provider
        registration.
        '''
        ActivityProviderInformation : Annotated[
            'IndalekoActivityDataProviderRegistrationDataModel.ActivityProviderInformation',
            required
        ]

        ActivityCollection: Annotated[
            str,
            schema(description="The unqieu name of the collection where the activity data is stored."),
            required
        ]


    @staticmethod
    def get_activity_provider() -> 'IndalekoActivityDataProviderRegistrationDataModel.ActivityProvider':
        '''Return the activity provider.'''
        return IndalekoActivityDataProviderRegistrationDataModel.ActivityProvider(
            ActivityProviderInformation=IndalekoActivityDataProviderRegistrationDataModel.get_activity_provider_information(),
            ActivityCollection='Test Collection'
        )


    @staticmethod
    def get_queries() -> list:
        '''Return the queries for the schema.'''
        return [IndalekoActivityDataProviderRegistrationDataModel.get_activity_provider,
                IndalekoActivityDataProviderRegistrationDataModel.get_activity_provider_information]

    @staticmethod
    def get_types() -> list:
        '''Return the types for the schema.'''
        return [IndalekoActivityDataProviderRegistrationDataModel.ActivityProvider,
                IndalekoActivityDataProviderRegistrationDataModel.ActivityProviderInformation]


def main():
    '''Test code for IndalekoObjectDataModel.'''
    print('GraphQL Schema:')
    print(print_schema(graphql_schema(
        query=IndalekoActivityDataProviderRegistrationDataModel.get_queries(),
        types=IndalekoActivityDataProviderRegistrationDataModel.get_types())))

if __name__ == '__main__':
    main()
