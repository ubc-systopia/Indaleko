"""
This module defines the database schema for any database record conforming to
the Indaleko Record requirements.

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

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Annotated, Optional, List
from uuid import UUID, uuid4
from apischema import schema, ValidationError, deserialize, serialize
from apischema.graphql import graphql_schema
from apischema.metadata import required
from graphql import print_schema
from icecream import ic

@dataclass
class IndalekoUUID:
    """Define a UUID with an optional label."""
    Identifier : Annotated[
        UUID,
        schema(description="A Universally Unique Identifier",
               format="uuid")
    ]

    Label: Annotated[
        Optional[str],
        schema(description="A human-readable label for the UUID.")
    ] = None

    @staticmethod
    def get_indaleko_uuid(identifier : UUID, label : str = None) -> 'IndalekoUUID':
        """Lookup a UUID."""
        return IndalekoUUID(
            Identifier=identifier,
            Label=label
        )

    @staticmethod
    def deserialize(data: Dict[str, Any]) -> 'IndalekoUUID':
        """Deserialize a dictionary to an object."""
        return deserialize(IndalekoUUID, data)

    @staticmethod
    def serialize(data) -> Dict[str, Any]:
        """Serialize the object to a dictionary."""
        return serialize(IndalekoUUID, data)


class IndalekoDataModel:
    """Base class for the IndalekoDataModel."""

    @dataclass
    class SourceIdentifier:
        """Define a source identifier for this Indaleko Record."""
        Identifier: Annotated[
            UUID,
            schema(description="The identifier of the source of the data.")
        ]
        Version: Annotated[
            str,
            schema(description="The version of the source of the data.")
        ]
        Description: Annotated[
            Optional[str],
            schema(description="A human-readable description of the source of the data.")
        ] = None

        @staticmethod
        def serialize(data) -> Dict[str, Any]:
            """Serialize the object to a dictionary."""
            return serialize(IndalekoDataModel.SourceIdentifier, data)

        @staticmethod
        def deserialize(data: Dict[str, Any]) -> 'IndalekoDataModel.SourceIdentifier':
            """Deserialize a dictionary to an object."""
            try:
                deserialize(IndalekoDataModel.SourceIdentifier, data)
            except ValidationError as error:
                raise ValidationError(f"Validation error: {error}") from error

    @staticmethod
    def get_source_identifier(uuid: UUID) -> 'IndalekoDataModel.SourceIdentifier':
        """Lookup a source identifier."""
        return IndalekoDataModel.SourceIdentifier(
            Identifier=uuid,
            Version='1.0',
            Description='This is a test record'
        )


    @dataclass
    class Timestamp:
        """General definition of a timestamp."""
        Label: Annotated[
            UUID,
            schema(description="UUID representing the semantic meaning of this timestamp."),
            required
        ]
        Value: Annotated[
            datetime,
            schema(description="Timestamp in ISO date and time format.",
                   format="date-time"),
            required
        ]
        Description: Annotated[
            Optional[str],
            schema(description="Description of the timestamp.")
        ] = None

    @staticmethod
    def get_timestamp(uuid: UUID, value: datetime = datetime.now(timezone.utc), description: str = 'Prototype description') -> 'IndalekoDataModel.Timestamp':
        """Lookup a timestamp."""
        return IndalekoDataModel.Timestamp(
            Label=uuid,
            Value=value,
            Description=description
        )

    @dataclass
    class SemanticAttribute:
        """Define a semantic attribute related to the data."""
        Identifier: Annotated[
            IndalekoUUID,
            schema(description="The UUID for this attribute.", format="uuid"), required
        ]
        Data: Annotated[
            str,
            schema(description="The data associated with this attribute."),
            required
        ]

    @staticmethod
    def get_semantic_attribute(identifier : IndalekoUUID) -> 'IndalekoDataModel.SemanticAttribute':
        """Lookup a semantic attribute."""
        return IndalekoDataModel.SemanticAttribute(
            Identifier=identifier,
            Data='This is the dummy data for the semantic attribute.'
        )

    @staticmethod
    def get_queries() -> List:
        """Return the queries for the IndalekoDataModel."""
        return [
            IndalekoDataModel.get_source_identifier,
            IndalekoDataModel.get_timestamp,
            IndalekoUUID.get_indaleko_uuid,
            IndalekoDataModel.get_semantic_attribute
        ]

    @staticmethod
    def get_types() -> List:
        """Return the types for the IndalekoDataModel."""
        return [
            IndalekoDataModel.SourceIdentifier,
            IndalekoDataModel.Timestamp,
            IndalekoUUID,
            IndalekoDataModel.SemanticAttribute
        ]

def main():
    """Test code for the IndalekoDataModel class."""
    ic("This is the IndalekoDataModel module")
    ic('GraphQL schema:')
    ic(print_schema(graphql_schema(query=IndalekoDataModel.get_queries(),
                                      types=IndalekoDataModel.get_types())))


    source_id = {
        "Identifier" : str(uuid4()),
        "Version" : "1.0",
        "Description" : "This is a test ID"
    }
    ic(IndalekoDataModel.SourceIdentifier.deserialize(source_id))
    ic(IndalekoDataModel.get_source_identifier(source_id['Identifier']))
    ic(IndalekoDataModel.SourceIdentifier.serialize(IndalekoDataModel.get_source_identifier(source_id['Identifier'])))

    timestamp = {
        "Label" : str(uuid4()),
        "Value" : datetime.now(timezone.utc).isoformat(),
        "Description" : "This is a test timestamp"
    }
    ic(deserialize(IndalekoDataModel.Timestamp, timestamp))
    ic(IndalekoDataModel.get_timestamp(UUID(timestamp['Label']),
                                       datetime.fromisoformat(timestamp['Value']),
                                       timestamp['Description']))

    indaleko_uuid = {
        "Identifier" : str(uuid4()),
        "Label" : "This is a test UUID"
    }
    ic(IndalekoUUID.deserialize(indaleko_uuid))
    ic(IndalekoUUID.get_indaleko_uuid(UUID(indaleko_uuid['Identifier']), indaleko_uuid['Label']))
    ic(IndalekoUUID.serialize(IndalekoUUID.get_indaleko_uuid(UUID(indaleko_uuid['Identifier']), indaleko_uuid['Label'])))
    semantic_attribute = {
        "Identifier" : indaleko_uuid,
        "Data" : "This is a test semantic attribute"
    }
    ic(deserialize(IndalekoDataModel.SemanticAttribute, semantic_attribute))
    ic(IndalekoDataModel.get_semantic_attribute(indaleko_uuid))

if __name__ == "__main__":
    main()
