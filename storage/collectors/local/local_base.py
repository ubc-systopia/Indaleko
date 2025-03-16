"""
This is the generic class for an Indaleko Local Storage Collector.

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
import logging
import os
from pathlib import Path
import sys
import uuid

from typing import Union, Callable, Any

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models import IndalekoSourceIdentifierDataModel
from perf.perf_collector import IndalekoPerformanceDataCollector
from perf.perf_recorder import IndalekoPerformanceDataRecorder
from platforms.machine_config import IndalekoMachineConfig
from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
from utils.cli.runner import IndalekoCLIRunner
from storage.collectors import BaseStorageCollector

# pylint: enable=wrong-import-position


class BaseLocalStorageCollector(BaseStorageCollector):
    """This is the base class for all local storage recorders in Indaleko."""

    def __init__(self, **kwargs):
        """This is the constructor for the base local storage recorder."""
        if "args" in kwargs:
            self.args = kwargs["args"]
            self.output_type = getattr(self.args, "output_type", "file")
            kwargs["storage_description"] = getattr(self.args, "storage")
        else:
            self.args = None
            self.output_type = "file"
        super().__init__(**kwargs)
        self.cli_handler_mixin = BaseLocalStorageCollector.local_collector_mixin

    @staticmethod
    def load_machine_config(keys: dict[str, str]) -> IndalekoMachineConfig:
        """Load the machine configuration"""
        if keys.get("debug"):
            ic(f"load_machine_config: {keys}")
        if "machine_config_file" not in keys:
            raise ValueError(
                f"{inspect.currentframe().f_code.co_name}: machine_config_file must be specified"
            )
        offline = keys.get("offline", False)
        platform_class = keys["class"]  # must exist
        return platform_class.load_config_from_file(
            config_file=str(keys["machine_config_file"]), offline=offline
        )

    @staticmethod
    def get_local_storage_collector() -> "BaseLocalStorageCollector":
        """This function should be overridden: it is used to create the appropriate local storage recorder."""
        raise NotImplementedError(
            "This function must be overridden by the derived class"
        )

    @staticmethod
    def execute_command(command: str) -> None:
        """Execute a command"""
        result = os.system(command)
        logging.info("Command %s result: %d", command, result)
        print(f"Command {command} result: {result}")

    class local_collector_mixin(IndalekoBaseCLI.default_handler_mixin):

        @staticmethod
        def get_pre_parser() -> Union[argparse.ArgumentParser, None]:
            """This method is used to get the pre-parser"""
            parser = argparse.ArgumentParser(add_help=False)
            default_path = os.path.expanduser("~")
            parser.add_argument(
                "--path",
                help=f"Path to the directory from which to collect metadata (default={default_path})",
                type=str,
                default=default_path,
            )
            return parser

        @staticmethod
        def load_machine_config(keys: dict[str, str]) -> IndalekoMachineConfig:
            """Load the machine configuration"""
            assert "class" in keys, "(machine config) class must be specified"
            return BaseLocalStorageCollector.load_machine_config(keys)

        @staticmethod
        def get_additional_parameters(pre_parser):
            """This method is used to add additional parameters (if any) to the parser."""
            return pre_parser

    @staticmethod
    def local_run(keys: dict[str, str]) -> Union[dict, None]:
        """Run the collector"""
        args = keys["args"]  # must be there.
        cli = keys["cli"]  # must be there.
        config_data = cli.get_config_data()
        debug = hasattr(args, "debug") and args.debug
        if debug:
            ic(config_data)
        # recorder_class = keys['parameters']['RecorderClass']
        machine_config_class = keys["parameters"]["MachineConfigClass"]
        collector_class = keys["parameters"]["CollectorClass"]  # unused for now
        output_file = str(Path(args.datadir) / config_data["OutputFile"])
        # recorders have the machine_id so they need to find the
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
        if config_data.get("StorageId"):
            kwargs["storage"] = config_data["StorageId"]
        else:
            ic(config_data)
        collector = collector_class(**kwargs)

        def collect(collector: BaseLocalStorageCollector, **kwargs):
            collector.collect()

        def extract_counters(**kwargs):
            collector = kwargs.get("collector")
            if collector:
                return collector.get_counts()
            else:
                return {}

        def capture_performance(
            task_func: Callable[..., Any], output_file_name: Union[Path, str] = None
        ):
            perf_data = IndalekoPerformanceDataCollector.measure_performance(
                task_func,
                source=IndalekoSourceIdentifierDataModel(
                    Identifier=collector.get_collector_service_identifier(),
                    Version=collector.get_collector_service_version(),
                    Description=collector.get_collector_service_description(),
                ),
                description=collector.get_collector_service_description(),
                MachineIdentifier=uuid.UUID(kwargs["machine_config"].machine_id),
                process_results_func=extract_counters,
                output_file_name=output_file_name,
                collector=collector,
            )
            if args.performance_db or args.performance_file:
                perf_recorder = IndalekoPerformanceDataRecorder()
                if args.performance_file:
                    perf_file = str(
                        Path(args.datadir) / config_data["PerformanceDataFile"]
                    )
                    perf_recorder.add_data_to_file(perf_file, perf_data)
                    if debug:
                        ic(
                            "Performance data written to ",
                            config_data["PerformanceDataFile"],
                        )
                if args.performance_db:
                    perf_recorder.add_data_to_db(perf_data)
                    if debug:
                        ic("Performance data written to the database")

        # Step 1: normalize the data and gather the performance.
        if args.debug:
            ic("Normalizing data")
        capture_performance(collect, output_file_name=output_file)
        # Step 2: record the time to save the object data.
        assert hasattr(collector, "data"), "No data collected"
        assert len(collector.data), "No data in set"
        if args.debug:
            ic("Writing file system metadata to file")
        capture_performance(collector.write_data_to_file, output_file)

    @staticmethod
    def local_collector_runner(
        collector_class: BaseStorageCollector,
        machine_config_class: IndalekoMachineConfig,
    ) -> None:
        """This is the CLI handler for local storage collectors."""
        IndalekoCLIRunner(
            cli_data=IndalekoBaseCliDataModel(
                RegistrationServiceName=collector_class.get_collector_service_registration_name(),
                FileServiceName=collector_class.get_collector_service_file_name(),
            ),
            handler_mixin=collector_class.get_collector_cli_handler_mixin(),
            features=IndalekoBaseCLI.cli_features(input=False),
            Run=BaseLocalStorageCollector.local_run,
            RunParameters={
                "CollectorClass": collector_class,
                "MachineConfigClass": machine_config_class,
            },
        ).run()
