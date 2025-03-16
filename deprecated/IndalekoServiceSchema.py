"""
This defines the Indaleko Services schema.

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

import jsonschema
import apischema

from uuid import UUID

from IndalekoRecordSchema import IndalekoRecordSchema
from IndalekoServiceDataModel import IndalekoServiceDataModel


class IndalekoServiceSchema(IndalekoRecordSchema):
    """This class defines the schema for Indaleko Services."""

    def __init__(self, **kwargs):
        """Initialize the Services schema."""
        if not hasattr(self, "data_model"):
            self.data_model = IndalekoServiceDataModel()
        if not hasattr(self, "base_type"):
            self.base_type = IndalekoServiceDataModel.IndalekoService
        services_rules = apischema.json_schema.deserialization_schema(
            IndalekoServiceDataModel.IndalekoService, additional_properties=True
        )
        if not hasattr(self, "rules"):
            self.rules = services_rules
        else:
            self.rules.update(services_rules)
        schema_id = kwargs.get(
            "schema_id", "https://activitycontext.work/schema/serviceprovider.json"
        )
        schema_title = kwargs.get("schema_title", "Service provider schema")
        schema_description = kwargs.get(
            "schema_description",
            "This schema describes information about service providers within the Indaleko system.",
        )
        super().__init__(
            schema_id=schema_id,
            schema_title=schema_title,
            schema_description=schema_description,
            data_model=self.data_model,
            base_type=self.base_type,
            schema_rules=services_rules,
        )

    @staticmethod
    def is_valid_services(indaleko_services: dict) -> bool:
        """Given a dict, determine if it is a valid Indaleko Services."""
        assert isinstance(indaleko_services, dict), "services must be a dict"
        valid = False
        try:
            jsonschema.validate(
                instance=indaleko_services,
                schema=IndalekoServiceSchema.get_old_schema(),
            )
            valid = True
        except jsonschema.exceptions.ValidationError as error:
            print(f"Validation error: {error.message}")
        return valid

    @staticmethod
    def get_service(identifier: UUID) -> IndalekoServiceDataModel.IndalekoService:
        """Return an IndalekoService object."""
        service = IndalekoServiceDataModel.IndalekoService(
            Record=None,
            Identifier=identifier,
            Version="1.0.0",
            Name="Test Service",
            Type="Test",
        )
        return service


def main():
    """Test code for IndalekoObjectSchema."""
    services_schema = IndalekoServiceSchema()
    services_schema.schema_detail()


if __name__ == "__main__":
    main()
