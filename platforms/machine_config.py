"""
Indaleko Machine Configuration class.

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
import json
import os
import sys
import uuid
from pathlib import Path

import arango
from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.append(str(current_path))

# Set environment variable to skip view creation for this script
# This is a performance optimization to avoid slow view creation in the database
os.environ["INDALEKO_SKIP_VIEWS"] = "1"

# pylint: disable=wrong-import-position
from constants import IndalekoConstants
from data_models import IndalekoMachineConfigDataModel
from db.collection import IndalekoCollection
from db.db_collections import IndalekoDBCollections
from db.i_collections import IndalekoCollections
from db.service_manager import IndalekoServiceManager
from utils.data_validation import validate_uuid_string

# pylint: enable=wrong-import-position

# Monkey patch to make this script run faster
# Original IndalekoCollections.get_collection method
original_get_collection = IndalekoCollections.get_collection


# Faster replacement that always skips views
@staticmethod
def fast_get_collection(name: str, skip_views: bool = True) -> IndalekoCollection:  # noqa: FBT001, FBT002
    """Get a collection by name, skipping view creation."""
    return original_get_collection(name, skip_views=skip_views)


# Replace the method
# This is a monkey patch to speed up the collection retrieval process
# by skipping view creation
IndalekoCollections.get_collection = fast_get_collection


class IndalekoMachineConfig:
    """Generic base for capturing a machine configuration."""

    default_config_dir = IndalekoConstants.default_config_dir
    indaleko_machine_config_captured_label_str = "eb7eaeed-6b21-4b6a-a586-dddca6a1d5a4"
    indaleko_machine_config_captured_label_uuid = uuid.UUID(
        indaleko_machine_config_captured_label_str,
    )

    def __init__(self, **kwargs: dict) -> None:
        """Initialize the machine configuration."""
        self.debug = kwargs.get("debug", False)
        if not hasattr(self, "offline"):
            self.offline = kwargs.get("offline", False)
        kwargs.pop("offline", None)
        if not hasattr(self, "source"):  # override in derived classes
            self.source_identifier = None
        self.machine_id = kwargs.get("machine_id", kwargs.get("MachineUUID"))
        if self.machine_id is None:
            raise ValueError("Machine ID must be specified")
        kwargs.pop("machine_id", None)
        self.machine_config = IndalekoMachineConfigDataModel(**kwargs)
        if not self.offline:
            self.collection = IndalekoCollections().get_collection(
                IndalekoDBCollections.Indaleko_MachineConfig_Collection,
                skip_views=True,  # Skip view creation for performance
            )
            if self.collection is None:
                raise ValueError(
                    "Failed to get the machine configuration collection",
                )

    @staticmethod
    def find_configs_in_db(source_id: str | None = None) -> list:
        """Find the machine configurations in the database."""
        if source_id is None:
            raise ValueError("Source identifier cannot be None")
        if not validate_uuid_string(source_id):
            raise ValueError("Invalid source identifier")
        return [
            IndalekoMachineConfig.serialize(config)
            for config in IndalekoMachineConfig.lookup_machine_configurations(
                source_id=source_id,
            )
        ]

    @staticmethod
    def register_machine_configuration_service(**kwargs: str) -> dict:
        """Register the machine configuration service."""
        return IndalekoServiceManager().register_service(
            service_name=kwargs["service_name"],
            service_description=kwargs["service_description"],
            service_version=kwargs["service_version"],
            service_type=kwargs.get("service_type", "Machine Configuration"),
            service_id=kwargs.get("service_identifier"),
        )

    def write_config_to_db(self, overwrite: bool = False) -> bool:  # noqa: FBT001,FBT002
        """Write the configuration to the database."""
        status = False
        if not overwrite:
            existing_machine_config = IndalekoMachineConfig.lookup_machine_configuration_by_machine_id(
                self.machine_id,
            )
            if existing_machine_config:
                ic("Machine configuration already exists, overwrite not set")
                return status
        doc = json.loads(self.machine_config.model_dump_json())
        if "_key" not in doc:
            doc["_key"] = self.machine_id
        if "MachineUUID" not in doc:
            doc["MachineUUID"] = self.machine_id
        try:
            self.collection.insert(doc, overwrite=overwrite)
            status = True
        except arango.exceptions.DocumentInsertError as e:
            ic(f"Failed to insert document: {e}")
            ic(f"Error: {e}")
            raise
        return status

    @staticmethod
    def delete_config_in_db(machine_id: str) -> bool:
        """Delete the configuration from the database."""
        if not validate_uuid_string(machine_id):
            raise ValueError("Invalid machine identifier")
        IndalekoCollections(skip_views=True).get_collection(
            IndalekoDBCollections.Indaleko_MachineConfig_Collection,
            skip_views=True,
        ).delete(machine_id)

    @staticmethod
    def lookup_machine_configuration_by_machine_id(
        machine_id: str,
    ) -> "IndalekoMachineConfig":
        """Lookup a machine configuration service."""
        if not isinstance(machine_id, str):
            raise TypeError("Machine ID must be a UUID string")
        if not validate_uuid_string(machine_id):
            raise ValueError("Invalid machine identifier")
        collections = IndalekoCollections()
        results = collections.db_config.get_arangodb().aql.execute(
            "FOR doc IN @@collection FILTER doc._key == @machine_id RETURN doc",
            bind_vars={
                "@collection": IndalekoDBCollections.Indaleko_MachineConfig_Collection,
                "machine_id": machine_id,
            },
        )
        return [IndalekoMachineConfig(**entry) for entry in results]

    @staticmethod
    def lookup_machine_configurations(
        source_id: str | None = None,
    ) -> list["IndalekoMachineConfig"]:
        """Lookup all machine configurations."""
        collections = IndalekoCollections(
            skip_views=True,
        )  # Skip view creation for performance
        query = "FOR doc IN @@collection RETURN doc"
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_MachineConfig_Collection,
        }
        if source_id is not None:
            if not validate_uuid_string(source_id):
                raise ValueError("Invalid source identifier")
            query = "FOR doc IN @@collection "
            query += 'FILTER doc.Record["SourceIdentifier"].Identifier == '
            query += "@source RETURN doc"
            bind_vars = {
                "@collection": IndalekoDBCollections.Indaleko_MachineConfig_Collection,
                "source": source_id,
            }
        results = collections.db_config.get_arangodb().aql.execute(
            query,
            bind_vars=bind_vars,
        )
        return [IndalekoMachineConfig(**entry) for entry in results]

    def serialize(self) -> dict:
        """Serialize the machine configuration."""
        if self.debug:
            return ic(json.loads(self.machine_config.model_dump_json()))
        return json.loads(self.machine_config.model_dump_json())

    @staticmethod
    def deserialize(data: dict) -> "IndalekoMachineConfig":
        """Deserialize the machine configuration."""
        return IndalekoMachineConfig(**data)

    @staticmethod
    def find_config_files(directory: str, prefix: str, suffix: str = ".json") -> list:
        """Find configuration files in the directory."""
        if not isinstance(prefix, str):
            raise TypeError("Prefix must be a string")
        if not isinstance(directory, str):
            raise TypeError("Directory must be a string")
        return [x for x in Path(directory).iterdir() if x.startswith(prefix) and x.endswith(suffix)]


def register_handler(args: argparse.Namespace) -> None:
    """Register a test machine configuration."""
    if args is None:
        raise ValueError("Arguments cannot be None")
    IndalekoMachineConfig.register_machine_configuration_service(
        service_name="Test Machine Configuration",
        service_description="Test Config",
        service_version="1.0.2",
        service_identifier="05567376-0f4f-4d40-97f1-3ac5f764fcf3",
    )


def list_handler(args: argparse.Namespace) -> None:
    """List all machine configurations."""
    if args is None:
        raise ValueError("Arguments cannot be None")
    machine_configs = IndalekoMachineConfig.lookup_machine_configurations()
    for machine_config in machine_configs:
        print(json.dumps(machine_config.serialize(), indent=4))  # noqa: T201


class TestMachineConfig:
    """Class for testing Machine Config."""

    test_machine_config_data = {  # noqa: RUF012
        "machine_id": "f7a439ec-c2d0-4844-a043-d8ac24d9ac0b",
        "Record": {
            "SourceIdentifier": {
                "Identifier": "8a948e74-6e43-4a6e-91c0-0cb5fd97355e",
                "Version": "1.0",
                "Description": ("This service provides the configuration information for a macOS machine."),
            },
            "Timestamp": "2024-08-09T07:52:59.839237+00:00",
            "Attributes": {
                "MachineUUID": "f7a439ec-c2d0-4844-a043-d8ac24d9ac0b",
            },
            "Data": "xx",
        },
        "Captured": {
            "Label": "eb7eaeed-6b21-4b6a-a586-dddca6a1d5a4",
            "Value": "2024-08-08T21:26:22.418196+00:00",
        },
        "Software": {
            "OS": "Linux",
            "Version": "5.4.0-104-generic",
            "Architecture": "x86_64",
            "Hostname": "testhost",
        },
        "Hardware": {
            "CPU": "Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz",
            "Version": "06_9E_09",
            "Cores": 8,
        },
    }

    def __init__(self, args: argparse.Namespace) -> None:
        """Initialize the test machine configuration class."""
        self.args = args

    @staticmethod
    def create_test_machine_config() -> None:
        """Create a test machine configuration."""
        ic("Create a test machine configuration")
        existing_machine_config = IndalekoMachineConfig.lookup_machine_configuration_by_machine_id(
            TestMachineConfig.test_machine_config_data["machine_id"],
        )
        if existing_machine_config:
            ic("Machine configuration already exists")
            ic(existing_machine_config)
            return
        machine_config = IndalekoMachineConfig(
            **TestMachineConfig.test_machine_config_data,
        )
        machine_config.write_config_to_db()
        retrieved_config = IndalekoMachineConfig.lookup_machine_configuration_by_machine_id(
            TestMachineConfig.test_machine_config_data["machine_id"],
        )
        ic(retrieved_config)

    @staticmethod
    def list_test_machine_config(machine_id: str | None = None) -> None:
        """List the test machine configuration."""
        if machine_id is not None:
            if not validate_uuid_string(machine_id):
                raise ValueError("Invalid machine identifier")
            retrieved_configs = IndalekoMachineConfig.lookup_machine_configuration_by_machine_id(
                machine_id,
            )
            ic("List the test machine configuration")
        else:
            retrieved_configs = IndalekoMachineConfig.lookup_machine_configurations()
            ic("List the test machine configurations")
        for config in retrieved_configs:
            ic(config)
            print(json.dumps(config.serialize(), indent=4))  # noqa: T201

    @staticmethod
    def delete_test_machine_config(machine_id: str | None = None) -> None:
        """Delete the test machine configuration."""
        ic("Delete the test machine configuration")
        if machine_id is not None:
            machine_id = TestMachineConfig.test_machine_config_data["machine_id"]
        if not validate_uuid_string(machine_id):
            raise ValueError("Invalid machine identifier")
        IndalekoMachineConfig.delete_config_in_db(machine_id)

    @staticmethod
    def test_handler(args: argparse.Namespace) -> None:
        """This is the test command handler."""
        ic(args)
        delete_config = args.delete
        list_config = args.list
        create = True and not delete_config and not list_config
        if list_config:
            TestMachineConfig.list_test_machine_config()
        if delete_config:
            TestMachineConfig.delete_test_machine_config()
        if create:
            TestMachineConfig.create_test_machine_config()


def test_handler(args: argparse.Namespace) -> None:
    """Test creating a machine configuration."""
    ic("Test creating a machine configuration")
    ic(args)
    test_machine_config_data = {
        "machine_id": "f7a439ec-c2d0-4844-a043-d8ac24d9ac0b",
        "Record": {
            "SourceIdentifier": {
                "Identifier": "8a948e74-6e43-4a6e-91c0-0cb5fd97355e",
                "Version": "1.0",
                "Description": ("This service provides the configuration information for a macOS machine."),
            },
            "Timestamp": "2024-08-09T07:52:59.839237+00:00",
            "Attributes": {
                "MachineUUID": "f7a439ec-c2d0-4844-a043-d8ac24d9ac0b",
            },
            "Data": "xx",
        },
        "Captured": {
            "Label": "eb7eaeed-6b21-4b6a-a586-dddca6a1d5a4",
            "Value": "2024-08-08T21:26:22.418196+00:00",
        },
        "Hardware": {
            "CPU": "Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz",
            "Version": "06_9E_09",
            "Cores": 8,
        },
        "Software": {
            "OS": "Linux",
            "Version": "5.4.0-104-generic",
            "Architecture": "x86_64",
            "Hostname": "testhost",
        },
    }
    existing_machine_config = IndalekoMachineConfig.lookup_machine_configuration_by_machine_id(
        test_machine_config_data["machine_id"],
    )
    if existing_machine_config:
        ic("Machine configuration already exists")
        ic(existing_machine_config)
        return
    machine_config = IndalekoMachineConfig(data=test_machine_config_data)
    machine_config.write_config_to_db()
    retrieved_config = IndalekoMachineConfig.lookup_machine_configuration_by_machine_id(
        test_machine_config_data["machine_id"],
    )
    ic(retrieved_config)


def main() -> None:
    """Interact with the IndalekoMachineConfig class."""
    parser = argparse.ArgumentParser(description="Indaleko Machine Configuration")
    command_subparser = parser.add_subparsers(title="commands", dest="command")
    command_register = command_subparser.add_parser(
        "register",
        help="Register a test machine configuration",
    )
    command_register.set_defaults(func=register_handler)
    command_list = command_subparser.add_parser(
        "list",
        help="List all machine configurations",
    )
    command_list.add_argument(
        "--machine_id",
        nargs=1,
        type=str,
        default=None,
        help="Machine ID to list",
    )
    command_list.set_defaults(func=list_handler)
    command_test = command_subparser.add_parser(
        "test",
        help="Test creating a machine configuration",
    )
    command_test.add_argument(
        "--delete",
        action="store_true",
        help="Delete the test machine configuration",
    )
    command_test.add_argument(
        "--list",
        action="store_true",
        help="List the test machine configuration",
    )
    command_test.add_argument(
        "--machine_id",
        nargs=1,
        type=str,
        default=None,
        help="Machine ID to list",
    )
    command_test.set_defaults(func=TestMachineConfig.test_handler)
    parser.set_defaults(func=list_handler)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
