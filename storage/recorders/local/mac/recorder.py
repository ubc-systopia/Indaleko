"""
This module handles recording metadata collected from the Mac local file system.

Indaleko Mac Local Storage Metadata Recorder

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

import datetime
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
import uuid

from typing import Union
from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from data_models import IndalekoRecordDataModel
from db import IndalekoDBConfig, IndalekoServiceManager
from platforms.mac.machine_config import IndalekoMacOSMachineConfig
from platforms.unix import UnixFileAttributes
from storage import IndalekoObject
from storage.collectors.local.mac.collector import IndalekoMacLocalStorageCollector
from storage.recorders.data_model import IndalekoStorageRecorderDataModel
from storage.recorders.local.local_base import BaseLocalStorageRecorder
from utils.misc.data_management import encode_binary_data

# pylint: enable=wrong-import-position


class IndalekoMacLocalStorageRecorder(BaseLocalStorageRecorder):
    """
    This class handles the processing of metadata from the Indaleko Mac local storage recorder service.
    """

    mac_local_recorder_uuid = "07670255-1e82-4079-ad6f-f2bb39f44f8f"
    mac_local_recorder_service = {
        "service_name": "Mac Local Storage Recorder",
        "service_description": "This service records metadata collected from local filesystems of a Mac machine.",
        "service_version": "1.0",
        "service_type": IndalekoServiceManager.service_type_storage_recorder,
        "service_identifier": mac_local_recorder_uuid,
    }

    mac_platform = IndalekoMacLocalStorageCollector.mac_platform
    mac_local_recorder = "mac_local_recorder"

    recorder_data = IndalekoStorageRecorderDataModel(
        PlatformName=mac_platform,
        ServiceName=mac_local_recorder,
        ServiceUUID=uuid.UUID(mac_local_recorder_uuid),
        ServiceVersion=mac_local_recorder_service["service_version"],
        ServiceDescription=mac_local_recorder_service["service_description"],
    )

    def __init__(
        self, reset_collection=False, objects_file="", relations_file="", **kwargs
    ) -> None:
        self.db_config = IndalekoDBConfig()
        if "input_file" not in kwargs:
            raise ValueError("input_file must be specified")
        if "machine_config" not in kwargs:
            raise ValueError("machine_config must be specified")
        self.machine_config = kwargs["machine_config"]
        if "machine_id" not in kwargs:
            kwargs["machine_id"] = self.machine_config.machine_id
        else:
            kwargs["machine_id"] = self.machine_config.machine_id
            if kwargs["machine_id"] != self.machine_config.machine_id:
                logging.warning(
                    "Warning: machine ID of collector file "
                    + f'({kwargs["machine"]}) does not match machine ID of recorder '
                    + f"({self.machine_config.machine_id}.)"
                )
        if "timestamp" not in kwargs:
            kwargs["timestamp"] = datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat()
        if "platform" not in kwargs:
            kwargs["platform"] = sys.platform
        if "recorder" not in kwargs:
            kwargs["recorder"] = IndalekoMacLocalStorageRecorder.mac_local_recorder
        if "input_file" not in kwargs:
            kwargs["input_file"] = None
        for key, value in self.mac_local_recorder_service.items():
            if key not in kwargs:
                kwargs[key] = value
        if "Identifier" not in kwargs and "service_id" not in kwargs:
            kwargs["Identifier"] = self.mac_local_recorder_uuid
        super().__init__(**kwargs)
        self.input_file = kwargs["input_file"]
        if "output_file" not in kwargs:
            self.output_file = self.generate_file_name()
            assert (
                "unknown" not in self.output_file
            ), f"Output file should not have unknown in its name {self.output_file}"
        else:
            self.output_file = kwargs["output_file"]
        self.source = {"Identifier": self.mac_local_recorder_uuid, "Version": "1.0"}
        self.docker_upload = kwargs.get("docker_upload", False)
        if not isinstance(self.docker_upload, bool):
            self.docker_upload = False
        self.reset_collection = reset_collection
        self.objects_file = objects_file
        self.relations_file = relations_file

    def find_collector_files(self) -> list:
        """This function finds the files to process:
        search_dir: path to the search directory
        prefix: prefix of the file to process
        suffix: suffix of the file to process (default is .json)
        """
        if self.data_dir is None:
            raise ValueError("data_dir must be specified")
        return [
            x
            for x in super().find_collector_files(self.data_dir)
            if IndalekoMacLocalStorageCollector.mac_platform in x
            and IndalekoMacLocalStorageCollector.mac_local_collector_name in x
        ]

    class macos_recorder_mixin(BaseLocalStorageRecorder.local_recorder_mixin):
        """MacOS Specific mixin - dealing with machine config files again"""

        @staticmethod
        def find_machine_config_files(config_dir, platform=None, machine_id=None):
            return IndalekoMacLocalStorageCollector.local_collector_mixin.find_machine_config_files(
                config_dir, platform, machine_id
            )

        @staticmethod
        def extract_filename_metadata(file_name: str) -> dict:
            """This method is used to parse the file name."""
            return IndalekoMacLocalStorageCollector.local_collector_mixin.extract_filename_metadata(
                file_name=file_name
            )

        @staticmethod
        def find_data_files(
            data_dir: Union[str, Path], keys: dict[str, str], prefix: str, suffix: str
        ) -> Union[list[str], None]:
            """This method is used to find data files"""
            # This is a hack, but the input files are labeled Darwin.  Need to track it down
            # and fix it, but for now this works.
            keys["plt"] = "Darwin"
            candidates = BaseLocalStorageRecorder.local_recorder_mixin.find_data_files(
                data_dir, keys, prefix, suffix
            )
            return candidates

    local_recorder_mixin = macos_recorder_mixin

    def normalize_collector_data(self, data: dict) -> IndalekoObject:
        """
        Given some metadata, this will create a record that can be inserted into the
        Object collection.
        """
        if data is None:
            raise ValueError("Data cannot be None")
        if not isinstance(data, dict):
            raise ValueError(f"Data must be a dictionary, not {type(data)}\n\t{data}")
        if "ObjectIdentifier" in data:
            oid = data["ObjectIdentifier"]
        else:
            oid = str(uuid.uuid4())
        kwargs = {
            "URI": data["URI"],
            "ObjectIdentifier": oid,
            "Timestamps": [
                {
                    "Label": IndalekoObject.CREATION_TIMESTAMP,
                    "Value": datetime.datetime.fromtimestamp(
                        data["st_birthtime"], datetime.timezone.utc
                    ).isoformat(),
                    "Description": "Created",
                },
                {
                    "Label": IndalekoObject.MODIFICATION_TIMESTAMP,
                    "Value": datetime.datetime.fromtimestamp(
                        data["st_mtime"], datetime.timezone.utc
                    ).isoformat(),
                    "Description": "Modified",
                },
                {
                    "Label": IndalekoObject.ACCESS_TIMESTAMP,
                    "Value": datetime.datetime.fromtimestamp(
                        data["st_atime"], datetime.timezone.utc
                    ).isoformat(),
                    "Description": "Accessed",
                },
                {
                    "Label": IndalekoObject.CHANGE_TIMESTAMP,
                    "Value": datetime.datetime.fromtimestamp(
                        data["st_ctime"], datetime.timezone.utc
                    ).isoformat(),
                    "Description": "Changed",
                },
            ],
            "Size": data["st_size"],
            "Machine": self.machine_config.machine_id,
            "SemanticAttributes": self.map_posix_storage_attributes_to_semantic_attributes(
                data
            ),
        }
        if "st_mode" in data:
            kwargs["PosixFileAttributes"] = UnixFileAttributes.map_file_attributes(
                data["st_mode"]
            )
        if "st_ino" in data:
            kwargs["LocalIdentifier"] = str(data["st_ino"])
        if "Name" in data:
            kwargs["Label"] = data["Name"]
        if "Path" in data:
            kwargs["LocalPath"] = data["Path"]
        if "timestamp" not in kwargs:
            if isinstance(self.timestamp, str):
                kwargs["timestamp"] = datetime.datetime.fromisoformat(self.timestamp)
            else:
                kwargs["timestamp"] = self.timestamp
        kwargs["Record"] = IndalekoRecordDataModel(
            SourceIdentifier=self.source,
            Timestamp=kwargs["timestamp"],
            Data=encode_binary_data(bytes(json.dumps(data).encode("utf-8"))),
        )

        return IndalekoObject(**kwargs)

    def arangoimport(self):
        print("{:-^20}".format(""))
        print("using arangoimport to import objects")

        # check if the docker is up
        self.__run_docker_cmd("docker ps")

        # read the config file
        config = self.db_config.config

        dest = "/home"  # where in the container we copy the files; we use this for import to the database
        container_name = config["database"]["container"]
        server_username = config["database"]["user_name"]
        server_password = config["database"]["user_password"]
        server_database = config["database"]["database"]
        overwrite = str(self.reset_collection).lower()

        # copy the files first
        for filename, dest_filename in [
            (self.objects_file, "objects.jsonl"),
            (self.relations_file, "relations.jsonl"),
        ]:
            self.__run_docker_cmd(
                f"docker cp {filename} {
                                  container_name}:{dest}/{dest_filename}"
            )

        # run arangoimport on both of these files
        for filename, collection_name in [
            ("objects.jsonl", "Objects"),
            ("relations.jsonl", "Relationships"),
        ]:
            self.__run_docker_cmd(
                f'docker exec -t {container_name} arangoimport --file {dest}/{filename} --type "jsonl" --collection "{collection_name}" --server.username "{
                                  server_username}" --server.password "{server_password}" --server.database "{server_database}" --overwrite {overwrite}'
            )

    def __run_docker_cmd(self, cmd):
        print("Running:", cmd)
        try:
            subprocess.run(cmd, check=True, shell=True)
        except subprocess.CalledProcessError as e:
            print(f"failed to run the command, got: {e}")


def main():
    """This is the CLI handler for the MacOS local storage recorder."""
    BaseLocalStorageRecorder.local_recorder_runner(
        IndalekoMacLocalStorageCollector,
        IndalekoMacLocalStorageRecorder,
        IndalekoMacOSMachineConfig,
    )


if __name__ == "__main__":
    main()
