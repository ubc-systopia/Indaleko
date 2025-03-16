"""
This module collects local file system metadata from the Mac local file
system.

Indaleko Mac Local Collector
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
import inspect
import os
import logging
import platform
import sys
import uuid

from pathlib import Path
from typing import Union

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db.service_manager import IndalekoServiceManager
from platforms.mac.machine_config import IndalekoMacOSMachineConfig
from storage.collectors.base import BaseStorageCollector
from storage.collectors.data_model import IndalekoStorageCollectorDataModel
from storage.collectors.local.local_base import BaseLocalStorageCollector
from utils.misc.file_name_management import (
    generate_file_name,
    extract_keys_from_file_name,
    find_candidate_files,
)

# pylint: enable=wrong-import-position


class IndalekoMacLocalStorageCollector(BaseLocalStorageCollector):
    """
    This is the class that indexes Mac local file systems.
    """

    mac_platform = "Mac"
    mac_local_collector_name = "fs_collector"

    indaleko_mac_local_collector_uuid = "14d6c989-0d1e-4ccc-8aea-a75688a6bb5f"
    indaleko_mac_local_collector_service_name = "Mac Local Storage Collector"
    indaleko_mac_local_collector_service_description = (
        "This service collects metadata from the local filesystems of a Mac machine."
    )
    indaleko_mac_local_collector_service_version = "1.0"
    indaleko_mac_local_collector_service_type = (
        IndalekoServiceManager.service_type_storage_collector
    )

    indaleko_mac_local_collector_service = {
        "service_name": indaleko_mac_local_collector_service_name,
        "service_description": indaleko_mac_local_collector_service_description,
        "service_version": indaleko_mac_local_collector_service_version,
        "service_type": indaleko_mac_local_collector_service_type,
        "service_identifier": indaleko_mac_local_collector_uuid,
    }

    collector_data = IndalekoStorageCollectorDataModel(
        PlatformName=mac_platform,
        ServiceFileName=mac_local_collector_name,
        ServiceDescription=indaleko_mac_local_collector_service_description,
        ServiceUUID=uuid.UUID(indaleko_mac_local_collector_uuid),
        ServiceVersion=indaleko_mac_local_collector_service_version,
    )

    def __init__(self, **kwargs):
        super().__init__(
            **kwargs,
            **IndalekoMacLocalStorageCollector.indaleko_mac_local_collector_service,
        )

        self.dir_count = 0
        self.file_count = 0

    def generate_mac_collector_file_name(self, **kwargs) -> str:
        if "platform" not in kwargs:
            kwargs["platform"] = IndalekoMacLocalStorageCollector.mac_platform
        if "collector_name" not in kwargs:
            kwargs["collector_name"] = (
                IndalekoMacLocalStorageCollector.mac_local_collector_name
            )
        if "machine_id" not in kwargs:
            kwargs["machine_id"] = uuid.UUID(self.machine_config.machine_id).hex
        ic(kwargs)
        return BaseStorageCollector.generate_collector_file_name(**kwargs)

    def build_stat_dict(self, name: str, root: str, last_uri=None) -> tuple:
        """
        Given a file name and a root directory, this will return a dict
        constructed from the file system metadata ("stat") for that file.
        Returns: dict_stat, last_uri
        """

        file_path = os.path.join(root, name)

        if last_uri is None:
            last_uri = file_path
        try:
            stat_data = os.stat(file_path)
        except Exception as e:  # pylint: disable=broad-except
            # at least for now, we just skip errors
            logging.warning("Unable to stat %s : %s", file_path, e)
            self.error_count += 1
            return None

        stat_dict = {
            key: getattr(stat_data, key)
            for key in dir(stat_data)
            if key.startswith("st_")
        }
        stat_dict["Name"] = name
        stat_dict["Path"] = root
        stat_dict["URI"] = os.path.join(root, name)
        stat_dict["Collector"] = str(self.get_collector_service_identifier())
        return stat_dict

    class local_collector_mixin(BaseLocalStorageCollector.local_collector_mixin):
        @staticmethod
        def load_machine_config(keys: dict[str, str]) -> IndalekoMacOSMachineConfig:
            """Load the machine configuration"""
            if keys.get("debug"):
                ic(f"local_collector_mixin.load_machine_config: {keys}")
            if "machine_config_file" not in keys:
                raise ValueError(
                    f"{inspect.currentframe().f_code.co_name}: machine_config_file must be specified"
                )
            offline = keys.get("offline", False)
            return IndalekoMacOSMachineConfig.load_config_from_file(
                config_file=str(keys["machine_config_file"]), offline=offline
            )

        @staticmethod
        def find_machine_config_files(
            config_dir: Union[str, Path], platform: str, debug: bool = False
        ) -> Union[list[str], None]:
            """Find the machine configuration files"""
            if debug:
                ic(f"find_machine_config_files: config_dir = {config_dir}")
                ic(f"find_machine_config_files:   platform = {platform}")
            if not Path(config_dir).exists():
                ic(f"Warning: did not find any config files in {config_dir}")
                return None
            platform = "macos"
            ic(platform)
            return [
                fname
                for fname, _ in find_candidate_files(
                    [platform, "-hardware-info"], str(config_dir)
                )
                if fname.endswith(".json")
            ]

        @staticmethod
        def extract_filename_metadata(file_name):
            # the mac uses non-standard naming for machine config files, so we have to handle that here.
            if not file_name.startswith(
                IndalekoMacOSMachineConfig.macos_machine_config_file_prefix
            ):
                return BaseLocalStorageCollector.local_collector_mixin.extract_filename_metadata(
                    file_name
                )
            # macos-hardware-info-f6ff7c7f-b4d7-484f-9b58-1ad2820a8d85-2024-12-04T00-44-25.583891Z.json
            assert file_name.endswith(".json")  # if not, generalize this
            prefix_length = len(
                IndalekoMacOSMachineConfig.macos_machine_config_file_prefix
            )
            machine_id = uuid.UUID(
                file_name[prefix_length + 1 : prefix_length + 37]
            ).hex
            timestamp = file_name[prefix_length + 38 : -5]
            keys = {
                "platform": platform.system(),
                "service": "macos_machine_config",
                "machine": machine_id,
                "timestamp": timestamp,
                "suffix": ".json",
            }
            return keys

    cli_handler_mixin = local_collector_mixin


def main():
    """This is the CLI handler for the mac local storage collector."""
    BaseLocalStorageCollector.local_collector_runner(
        IndalekoMacLocalStorageCollector, IndalekoMacOSMachineConfig
    )


if __name__ == "__main__":
    main()
