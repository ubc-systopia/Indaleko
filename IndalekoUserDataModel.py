'''
This module defines the database schema for the MachineConfig collection.

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

from apischema import schema
from apischema.graphql import graphql_schema
from apischema.metadata import required
from graphql import print_schema

from IndalekoDataModel import IndalekoDataModel
from IndalekoRecordDataModel import IndalekoRecordDataModel
class IndalekoUserDataModel(IndalekoRecordDataModel):
    '''
    This is the Indaleko data model for tracking user information.
    '''

    @dataclass
    class UserDomain:
        '''Define the security domain for a user.'''
        Domain: Annotated[
            IndalekoDataModel.IndalekoUUID,
            schema(description="The security domain for the user."),
            required
        ]

        Description: Annotated[
            str,
            schema(description="Human readable description of the security domain.")
        ]

    @staticmethod
    def get_user_domain() -> 'IndalekoUserDataModel.UserDomain':
        '''Return the user domain.'''
        return IndalekoUserDataModel.UserDomain(
            Domain=IndalekoDataModel.get_source_identifier(UUID('12345678-1234-5678-1234-567812345678')),
            Description='This is a test record'
        )
    @dataclass
    class UserData:

        '''
        Define the data we maintain about users.
        '''
        Identifier : Annotated[
            IndalekoDataModel.IndalekoUUID,
            schema(description="This is an Indaleko defined UUID that represents the user."),
            required
        ]

        Domains : Annotated[
            List['IndalekoUserDataModel.UserDomain'],
            schema(description="The security domains for the user."),
            required
        ]

        Description: Annotated[
            str,
            schema(description="Human readable description of the user.")
        ]

    @staticmethod
    def get_user_data() -> 'IndalekoUserDataModel.UserData':
        '''Return the user data.'''
        return IndalekoUserDataModel.UserData(
            Identifier=IndalekoDataModel.get_source_identifier(UUID('12345678-1234-5678-1234-567812345678')),
            Domains=[IndalekoUserDataModel.get_user_domain()],
            Description='This is a test record'
        )

    @staticmethod
    def get_queries() -> list:
        '''Return the queries for the User collection.'''
        return [IndalekoUserDataModel.get_user_domain,
                IndalekoUserDataModel.get_user_data]

    @staticmethod
    def get_types() -> list:
        '''Return the types for the User collection.'''
        return [IndalekoUserDataModel.UserDomain,
                IndalekoUserDataModel.UserData]


def main():
    '''Test code for IndalekoUserDataModel.'''
    print('GraphQL Schema:')
    print(print_schema(graphql_schema(query=IndalekoUserDataModel.get_queries(),
                                      types=IndalekoUserDataModel.get_types())))
if __name__ == "__main__":
    main()
