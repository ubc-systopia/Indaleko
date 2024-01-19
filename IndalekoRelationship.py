"""
Indaleko is all about mining associations between discrete storage objects.
These associations are "relationships".  For example, a directory has a
"contains" relationship with a file and a file has a "contained by" relationship
with some directory.

This module defines the IndalekoRelationship class, which is used to represent a
relationship between two objects.

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
"""
import uuid
import argparse
import os
import random
import json
import msgpack
from Indaleko import Indaleko
from IndalekoRecord import IndalekoRecord
from IndalekoRelationshipSchema import IndalekoRelationshipSchema

class IndalekoRelationship(IndalekoRecord):
    '''
    This schema defines the fields that are required as part of identifying
    relationships between objects.
    '''
    Schema = IndalekoRelationshipSchema.get_schema()

    class RelationshipConfiguration:
        '''This subclass will be a central hub for the registration data for relationships.'''
        _instance = None

        def __new__(cls):
            if cls._instance is None:
                # cls._instance = super(IndalekoRelationship.RelationshipConfiguration).__new__(cls)
                cls._instance.relationships = {}
            return cls._instance

        def initialize(self):
            raise NotImplementedError('initialize not implemented')

        def add_relationship(self, relationship : dict) -> None:
            raise NotImplementedError('add_relationship not implemented')

    def validate_vertex(self, vertex : dict) -> bool:
        """
        This is used to verify that the given vertex has the minimum
        information required.
        """
        assert isinstance(vertex, dict), 'vertex must be a dict'
        assert 'object' in vertex, 'object1 must be specified.'
        assert 'collection' in vertex, 'collection must be specified.'
        assert self.validate_uuid_string(vertex['object']), 'object must be a valid UUID.'
        assert isinstance(vertex['collection'], str), 'collection must be a string.'
        return True

    def __init__(self, **kwargs):
        """
        Constructor for the IndalekoRelationship class. Takes a configuration
        object as a parameter. The configuration object is a dictionary that
        contains all the configuration parameters for the relationship.
        """
        assert 'relationship' in kwargs, 'Relationship UUID must be specified'
        assert 'object1' in kwargs, 'Object1 must be specified'
        assert 'object2' in kwargs, 'Object2 must be specified'
        assert 'Record' not in kwargs, 'Record must not be specified'
        self.vertex1 = kwargs['object1']
        self.vertex2 = kwargs['object2']
        self.relationship = kwargs['relationship']
        self.metadata = {}
        if 'metadata' in kwargs:
            self.metadata = kwargs['metadata']
        assert self.validate_vertex(self.vertex1), 'vertex1 must be a valid vertex.'
        assert self.validate_vertex(self.vertex2), 'vertex2 must be a valid vertex.'
        assert self.validate_uuid_string(self.relationship), 'relationship must be a valid UUID.'
        assert isinstance(self.metadata, dict), 'metadata must be a dictionary.'
        if 'raw_data' not in kwargs:
            kwargs['raw_data'] = b''
        super().__init__(**kwargs)


    def to_dict(self):
        """Return a dictionary representation of this object."""
        obj = {}
        obj['Record'] = super().to_dict()
        obj['_from'] = f'{self.vertex1["collection"]}/{self.vertex1["object"]}'
        obj['_to'] = f'{self.vertex2["collection"]}/{self.vertex2["object"]}'
        obj['Object1'] = f'{self.vertex1["object"]}'
        obj['Object2'] = f'{self.vertex2["object"]}'
        obj['Relationship'] = f'{self.relationship}'
        return obj

    def to_json(self, indent : int = 4) -> str:
        """Return a JSON representation of this object."""
        return json.dumps(self.to_dict(), indent=indent)

def main():
    """Test the IndalekoRelationship class."""
    if IndalekoRelationshipSchema.is_valid_schema(IndalekoRelationship.get_schema()):
        print('Schema is valid.')
    print(json.dumps(IndalekoRelationship.get_schema(), indent=4))
    random_raw_data = msgpack.packb(os.urandom(64))
    source_uuid = str(uuid.uuid4())
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('--source' ,
                        '-s',
                        type=str,
                        default=source_uuid,
                        help='The source UUID of the data.')
    parser.add_argument('--raw-data',
                        '-r',
                        type=str,
                        default=random_raw_data,
                        help='The raw data to be stored.')
    args = parser.parse_args()
    attributes = {
        'field1' : random.randint(0, 100),
        'field2' : random.randint(101,200),
        'field3' : random.randint(201,300),
    }
    vertex1 = {
        'object' : str(uuid.uuid4()),
        'collection' : Indaleko.Indaleko_Objects,
    }
    vertex2 = {
        'object' : str(uuid.uuid4()),
        'collection' : Indaleko.Indaleko_Objects,
    }
    r = IndalekoRelationship(
        source = {
            'Identifier' : args.source,
            'Version' : '1.0'
        },
        raw_data = args.raw_data,
        object1 = vertex1,
        object2 = vertex2,
        metadata = attributes,
        relationship = str(uuid.uuid4())
    )
    print(json.dumps(r.to_dict(), indent=4))
    if IndalekoRelationshipSchema.is_valid_relationship(r.to_dict()):
        print('Relationship is valid.')

if __name__ == "__main__":
    main()

