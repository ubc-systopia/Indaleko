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
from IndalekoUserDataModel import IndalekoUserDataModel

class IndalekoUserRelationshipDataModel(IndalekoRecordDataModel):
    '''
    This defines the data model for user relationships (which means use to
    group and user to domain, but could be generalized.)
    '''

    @dataclass
    class UserIdentity:
        '''
        A User can have multiple identities: same user, different
        identities.
        '''
        Identities: Annotated[
            List[IndalekoUserDataModel.UserData],
            schema(description="The user's identities."),
            required
        ]

    @staticmethod
    def get_user_identities() -> 'IndalekoUserRelationshipDataModel.UserIdentity':
        '''Return the user identity.'''
        return IndalekoUserRelationshipDataModel.UserIdentity(
            Identities=[
                IndalekoUserDataModel.get_user_data()
            ]
        )

    @dataclass
    class GroupIdentity:
        '''
        There is a relationship concept known as a group, so we define the
        group identity data here.
        '''
        Domain : Annotated[
            IndalekoUserDataModel.UserDomain,
            schema(description="The security domain that defines this group."),
            required
        ]

        Description : Annotated[
            str,
            schema(description="A human readable description of the group.")
        ]

    @staticmethod
    def get_group_identity() -> 'IndalekoUserRelationshipDataModel.GroupIdentity':
        '''Return the group identity.'''
        return IndalekoUserRelationshipDataModel.GroupIdentity(
            Domain=IndalekoUserDataModel.get_user_domain(),
            Description='This is a test record'
        )

    @dataclass
    class UserRelationship:
        '''
        Define the relationship between a user and a group.
        '''
        User : Annotated[
            IndalekoUserDataModel.UserData,
            schema(description="The user in the relationship."),
            required
        ]

        Group : Annotated[
            'IndalekoUserRelationshipDataModel.GroupIdentity',
            schema(description="The group in the relationship."),
            required
        ]


    @staticmethod
    def get_user_relationship() -> 'IndalekoUserRelationshipDataModel.UserRelationship':
        '''Return the user relationship.'''
        return IndalekoUserRelationshipDataModel.UserRelationship(
            User=IndalekoUserDataModel.get_user_data(),
            Group=IndalekoUserRelationshipDataModel.get_group_identity()
        )


    @dataclass
    class EntityRelationship:

        '''
        Define the relationship between a user entities:
            - user to group
            - group to users
        '''
        Identity1 : Annotated[
            IndalekoDataModel.IndalekoUUID,
            schema(description="The first element in the relationship."),
            required
        ]

        Identity2 : Annotated[
            IndalekoDataModel.IndalekoUUID,
            schema(description="The second element in the relationship."),
            required
        ]

        RelationshipType : Annotated[
            IndalekoDataModel.IndalekoUUID,
            schema(description="The UUID that defines the type of relationship."),
            required
        ]

        Metadata : Annotated[
            List[IndalekoDataModel.SemanticAttribute],
            schema(description="Metadata associated with this relationship."),
            required
        ]

        Description : Annotated[
            str,
            schema(description="A human readable description of the relationship.")
        ]

    @staticmethod
    def get_entity_relationship() -> 'IndalekoUserRelationshipDataModel.EntityRelationship':
        '''Return the entity relationship.'''
        return IndalekoUserRelationshipDataModel.EntityRelationship(
            Identity1=IndalekoDataModel.get_source_identifier(UUID('12345678-1234-5678-1234-567812345678')),
            Identity2=IndalekoDataModel.get_source_identifier(UUID('12345678-1234-5678-1234-567812345678')),
            RelationshipType=IndalekoDataModel.get_source_identifier(UUID('12345678-1234-5678-1234-567812345678')),
            Metadata=[IndalekoDataModel.get_semantic_attribute()],
            Description='This is a test record'
        )

    @staticmethod
    def get_queries() -> List:
        return [IndalekoUserRelationshipDataModel.get_user_identities,
                IndalekoUserRelationshipDataModel.get_group_identity,
                IndalekoUserRelationshipDataModel.get_entity_relationship,
                IndalekoUserRelationshipDataModel.get_user_relationship]

    @staticmethod
    def get_types() -> List:
        return [IndalekoUserRelationshipDataModel.UserIdentity,
                IndalekoUserRelationshipDataModel.GroupIdentity,
                IndalekoUserRelationshipDataModel.UserRelationship,
                IndalekoUserRelationshipDataModel.EntityRelationship]

def main():
    '''Test the IndalekoUserRelationshipDataModel data model.'''
    print('GraphQL Schema:')
    print(print_schema(graphql_schema(query=IndalekoUserRelationshipDataModel.get_queries(),
                                      types=IndalekoUserRelationshipDataModel.get_types())))
if __name__ == "__main__":
    main()
