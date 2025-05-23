"""
Implements registration service for activity data providers.

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

import os
import sys
from pathlib import Path
from typing import Any

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position

from activity.registration import IndalekoActivityDataRegistration
from data_models.activity_data_registration import (
    IndalekoActivityDataRegistrationDataModel,
)
from db import IndalekoCollection, IndalekoDBCollections, IndalekoServiceManager
from utils.registration_service import IndalekoRegistrationService

# pylint: enable=wrong-import-position


class IndalekoActivityDataRegistrationService(IndalekoRegistrationService):
    """
    Implements the Indaleko Activity Data Provider Registration Service.

    This service manages the registration of activity data providers,
    which collect and record user and system activities.
    """

    # Service details
    service_uuid_str = "5ef4125d-4e46-4e35-bea5-f23a9fcb3f63"
    service_version = "1.0"
    service_description = "Indaleko Activity Data Provider Registration Service"
    service_name = "IndalekoActivityDataProviderRegistrationService"
    collection_name = IndalekoDBCollections.Indaleko_ActivityDataProvider_Collection
    collection_prefix = IndalekoActivityDataRegistration.provider_prefix
    service_type = IndalekoServiceManager.service_type_activity_data_registrar

    def __init__(self) -> None:
        """Create an instance of the registration service."""
        super().__init__(
            service_uuid=self.service_uuid_str,
            service_name=self.collection_name,  # For backward compatibility
            service_description=self.service_description,
            service_version=self.service_version,
            service_type=self.service_type,
            collection_name=self.collection_name,
            collection_prefix=self.collection_prefix,
        )

        # For backward compatibility
        self.activity_provider_collection = self.provider_collection
        # pylint: disable=invalid-name
        self.Version = self.service_version
        self.Description = self.service_description
        # pylint: enable=invalid-name
        self.Name = self.service_name

    def _process_registration_data(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """
        Process registration data for activity providers.

        Args:
            kwargs: Registration parameters

        Returns:
            Processed registration data
        """
        # Process through IndalekoActivityDataRegistration
        activity_registration = IndalekoActivityDataRegistration(
            registration_data=kwargs,
        )

        # Use the model_dump_json method to process the data
        return activity_registration.model_dump_json()

    # Legacy compatibility methods

    @staticmethod
    def deserialize(data: dict) -> "IndalekoActivityDataRegistrationService":
        """Deserialize the registration service from a dictionary."""
        return IndalekoActivityDataRegistrationService(**data)

    @staticmethod
    def lookup_provider_by_identifier(
        identifier: str,
    ) -> IndalekoActivityDataRegistrationDataModel | None:
        """Return the provider with the given identifier."""
        service = IndalekoActivityDataRegistrationService()
        provider = service.lookup_provider_by_identifier_internal(identifier)
        if provider is None:
            return None
        return IndalekoActivityDataRegistrationDataModel.deserialize(provider)

    def lookup_provider_by_identifier_internal(
        self,
        identifier: str,
    ) -> dict[str, Any] | None:
        """Internal method to lookup provider by identifier."""
        return super().lookup_provider_by_identifier(identifier)

    @staticmethod
    def lookup_provider_by_name(
        name: str,
    ) -> IndalekoActivityDataRegistrationDataModel | None:
        """Return the provider with the given name."""
        service = IndalekoActivityDataRegistrationService()
        provider = service.lookup_provider_by_name_internal(name)
        if provider is None:
            return None
        return IndalekoActivityDataRegistrationDataModel.deserialize(provider)

    def lookup_provider_by_name_internal(self, name: str) -> dict[str, Any] | None:
        """Internal method to lookup provider by name."""
        return super().lookup_provider_by_name(name)

    @staticmethod
    def lookup_activity_provider_collection(identifier: str) -> IndalekoCollection:
        """Lookup an activity provider collection."""
        return IndalekoActivityDataRegistrationService().lookup_provider_collection(
            identifier,
        )

    @staticmethod
    def create_activity_provider_collection(
        identifier: str,
        schema: dict | str | None = None,
        edge: bool = False,  # noqa: FBT001
        indices: list | None = None,
        reset: bool = False,  # noqa: FBT001
    ) -> IndalekoCollection:
        """Create/lookup  an activity provider collection.

        If it exists, the existing entry is returned.
        """
        service = IndalekoActivityDataRegistrationService()
        return service.create_provider_collection(
            identifier,
            schema=schema,
            edge=edge,
            indices=indices,
            reset=reset,
        )

    @staticmethod
    def delete_activity_provider_collection(
        identifier: str,
        delete_data_collection: bool = True,  # noqa: FBT001, FBT002
    ) -> bool:
        """Delete an activity provider collection."""
        service = IndalekoActivityDataRegistrationService()
        return service.delete_provider_collection(
            identifier,
            delete_data=delete_data_collection,
        )

    def register_activity_provider(self, **kwargs: dict) -> tuple[dict, IndalekoCollection]:
        """Register an activity data provider with a friendlier name."""
        return self.register_provider(**kwargs)

    @staticmethod
    def get_activity_providers_by_type(provider_type: str) -> list:
        """
        Get activity providers of a specific type.

        Args:
            provider_type: The type of provider to find

        Returns:
            List of matching providers
        """
        service = IndalekoActivityDataRegistrationService()
        providers = service.get_provider_list()

        return [
            provider
            for provider in providers
            if ("DataProviderSubType" in provider and provider["DataProviderSubType"] == provider_type)
        ]


def main() -> None:
    """Test the IndalekoActivityDataRegistrationService."""
    service = IndalekoActivityDataRegistrationService()

    print(f"Initialized {service.__class__.__name__}")  # noqa: T201
    print(f"Service UUID: {service.service_uuid_str}")  # noqa: T201
    print(f"Collection name: {service.collection_name}")  # noqa: T201
    print(f"Provider count: {len(service.get_provider_list())}")  # noqa: T201
    print()  # noqa: T201
    print("Service JSON:")  # noqa: T201
    print(service.to_json())  # noqa: T201


if __name__ == "__main__":
    main()
