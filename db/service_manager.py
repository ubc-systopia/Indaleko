"""
The purpose of this package is to create a common class structure for managing
Indaleko Services.

We have multiple sources of information that can be indexed by Indaleko.  Thus,
this provides a "registration mechanism" that allows a service to create a
registration endpoint and get back an object that it can use for interacting
with its service information.

The types of services envisioned here are:

* Collectors - these are component that gather data from storage locations.
* Recorders - these are components that convert raw indexed information into a
  common format that is used when storing the actual data.

I expect there will be other kinds of services in the future, but that's the
list for now.

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
import datetime
import logging
import os
import sys
import uuid

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from constants import IndalekoConstants
from data_models import (
    IndalekoRecordDataModel,
    IndalekoServiceDataModel,
    IndalekoSourceIdentifierDataModel,
)
from db import IndalekoDBCollections
from db.collection import IndalekoCollection
from db.db_config import IndalekoDBConfig
from utils.data_validation import validate_uuid_string
from utils.i_logging import IndalekoLogging
from utils.misc.data_management import encode_binary_data
from utils.misc.directory_management import indaleko_default_log_dir
from utils.misc.file_name_management import generate_file_name
from utils.misc.service import IndalekoService
from utils.singleton import IndalekoSingleton


# pylint: enable=wrong-import-position


class IndalekoServiceManager(IndalekoSingleton):
    """This class defines the service model for Indaleko."""

    Schema = IndalekoServiceDataModel.get_arangodb_schema()

    service_manager_uuid_str = "c3e03488-660c-42f5-8277-1c8073fb2144"
    service_manager_version = "1.1"

    indaleko_services = "Services"
    assert (
        indaleko_services in IndalekoDBCollections.Collections
    ), f"{indaleko_services} must be in Indaleko_Collections"

    service_type_test = IndalekoConstants.service_type_test
    service_type_machine_configuration = IndalekoConstants.service_type_machine_configuration
    service_type_storage_collector = IndalekoConstants.service_type_storage_collector
    service_type_storage_recorder = IndalekoConstants.service_type_storage_recorder
    service_type_semantic_transducer = IndalekoConstants.service_type_semantic_transducer
    service_type_activity_context_generator = IndalekoConstants.service_type_activity_context_generator
    service_type_activity_data_collector = IndalekoConstants.service_type_activity_data_collector
    service_type_activity_data_registrar = IndalekoConstants.service_type_activity_data_registrar

    service_types = (
        service_type_test,
        service_type_machine_configuration,
        service_type_storage_collector,
        service_type_storage_recorder,
        service_type_semantic_transducer,
        service_type_activity_context_generator,
        service_type_activity_data_collector,
        service_type_activity_data_registrar,
    )

    CollectionDefinition = {
        "schema": Schema,
        "edge": False,
        "indices": {
            "name": {"fields": ["Name"], "unique": True, "type": "persistent"},
        },
    }

    def __init__(self, reset: bool = False) -> None:
        self.db_config = IndalekoDBConfig()
        self.db_config.start()
        self.service_collection = IndalekoCollection(
            name=self.indaleko_services,
            definition=self.CollectionDefinition,
            db=self.db_config,
            reset=reset,
        )
        if not self.db_config._arangodb.has_collection(self.indaleko_services):
            self.create_indaleko_services_collection()

    def create_indaleko_services_collection(self) -> IndalekoCollection:
        """This method creates the IndalekoServices collection in the database."""
        assert not self.db_config._arangodb.has_collection(
            self.indaleko_services,
        ), f"{self.indaleko_services} collection already exists, cannot create it."
        self.service_collection = IndalekoCollection(
            name=self.indaleko_services,
            definition=self.CollectionDefinition,
            db=self.db_config._arangodb,
        )
        self.service_collection.add_schema(IndalekoServiceManager.Schema)
        self.service_collection.create_index(
            name="service name",
            fields=["Name"],
            type="persistent",
            unique=True,
        )
        return self.service_collection

    def lookup_service_by_name(self, name: str) -> dict:
        """This method is used to lookup a service by name."""
        entries = self.service_collection.find_entries(Name=name)
        assert len(entries) < 2, f"Multiple entries found for service {name}, not handled."
        if len(entries) == 0:
            return None
        return IndalekoService.deserialize(entries[0])

    def lookup_service_by_identifier(self, service_identifier: str) -> dict:
        """This method is used to lookup a service by name."""
        if not validate_uuid_string(service_identifier):
            raise ValueError(f"{service_identifier} is not a valid UUID.")
        entries = self.service_collection.find_entries(Identifier=service_identifier)
        assert len(entries) < 2, f"Multiple entries found for service {service_identifier}, not handled."
        if len(entries) == 0:
            return None
        return IndalekoService.deserialize(entries[0])

    def register_service(
        self,
        service_name: str,
        service_description: str,
        service_version: str,
        service_type: str,
        service_id: str | None = None,
        debug: bool = False,
    ) -> dict:
        """
        This method registers a service with the given name, description, and
        version in the database.
        """
        assert service_type in IndalekoServiceManager.service_types, f"Invalid service type {service_type} specified."
        existing_service = None
        if service_id is not None:
            existing_service = self.lookup_service_by_identifier(str(service_id))
            if existing_service is not None:
                # Make sure the registration data matches.
                if existing_service.service_name != service_name:
                    ic(
                        "Service name mismatch",
                        existing_service.service_name,
                        service_name,
                    )
                if existing_service.service_description != service_description:
                    ic(
                        "Service description mismatch",
                        existing_service.service_description,
                        service_description,
                    )
                if existing_service.service_version != service_version:
                    ic(
                        "Service version mismatch",
                        existing_service.service_version,
                        service_version,
                    )
                if existing_service.service_type != service_type:
                    ic(
                        "Service type mismatch",
                        existing_service.service_type,
                        service_type,
                    )
        if existing_service is None:
            if service_id is None:
                service_id = str(uuid.uuid4())
            if debug:
                ic("Creating new service:", service_id)
            new_service = IndalekoService(
                record=IndalekoRecordDataModel(
                    SourceIdentifier=IndalekoSourceIdentifierDataModel(
                        Identifier=IndalekoServiceManager.service_manager_uuid_str,
                        Version=IndalekoServiceManager.service_manager_version,
                        Description="Indaleko Service Manager",
                    ),
                    Timestamp=datetime.datetime.now(datetime.UTC),
                    Attributes={},
                    Data=encode_binary_data(b"{}"),
                ),
                service_name=service_name,
                service_description=service_description,
                service_version=service_version,
                service_type=service_type,
                service_identifier=service_id,
            )
            document = new_service.serialize()
            self.service_collection.insert(document)
            existing_service = self.lookup_service_by_identifier(service_id)
        return existing_service


class IndalekoServiceManagerTest:
    """This class defines the test operations for the IndalekoServiceManager."""

    def __init__(self) -> None:
        self.service_manager = IndalekoServiceManager()

    @staticmethod
    def find_test_service():
        """Find the test service."""
        service_manager = IndalekoServiceManager()
        return service_manager.lookup_service_by_name("Test Service")

    @staticmethod
    def test_create_service(args: argparse.Namespace) -> None:
        """Test creating a service."""
        ic("Creating the test service")
        ic(args)
        service_manager = IndalekoServiceManager()
        new_service = service_manager.register_service(
            service_name="Test Service",
            service_description="This is a test service.",
            service_version="1.0.0",
            service_type="Test",
        )
        ic(new_service)

    @staticmethod
    def test_lookup_service(args: argparse.Namespace) -> None:
        """Test looking up a service."""
        ic("Looking up the test service")
        ic(args)

    @staticmethod
    def test_delete_service(args: argparse.Namespace) -> None:
        """Test deleting a service."""
        ic("Deleting the service")
        ic(args)
        service_manager = IndalekoServiceManager()
        service = service_manager.lookup_service_by_name("Test Service")
        if service is not None:
            ic(dir(service))
            ic(service.service_identifier)
            service_manager.service_collection.delete(service.service_identifier)
            ic("Test Service deleted.")
        else:
            ic("Test Service not found.")


def list_services(args: argparse.Namespace) -> None:
    """List the services in the database."""
    ic("List the services")
    ic(args)
    service_manager = IndalekoServiceManager()
    services = service_manager.service_collection.find_entries()
    for service in services:
        ic(service)


def delete_service(args: argparse.Namespace) -> None:
    """Delete a service from the database."""
    ic("Deleting the service")
    ic(args)
    service_manager = IndalekoServiceManager()
    if args.name:
        ic("Function not implemented yet.")
    else:
        service = service_manager.lookup_service_by_identifier(args.identifier)
        if service is not None:
            service_manager.service_collection.delete(service.service_identifier)
            ic(f"Service {args.identifier} deleted.")
        else:
            ic(f"Service {args.identifier} not found.")


def main() -> None:
    """The interface for the service manager."""
    now = datetime.datetime.now(datetime.UTC)
    timestamp = now.isoformat()
    parser = argparse.ArgumentParser(description="Indaleko Service Manager")
    parser.add_argument(
        "--logdir",
        type=str,
        default=indaleko_default_log_dir,
        help="Log directory",
    )
    parser.add_argument("--log", type=str, default=None, help="Log file name")
    parser.add_argument(
        "--loglevel",
        type=int,
        default=logging.DEBUG,
        choices=IndalekoLogging.get_logging_levels(),
        help="Log level",
    )
    command_subparser = parser.add_subparsers(dest="command")
    parser_test = command_subparser.add_parser("test", help="Test the service manager")
    # Set up the test logic
    test_subparser = parser_test.add_subparsers(dest="test_command")
    parser_test_create = test_subparser.add_parser(
        "create",
        help="Create the test service manager",
    )
    parser_test_create.set_defaults(func=IndalekoServiceManagerTest.test_create_service)
    parser_test_lookup = test_subparser.add_parser(
        "lookup",
        help="Lookup the test service",
    )
    parser_test_lookup.set_defaults(func=IndalekoServiceManagerTest.test_lookup_service)
    parser_test_delete = test_subparser.add_parser(
        "delete",
        help="Delete the test service",
    )
    parser_test_delete.set_defaults(func=IndalekoServiceManagerTest.test_delete_service)
    # List the registered services
    parser_list = command_subparser.add_parser(
        "list",
        help="List the registered services",
    )
    parser_list.set_defaults(func=list_services)
    # Delete a registered service
    parser_delete = command_subparser.add_parser(
        "delete",
        help="Delete a registered services",
    )
    parser_delete.add_argument(
        "--name",
        type=str,
        help="The name of the service to delete",
    )
    parser_delete.add_argument(
        "--identifier",
        type=str,
        help="The identifier of the service to delete",
    )
    parser_delete.set_defaults(func=delete_service)
    parser.set_defaults(func=list_services)
    args = parser.parse_args()
    ic(args)
    if args.log is None:
        args.log = generate_file_name(
            suffix="log",
            service="IndalekoServiceManager",
            timestamp=timestamp,
        )
    indaleko_logging = IndalekoLogging(
        service_name="IndalekoServiceManager",
        log_level=args.loglevel,
        log_file=args.log,
        log_dir=args.logdir,
    )
    if indaleko_logging is None:
        sys.exit(1)
    logging.info("Starting IndalekoServiceManager")
    logging.debug(args)
    args.func(args)
    logging.info("IndalekoServiceManager: done processing.")


if __name__ == "__main__":
    main()
