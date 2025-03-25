"""
This module handles processing and recording data from the Windows local data
collector.

Indaleko Windows Local Recorder
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
import os
import uuid
import sys

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models import IndalekoRecordDataModel
from db import IndalekoServiceManager
from platforms.windows.machine_config import IndalekoWindowsMachineConfig
from platforms.posix import IndalekoPosix
from platforms.windows_attributes import IndalekoWindows
from storage.i_object import IndalekoObject
from storage.collectors.local.windows.collector import (
    IndalekoWindowsLocalStorageCollector,
)
from storage.recorders.data_model import IndalekoStorageRecorderDataModel
from storage.recorders.local.local_base import BaseLocalStorageRecorder
from utils.misc.file_name_management import find_candidate_files
from utils.misc.data_management import encode_binary_data

# pylint: enable=wrong-import-position


class IndalekoWindowsLocalStorageRecorder(BaseLocalStorageRecorder):
    """
    This class handles recording of metadata from the Indaleko Windows
    collector service.
    """

    windows_local_recorder_uuid = "429f1f3c-7a21-463f-b7aa-cd731bb202b1"
    windows_local_recorder_service = {
        "service_name": "Windows Local Recorder",
        "service_description":
        "This service records metadata collected from the local filesystems of a Windows machine.",
        "service_version": "1.0",
        "service_type": IndalekoServiceManager.service_type_storage_recorder,
        "service_identifier": windows_local_recorder_uuid,
    }

    windows_platform = IndalekoWindowsLocalStorageCollector.windows_platform
    windows_local_recorder_name = "fs_recorder"

    recorder_data = IndalekoStorageRecorderDataModel(
        PlatformName=windows_platform,
        ServiceRegistrationName=windows_local_recorder_service["service_name"],
        ServiceFileName=windows_local_recorder_name,
        ServiceName=windows_local_recorder_name,
        ServiceUUID=uuid.UUID(windows_local_recorder_uuid),
        ServiceVersion=windows_local_recorder_service["service_version"],
        ServiceDescription=windows_local_recorder_service["service_description"],
    )

    def __init__(self, **kwargs) -> None:
        assert "machine_config" in kwargs, "machine_config must be specified"
        self.machine_config = kwargs["machine_config"]
        if "machine_id" not in kwargs:
            kwargs["machine_id"] = self.machine_config.machine_id
        for key, value in self.windows_local_recorder_service.items():
            if key not in kwargs:
                kwargs[key] = value
        if "platform" not in kwargs:
            kwargs["platform"] = IndalekoWindowsLocalStorageRecorder.windows_platform
        if "recorder" not in kwargs:
            kwargs["recorder"] = (
                IndalekoWindowsLocalStorageRecorder.windows_local_recorder_name
            )
        super().__init__(**kwargs)
        self.output_file = kwargs.get("output_file", self.generate_file_name())
        self.source = {
            "Identifier": self.windows_local_recorder_uuid,
            "Version": self.windows_local_recorder_service["service_version"],
        }

    def find_collector_files(self) -> list:
        """This function finds the files to record:
        search_dir: path to the search directory
        prefix: prefix of the file to record
        suffix: suffix of the file to record (default is .json)
        """
        if self.data_dir is None:
            raise ValueError("data_dir must be specified")
        return [
            x
            for x in find_candidate_files(
                [
                    IndalekoWindowsLocalStorageCollector.windows_platform,
                    IndalekoWindowsLocalStorageCollector.windows_local_collector_name,
                ],
                self.data_dir,
            )
        ]

    def normalize_collector_data(self, data: dict) -> IndalekoObject:
        """
        Given some metadata, this will create a record that can be inserted into the
        Object collection.
        """
        if data is None:
            raise ValueError("Data cannot be None")
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        if "ObjectIdentifier" in data:
            oid = data["ObjectIdentifier"]
        else:
            oid = str(uuid.uuid4())
        timestamps = []
        if "st_birthtime" in data:
            timestamps.append(
                {
                    "Label": IndalekoObject.CREATION_TIMESTAMP,
                    "Value": datetime.datetime.fromtimestamp(
                        data["st_birthtime"], datetime.timezone.utc
                    ).isoformat(),
                    "Description": "Created",
                }
            )
        if "st_mtime" in data:
            timestamps.append(
                {
                    "Label": IndalekoObject.MODIFICATION_TIMESTAMP,
                    "Value": datetime.datetime.fromtimestamp(
                        data["st_mtime"], datetime.timezone.utc
                    ).isoformat(),
                    "Description": "Modified",
                }
            )
        if "st_atime" in data:
            timestamps.append(
                {
                    "Label": IndalekoObject.ACCESS_TIMESTAMP,
                    "Value": datetime.datetime.fromtimestamp(
                        data["st_atime"], datetime.timezone.utc
                    ).isoformat(),
                    "Description": "Accessed",
                }
            )
        if "st_ctime" in data:
            timestamps.append(
                {
                    "Label": IndalekoObject.CHANGE_TIMESTAMP,
                    "Value": datetime.datetime.fromtimestamp(
                        data["st_ctime"], datetime.timezone.utc
                    ).isoformat(),
                    "Description": "Changed",
                }
            )
        semantic_attributes = self.map_posix_storage_attributes_to_semantic_attributes(data)
        kwargs = {
            "source": self.source,
            "raw_data": encode_binary_data(bytes(json.dumps(data).encode("utf-8"))),
            "URI": data["URI"],
            "ObjectIdentifier": oid,
            "Timestamps": timestamps,
            "Size": data["st_size"],
            "Machine": self.machine_config.machine_id,
            "SemanticAttributes": semantic_attributes,
        }
        if "Volume GUID" in data:
            kwargs["Volume"] = data["Volume GUID"]
        elif data["URI"].startswith("\\\\?\\Volume{"):
            kwargs["Volume"] = data["URI"][11:47]
        if "st_mode" in data:
            kwargs["PosixFileAttributes"] = IndalekoPosix.map_file_attributes(
                data["st_mode"]
            )
        if "st_file_attributes" in data:
            kwargs["WindowsFileAttributes"] = IndalekoWindows.map_file_attributes(
                data["st_file_attributes"]
            )
        if "st_ino" in data:
            kwargs["LocalIdentifier"] = str(data["st_ino"])
        if "Name" in data:
            kwargs["Label"] = data["Name"]
        if "Path" in data:
            kwargs["LocalPath"] = data["Path"]
        else:
            ic("\n***Warning: no path in data***\n")
            # ic(data)
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


def main():
    """This is the CLI handler for the Windows local storage collector."""
    BaseLocalStorageRecorder.local_recorder_runner(
        IndalekoWindowsLocalStorageCollector,
        IndalekoWindowsLocalStorageRecorder,
        IndalekoWindowsMachineConfig,
    )


if __name__ == "__main__":
    main()
