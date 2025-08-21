import builtins
import contextlib
import json
import uuid

import jsonschema

from arango import ArangoClient


json_relationship_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema#",
    "$id": "https://fsgeek.ca/indaleko/schema/container-relationship.json",
    "title": "Container Relationship Schema",
    "description": "Schema for the JSON representation of Indaleko container schema.",
    "type": "object",
    "properties": {
        "uuid1": {
            "description": "This is the UUID of the starting vertex (container or contained)",
            "type": "string",
            "format": "uuid",
        },
        "uuid2": {
            "description": "This is the UUID of the ending vertex (container or contained)",
            "type": "string",
            "format": "uuid",
        },
    },
    "required": ["uuid1", "uuid2"],
}

relationship_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema#",
    "$id": "https://fsgeek.ca/indaleko/schema/container-relationship.json",
    "title": "Container Relationship Schema",
    "description": "Schema for the JSON representation of Indaleko container schema.",
    "rule": {
        "type": "object",
        "properties": {
            "uuid1": {
                "description": "This is the UUID of the starting vertex (container or contained)",
                "type": "string",
                "format": "uuid",
            },
            "uuid2": {
                "description": "This is the UUID of the ending vertex (container or contained)",
                "type": "string",
                "format": "uuid",
            },
        },
        "required": ["uuid1", "uuid2"],
    },
    "level": "moderate",
    "message": "Schema validation failed",
}


# jsonschema.validate(relationship_schema)


# ArangoDB connection settings
arango_url = "http://localhost:8529"
arango_username = "tony"
arango_password = "Kwishut$23!"
arango_db_name = "Indaleko"
arango_collection_name = "schema-test"

# Initialize the ArangoDB client
client = ArangoClient()

# Connect to the database
db = client.db(
    arango_db_name,
    username=arango_username,
    password=arango_password,
    auth_method="basic",
)


# Start with a clean collection each run
if db.has_collection(arango_collection_name):
    db.delete_collection(arango_collection_name)
collection = db.create_collection(arango_collection_name, schema=relationship_schema)

uuid1 = str(uuid.uuid4())
uuid2 = str(uuid.uuid4())

relationship = {"uuid1": uuid1, "uuid2": uuid2}

result = collection.insert(json.dumps(relationship))


with contextlib.suppress(builtins.BaseException):
    jsonschema.validators.validate(relationship, relationship_schema)
