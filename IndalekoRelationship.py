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
import msgpack
from IndalekoRecord import IndalekoRecord

class IndalekoRelationship(IndalekoRecord):
    '''
    This schema defines the fields that are required as part of identifying
    relationships between objects.
    '''
    Schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema#",
        "$id" : "https://activitycontext.work/schema/indaleko-relationship.json",
        "title" : "Indaleko Relationship Schema",
        "description" : "Schema for the JSON representation of an Indaleko Relationship, which is used for identifying related objects.",
        "type" : "object",
        "rule" : {
            "properties" : {
                "object1" : {
                    "type" : "string",
                    "format" : "uuid",
                    "description" : "The Indaleko UUID for the first object in the relationship.",
                },
                "object2" : {
                    "type" : "string",
                    "format" : "uuid",
                    "description" : "The Indaleko UUID for the second object in the relationship.",
                },
                "relationship" : {
                    "type" : "string",
                    "description" : "The UUID specifying the specific relationship between the two objects.",
                    "format" : "uuid",
                },
                "metadata" :  {
                    "type" : "array",
                    "items" : {
                        "type" : "object",
                        "properties" : {
                            "UUID" : {
                                "type" : "string",
                                "format" : "uuid",
                                "description" : "The UUID for this metadata.",
                            },
                            "Data" : {
                                "type" : "string",
                                "description" : "The data associated with this metadata.",
                            },
                        },
                        "required" : ["UUID", "Data"],
                    },
                    "description" : "Optional metadata associated with this relationship.",
                },
            },
            "required" : ["object1", "object2" , "relationship"],
        },
    }

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
        obj = super().to_dict()
        obj['_from'] = f'{self.vertex1["collection"]}/{self.vertex1["object"]}'
        obj['_to'] = f'{self.vertex2["collection"]}/{self.vertex2["object"]}'
        obj['object1'] = f'{self.vertex1["object"]}'
        obj['object2'] = f'{self.vertex2["object"]}'
        obj['relationship'] = f'{self.relationship}'
        return obj

def main():
    """Test the IndalekoRelationship class."""
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
    print(r)

if __name__ == "__main__":
    main()

