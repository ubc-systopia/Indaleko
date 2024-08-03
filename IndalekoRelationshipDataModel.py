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

from uuid import UUID
from typing import Annotated, List, Optional
from dataclasses import dataclass
import json

from graphql import print_schema
from apischema import schema, deserialize, serialize
from apischema.graphql import graphql_schema
from apischema.metadata import required
from apischema.json_schema import deserialization_schema, serialization_schema


from IndalekoDataModel import IndalekoDataModel, IndalekoUUID
from IndalekoRecordDataModel import IndalekoRecordDataModel

class IndalekoRelationshipDataModel:
    '''This is the data model Activity Provider Registration.'''

    @dataclass
    class RelationshipMetadataElement:
        '''Defines a single metadata element for a relationship.'''
        Identifier : Annotated[
            UUID,
            schema(description="The UUID defining the meaning of the metadata element."),
            required
        ]

        Data : Annotated[
            str,
            schema(description="Data defining this metadata."),
            required
        ]

        Record: IndalekoRecordDataModel.IndalekoRecord

    @staticmethod
    def get_relationship_metadata_element() -> \
        'IndalekoRelationshipDataModel.RelationshipMetadataElement':
        '''Return the relationship metadata element.'''
        return IndalekoRelationshipDataModel.RelationshipMetadataElement(
            Identifier=IndalekoUUID.Identifier(UUID('12345678-1234-5678-1234-567812345678')),
            Data='This is a test record',
            Record = None
        )

    @dataclass
    class IndalekoRelationship:
        '''
        This defines the data model for relationship information.
        '''
        Object1 : Annotated[
            UUID,
            schema(description="The first object in the relationship."),
            required
        ]

        Object2 : Annotated[
            UUID,
            schema(description="The second object in the relationship."),
            required
        ]

        Relationship: Annotated[
            UUID,
            schema(description="The relationship between the objects."),
            required
        ]

        Metadata: Annotated[
            Optional[List['IndalekoRelationshipDataModel.RelationshipMetadataElement']],
            schema(description="Metadata for the relationship (optional).")
        ] = None

    @staticmethod
    def get_relationship(relationship_identifier : UUID) -> 'IndalekoRelationshipDataModel.IndalekoRelationship':
        '''Return the relationship information.'''
        return IndalekoRelationshipDataModel.IndalekoRelationship(
            Object1=IndalekoDataModel.get_source_identifier(UUID('12345678-1234-5678-1234-567812345678')),
            Object2=IndalekoDataModel.get_source_identifier(UUID('12345678-1234-5678-1234-567812345678')),
            Relationship=IndalekoDataModel.get_source_identifier(relationship_identifier),
            Metadata=[
                IndalekoRelationshipDataModel.RelationshipMetadataElement(
                    Identifier=UUID('12345678-1234-5678-1234-567812345678'),
                    Data='This is a test record',
                    Record=None
                )
            ]
        )

    @staticmethod
    def get_queries() -> list:
        '''Return the queries for the relationship data model.'''
        return [IndalekoRelationshipDataModel.get_relationship_metadata_element,
                IndalekoRelationshipDataModel.get_relationship]

    @staticmethod
    def get_types() -> list:
        '''Return the types for the relationship data model.'''
        return [IndalekoRelationshipDataModel.RelationshipMetadataElement,
                IndalekoRelationshipDataModel.IndalekoRelationship]

    @staticmethod
    def deserialize(data: dict) -> 'IndalekoRelationshipDataModel.IndalekoRelationship':
        '''Deserialize a dictionary to an object.'''
        return deserialize(IndalekoRelationshipDataModel.IndalekoRelationship,
                           data,
                           additional_properties=True)

    @staticmethod
    def serialize(data) -> dict:
        '''Serialize the object to a dictionary.'''
        return serialize(IndalekoRelationshipDataModel.IndalekoRelationship, data)

def main():
    '''Test code for IndalekoObjectDataModel.'''
    print('GraphQL Schema:')
    print(print_schema(graphql_schema(
        query=IndalekoRelationshipDataModel.get_queries(),
        types=IndalekoRelationshipDataModel.get_types())))
    unpack_schema = deserialization_schema(IndalekoRelationshipDataModel.IndalekoRelationship,
                                           additional_properties=True)
    json_unpack_schema = json.dumps(unpack_schema, indent=4)
    print('Deserialization Schema:')
    print(json_unpack_schema)
    pack_schema = serialization_schema(IndalekoRelationshipDataModel.IndalekoRelationship,
                                       additional_properties=True)
    json_pack_schema = json.dumps(pack_schema, indent=4)
    print('Serialization Schema:')
    print(json_pack_schema)

if __name__ == '__main__':
    main()
