"""
Indaleko is all about mining associations between discrete storage objects.
These associations are "relationships".  For example, a directory has a
"contains" relationship with a file and a file has a "contained by" relationship
with some directory.

This module defines the IndalekoRelationship class, which is used to represent a
relationship between two objects.
"""
import uuid
import argparse
import os
import random
import json
import msgpack
from IndalekoRecord import IndalekoRecord
from IndalekoRelationshipSchema import IndalekoRelationshipSchema

class IndalekoRelationship(IndalekoRecord):
    '''
    This schema defines the fields that are required as part of identifying
    relationships between objects.
    '''
    Schema = IndalekoRelationshipSchema.get_schema()

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


    def __init__(self,
                 source : dict,
                 raw_data : bytes,
                 vertex1 : dict,
                 vertex2 : dict,
                 relationship: str,
                 attributes : dict) -> None:
        assert self.validate_source(source), f'source ({source}) must be a valid source.'
        assert isinstance(raw_data, bytes), 'raw_data must be bytes'
        assert self.validate_vertex(vertex1), 'vertex1 must be a valid vertex.'
        assert self.validate_vertex(vertex2), 'vertex2 must be a valid vertex.'
        assert self.validate_uuid_string(relationship), 'relationship must be a valid UUID.'
        self.vertex1 = vertex1
        self.vertex2 = vertex2
        self.relationship = relationship
        super().__init__(raw_data, attributes, source)


    def to_dict(self):
        """Return a dictionary representation of this object."""
        obj = {}
        obj['Record'] = super().to_dict()
        obj['_from'] = f'{self.vertex1["collection"]}/{self.vertex1["object"]}'
        obj['_to'] = f'{self.vertex2["collection"]}/{self.vertex2["object"]}'
        obj['object1'] = f'{self.vertex1["object"]}'
        obj['object2'] = f'{self.vertex2["object"]}'
        obj['relationship'] = f'{self.relationship}'
        return obj

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
        'collection' : 'Objects',
    }
    vertex2 = {
        'object' : str(uuid.uuid4()),
        'collection' : 'Objects',
    }
    r = IndalekoRelationship({
        'Identifier' : args.source,
        'Version' : '1.0'},
        args.raw_data,
        vertex1,
        vertex2,
        str(uuid.uuid4()),
        attributes)
    print(json.dumps(r.to_dict(), indent=4))
    if IndalekoRelationshipSchema.is_valid_relationship(r.to_dict()):
        print('Relationship is valid.')

if __name__ == "__main__":
    main()

