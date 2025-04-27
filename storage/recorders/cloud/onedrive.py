"""
This module handles data ingestion into Indaleko from the One Drive data
collector.

Indaleko OneDrive Data Recorder
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
import re
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
from data_models import IndalekoRecordDataModel
from db import IndalekoServiceManager
from platforms.unix import UnixFileAttributes
from platforms.windows_attributes import IndalekoWindows
from storage.collectors.cloud.one_drive import IndalekoOneDriveCloudStorageCollector
from storage.i_object import IndalekoObject
from storage.recorders.cloud.cloud_base import BaseCloudStorageRecorder
from storage.recorders.data_model import IndalekoStorageRecorderDataModel
from utils.misc.data_management import encode_binary_data
from utils.misc.file_name_management import (
    extract_keys_from_file_name,
    find_candidate_files,
)


# pylint: enable=wrong-import-position


class IndalekoOneDriveCloudStorageRecorder(BaseCloudStorageRecorder):
    """
    This class provides the OneDrive Ingester for Indaleko.
    """

    onedrive_recorder_uuid = "c15afa0f-5e5a-4a5b-82ab-8adb0311dfaf"
    onedrive_recorder_service = {
        "service_name": "Microsoft OneDrive Collector",
        "service_description": "This service ingests metadata from OneDrive into Indaleko.",
        "service_version": "1.0.0",
        "service_type": IndalekoServiceManager.service_type_storage_recorder,
        "service_identifier": onedrive_recorder_uuid,
    }

    onedrive_platform = IndalekoOneDriveCloudStorageCollector.onedrive_platform
    onedrive_recorder = "recorder"

    recorder_data = IndalekoStorageRecorderDataModel(
        PlatformName=onedrive_platform,
        ServiceRegistrationName=onedrive_recorder_service["service_name"],
        ServiceFileName=onedrive_recorder,
        ServiceUUID=uuid.UUID(onedrive_recorder_uuid),
        ServiceVersion=onedrive_recorder_service["service_version"],
        ServiceDescription=onedrive_recorder_service["service_description"],
    )

    def __init__(self, **kwargs: dict) -> None:
        """Initialize the OneDrive Drive Ingester"""
        for key, value in self.onedrive_recorder_service.items():
            if key not in kwargs:
                kwargs[key] = value
        if "platform" not in kwargs:
            kwargs["platform"] = self.onedrive_platform
        if "recorder" not in kwargs:
            kwargs["recorder"] = self.onedrive_recorder
        if "user_id_ not in kwargs":
            assert "input_file" in kwargs
            keys = extract_keys_from_file_name(kwargs["input_file"])
            assert "userid" in keys, f'userid not found in input file name: {kwargs["input_file"]}'
            self.user_id = keys["userid"]
        else:
            self.user_id = kwargs["user_id"]
        super().__init__(**kwargs)
        self.output_file = kwargs.get("output_file", self.generate_file_name())
        self.source = {
            "Identifier": self.onedrive_recorder_uuid,
            "Version": self.onedrive_recorder_service["service_version"],
        }
        # self.dir_data.append(self.build_dummy_root_dir_entry())

    def find_collector_files(self) -> list:
        """This function finds the files produced by the collector."""
        if self.data_dir is None:
            raise ValueError("data_dir must be specified")
        candidates = find_candidate_files(
            [
                IndalekoOneDriveCloudStorageCollector.onedrive_platform,
                IndalekoOneDriveCloudStorageCollector.onedrive_collector_name,
            ],
            self.data_dir,
        )
        if self.debug:
            ic(candidates)
        return candidates

    @staticmethod
    def extract_uuid_from_etag(etag: str) -> uuid.UUID:
        """Extract the UUID from the eTag"""
        if etag is None:
            raise ValueError("etag is required")
        if not isinstance(etag, str):
            raise ValueError("etag must be a string")
        match = re.search(r"\{([a-f0-9-]+)\}", etag, re.IGNORECASE)
        if match is None:
            return None
        return uuid.UUID(match.group(1))

    def normalize_collector_data(self, data: dict) -> dict:
        """
        Given some metadata, this will create a record that can be inserted into the
        Object collection.
        """
        if data is None:
            raise ValueError("data is required")
        if not isinstance(data, dict):
            raise ValueError("data must be a dictionary")
        if "eTag" in data:
            oid = self.extract_uuid_from_etag(data["eTag"])
        else:
            ic("No eTag in data, generating a new UUID")
            oid = uuid.uuid4()
            # "eTag": "\"{4F181015-B1D6-4793-8104-806A631830FF},1\""
            data["eTag"] = '"{' + str(oid) + '},1"'
            ic(data["eTag"])
        # assert data['parentReference']['path'].strip() == '/drive/root:', \
        #    f'Only root is supported\n{data['parentReference']['path']}\n{json.dumps(data, indent=2)}'
        path = "/" + data["parentReference"]["name"] + "/" + data["name"]
        timestamps = []
        if "fileSystemInfo" in data:
            if "createdDateTime" in data["fileSystemInfo"]:
                timestamps.append(
                    {
                        "Label": IndalekoObject.CREATION_TIMESTAMP,
                        "Value": datetime.datetime.fromisoformat(
                            data["fileSystemInfo"]["createdDateTime"],
                        ).isoformat(),
                        "Description": "Creation Time",
                    },
                )
            if "lastModifiedDateTime" in data["fileSystemInfo"]:
                # No distinction between modified and changed.
                timestamps.append(
                    {
                        "Label": IndalekoObject.MODIFICATION_TIMESTAMP,
                        "Value": datetime.datetime.fromisoformat(
                            data["fileSystemInfo"]["lastModifiedDateTime"],
                        ).isoformat(),
                        "Description": "Modification Time",
                    },
                )
                timestamps.append(
                    {
                        "Label": IndalekoObject.CHANGE_TIMESTAMP,
                        "Value": datetime.datetime.fromisoformat(
                            data["fileSystemInfo"]["lastModifiedDateTime"],
                        ).isoformat(),
                        "Description": "Access Time",
                    },
                )
        else:
            if "createdDateTime" in data:
                timestamps.append(
                    {
                        "Label": IndalekoObject.CREATION_TIMESTAMP,
                        "Value": datetime.datetime.fromisoformat(
                            data["createdTime"],
                        ).isoformat(),
                        "Description": "Creation Time",
                    },
                )
            if "lastModifiedDateTime" in data:
                # No distinction between modified and changed.
                timestamps.append(
                    {
                        "Label": IndalekoObject.MODIFICATION_TIMESTAMP,
                        "Value": datetime.datetime.fromisoformat(
                            data["modifiedTime"],
                        ).isoformat(),
                        "Description": "Modification Time",
                    },
                )
                timestamps.append(
                    {
                        "Label": IndalekoObject.CHANGE_TIMESTAMP,
                        "Value": datetime.datetime.fromisoformat(
                            data["modifiedTime"],
                        ).isoformat(),
                        "Description": "Access Time",
                    },
                )
        data["Path"] = path
        data["Name"] = data["name"]
        if "folder" in data:
            unix_file_attributes = UnixFileAttributes.FILE_ATTRIBUTES["S_IFDIR"]
            windows_file_attributes = IndalekoWindows.FILE_ATTRIBUTES["FILE_ATTRIBUTE_DIRECTORY"]
        elif "file" in data:
            unix_file_attributes = UnixFileAttributes.FILE_ATTRIBUTES["S_IFREG"]
            windows_file_attributes = IndalekoWindows.FILE_ATTRIBUTES["FILE_ATTRIBUTE_NORMAL"]
        else:
            raise ValueError("Unknown file type")
        kwargs = {
            "Record": IndalekoRecordDataModel(
                SourceIdentifier=self.source,
                Timestamp=self.timestamp,
                Data=encode_binary_data(bytes(json.dumps(data).encode("utf-8"))),
            ),
            "URI": data.get("webUrl"),
            "ObjectIdentifier": str(oid),
            "Timestamps": timestamps,
            "Size": int(data.get("size", 0)),
            "SemanticAttributes": None,
            "Label": data.get("name"),
            "LocalPath": path,
            "LocalIdentifier": data.get("id"),
            "Volume": None,
            "PosixFileAttributes": UnixFileAttributes.map_file_attributes(
                unix_file_attributes,
            ),
            "WindowsFileAttributes": IndalekoWindows.map_file_attributes(
                windows_file_attributes,
            ),
        }
        # ic(kwargs)
        return IndalekoObject(**kwargs)


def main():
    """Main entry point for the OneDrive recorder"""
    BaseCloudStorageRecorder.cloud_recorder_runner(
        IndalekoOneDriveCloudStorageCollector,
        IndalekoOneDriveCloudStorageRecorder,
    )


if __name__ == "__main__":
    main()
