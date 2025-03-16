"""
This defines the Indaleko Object schema.

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

import apischema
import jsonschema
from jsonschema import validate

from IndalekoRecordSchema import IndalekoRecordSchema
from IndalekoObjectDataModel import IndalekoObjectDataModel


class IndalekoObjectSchema(IndalekoRecordSchema):
    """This class defines the schema for an Indaleko Object."""

    def __init__(self, **kwargs):
        """Initialize the Object schema."""
        if not hasattr(self, "data_model"):
            self.data_model = IndalekoObjectDataModel()
        if not hasattr(self, "base_type"):
            self.base_type = IndalekoObjectDataModel.IndalekoObject
        object_rules = apischema.json_schema.serialization_schema(
            IndalekoObjectDataModel.IndalekoObject, additional_properties=True
        )
        if not hasattr(self, "rules"):
            self.rules = object_rules
        else:
            self.rules.update(object_rules)
        schema_id = kwargs.get(
            "schema_id", "https://activitycontext.work/schema/indaleko-object.json"
        )
        schema_title = kwargs.get("schema_title", "Indaleko Object Schema")
        schema_description = kwargs.get(
            "schema_description",
            "Schema for the JSON representation of an Indaleko Object.",
        )
        super().__init__(
            schema_id=schema_id,
            schema_title=schema_title,
            schema_description=schema_description,
            data_model=self.data_model,
            base_type=self.base_type,
            schema_rules=object_rules,
        )

    @staticmethod
    def is_valid_object(indaleko_object: dict) -> bool:
        """Given a dict, determine if it is a valid Indaleko Object."""
        assert isinstance(indaleko_object, dict), "object must be a dict"
        valid = False
        try:
            validate(
                instance=indaleko_object, schema=IndalekoObjectSchema.get_old_schema()
            )
            valid = True
        except jsonschema.exceptions.ValidationError as error:
            print(f"Validation error: {error.message}")
        return valid

    @staticmethod
    def get_old_schema():
        object_schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema#",
            "$id": "https://activitycontext.work/schema/indaleko-object.json",
            "title": "Indaleko Object Schema",
            "description": "Schema for the JSON representation of an Indaleko Object, which is used for indexing storage content.",
            "type": "object",
            "rule": {
                "type": "object",
                "properties": {
                    "Label": {
                        "type": "string",
                        "description": "The object label (like a file name).",
                    },
                    "URI": {"type": "string", "description": "The URI of the object."},
                    "ObjectIdentifier": {
                        "type": "string",
                        "description": "The object identifier (UUID).",
                        "format": "uuid",
                    },
                    "LocalIdentifier": {
                        "type": "string",
                        "description": "The local identifier used by the storage system to find this, such as a UUID or inode number.",
                    },
                    "Timestamps": {
                        "type": "array",
                        "properties": {
                            "Label": {
                                "type": "string",
                                "description": "UUID representing the semantic meaning of this timestamp.",
                                "format": "uuid",
                            },
                            "Value": {
                                "type": "string",
                                "description": "Timestamp in ISO date and time format.",
                                "format": "date-time",
                            },
                            "Description": {
                                "type": "string",
                                "description": "Description of the timestamp.",
                            },
                        },
                        "required": ["Label", "Value"],
                        "description": "List of timestamps with UUID-based semantic meanings associated with this object.",
                    },
                    "Size": {
                        "type": "integer",
                        "description": "Size of the object in bytes.",
                    },
                    "RawData": {
                        "type": "string",
                        "description": "Raw data captured for this object.",
                        "contentEncoding": "base64",
                        "contentMediaType": "application/octet-stream",
                    },
                    "SemanticAttributes": {
                        "type": "array",
                        "description": "Semantic attributes associated with this object.",
                        "properties": {
                            "UUID": {
                                "type": "string",
                                "description": "The UUID for this attribute.",
                                "format": "uuid",
                            },
                            "Data": {
                                "type": "string",
                                "description": "The data associated with this attribute.",
                            },
                        },
                        "required": ["UUID", "Data"],
                    },
                },
                "required": [
                    "URI",
                    "ObjectIdentifier",
                    "Timestamps",
                    "Size",
                ],
            },
        }
        assert (
            "Record" not in object_schema["rule"]["properties"]
        ), "Record should not be in object schema."
        object_schema["rule"]["properties"][
            "Record"
        ] = IndalekoRecordSchema.get_old_schema()["rule"]
        object_schema["rule"]["required"].append("Record")
        return object_schema


def main():
    """Test code for IndalekoObjectSchema."""
    object_schema = IndalekoObjectSchema()
    object_schema.schema_detail()


if __name__ == "__main__":
    main()
