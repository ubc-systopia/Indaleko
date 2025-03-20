"""
Indaleko is all about mining associations between discrete storage objects.
These associations are "relationships".  For example, a directory has a
"contains" relationship with a file and a file has a "contained by" relationship
with some directory.

This module defines the IndalekoRelationship class, which is used to represent a
relationship between two objects.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

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

import argparse
from enum import Enum
import json
import random
import os
import sys
import uuid

from typing import Tuple, Union, Dict, List

from pydantic import BaseModel, Field
from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
# from Indaleko import Indaleko
# from IndalekoRelationshipSchema import IndalekoRelationshipSchema
# from IndalekoRelationshipDataModel import IndalekoRelationshipDataModel
# from IndalekoDataModel import IndalekoUUID
from data_models import (
    IndalekoRelationshipDataModel,
    IndalekoUUIDDataModel,
    IndalekoRecordDataModel,
    IndalekoSourceIdentifierDataModel,
    IndalekoSemanticAttributeDataModel,
)
from db import IndalekoDBCollections
from utils.data_validation import validate_uuid_string
from utils.misc.data_management import encode_binary_data

# pylint: enable=wrong-import-position


class IndalekoRelationship:
    """
    This schema defines the fields that are required as part of identifying
    relationships between objects.
    """

    Schema = IndalekoRelationshipDataModel.get_arangodb_schema()
    indaleko_relationship_uuid_str = "a57f185b-5f6e-4b66-95f9-4e4f3c3b3105"

    # Maybe these should be externally defined?
    class RelationshipType(str, Enum):
        CONTAINED_BY_DIRECTORY_RELATIONSHIP_UUID_STR = (
            "3d4b772d-b4b0-4203-a410-ecac5dc6dafa"
        )
        CONTAINED_BY_VOLUME_RELATIONSHIP_UUID_STR = (
            "f38c45ce-e8d8-4c5a-adc6-fc34f5f8b8e9"
        )
        CONTAINED_BY_MACHINE_RELATIONSHIP_UUID_STR = (
            "1ba5935c-8e82-4dd9-92e7-d4b085958487"
        )
        DIRECTORY_CONTAINS_RELATIONSHIP_UUID_STR = (
            "cde81295-f171-45be-8607-8100f4611430"
        )
        VOLUME_CONTAINS_RELATIONSHIP_UUID_STR = "db1a48c0-91d9-4f16-bd65-845433e6cba9"
        MACHINE_CONTAINS_RELATIONSHIP_UUID_STR = "f3dde8a2-cff5-41b9-bd00-0f41330895e1"

    # These definitions are for backwards compatibility
    # the goal really is to use the RelationshipType enum
    CONTAINED_BY_DIRECTORY_RELATIONSHIP_UUID_STR = (
        RelationshipType.CONTAINED_BY_DIRECTORY_RELATIONSHIP_UUID_STR
    )
    CONTAINED_BY_VOLUME_RELATIONSHIP_UUID_STR = (
        RelationshipType.CONTAINED_BY_VOLUME_RELATIONSHIP_UUID_STR
    )
    CONTAINED_BY_MACHINE_RELATIONSHIP_UUID_STR = (
        RelationshipType.CONTAINED_BY_MACHINE_RELATIONSHIP_UUID_STR
    )
    DIRECTORY_CONTAINS_RELATIONSHIP_UUID_STR = (
        RelationshipType.DIRECTORY_CONTAINS_RELATIONSHIP_UUID_STR
    )
    VOLUME_CONTAINS_RELATIONSHIP_UUID_STR = (
        RelationshipType.VOLUME_CONTAINS_RELATIONSHIP_UUID_STR
    )
    MACHINE_CONTAINS_RELATIONSHIP_UUID_STR = (
        RelationshipType.MACHINE_CONTAINS_RELATIONSHIP_UUID_STR
    )

    class IndalekoRelationshipObject(BaseModel):
        """This is the definition of the relationship object."""

        collection: str = Field(None, title="Collection Name")
        object: Union[str, uuid.UUID] = Field(None, title="Object ID")

    def __init__(
        self,
        objects: Tuple[IndalekoRelationshipObject, IndalekoRelationshipObject],
        relationships: Union[List[IndalekoSemanticAttributeDataModel], None] = None,
        source_id: Union[IndalekoSourceIdentifierDataModel, None] = None,
    ):
        """Create an empty relationship object."""
        assert len(objects) == 2, "objects must be a tuple of two objects."
        if source_id is not None:
            assert isinstance(
                source_id, IndalekoSourceIdentifierDataModel
            ), "source_id must be an IndalekoSourceIdentifierDataModel."
            self.source_identifier = source_id
        else:
            self.source_identifier = IndalekoSourceIdentifierDataModel(
                Identifier=IndalekoRelationship.indaleko_relationship_uuid_str,
                Version="1.0",
                Description="Indaleko Relationship",
            )
        assert len(objects) == 2, "objects must be a tuple of two objects."
        self.object1 = IndalekoRelationship.IndalekoRelationshipObject(**objects[0])
        self.object2 = IndalekoRelationship.IndalekoRelationshipObject(**objects[1])
        self.relationships = relationships
        self.record = IndalekoRecordDataModel(SourceIdentifier=self.source_identifier)

    def vertex_to_indaleko_uuid(
        self, vertex: Union[uuid.UUID, str, IndalekoUUIDDataModel]
    ) -> IndalekoUUIDDataModel:
        """Convert a vertex to an IndalekoUUIDDataModel."""
        if isinstance(vertex, IndalekoUUIDDataModel):
            return vertex
        if isinstance(vertex, uuid.UUID):
            return IndalekoUUIDDataModel(Identifier=vertex)
        if isinstance(vertex, str) and validate_uuid_string(vertex):
            return IndalekoUUIDDataModel(Identifier=uuid.UUID(vertex))
        raise ValueError("vertex must be a UUID or IndalekoUUIDDataModel.")

    def add_relationship(self, key: str, value: str = None) -> None:
        """Add a relationship to the relationship object."""
        if self.relationships is None:
            self.relationships = {}
        assert isinstance(
            self.relationships, dict
        ), "relationships must be a dictionary."
        assert key not in self.relationships, "relationship already exists."
        self.relationships[key] = value
        return self

    def update_relationship(self, key: str, value: str) -> None:
        """Update a relationship in the relationship object."""
        assert key in self.relationships, "relationship does not exist."
        self.relationships[key] = value

    @staticmethod
    def vertex_to_uuid(
        vertex: Union[IndalekoUUIDDataModel, uuid.UUID, str],
    ) -> IndalekoUUIDDataModel:
        """Convert a vertex to a UUID."""
        if isinstance(vertex, IndalekoUUIDDataModel):
            return vertex
        if isinstance(vertex, uuid.UUID):
            return IndalekoUUIDDataModel(Identifier=vertex)
        if isinstance(vertex, str) and validate_uuid_string(vertex):
            return IndalekoUUIDDataModel(Identifier=uuid.UUID(vertex))
        raise ValueError("vertex must be a UUID or IndalekoUUIDDataModel.")

    @staticmethod
    def relationships_to_list(
        relationships: Union[List[Dict[str, str]], None],
    ) -> List[Dict[str, str]]:
        """Convert a list of relationships to a list of dictionaries."""
        if relationships is None:
            return []
        for relationship in relationships:
            assert isinstance(relationship, dict), "relationship must be a dictionary."
            assert (
                "relationship" in relationship
            ), "relationship must have a relationship key."
            assert (
                "description" in relationship
            ), "relationship must have a description key."
        return relationships

    def serialize(self) -> dict:
        """Serialize the object to a dictionary."""
        assert (
            self.relationships is not None and len(self.relationships) > 0
        ), "Must have at least one relationship for serialization."
        assert isinstance(
            self.relationships, list
        ), "relationships must be a dictionary."
        reldata = [
            IndalekoSemanticAttributeDataModel(
                Identifier=item.Identifier, Value=item.Value
            )
            for item in self.relationships
        ]
        obj1 = str(self.object1.object)
        obj2 = str(self.object2.object)
        relationship_data = IndalekoRelationshipDataModel(
            Record=self.record,
            Objects=[obj1, obj2],
            Relationships=reldata,
        )
        doc = json.loads(relationship_data.model_dump_json(exclude_none=True))
        doc["_key"] = str(uuid.uuid4())
        doc["_from"] = self.object1.collection + "/" + obj1
        doc["_to"] = self.object2.collection + "/" + obj2
        return doc

    @staticmethod
    def deserialize(data: dict) -> "IndalekoRelationship":
        """Deserialize the data into an IndalekoRelationship object."""
        return IndalekoRelationship(**data)


def main():
    """Test the IndalekoRelationship class."""
    random_raw_data = encode_binary_data(os.urandom(64))
    source_uuid = str(uuid.uuid4())
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", action="version", version="%(prog)s 1.0")
    parser.add_argument(
        "--source",
        "-s",
        type=str,
        default=source_uuid,
        help="The source UUID of the data.",
    )
    parser.add_argument(
        "--raw-data",
        "-r",
        type=str,
        default=random_raw_data,
        help="The raw data to be stored.",
    )
    args = parser.parse_args()
    attributes = {
        "field1": random.randint(0, 100),
        "field2": random.randint(101, 200),
        "field3": random.randint(201, 300),
    }
    vertex1 = {
        "object": str(uuid.uuid4()),
        "collection": IndalekoDBCollections.Indaleko_Object_Collection,
    }
    vertex2 = {
        "object": str(uuid.uuid4()),
        "collection": IndalekoDBCollections.Indaleko_Object_Collection,
    }
    r = IndalekoRelationship(
        objects=[vertex1, vertex2],
    )
    contains_relationship = "207ec370-11e7-4aed-9d1e-429a5b84e7bf"
    r.add_relationship(contains_relationship, attributes)
    ic(r.serialize())
    ic(args)


if __name__ == "__main__":
    main()
