"""
This class is used to manage the configuration information for a Windows
machine.

Indaleko Windows Machine Configuration
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
import json
import os
import platform
import subprocess
import sys
import uuid

import arango

from typing import Union
from icecream import ic

init_path = os.path.dirname(os.path.abspath(__file__))

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from constants import IndalekoConstants  # noqa: E402
from data_models import (
    IndalekoRecordDataModel,
    IndalekoSourceIdentifierDataModel,
    IndalekoTimestampDataModel,
)  # noqa: E402
from platforms.data_models.machine_platform import MachinePlatform  # noqa: E402
from platforms.machine_config import IndalekoMachineConfig  # noqa: E402
from platforms.data_models.hardware import Hardware  # noqa: E402
from platforms.data_models.software import Software  # noqa: E402
from utils.misc.data_management import encode_binary_data  # noqa: E402
from utils.data_validation import validate_uuid_string  # noqa: E402
from utils.misc.file_name_management import extract_keys_from_file_name  # noqa: E402

# pylint: enable=wrong-import-position


class IndalekoWindowsMachineConfig(IndalekoMachineConfig):
    """
    The IndalekoWindowsMachineConfig class is used to capture information about
    a Windows machine.  It is a specialization of the IndalekoMachineConfig
    class, which is shared across all platforms.
    """

    windows_machine_config_file_prefix = "windows_hardware_info"
    windows_machine_config_uuid_str = "3360a328-a6e9-41d7-8168-45518f85d73e"
    windows_machine_config_service_name = "Windows Machine Configuration"
    windows_machine_config_service_description = (
        "This service provides the configuration information for a Windows machine."
    )
    windows_machine_config_service_version = "1.0"

    windows_machine_config_service = {
        "service_name": windows_machine_config_service_name,
        "service_description": windows_machine_config_service_description,
        "service_version": windows_machine_config_service_version,
        "service_type": "Machine Configuration",
        "service_identifier": windows_machine_config_uuid_str,
    }

    def __init__(self: "IndalekoWindowsMachineConfig", **kwargs):
        self.debug = kwargs.get("debug", False)
        if self.debug:
            ic(kwargs)
        self.service_registration = (
            IndalekoMachineConfig.register_machine_configuration_service(
                **IndalekoWindowsMachineConfig.windows_machine_config_service
            )
        )
        self.db = kwargs.get("db", None)
        if "machine_id" not in kwargs:
            kwargs["machine_id"] = kwargs["MachineUUID"]
        super().__init__(**kwargs)
        self.volume_data = {}

    @staticmethod
    def find_config_files(
        directory: str, prefix: str = None, suffix: str = ".json"
    ) -> list:
        """This looks for configuration files in the given directory."""
        if prefix is None:
            prefix = IndalekoWindowsMachineConfig.windows_machine_config_file_prefix
        return IndalekoMachineConfig.find_config_files(directory, prefix, suffix=suffix)

    @staticmethod
    def find_configs_in_db(source_id: Union[str, None]) -> list:
        """Find the machine configurations in the database for Windows."""
        if source_id is None:
            source_id = IndalekoWindowsMachineConfig.windows_machine_config_uuid_str
        return IndalekoMachineConfig.find_configs_in_db(source_id)

    @staticmethod
    def load_config_from_file(
        config_dir: str = None,
        config_file: str = None,
        offline: bool = False,
        debug: bool = False,
    ) -> "IndalekoWindowsMachineConfig":
        """Given the directory and name of a configuration file, load the configuration."""
        config_data = {}
        if config_dir is None and config_file is None:
            # nothing specified, so we'll search and find
            config_dir = IndalekoWindowsMachineConfig.default_config_dir
        if config_file is None:
            # now we have a config_dir, so we'll find the most recent file
            assert config_dir is not None, "config_dir must be specified"
            config_file = IndalekoWindowsMachineConfig.get_most_recent_config_file(
                config_dir
            )
        if config_file is not None:
            keys = extract_keys_from_file_name(config_file)
            timestamp = keys["timestamp"]
            guid = keys["machine"]
            assert os.path.exists(
                config_file
            ), f"Config file {config_file} does not exist"
            assert os.path.isfile(
                config_file
            ), f"Config file {config_file} is not a file"
            with open(config_file, "rt", encoding="utf-8-sig") as fd:
                config_data = json.load(fd)
            if "MachineUUID" not in config_data:
                config_data["MachineUUID"] = config_data["MachineGuid"]
            assert (
                str(guid) == config_data["MachineUUID"]
            ), f'GUID mismatch: {guid} != {config_data["MachineUUID"]}'
        software = Software(
            OS=config_data["OperatingSystem"]["Caption"],
            Version=config_data["OperatingSystem"]["Version"],
            Architecture=config_data["OperatingSystem"]["OSArchitecture"],
            Hostname=config_data["Hostname"],
        )
        hardware = Hardware(
            CPU=config_data["CPU"]["Name"],
            Version="",
            Cores=config_data["CPU"]["Cores"],
        )
        record = IndalekoRecordDataModel(
            SourceIdentifier=IndalekoSourceIdentifierDataModel(
                Identifier=IndalekoWindowsMachineConfig.windows_machine_config_service[
                    "service_identifier"
                ],
                Version=IndalekoWindowsMachineConfig.windows_machine_config_service[
                    "service_version"
                ],
                Description=IndalekoWindowsMachineConfig.windows_machine_config_service[
                    "service_description"
                ],
            ),
            Timestamp=timestamp,
            Data=encode_binary_data(config_data),
            Attributes=config_data,
        )
        captured = IndalekoTimestampDataModel(
            Label=IndalekoMachineConfig.indaleko_machine_config_captured_label_uuid,
            Value=timestamp,
        )
        machine_config_data = {
            "Hardware": hardware.serialize(),
            "Software": software.serialize(),
            "Record": record.serialize(),
            "Captured": captured.serialize(),
        }
        if "MachineUUID" not in machine_config_data:
            machine_config_data["MachineUUID"] = config_data["MachineGuid"]
        if "Hostname" not in machine_config_data:
            machine_config_data["Hostname"] = config_data["Hostname"]
        config = IndalekoWindowsMachineConfig(**machine_config_data)
        if debug:
            ic(MachinePlatform.serialize(config.machine_config))
        if not offline:
            config.write_config_to_db()
        if hasattr(config, "extract_volume_info"):
            getattr(config, "extract_volume_info")()
        return config

    @staticmethod
    def get_most_recent_config_file(config_dir):
        """
        Given a configuration directory and a prefix, find the most recent
        configuration file.
        """
        files = IndalekoWindowsMachineConfig.find_config_files(config_dir)
        if len(files) == 0:
            return None
        candidate_files = []
        for file in files:
            keys = extract_keys_from_file_name(file)
            candidate_files.append((keys["timestamp"], file))
        # ic (extract_keys_from_file_name(files[0]))
        candidate_files.sort(key=lambda x: x[0])
        candidate = candidate_files[0][1]
        if config_dir is not None:
            candidate = os.path.join(config_dir, candidate)
        return candidate

    class WindowsDriveInfo:
        """This class is used to capture information about a Windows drive."""

        WindowsDriveInfo_UUID_str = "a0b3b3e0-0b1a-4e1f-8b1a-4e1f8b1a4e1f"
        WindowsDriveInfo_UUID = uuid.UUID(WindowsDriveInfo_UUID_str)
        WindowsDriveInfo_Version = "1.0"
        WindowsDriveInfo_Description = "Windows Drive Info"

        def __init__(
            self,
            machine_id: str,
            software: Software,
            hardware: Hardware,
            drive_data: dict,
            captured: dict,
            machine_config: IndalekoMachineConfig = None,
            offline: bool = False,
            debug: bool = False,
        ) -> None:
            assert "GUID" not in drive_data, "GUID should not be in drive_data"
            assert "UniqueId" in drive_data, "UniqueId must be in drive_data"
            assert validate_uuid_string(machine_id), "machine_id must be a valid UUID"
            self.machine_id = machine_id
            self.attributes = drive_data.copy()
            self.volume_guid = str(uuid.uuid4())
            if self.attributes["UniqueId"].startswith("\\\\?\\Volume{"):
                self.volume_guid = self.__find_volume_guid__(drive_data["UniqueId"])
            self.attributes["GUID"] = self.volume_guid
            if debug:
                ic(self.attributes)
            timestamp = captured["Value"]
            if isinstance(timestamp, str):
                timestamp = datetime.datetime.fromisoformat(timestamp)
            if machine_config is not None:
                self.machine_config = machine_config
            else:
                self.machine_config = IndalekoWindowsMachineConfig(
                    machine_id=machine_id,
                    Hardware=hardware,
                    Software=software,
                    Captured=captured,
                    Record=IndalekoRecordDataModel(
                        SourceIdentifier=IndalekoSourceIdentifierDataModel(
                            Identifier=self.WindowsDriveInfo_UUID_str,
                            Version=self.WindowsDriveInfo_Version,
                            Description=self.WindowsDriveInfo_Description,
                        ),
                        Timestamp=timestamp,
                        Data=encode_binary_data(drive_data),
                        Attributes=drive_data,
                    ),
                    debug=debug,
                    offline=offline,
                )
                return

        @staticmethod
        def __find_volume_guid__(vol_name: str) -> str:
            assert vol_name is not None, "Volume name cannot be None"
            assert isinstance(vol_name, str), "Volume name must be a string"
            assert vol_name.startswith("\\\\?\\Volume{")
            return vol_name[11:-2]

        def get_vol_guid(self):
            """Return the GUID of the volume."""
            return self.volume_guid

        def serialize(self) -> dict:
            """Serialize the WindowsDriveInfo object."""
            assert isinstance(
                self.machine_config, IndalekoMachineConfig
            ), f"machine_config must be an IndalekoMachineConfig, not {type(self.machine_config)}"
            config_data = self.machine_config.serialize()
            if hasattr(self, "machine_id"):
                config_data["MachineUUID"] = self.machine_id
            config_data["_key"] = self.get_vol_guid()
            return config_data

        def to_dict(self):
            """Return the WindowsDriveInfo object as a dictionary."""
            return self.serialize()

        def __getitem__(self, key):
            """Return the item from the dictionary."""
            return self.attributes[key]

    def extract_volume_info(
        self: "IndalekoWindowsMachineConfig", debug: bool = False
    ) -> None:
        """Extract the volume information from the machine configuration."""
        if debug:
            ic("Extracting volume information")
        config_data = self.serialize()
        volume_info = config_data["Record"]["Attributes"]["VolumeInfo"]
        machine_id = config_data["Record"]["Attributes"]["MachineUUID"]
        software = config_data["Software"]
        hardware = config_data["Hardware"]
        captured = config_data["Captured"]
        if debug:
            ic(volume_info)
        for volume in volume_info:
            wdi = self.WindowsDriveInfo(
                machine_id, software, hardware, volume, captured, self, debug=debug
            )
            if debug:
                ic(volume)
            assert (
                wdi.get_vol_guid() not in self.volume_data
            ), f"Volume GUID {wdi.get_vol_guid()} already in volume_data"
            self.volume_data[wdi.get_vol_guid()] = wdi
        return

    def get_volume_info(self: "IndalekoWindowsMachineConfig") -> dict:
        """This returns the volume information."""
        return self.volume_data

    def map_drive_letter_to_volume_guid(
        self: "IndalekoWindowsMachineConfig", drive_letter: str
    ) -> str:
        """Map a drive letter to a volume GUID."""
        assert drive_letter is not None, "drive_letter must be a valid string"
        assert len(drive_letter) == 1, "drive_letter must be a single character"
        drive_letter = drive_letter.upper()
        for vol in self.get_volume_info().values():
            if vol["DriveLetter"] == drive_letter:
                return vol["GUID"]
        return None

    def write_volume_info_to_db(
        self: "IndalekoWindowsMachineConfig", volume_data: WindowsDriveInfo
    ) -> bool:
        """Write the volume information to the database."""
        assert isinstance(
            volume_data, self.WindowsDriveInfo
        ), "volume_data must be a WindowsDriveInfo"
        success = False
        try:
            self.collection.insert(volume_data.serialize(), overwrite=True)
            success = True
        except arango.exceptions.DocumentInsertError as error:
            print(f"Error inserting volume data: {error}")
            print(volume_data.serialize())
        return success

    def write_config_to_db(self, overwrite: bool = True) -> None:
        """Write the machine configuration to the database."""
        super().write_config_to_db(overwrite=overwrite)
        for _, vol_data in self.volume_data.items():
            if not self.write_volume_info_to_db(vol_data):
                print("DB write failed, aborting")
                break


def get_execution_policy():
    try:
        result = subprocess.run(
            ["powershell.exe", "-Command", "Get-ExecutionPolicy"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error checking ExecutionPolicy: {e}")
        return None


def ensure_execution_policy():
    policy = get_execution_policy()
    if policy in {"Restricted", "AllSigned"}:
        print(
            f"Current ExecutionPolicy is '{policy}', which might block script execution."
        )
        print("You can change it temporarily by running:")
        print("  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass")
        print("or use an administrator to set a less restrictive policy permanently.")
        return False
    return True


def collect_machine_configuration(
    output_dir: str = IndalekoConstants.default_config_dir,
    script_name: str = "windows-hardware-info.ps1",
) -> bool:
    """This executes the external powershell script to capture the machine configuration."""
    if not ensure_execution_policy():
        return False
    script_path = os.path.abspath(script_name)
    output_dir = os.path.abspath(output_dir)
    powershell_command = (
        f"$process = Start-Process -FilePath 'powershell.exe' "
        f"-ArgumentList @('-ExecutionPolicy', 'Bypass', '-File', '{script_path}', '-outputDir', '{output_dir}') "
        f"-Verb RunAs -PassThru; "
        f"if ($process) {{ $process.WaitForExit() }} else {{ Write-Error 'Failed to start process'; exit 1 }}"
    )
    command = [
        "powershell.exe",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        powershell_command,
    ]
    success = False
    try:
        result = subprocess.run(command, shell=True, text=True)
        if result.returncode == 0:
            success = True
        else:
            ic(f"Command failed with return code {result.returncode}")
            ic(result)
    except Exception as e:
        ic(f"An error occurred: {e}")
    return success


def main():
    """This is the main handler for the Indaleko Windows Machine Config
    service."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", action="version", version="%(prog)s 1.0")
    parser.add_argument(
        "--delete",
        "-d",
        action="store_true",
        help="Delete the machine configuration if it exists in the database.",
    )
    parser.add_argument(
        "--uuid", "-u", type=str, default=None, help="The UUID of the machine."
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List the machine configurations in the database.",
    )
    parser.add_argument(
        "--files",
        "-f",
        action="store_true",
        help="List the machine configuration files in the default directory.",
    )
    parser.add_argument(
        "--add",
        "-a",
        action="store_true",
        help="Add a machine configuration (from the file) to the database.",
    )
    if platform.system() == "Windows":
        # can only capture windows machine state on a Windows machine
        parser.add_argument(
            "--capture",
            "-c",
            action="store_true",
            help="Capture the current machine configuration.",
        )
    args = parser.parse_args()
    if args.capture:
        if not ensure_execution_policy():
            return
        existing_config_files = set(
            IndalekoWindowsMachineConfig.find_config_files(
                IndalekoWindowsMachineConfig.default_config_dir
            )
        )
        print("Starting data collection.  Note that:")
        print(
            "\t(1) this script will run as administrator so you will be asked for permission;"
        )
        print("\t(2) this takes 30-60 seconds, so be patient;")
        print(
            "\t(3) the file is not added to the database automatically. Use --add to do that."
        )
        if collect_machine_configuration():
            new_config_files = set(
                IndalekoWindowsMachineConfig.find_config_files(
                    IndalekoWindowsMachineConfig.default_config_dir
                )
            )
            added_files = list[new_config_files - existing_config_files]
            if added_files:
                ic(f"Added new file(s): {added_files}")
            else:
                ic("No new files added (not sure why)")
                ic(existing_config_files)
                ic(new_config_files)
        else:
            print(
                "Error collecting machine configuration (recommendation: run script as administrator directly.)"
            )
        print("data collection complete.")
        return
    if args.list:
        print("Listing machine configurations in the database.")
        configs = IndalekoWindowsMachineConfig.find_configs_in_db(None)
        for config in configs:
            hostname = "unknown"
            if "hostname" in config:
                hostname = config["hostname"]
            # print(json.dumps(config, indent=4))
            print("Configuration for machine:", hostname)
            if "_key" in config:
                print(f'\t    UUID: {config["_key"]}')
            else:
                print(f"\t    UUID: {config['Record']['Attributes']['MachineUUID']}")
            print(f'\tCaptured: {config["Captured"]["Value"]}')
            print(f'\tPlatform: {config["Software"]["OS"]}')
            return
    if args.delete:
        assert (
            args.uuid is not None
        ), "UUID must be specified when deleting a machine configuration."
        assert validate_uuid_string(args.uuid), f"UUID {args.uuid} is not a valid UUID."
        print(f"Deleting machine configuration with UUID {args.uuid}")
        IndalekoWindowsMachineConfig.delete_config_in_db(args.uuid)
        return
    if args.files:
        print("Listing machine configuration files in the default directory.")
        files = IndalekoWindowsMachineConfig.find_config_files(
            IndalekoWindowsMachineConfig.default_config_dir
        )
        for file in files:
            print(file)
        return
    if args.add:
        print("Adding machine configuration to the database.")
        config = IndalekoWindowsMachineConfig.load_config_from_file()
        config.write_config_to_db()

        return


if __name__ == "__main__":
    main()
