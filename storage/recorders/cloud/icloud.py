"""
IndalekoiCloudRecorder.py

This script is used to record metadata about the files that have been scanned from iCloud.  It
will create a JSONL file with the collected metadata suitable for uploading to
the Indaleko database.

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
import os
import sys
import uuid
from datetime import datetime

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db import IndalekoServiceManager
from platforms.unix import UnixFileAttributes
from platforms.windows_attributes import IndalekoWindows
from storage.collectors.cloud.i_cloud import IndalekoICloudStorageCollector
from storage.i_object import IndalekoObject
from storage.recorders.cloud.cloud_base import BaseCloudStorageRecorder
from storage.recorders.data_model import IndalekoStorageRecorderDataModel
from utils.misc.data_management import encode_binary_data
from utils.misc.file_name_management import (
    extract_keys_from_file_name,
    find_candidate_files,
)

# pylint: enable=wrong-import-position


class IndalekoICloudStorageRecorder(BaseCloudStorageRecorder):
    """
    This class handles processing metadata from the Indaleko iCloud collector.
    """

    icloud_recorder_uuid = "c2b887b3-2a2f-4fbf-83dd-062743f31477"
    icloud_recorder_service = {
        "service_name": "iCloud Recorder",
        "service_description": "This service records metadata collected from iCloud.",
        "service_version": "1.0",
        "service_type": IndalekoServiceManager.service_type_storage_recorder,
        "service_id": icloud_recorder_uuid,
    }

    icloud_platform = IndalekoICloudStorageCollector.icloud_platform
    icloud_recorder = "recorder"
    platform = icloud_platform

    recorder_data = IndalekoStorageRecorderDataModel(
        PlatformName=icloud_platform,
        ServiceName=icloud_recorder_service["service_name"],
        ServiceUUID=uuid.UUID(icloud_recorder_uuid),
        ServiceVersion=icloud_recorder_service["service_version"],
        ServiceDescription=icloud_recorder_service["service_description"],
    )

    def __init__(self, **kwargs) -> None:
        for key, value in self.icloud_recorder_service.items():
            if key not in kwargs:
                kwargs[key] = value
        if "platform" not in kwargs:
            kwargs["platform"] = self.icloud_platform
        if "recorder" not in kwargs:
            kwargs["recorder"] = self.icloud_recorder
        if "user_id" not in kwargs:
            assert "input_file" in kwargs
            keys = extract_keys_from_file_name(kwargs["input_file"])
            assert "userid" in keys, f'userid not found in input file name: {kwargs["input_file"]}'
            self.user_id = keys["userid"]
        else:
            self.user_id = kwargs["user_id"]
        super().__init__(**kwargs)
        self.output_file = kwargs.get("output_file", self.generate_file_name())
        self.source = {
            "Identifier": self.icloud_recorder_uuid,
            "Version": self.icloud_recorder_service["service_version"],
        }
        # self.dir_data.append(self.build_dummy_root_dir_entry())

    def normalize_collector_data(self, data: dict) -> IndalekoObject:
        """
        Given some metadata, this will create a record that can be inserted into the
        Object collection.
        """
        if data is None:
            raise ValueError("Data cannot be None")
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        if "ObjectIdentifier" not in data:
            raise ValueError("Data must contain an ObjectIdentifier")
        if "user_id" not in data:
            data["user_id"] = self.user_id
        timestamps = []
        if "date_created" in data:
            timestamps.append(
                {
                    "Label": IndalekoObject.CREATION_TIMESTAMP,
                    "Value": datetime.fromisoformat(data["date_created"]).isoformat(),
                    "Description": "Date Created",
                },
            )
        if "last_opened" in data:
            if isinstance(data["last_opened"], str):
                data["last_opened"] = datetime.fromisoformat(data["last_opened"])
            timestamps.append(
                {
                    "Label": IndalekoObject.ACCESS_TIMESTAMP,
                    "Value": data["last_opened"].isoformat(),
                    "Description": "Last Opened",
                },
            )
        if "date_changed" in data:
            if isinstance(data["date_changed"], str):
                data["date_changed"] = datetime.fromisoformat(data["date_changed"])
            timestamps.append(
                {
                    "Label": IndalekoObject.ACCESS_TIMESTAMP,
                    "Value": data["date_changed"].isoformat(),
                    "Description": "Changed",
                },
            )
        if data["type"] == "folder":
            unix_file_attributes = UnixFileAttributes.FILE_ATTRIBUTES["S_IFDIR"]
            windows_file_attributes = IndalekoWindows.FILE_ATTRIBUTES["FILE_ATTRIBUTE_DIRECTORY"]
        else:
            unix_file_attributes = UnixFileAttributes.FILE_ATTRIBUTES["S_IFREG"]
            windows_file_attributes = IndalekoWindows.FILE_ATTRIBUTES["FILE_ATTRIBUTE_NORMAL"]

        # Ensure all datetime objects are converted to strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()

        # Save debug information to a file
        debug_file_path = "debug_data.jsonl"
        with open(debug_file_path, "a") as debug_file:
            debug_file.write(json.dumps(data, indent=4, default=str) + "\n")

        # As much as I dislike this, we need to stuff some values inside the Attributes field
        # TODO: fix this - we shouldn't have ANY dependency on what is inside Attributes.
        data["Path"] = data["path_display"]
        data["Name"] = data["name"]

        try:
            raw_data = encode_binary_data(bytes(json.dumps(data).encode("utf-8")))
        except TypeError as e:
            with open(debug_file_path, "a") as debug_file:
                debug_file.write("Failed to serialize the following data entry:\n")
                debug_file.write(json.dumps(data, indent=4, default=str) + "\n")
            raise e

        kwargs = {
            "source": self.source,
            "raw_data": raw_data,
            "URI": "https://www.icloud.com/" + data["path_display"],
            "Path": data["path_display"],
            "Name": data["name"],
            "ObjectIdentifier": data["ObjectIdentifier"],
            "Timestamps": timestamps,
            "Size": data.get("size", 0),
            "Attributes": data,
            "Label": data["name"],
            "PosixFileAttributes": UnixFileAttributes.map_file_attributes(
                unix_file_attributes,
            ),
            "WindowsFileAttributes": IndalekoWindows.map_file_attributes(
                windows_file_attributes,
            ),
        }
        return IndalekoObject(**kwargs)

    def find_collector_files(self) -> list:
        """This function finds the files produced by the collector."""
        if self.data_dir is None:
            raise ValueError("data_dir must be specified")
        candidates = find_candidate_files(
            [
                IndalekoICloudStorageCollector.icloud_platform,
                IndalekoICloudStorageCollector.icloud_collector_name,
            ],
            self.data_dir,
        )
        if self.debug:
            ic(candidates)
        return candidates

    class icloud_recorder_mixin(BaseCloudStorageRecorder.cloud_recorder_mixin):
        """This class is a mixin for the IndalekoICloudStorageRecorder class."""

        @staticmethod
        def get_platform_name() -> str:
            """This method is used to get the platform name"""
            return IndalekoICloudStorageRecorder.icloud_platform

    cloud_recorder_mixin = icloud_recorder_mixin


def main():
    """This is the main handler for the iCloud recorder."""
    BaseCloudStorageRecorder.cloud_recorder_runner(
        IndalekoICloudStorageCollector,
        IndalekoICloudStorageRecorder,
    )


if __name__ == "__main__":
    main()
