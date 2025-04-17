"""
This module is a test wrapper for the NTFS activity data collector.

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
import inspect
from pathlib import Path
import os
import sys
import uuid

from icecream import ic
from typing import Union

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from activity.collectors.base import BaseActivityCollector
from activity.collectors.data_model import IndalekoActivityCollectorDataModel
from platforms.machine_config import IndalekoMachineConfig
from platforms.windows.machine_config import IndalekoWindowsMachineConfig
from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
from utils.cli.runner import IndalekoCLIRunner
# pylint: enable=wrong-import-position


class TestCollectorV2(BaseActivityCollector):
    """This is a test wrapper for the NTFS activity data collector."""

    collector_data = IndalekoActivityCollectorDataModel(
        PlatformName="Windows",
        ServiceRegistrationName="NTFS Test Collection V2",
        ServiceFileName="activity_collector",
        ServiceUUID=uuid.UUID("c53c339a-edba-4328-bfdf-0504ac9c0b35"),
        ServiceVersion="1.0",
        ServiceDescription="NTFS Test Activity Collector V2",
    )

    def __init__(self, **kwargs):
        """This is the constructor for the test collector."""
        for key, value in self.collector_data:
            if key not in kwargs:
                kwargs[key] = value
        if "platform" not in kwargs:
            kwargs["platform"] = "Windows"
        if "collector_data" not in kwargs:
            kwargs["collector_data"] = (
                TestCollectorV2.collector_data
            )
        super().__init__(**kwargs)
        if not hasattr(self, "storage") and "storage" in kwargs:
            self.storage = kwargs["storage"]

    class collector_mixin(IndalekoBaseCLI.default_handler_mixin):
        """This is the CLI handler mixin for the NTFS activity collector."""

        @staticmethod
        def get_pre_parser() -> Union[argparse.ArgumentParser, None]:
            """This method is used to get the pre-parser"""
            parser = argparse.ArgumentParser(add_help=False)
            default_drive = "C:"
            parser.add_argument(
                "--drive",
                help=f"Drive to monitor (default={default_drive})",
                type=str,
                default=default_drive,
            )
            return parser

        @staticmethod
        def load_machine_config(keys: dict[str, str]) -> IndalekoMachineConfig:
            """Load the machine configuration"""
            ic(keys)
            if keys.get("debug"):
                ic(f"load_machine_config: {keys}")
            if "machine_config_file" not in keys:
                raise ValueError(
                    f"{inspect.currentframe().f_code.co_name}: "
                    "machine_config_file must be specified"
                )
            offline = keys.get("offline", False)
            platform_class = keys["class"]  # must exist
            return platform_class.load_config_from_file(
                config_file=str(keys["machine_config_file"]), offline=offline
            )

    cli_handler_mixin = collector_mixin()

    @staticmethod
    def local_run(keys: dict[str, str]) -> Union[dict, None]:
        """Run the test"""
        args = keys["args"]  # must be here
        cli = keys["cli"]  # must be here
        config_data = cli.get_config_data()
        debug = hasattr(args, "debug") and args.debug
        if debug:
            ic(config_data)
        machine_config_class = keys["parameters"]["MachineConfigClass"]
        collector_class = keys["parameters"]["CollectorClass"]
        kwargs = {
            "machine_config": cli.handler_mixin.load_machine_config(
                {
                    "machine_config_file": str(
                        Path(args.configdir) / args.machine_config
                    ),
                    "offline": args.offline,
                    "class": machine_config_class,
                }
            ),
            "timestamp": config_data["Timestamp"],
            "path": args.path,
            "offline": args.offline,
        }
        collector = collector_class(**kwargs)
        ic(collector)
        # Continue here...

    @staticmethod
    def local_collector_runner(
        collector_class,
        machine_config_class: IndalekoMachineConfig,
    ) -> None:
        """This is the CLI handler for local storage collectors."""
        IndalekoCLIRunner(
            cli_data=IndalekoBaseCliDataModel(
                RegistrationServiceName=collector_class
                .get_collector_service_registration_name(),
                FileServiceName=collector_class
                .get_collector_service_file_name(),
            ),
            handler_mixin=collector_class.get_collector_cli_handler_mixin(),
            features=IndalekoBaseCLI.cli_features(input=False),
            Run=TestCollectorV2.local_run,
            RunParameters={
                "CollectorClass": collector_class,
                "MachineConfigClass": machine_config_class,
            },
        ).run()


def main():
    """The CLI handler for the NTFS activity collector test."""
    TestCollectorV2.local_collector_runner(
        TestCollectorV2, IndalekoWindowsMachineConfig
    )
    return
    tester = TestCollectorV2()
    IndalekoCLIRunner(
        cli_data=IndalekoBaseCliDataModel(
            RegistrationServiceName=tester
            .collector_data.ServiceRegistrationName,
            FileServiceName=tester.collector_data.ServiceFileName,
        ),
        handler_mixin=tester.cli_handler_mixin,
        features=IndalekoBaseCLI.cli_features(input=False),
        Run=TestCollectorV2.local_collector_runner,
        RunParameters={
            "CollectorClass": TestCollectorV2,
            "MachineConfigClass": IndalekoWindowsMachineConfig,
        },
    ).run()


if __name__ == "__main__":
    main()
