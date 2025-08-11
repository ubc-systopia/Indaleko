"""
This module handles metadata collection from local Linux file systems.

Indaleko Linux Local Collector
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

import inspect
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
from db.service_manager import IndalekoServiceManager
from platforms.linux.machine_config import IndalekoLinuxMachineConfig
from storage.collectors.data_model import IndalekoStorageCollectorDataModel
from storage.collectors.local.local_base import BaseLocalStorageCollector


# pylint: enable=wrong-import-position


class IndalekoLinuxLocalStorageCollector(BaseLocalStorageCollector):
    """This is the class that collects metadata from Linux local file systems."""

    linux_platform = "Linux"
    linux_local_collector_name = "fs_collector"

    indaleko_linux_local_collector_uuid = "bef019bf-b762-4297-bbe2-bf79a65027ae"
    indaleko_linux_local_collector_service_name = "Linux Local Collector"
    indaleko_linux_local_collector_service_description = (
        "This service collects local filesystem metadata of a Linux machine."
    )
    indaleko_linux_local_collector_service_version = "1.0"
    indaleko_linux_local_collector_service_type = IndalekoServiceManager.service_type_storage_collector

    indaleko_linux_local_collector_service = {
        "service_name": indaleko_linux_local_collector_service_name,
        "service_description": indaleko_linux_local_collector_service_description,
        "service_version": indaleko_linux_local_collector_service_version,
        "service_type": indaleko_linux_local_collector_service_type,
        "service_identifier": indaleko_linux_local_collector_uuid,
    }

    collector_data = IndalekoStorageCollectorDataModel(
        PlatformName=linux_platform,
        ServiceRegistrationName=indaleko_linux_local_collector_service_name,
        ServiceFileName=linux_local_collector_name,
        ServiceUUID=uuid.UUID(indaleko_linux_local_collector_uuid),
        ServiceVersion=indaleko_linux_local_collector_service_version,
        ServiceDescription=indaleko_linux_local_collector_service_description,
    )

    def __init__(self, **kwargs) -> None:
        super().__init__(
            **kwargs,
            **IndalekoLinuxLocalStorageCollector.indaleko_linux_local_collector_service,
        )

    class linux_local_collector_mixin(BaseLocalStorageCollector.local_collector_mixin):
        @staticmethod
        def load_machine_config(keys: dict[str, str]) -> IndalekoLinuxMachineConfig:
            """Load the machine configuration."""
            debug = keys.get("debug", False)
            if debug:
                ic(f"linux_local_collector_mixin.load_machine_config: {keys}")
            if "machine_config_file" not in keys:
                raise ValueError(
                    f"{inspect.currentframe().f_code.co_name}: machine_config_file must be specified",
                )
            offline = keys.get("offline", False)
            return IndalekoLinuxMachineConfig.load_config_from_file(
                config_file=str(keys["machine_config_file"]),
                offline=offline,
            )

    cli_handler_mixin = linux_local_collector_mixin


def main() -> None:
    """The CLI handler for the linux local storage collector."""
    BaseLocalStorageCollector.local_collector_runner(
        IndalekoLinuxLocalStorageCollector,
        IndalekoLinuxMachineConfig,
    )


if __name__ == "__main__":
    main()
