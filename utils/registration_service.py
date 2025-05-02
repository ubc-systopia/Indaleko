"""
Base registration service for Indaleko data providers.

This module provides a generic registration service that can be extended
for specific types of data providers (activity, semantic, storage, etc.)

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
import logging
import os
import sys

from contextlib import suppress
from pathlib import Path
from typing import Any


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from db import (
    IndalekoCollection,
    IndalekoCollections,
    IndalekoDBConfig,
    IndalekoServiceManager,
)
from utils.data_validation import validate_uuid_string
from utils.misc.service import IndalekoService
from utils.singleton import IndalekoSingleton


# pylint: enable=wrong-import-position


class IndalekoRegistrationService(IndalekoSingleton):
    """
    Base class for Indaleko data provider registration services.

    This class provides generic registration functionality that can be
    extended for specific types of data providers. The registration service
    maintains a registry of data providers and their associated collections.
    """

    def __init__(
        self,
        service_uuid: str,
        service_name: str,
        service_description: str,
        service_version: str,
        service_type: str,
        collection_name: str,
        collection_prefix: str,
    ) -> None:
        """
        Initialize the registration service.

        Args:
            service_uuid: UUID string for this registration service
            service_name: Name of this registration service
            service_description: Description of this registration service
            service_version: Version string for this registration service
            service_type: Type of service (e.g., "activity_data_registrar")
            collection_name: Name of the collection to store provider registrations
            collection_prefix: Prefix for provider data collections
        """
        if self._initialized:
            return

        # Store service information
        self.service_uuid_str = service_uuid
        self.service_name = service_name
        self.service_description = service_description
        self.service_version = service_version
        self.service_type = service_type
        self.collection_name = collection_name
        self.collection_prefix = collection_prefix

        # Set up logging
        self.logger = logging.getLogger(f"Indaleko.{self.__class__.__name__}")

        # Register this service with the service manager
        self.service = IndalekoServiceManager().register_service(
            service_name=self.service_name,
            service_description=self.service_description,
            service_version=self.service_version,
            service_type=self.service_type,
            service_id=self.service_uuid_str,
        )

        # Get or create the provider collection
        self.provider_collection = IndalekoCollections().get_collection(
            self.collection_name,
        )
        assert self.provider_collection is not None, (    # noqa: S101
            f"Provider collection {self.collection_name} must exist"
        )

        self._initialized = True
        self.logger.info("Initialized %s", self.__class__.__name__)

    def serialize(self) -> dict:
        """Serialize the registration service to a dictionary."""
        serialized_data = IndalekoService.serialize(self.service)
        if isinstance(serialized_data, tuple):
            assert len(serialized_data) == 1, "Serialized data is a multi-entry tuple."  # noqa: S101
            serialized_data = serialized_data[0]
        if isinstance(serialized_data, dict):
            serialized_data["_key"] = self.service_uuid_str
        return serialized_data

    def to_json(self) -> str:
        """Serialize the service to JSON."""
        return json.dumps(self.serialize(), indent=4)

    def lookup_provider_by_identifier(
        self,
        identifier: str,
    ) -> dict[str, Any] | None:
        """
        Return the provider with the given identifier.

        Args:
            identifier: UUID string of the provider

        Returns:
            Provider data if found, None otherwise
        """
        try:
            providers = self.provider_collection.find_entries(_key=identifier)
            if providers is None or len(providers) == 0:
                return None

            assert len(providers) > 0, "Expected at least one provider"  # noqa: S101
            return providers[0]
        except OSError:
            self.logger.exception("Error looking up provider by identifier %s", identifier)
            return None

    def lookup_provider_by_name(self, name: str) -> dict[str, Any] | None:
        """
        Return the provider with the given name.

        Args:
            name: Name of the provider

        Returns:
            Provider data if found, None otherwise
        """
        try:
            providers = self.provider_collection.find_entries(name=name)
            if providers is None or len(providers) == 0:
                return None

            assert len(providers) > 0, "Expected at least one provider"  # noqa: S101
            return providers[0]
        except OSError:
            self.logger.exception("Error looking up provider by name")
            return None

    def get_provider_list(self) -> list[dict[str, Any]]:
        """
        Return a list of all registered providers.

        Returns:
            List of provider data
        """
        try:
            aql_query = f"""
                FOR provider IN {self.collection_name}
                RETURN provider
            """
            cursor = IndalekoDBConfig().get_arangodb().aql.execute(aql_query)
            return list(cursor)
        except OSError:
            self.logger.exception("Error getting provider list")
            return []

    def generate_provider_collection_name(self, identifier: str) -> str:
        """
        Generate a collection name for a provider's data.

        Args:
            identifier: UUID string of the provider

        Returns:
            Collection name
        """
        assert isinstance(  # noqa: S101
            identifier,
            str,
        ), f"Identifier {identifier} must be a string is {type(identifier)}"
        assert validate_uuid_string(  # noqa: S101
            identifier,
        ), f"Identifier {identifier} must be a valid UUID"

        return f"{self.collection_prefix}{identifier}"

    def lookup_provider_collection(self, identifier: str) -> IndalekoCollection:
        """
        Lookup a provider's data collection.

        Args:
            identifier: UUID string of the provider

        Returns:
            The IndalekoCollection for the provider
        """
        return self.create_provider_collection(
            identifier,
            reset=False,
        )

    def create_provider_collection(
        self,
        identifier: str,
        schema: dict | None | str = None,
        edge: bool = False,  # noqa: FBT001, FBT002
        indices: list | None = None,
        reset: bool = False,  # noqa: FBT001, FBT002
    ) -> IndalekoCollection:
        """
        Create a collection for a provider's data.

        Args:
            identifier: UUID string of the provider
            schema: Optional schema for the collection
            edge: Whether this is an edge collection
            indices: Optional indices for the collection
            reset: Whether to reset the collection if it already exists

        Returns:
            The IndalekoCollection for the provider
        """
        assert isinstance(identifier, str), "Identifier must be a string"  # noqa: S101
        assert validate_uuid_string(  # noqa: S101
            identifier,
        ), "Identifier must be a valid UUID"

        provider_collection_name = self.generate_provider_collection_name(identifier)

        # Check if the collection already exists
        existing_collection = None

        with suppress(ValueError):
            existing_collection = IndalekoCollections.get_collection(
                provider_collection_name,
            )

        if existing_collection is not None and not reset:
            return existing_collection

        # Create collection configuration
        config = {
            "edge": edge,
        }
        if schema is not None:
            config["schema"] = {
                "rule": schema,
                "level": "strict",
                "message": "The document failed schema validation.",
            }
        if indices is not None:
            config["indices"] = indices

        # Create the collection
        return IndalekoCollections.get_collection(
            self.collection_name,
        ).create_collection(name=provider_collection_name, config=config, reset=reset)

    def delete_provider_collection(
        self,
        identifier: str,
    ) -> bool:
        """
        Delete a provider's data collection.

        Args:
            identifier: UUID string of the provider

        Returns:
            True if successful, False otherwise
        """
        # Clean up identifier if it includes the prefix
        identifier = identifier.removeprefix(self.collection_prefix)

        assert validate_uuid_string(  # noqa: S101
            identifier,
        ), "Identifier must be a valid UUID"

        provider_collection_name = self.generate_provider_collection_name(identifier)

        try:
            # Find the collection
            existing_collection = None

            with suppress(ValueError):
                existing_collection = IndalekoCollections.get_collection(
                    provider_collection_name,
                )

            # Delete the collection if it exists
            if existing_collection is not None:
                self.logger.info(
                    "Collection %s exists, deleting",
                    provider_collection_name,
                )
                existing_collection.delete_collection(provider_collection_name)
                return True
            self.logger.info(
                "Collection %s does not exist", provider_collection_name,
            )
        except OSError:
            self.logger.exception("Error deleting provider collection")

        return False

    def delete_provider(self, identifier: str) -> bool:
        """
        Delete a provider registration.

        Args:
            identifier: UUID string of the provider

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if the provider exists
            existing_provider = self.lookup_provider_by_identifier(identifier)
            if existing_provider is None:
                self.logger.info("Provider %s does not exist", identifier)
                return False

            # Delete the provider
            self.logger.info("Deleting provider %s", identifier)
            self.provider_collection.delete(identifier)
        except OSError:
            self.logger.exception("Error deleting provider")
            return False
        return True

    def register_provider(self, **kwargs: dict) -> tuple[dict, IndalekoCollection]:
        """
        Register a data provider.

        This is a generic implementation that should be overridden by subclasses
        to provide type-specific validation and processing.

        Args:
            **kwargs: Provider configuration parameters

        Returns:
            Tuple of (provider_data, provider_collection)
        """
        # Basic validation
        if "Identifier" not in kwargs:
            raise ValueError(f"Identifier must be in kwargs: {kwargs}")
        provider_id = kwargs["Identifier"]
        if not isinstance(provider_id, str):
            raise TypeError(f"Provider ID must be a string: {provider_id}")
        assert validate_uuid_string(  # noqa: S101
            provider_id,
        ), f"Provider ID must be a valid UUID: {provider_id}"

        # Check if provider already exists
        existing_provider = self.lookup_provider_by_identifier(provider_id)
        if existing_provider is not None:
            raise ValueError(f"Provider {provider_id} already exists")

        # Process registration data (subclasses should override this)
        registration_data = self._process_registration_data(kwargs)

        # Add _key field for ArangoDB
        registration_data["_key"] = provider_id

        # Insert into provider collection
        self.provider_collection.insert(json.dumps(registration_data, default=str))

        # Create data collection if requested
        provider_collection = None
        create_collection = kwargs.get("CreateCollection", True)
        if create_collection:
            schema = kwargs.get("Schema")
            edge = kwargs.get("Edge", False)
            indices = kwargs.get("Indices")

            provider_collection = self.create_provider_collection(
                provider_id,
                schema=schema,
                edge=edge,
                indices=indices,
            )

        # Verify registration
        registered_provider = self.lookup_provider_by_identifier(provider_id)
        if registered_provider is None:
            raise ValueError("Provider registration failed")

        self.logger.info("Registered provider %s", provider_id)
        return registration_data, provider_collection

    def _process_registration_data(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """
        Process registration data before inserting it.

        This method should be overridden by subclasses to provide
        type-specific validation and processing.

        Args:
            kwargs: Provider configuration parameters

        Returns:
            Processed registration data
        """
        # This is a minimal implementation that just returns the data
        # Subclasses should override this to provide proper validation
        return kwargs

    def deactivate_provider(self, identifier: str) -> bool:
        """
        Deactivate a provider.

        Args:
            identifier: UUID string of the provider

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if the provider exists
            existing_provider = self.lookup_provider_by_identifier(identifier)
            if existing_provider is None:
                self.logger.info("Provider %s does not exist", identifier)
                return False
            # Update the provider to mark it as inactive
            existing_provider["Active"] = False
            self.provider_collection.update(identifier, existing_provider)
        except OSError:
            self.logger.exception("Error deactivating provider")
            return False

        return True


def main() -> None:
    """Test the registration service."""
    # Can't instantiate the base class directly
    print("IndalekoRegistrationService is an abstract base class.")  # noqa: T201
    print("It should be extended by specific registration services.")  # noqa: T201


if __name__ == "__main__":
    main()
