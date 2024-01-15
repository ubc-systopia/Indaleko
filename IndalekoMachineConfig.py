'''
Indaleko Machine Configuration class.
'''
import argparse
import datetime
import json
import uuid
import socket

from IndalekoCollections import IndalekoCollections
from IndalekoDBConfig import IndalekoDBConfig
from IndalekoRecord import IndalekoRecord
from IndalekoMachineConfigSchema import IndalekoMachineConfigSchema
from Indaleko import Indaleko
from IndalekoServices import IndalekoService


class IndalekoMachineConfig(IndalekoRecord):
    """
    This is the generic class for machine config.  It should be used to create
    platform specific machine configuration classes.
    """

    indaleko_machine_config_uuid_str = "e65e412e-7862-4d81-affd-2bbd4f6b9a01"
    indaleko_machine_config_version_str = "1.0"
    indaleko_machine_config_captured_label_str = "eb7eaeed-6b21-4b6a-a586-dddca6a1d5a4"

    default_config_dir = "./config"

    Schema = IndalekoMachineConfigSchema.get_schema()

    def __init__(
        self: "IndalekoMachineConfig",
        timestamp: datetime = None,
        db: IndalekoDBConfig = None,
        **kwargs
    ):
        """
        Constructor for the IndalekoMachineConfig class. Takes a
        set of configuration data as a parameter and initializes the object.
        """
        self.machine_id = None
        if timestamp is None:
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        super().__init__(
            b"",
            {},
            {
                "Identifier": IndalekoMachineConfig.indaleko_machine_config_uuid_str,
                "Version": IndalekoMachineConfig.indaleko_machine_config_version_str,
            },
        )
        self.platform = {}
        self.captured = {
            "Label": "Timestamp",
            "Value": timestamp,
        }
        collections = IndalekoCollections(db_config=db)
        self.collection = collections.get_collection(Indaleko.Indaleko_MachineConfig)
        assert self.collection is not None, "MachineConfig collection does not exist."
        service_name = "Indaleko Machine Config Service"
        if "service_name" in kwargs:
            service_name = kwargs["service_name"]
        service_identifier = self.indaleko_machine_config_uuid_str
        if "service_identifier" in kwargs:
            service_identifier = kwargs["service_identifier"]
        service_description = None
        if "service_description" in kwargs:
            service_description = kwargs["service_description"]
        service_version = self.indaleko_machine_config_version_str
        if "service_version" in kwargs:
            service_version = kwargs["service_version"]
        service_type = "Machine Configuration"
        if "service_type" in kwargs:
            service_type = kwargs["service_type"]
        self.machine_config_service = IndalekoService(service_name=service_name,
                              service_identifier=service_identifier,
                              service_description=service_description,
                              service_version=service_version,
                              service_type=service_type)
        assert self.machine_config_service is not None, "MachineConfig service does not exist."



    def set_platform(self, platform: dict) -> None:
        """
        This method sets the platform information for the machine.
        """
        assert isinstance(
            platform, dict
        ), f"platform must be a dict (not {type(platform)})"
        assert "software" in platform, "platform must contain a software field"
        assert isinstance(
            platform["software"], dict
        ), f'platform["software"] must be a dictionary, not {type(platform["software"])}'
        assert isinstance(
            platform["software"]["OS"], str
        ), f'platform must contain a string OS field, not {type(platform["software"]["OS"])}'
        assert isinstance(
            platform["software"]["Version"], str
        ), "platform must contain a string version field"
        assert isinstance(
            platform["software"]["Architecture"], str
        ), "platform must contain a string architecture field"
        assert "hardware" in platform, "platform must contain a hardware field"
        assert isinstance(
            platform["hardware"], dict
        ), 'platform["hardware"] must be a dictionary'
        assert isinstance(
            platform["hardware"]["CPU"], str
        ), "platform must contain a string CPU field"
        assert isinstance(
            platform["hardware"]["Version"], str
        ), "platform must contain a string version field"
        assert isinstance(
            platform["hardware"]["Cores"], int
        ), "platform must contain an integer cores field"
        self.platform = platform
        return self

    def get_platform(self) -> dict:
        """
        This method returns the platform information for the machine.
        """
        if hasattr(self, "Platform"):
            return self.platform
        return None

    def set_captured(self, timestamp: datetime) -> None:
        """
        This method sets the timestamp for the machine configuration.
        """
        if isinstance(timestamp, dict):
            assert "Label" in timestamp, "timestamp must contain a Label field"
            assert (
                timestamp["Label"] == "Timestamp"
            ), "timestamp must have a Label of Timestamp"
            assert "Value" in timestamp, "timestamp must contain a Value field"
            assert isinstance(
                timestamp["Value"], str
            ), "timestamp must contain a string Value field"
            assert self.validate_iso_timestamp(
                timestamp["Value"]
            ), f'timestamp {timestamp["Value"]} is not a valid ISO timestamp'
            self.captured = {
                "Label": "Timestamp",
                "Value": timestamp["Value"],
            }
        elif isinstance(timestamp, datetime.datetime):
            timestamp = timestamp.isoformat()
        else:
            assert isinstance(
                timestamp, str
            ), f"timestamp must be a string or timestamp (not {type(timestamp)})"
        self.captured = {
            "Label": IndalekoMachineConfig.indaleko_machine_config_captured_label_str,
            "Value": timestamp,
            "Description" : "Timestamp when this machine configuration was captured.",
        }
        return self

    def get_captured(self) -> datetime.datetime:
        """
        This method returns the timestamp for the machine configuration.
        """
        if hasattr(self, "captured"):
            return self.captured
        return None

    def parse_config_file(self) -> None:
        """
        This method parses the configuration data from the config file.
        """
        raise AssertionError("This method should be overridden by the derived classes.")

    def set_machine_id(self, machine_id) -> None:
        """
        This method sets the machine ID for the machine configuration.
        """
        if isinstance(machine_id, str):
            assert self.validate_uuid_string(
                machine_id
            ), f"machine_id {machine_id} is not a valid UUID."
        elif isinstance(machine_id, uuid.UUID):
            machine_id = str(machine_id)
        self.machine_id = machine_id
        return self

    def get_machine_id(self) -> str:
        """
        This method returns the machine ID for the machine configuration.
        """
        if hasattr(self, "machine_id"):
            return self.machine_id
        return None

    def write_config_to_db(self) -> None:
        """
        This method writes the configuration to the database.
        """
        assert hasattr(
            self, "machine_id"
        ), "machine_id must be set before writing to the database."
        assert self.validate_uuid_string(
            self.machine_id
        ), f"machine_id {self.machine_id} is not a valid UUID."
        if not IndalekoMachineConfigSchema.is_valid_record(self.to_dict()):
            print("Invalid record:")
            print(json.dumps(self.to_dict(), indent=4))
            raise AssertionError("Invalid record.")
        self.collection.insert(self.to_json(), overwrite=True)

    @staticmethod
    def load_config_from_file() -> dict:
        """
        This method creates a new IndalekoMachineConfig object from an
        existing config file.  This must be overridden by the platform specific
        machine configuration implementation.
        """
        raise AssertionError("This method should be overridden by the derived classes.")

    @staticmethod
    def find_configs_in_db(source_id : str) -> list:
        """
        This method finds all the machine configs in the database.
        """
        if not IndalekoMachineConfig.validate_uuid_string(source_id):
            raise AssertionError(f"source_id {source_id} is not a valid UUID.")
        collections = IndalekoCollections()
        machine_config_collection = collections.get_collection(Indaleko.Indaleko_MachineConfig)
        entries = machine_config_collection.find_entries(source=source_id)
        return entries

    @staticmethod
    def delete_config_in_db(machine_id: str) -> None:
        """
        This method deletes the specified machine config from the database.
        """
        assert IndalekoMachineConfig.validate_uuid_string(
            machine_id
        ), f"machine_id {machine_id} is not a valid UUID."
        IndalekoCollections().get_collection(Indaleko.Indaleko_MachineConfig).delete(machine_id)

    @staticmethod
    def load_config_from_db(machine_id: str) -> "IndalekoMachineConfig":
        """
        This method loads the configuration from the database.
        """
        assert IndalekoMachineConfig.validate_uuid_string(
            machine_id
        ), f"machine_id {machine_id} is not a valid UUID."
        entries = IndalekoCollections().get_collection(Indaleko.Indaleko_MachineConfig).find_entries(_key=machine_id)
        if len(entries) == 0:
            return None  # not found
        assert (
            len(entries) == 1
        ), f"Found {len(entries)} entries for machine_id {machine_id} - multiple entries case not handled."
        entry = entries[0]
        machine_config = IndalekoMachineConfig()
        machine_config.set_platform(entry["Platform"])
        # temporary: I've changed the shape of the database, so I'll need to
        # work around it temporarily
        if isinstance(entry["Source"], str) and "Version" in entry:
            machine_config.set_source(
                {
                    "Identifier": entry["Source"],
                    "Version": entry["Version"],
                }
            )
        else:
            assert isinstance(
                entry["Source"], dict
            ), f'entry[Source"] must be a dict, not {type(entry["Source"])}'
            machine_config.set_source(entry["Source"])
        machine_config.set_captured(entry["Captured"])
        machine_config.set_base64_data(entry["Data"])
        machine_config.set_attributes(entry["Attributes"])
        machine_config.set_machine_id(machine_id)
        return machine_config

    @staticmethod
    def get_machine_name() -> str:
        """This retrieves a user friendly machine name."""
        return socket.gethostname()

    def to_dict(self) -> dict:
        """
        This method returns the dictionary representation of the machine config.
        """
        record = {}
        record['Record'] = super().to_dict()
        record["Platform"] = self.platform
        assert self.captured is not None, "Captured timestamp must be set."
        record["Captured"] = self.captured
        if hasattr(self, "machine_id"):
            record["_key"] = self.machine_id
        record["hostname"] = IndalekoMachineConfig.get_machine_name()
        return record

    def to_json(self, indent: int = 4) -> str:
        """
        This method returns the JSON representation of the machine config.
        """
        return json.dumps(self.to_dict(), indent=indent)

    @staticmethod
    def build_config(**kwargs) -> "IndalekoMachineConfig":
        """This method builds a machine config from the specified parameters."""
        assert "os" in kwargs, "OS must be specified"
        assert isinstance(kwargs["os"], str), "OS must be a string"
        assert "arch" in kwargs, "Architecture must be specified"
        assert isinstance(kwargs["arch"], str), "Architecture must be a string"
        assert "os_version" in kwargs, "OS version must be specified"
        assert isinstance(kwargs["os_version"], str), "OS version must be a string"
        assert "cpu" in kwargs, "CPU must be specified"
        assert isinstance(kwargs["cpu"], str), "CPU must be a string"
        assert "cpu_version" in kwargs, "CPU version must be specified"
        assert isinstance(kwargs["cpu_version"], str), "CPU version must be a string"
        assert "cpu_cores" in kwargs, "CPU cores must be specified"
        assert isinstance(kwargs["cpu_cores"], int), "CPU cores must be an integer"
        assert "source_id" in kwargs, "source must be specified"
        assert isinstance(kwargs["source_id"], str), "source must be a dict"
        assert "source_version" in kwargs, "source version must be specified"
        assert isinstance(
            kwargs["source_version"], str
        ), "source version must be a string"
        assert "attributes" in kwargs, "Attributes must be specified"
        assert "data" in kwargs, "Data must be specified"
        assert "machine_id" in kwargs, "Machine ID must be specified"
        if "timestamp" in kwargs:
            assert IndalekoMachineConfig.validate_iso_timestamp(
                kwargs["timestamp"]
            ), f'Timestamp {kwargs["timestamp"]} is not a valid ISO timestamp'
            timestamp = kwargs["timestamp"]
        else:
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if "machine_config" not in kwargs:
            machine_config = IndalekoMachineConfig()
        else:
            machine_config = kwargs["machine_config"]
        machine_config.set_platform(
            {
                "software": {
                    "OS": kwargs["os"],
                    "Architecture": kwargs["arch"],
                    "Version": kwargs["os_version"],
                },
                "hardware": {
                    "CPU": kwargs["cpu"],
                    "Version": kwargs["cpu_version"],
                    "Cores": kwargs["cpu_cores"],
                },
            }
        )
        machine_config.set_captured(timestamp)
        machine_config.set_source(
            {
                "Identifier": kwargs["source_id"],
                "Version": kwargs["source_version"],
            }
        )
        machine_config.set_attributes(kwargs["attributes"])
        machine_config.set_base64_data(kwargs["data"])
        machine_config.set_machine_id(kwargs["machine_id"])
        return machine_config


def main():
    """This is test code for the IndalekoMachineConfig class."""
    starttime = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    parser = argparse.ArgumentParser()
    logfile = f"indalekomachineconfig-test-{starttime}.log"
    parser = argparse.ArgumentParser(
        description="Test base class for MachineConfig for the Indaleko database."
    )
    parser.add_argument(
        "--machine_id",
        "-m",
        help="Machine ID to load from database",
        default="2e169bb7-0024-4dc1-93dc-18b7d2d28190",
    )
    parser.add_argument("--log", "-l", help="Log file to use", default=logfile)
    parser.add_argument("--logdir", help="Log directory to use", default="./logs")
    args = parser.parse_args()
    if args.machine_id is not None:
        assert IndalekoMachineConfig.validate_uuid_string(
            args.machine_id
        ), f"machine_id {args.machine_id} is not a valid UUID."
        # look it up in the database
        machine_config = IndalekoMachineConfig.load_config_from_db(args.machine_id)
        if machine_config is None:
            print(f"Machine config {args.machine_id} not found in database.")
            return
        print(json.dumps(machine_config.to_dict(), indent=4))


if __name__ == "__main__":
    main()
