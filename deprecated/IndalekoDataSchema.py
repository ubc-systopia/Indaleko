"""
This module defines the database schema for any database record conforming to
the Indaleko Record requirements.

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

import json
import uuid

from datetime import datetime

import jsonschema
import jsonschema.exceptions

from apischema.graphql import graphql_schema
from graphql import print_schema

from IndalekoDataModel import IndalekoDataModel, IndalekoUUID


class IndalekoDataSchema:
    """This is the base class for schema within Indaleko"""

    def __init__(self, **kwargs):
        """Initialize the schema"""
        self.data_model = kwargs.get("data_model", IndalekoDataModel())
        self.base_type = kwargs.get("base_type", IndalekoDataModel.SourceIdentifier)
        self.schema_rules = kwargs.get("schema_rules", {})
        self.schema_standard = kwargs.get(
            "schema_standard", "https://json-schema.org/draft/2020-12/schema#"
        )
        self.schema_id = kwargs.get(
            "schema_id", "https://activitycontext.work/indaleko/schema/record.json"
        )
        self.schema_title = kwargs.get("schema_title", "Indaleko Schema")
        self.schema_description = kwargs.get("schema_description", "Default Schema.")
        self.schema_type = kwargs.get("schema_type", "object")
        assert isinstance(self.schema_rules, dict), "schema_rules must be a dictionary"
        self.json_schema = kwargs.get(
            "json_schema",
            {
                "$schema": self.schema_standard,
                "$id": self.schema_id,
                "title": self.schema_title,
                "description": self.schema_description,
                "type": self.schema_type,
                "rule": self.schema_rules,
            },
        )
        self.graphql_queries = self.data_model.get_queries()
        if "graphql_queries" in kwargs:
            self.graphql_queries.extend(kwargs["graphql_queries"])
        self.graphql_types = self.data_model.get_types()
        if "graphql_types" in kwargs:
            self.graphql_types.extend(kwargs["graphql_types"])
        self.graphql_schema = graphql_schema(
            query=self.data_model.get_queries(), types=self.data_model.get_types()
        )

    def check_against_schema(self, data: dict) -> bool:
        """Check the data against the schema"""
        assert isinstance(data, dict), f"data must be a dictionary, not {type(data)}"
        try:
            jsonschema.validate(data, self.json_schema)
            return True
        except jsonschema.exceptions.ValidationError as error:
            print(f"Validation error: {error}")
            return False

    def is_valid_record(self, indaleko_record: dict) -> bool:
        """Check if the record is valid"""
        assert isinstance(indaleko_record, dict), "indaleko_record must be a dictionary"
        return self.check_against_schema(indaleko_record)

    def is_valid_json_schema(self) -> bool:
        """Is the schema associated with this object valid?"""
        return IndalekoDataSchema.is_valid_json_schema_dict(self.json_schema)

    @staticmethod
    def is_valid_json_schema_dict(schema_dict: dict) -> bool:
        """Given a dict representing a schema, determine if it is a valid schema."""
        valid = False
        try:
            jsonschema.Draft202012Validator.check_schema(schema_dict)
            valid = True
        except jsonschema.exceptions.SchemaError as e:
            print(f"Schema Validation Error: {e}")
        return valid

    @staticmethod
    def get_source_identifier(
        identifier: uuid.UUID = None,
    ) -> IndalekoDataModel.SourceIdentifier:
        """Return info on the source identifier"""
        record = IndalekoDataModel.SourceIdentifier(
            Identifier=identifier, Version="1.0", Description="This is a test record"
        )
        return record

    @staticmethod
    def get_indaleko_uuid(
        label: str = None, identifier: uuid.UUID = None
    ) -> IndalekoUUID:
        """Return a UUID"""
        indaleko_uuid = IndalekoUUID(Identifier=identifier, Label=label)
        return indaleko_uuid

    @staticmethod
    def get_semantic_attribute(
        identifier: IndalekoUUID = None, data: str = None
    ) -> IndalekoDataModel.SemanticAttribute:
        """Return a semantic attribute"""
        semantic_attribute = IndalekoDataModel.SemanticAttribute(
            Identifier=identifier, Data=data
        )
        return semantic_attribute

    @staticmethod
    def get_timestamp(
        label: uuid.UUID = None, value: datetime = None, description: str = None
    ) -> IndalekoDataModel.Timestamp:
        """Return a timestamp"""
        record = IndalekoDataModel.Timestamp(
            Label=label, Value=value, Description=description
        )
        return record

    def get_graphql_schema(self):
        """Return the GraphQL schema for the Record collection."""
        return self.graphql_schema

    def get(self, key: str, default: str = None) -> str:
        """Get a value from the schema object."""
        if hasattr(self, key):
            return getattr(self, key)
        return default

    def get_json_schema(self: "IndalekoDataSchema") -> dict:
        """Return the JSON schema for the object."""
        return self.json_schema

    def print_graphql_schema(self) -> str:
        """Return the GraphQL schema for the schema."""
        return print_schema(self.graphql_schema)

    def schema_detail(self) -> None:
        """Provide a basic function to check the schema detail."""
        if hasattr(self, "get_old_schema"):
            assert self.is_valid_json_schema_dict(
                self.get_old_schema()
            ), "Old schema is not valid."
            print("Old schema is valid.")
            print("Old Schema:")
            print(json.dumps(self.get_old_schema(), indent=4))
        assert self.is_valid_json_schema(), "New schema is not valid."
        print("New schema is valid")
        print("New Schema:")
        print(json.dumps(self.get_json_schema(), indent=4))
        print("GraphQL Schema:")
        print(self.print_graphql_schema())


def main():
    """Test code for IndalekoSchema."""
    indaleko_schema = IndalekoDataSchema()
    indaleko_schema.schema_detail()


if __name__ == "__main__":
    main()
