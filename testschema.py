import json
import os
import sys

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
# from IndalekoDBConfig import IndalekoDBConfig
# from IndalekoObject import IndalekoObject
# from IndalekoRelationshipSchema import IndalekoRelationshipSchema
# from IndalekoSourceSchema import IndalekoSourceSchema
from db import IndalekoDBConfig
from storage import IndalekoObject, IndalekoRelationship
from data_models import IndalekoSourceIdentifierDataModel
# pylint: enable=wrong-import-position


test_schema =  {
    "$schema": "https://json-schema.org/draft/2020-12/schema#",
    "$id": "https://fsgeek.ca/indaleko/schema/testschema.json",
    "title": "Test Schema",
    "description": "Schema for the JSON representation of Indaleko container schema.",
    "rule" : {
        "type": "object",
        "properties": {
            "uuid1": {
                "description": "This is the UUID of the starting vertex (container or contained)",
                "type": "string",
                "format" : "uuid",
            },
            "uuid2": {
                "description": "This is the UUID of the ending vertex (container or contained)",
                "type": "string",
                "format" : "uuid",
            },
        },
        "required": [
            "uuid1",
            "uuid2"
        ]
    },
    'level' : 'moderate',
    'message' : 'Schema validation failed',
}

test_schema2 = {
    "$schema": "https://json-schema.org/draft/2020-12/schema#",
    "$id" : "https://activitycontext.work/schema/indaleko-object.json",
    "title": "Indaleko Object Schema",
    "description": "Schema for the JSON representation of an Indaleko Object, which is used for indexing storage content.",
    "message" : "Schema validation failed",
    "level" : "moderate",
    "type": "json",
    "rule" : {
        "type" : "object",
        "properties" : {
            "Label" : {
                "type" : "string",
                "description" : "The object label."
            },
            "URI" : {
                "type" : "string",
                "description" : "The URI of the object."
            }
        },
        "required" : [
            "URI"
        ]
    }
}

test_schema3 = {
        "$schema": "https://json-schema.org/draft/2020-12/schema#",
        "$id" : "https://activitycontext.work/schema/indaleko-object.json",
        "title": "Indaleko Object Schema",
        "description": "Schema for the JSON representation of an Indaleko Object, which is used for indexing storage content.",
        "type": "object",
        "rule" : {
            "type" : "object",
            "properties" : {
                "Label" : {
                    "type" : "string",
                    "description" : "The object label (like a file name)."
                },
                "URI" : {
                    "type" : "string",
                    "description" : "The URI of the object."
                },
                "ObjectIdentifier" : {
                    "type" : "string",
                    "description" : "The object identifier (UUID).",
                    "format" : "uuid",
                },
                "LocalIdentifier": {
                    "type" : "string",
                    "description" : "The local identifier used by the storage system to find this, such as a UUID or inode number."
                },
                "Timestamps" : {
                    "type" : "array",
                    "properties" : {
                        "Label" : {
                            "type" : "string",
                            "description" : "UUID representing the semantic meaning of this timestamp.",
                            "format": "uuid",
                        },
                        "Value" : {
                            "type" : "string",
                            "description" : "Timestamp in ISO date and time format.",
                            "format" : "date-time",
                        },
                    },
                    "required" : [
                        "Label",
                        "Value"
                    ],
                    "description" : "List of timestamps with UUID-based semantic meanings associated with this object."
                },
                "Size" : {
                    "type" : "integer",
                    "description" : "Size of the object in bytes."
                },
                "RawData" : {
                    "type" : "string",
                    "description" : "Raw data captured for this object.",
                    "contentEncoding" : "base64",
                    "contentMediaType" : "application/octet-stream",
                },
                "SemanticAttributes" : {
                    "type" : "array",
                    "description" : "Semantic attributes associated with this object.",
                    "properties" : {
                        "UUID" : {
                            "type" : "string",
                            "description" : "The UUID for this attribute.",
                            "format" : "uuid",
                        },
                        "Data" : {
                            "type" : "string",
                            "description" : "The data associated with this attribute.",
                        },
                    },
                    "required" : [
                        "UUID",
                        "Data"
                    ]
                }
            },
            "required" : [
                "URI",
                "ObjectIdentifier",
                "Timestamps",
                "Size",
            ]
        }
}

test_schema4 = {
    "$schema": "https://json-schema.org/draft/2020-12/schema#",
    "$id" : "https://activitycontext.work/schema/indaleko-object.json",
    "title": "Indaleko Object Schema",
    "type" : "array",
    "rule" : {
        "type" : "object",
        "properties" : {
            "UUID" : {
                "type" : "string",
                "description" : "The UUID for this attribute.",
                "format" : "uuid",
            },
            "Data" : {
                "type" : "string",
                "description" : "The data associated with this attribute.",
            },
        },
        "required" : ["UUID", "Data"],
        "description" : "Semantic attributes associated with this object."
    }
}

test_schema5 = {
        "$schema": "https://json-schema.org/draft/2020-12/schema#",
        "$id" : "https://activitycontext.work/schema/indaleko-relationship.json",
        "title" : "Indaleko Relationship Schema",
        "description" : "Schema for the JSON representation of an Indaleko Relationship, which is used for identifying related objects.",
        "level" : "moderate",
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
                    "description" : "Optional metadata associated with this relationship.",
                    "properties" : {
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
                    },
                },
            },
        },
        "required" : ["object1", "object2" , "relationship"],
    }



def main():
    '''Test schema insertion into Arango.'''
    # print(json.dumps(test_schema3, indent=4))

    config = IndalekoDBConfig()
    config.start()
    if config.db.has_collection('schematest'):
        config.db.delete_collection('schematest')
    schema = IndalekoObject.Schema
    assert 'level' in schema, 'level must be in schema'
    collection = config.db.create_collection('schematest', schema=schema)
    print(json.dumps(schema, indent=4))
    ic(schema)
    #collection.configure(schema=IndalekoRelationshipSchema().get_schema())
    #collection.configure(schema=IndalekoSourceSchema().get_schema())
    #collection.configure(schema=test_schema)
    #print(collection)
    #uuid1 = str(uuid.uuid4())
    #uuid2 = str(uuid.uuid4())

    # relationship = {'uuid1': uuid1, 'uuid2': uuid2}

    # result = collection.insert(json.dumps(relationship))

    #print(result)


if __name__ == '__main__':
    main()
