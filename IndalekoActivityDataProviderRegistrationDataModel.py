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

from uuid import UUID
from typing import Annotated
from dataclasses import dataclass

import apischema
from graphql import print_schema
from apischema import schema
from apischema.graphql import graphql_schema
from apischema.metadata import required
from apischema.json_schema import deserialization_schema, serialization_schema


from IndalekoDataModel import IndalekoDataModel, IndalekoUUID
from IndalekoRecordDataModel import IndalekoRecordDataModel

class IndalekoActivityDataProviderRegistrationDataModel:
    '''This is the data model Activity Provider Registration.'''

    @dataclass
    class ActivityProviderInformation:
        '''
        This defines the data model for activity provider information.
        '''
        Identifier : Annotated[
            IndalekoUUID,
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

        Record : IndalekoRecordDataModel.IndalekoRecord

        @staticmethod
        def deserialize(data: dict) -> \
            'IndalekoActivityDataProviderRegistrationDataModel.ActivityProviderInformation':
            '''Deserialize the data into an
            IndalekoActivityDataProviderRegistrationDataModel.ActivityProviderInformation object.'''
            return apischema.deserialize(
                IndalekoActivityDataProviderRegistrationDataModel.ActivityProviderInformation,
                data,
                additional_properties=True)

        @staticmethod
        def serialize(activity_provider_information:
                      'IndalekoActivityDataProviderRegistrationDataModel.ActivityProviderInformation') \
                        -> dict:
            '''
            Serialize the
            IndalekoActivityDataProviderRegistrationDataModel.ActivityProviderInformation
            object into a dict.
            '''
            candidate = apischema.serialize(
                IndalekoActivityDataProviderRegistrationDataModel.ActivityProviderInformation,
                activity_provider_information,
                additional_properties=True,
                exclude_unset=True,
                exclude_none=True)
            return candidate

    @staticmethod
    def get_activity_provider_information() \
        -> 'IndalekoActivityDataProviderRegistrationDataModel.ActivityProviderInformation':
        '''Return the activity provider information.'''
        return IndalekoActivityDataProviderRegistrationDataModel\
            .ActivityProviderInformation(
                Record = None,
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
            schema(description="The unique name of the collection where the activity data is stored."),
            required
        ]

        @staticmethod
        def deserialize(data: dict) -> \
            'IndalekoActivityDataProviderRegistrationDataModel.ActivityProvider':
            """Deserialize the data into an
            IndalekoActivityDataProviderRegistrationDataModel.ActivityProvider object."""
            return apischema.deserialize(
                IndalekoActivityDataProviderRegistrationDataModel.ActivityProvider,
                data,
                additional_properties=True)

        @staticmethod
        def serialize(activity_provider: 'IndalekoActivityDataProviderRegistrationDataModel.ActivityProvider') -> dict:
            """Serialize the IndalekoActivityDataProviderRegistrationDataModel.ActivityProvider object into a dict."""
            candidate = apischema.serialize(
                IndalekoActivityDataProviderRegistrationDataModel.ActivityProvider,
                activity_provider,
                additional_properties=True,
                exclude_unset=True,
                exclude_none=True)
            return candidate

    @staticmethod
    def deserialize(data: dict) -> \
        'IndalekoActivityDataProviderRegistrationDataModel.ActivityProvider':
        '''Deserialize the data into an IndalekoActivityDataProviderRegistrationDataModel.ActivityProvider object.'''
        return apischema.deserialize(
            IndalekoActivityDataProviderRegistrationDataModel.ActivityProvider,
            data,
            additional_properties=True)

    @staticmethod
    def serialize(activity_provider:
                  'IndalekoActivityDataProviderRegistrationDataModel.ActivityProvider') -> dict:
        '''
        Serialize the
        IndalekoActivityDataProviderRegistrationDataModel.ActivityProvider
        object into a dict.
        '''
        candidate = apischema.serialize(
            IndalekoActivityDataProviderRegistrationDataModel.ActivityProvider,
            activity_provider,
            additional_properties=True,
            exclude_unset=True,
            exclude_none=True)
        return candidate

    @staticmethod
    def get_activity_provider() -> \
        'IndalekoActivityDataProviderRegistrationDataModel.ActivityProvider':
        '''Return the activity provider.'''
        return IndalekoActivityDataProviderRegistrationDataModel.ActivityProvider(
            ActivityProviderInformation=\
                IndalekoActivityDataProviderRegistrationDataModel\
                    .get_activity_provider_information(),
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
    ap_pack_schema = deserialization_schema(
        IndalekoActivityDataProviderRegistrationDataModel.ActivityProvider,
        additional_properties=True)
    ap_unpack_schema = serialization_schema(
        IndalekoActivityDataProviderRegistrationDataModel.ActivityProvider,
        additional_properties=True)
    api_pack_schema = deserialization_schema(
        IndalekoActivityDataProviderRegistrationDataModel.ActivityProviderInformation,
        additional_properties=True)
    api_unpack_schema = serialization_schema(
        IndalekoActivityDataProviderRegistrationDataModel.ActivityProviderInformation,
        additional_properties=True)
    print('Activity Provider Pack Schema:')
    print(json.dumps(ap_pack_schema, indent=4))
    print('Activity Provider Unpack Schema:')
    print(json.dumps(ap_unpack_schema, indent=4))
    print('Activity Provider Information Pack Schema:')
    print(json.dumps(api_pack_schema, indent=4))
    print('Activity Provider Information Unpack Schema:')
    print(json.dumps(api_unpack_schema, indent=4))

if __name__ == '__main__':
    main()
