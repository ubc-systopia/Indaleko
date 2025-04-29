"""
This is the generic class for an Indaleko Local Storage Recorder.

An Indaleko local storage recorder takes information about some (or all) of the data that is stored in
local file system(s) on this machine. It is derived from the generic base for all
recorders, but includes support for local-specific options.

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

import gc
import inspect
import os
import sys
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import psutil
from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models import IndalekoSourceIdentifierDataModel
from db import IndalekoDBCollections
from perf.perf_collector import IndalekoPerformanceDataCollector
from perf.perf_recorder import IndalekoPerformanceDataRecorder
from platforms.machine_config import IndalekoMachineConfig
from storage.collectors import BaseStorageCollector
from storage.recorders.base import BaseStorageRecorder
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
from utils.cli.runner import IndalekoCLIRunner

# pylint: enable=wrong-import-position


class BaseLocalStorageRecorder(BaseStorageRecorder):
    """This is the base class for all local storage recorders in Indaleko."""

    def find_collector_files(self) -> list:
        """This function should be overridden: it is used to find the collector files for the recorder."""
        raise NotImplementedError(
            "This function must be overridden by the derived class",
        )

    @staticmethod
    def load_machine_config(keys: dict[str, str]) -> IndalekoMachineConfig:
        """Load the machine configuration"""
        if keys.get("debug"):
            ic(f"local_recorder_mixin.load_machine_config: {keys}")
        if "machine_config_file" not in keys:
            raise ValueError(
                f"{inspect.currentframe().f_code.co_name}: machine_config_file must be specified",
            )
        offline = keys.get("offline", False)
        platform_class = keys["class"]  # must exist
        return platform_class.load_config_from_file(
            config_file=str(keys["machine_config_file"]),
            offline=offline,
        )

    @staticmethod
    def get_local_storage_recorder() -> "BaseLocalStorageRecorder":
        """This function should be overridden: it is used to create the appropriate local storage recorder."""
        raise NotImplementedError(
            "This function must be overridden by the derived class",
        )

    class local_recorder_mixin(BaseStorageRecorder.base_recorder_mixin):
        """This is the mixin for the local recorder"""

        @staticmethod
        def load_machine_config(keys: dict[str, str]) -> IndalekoMachineConfig:
            assert "class" in keys, "(machine config) class must be specified"
            return BaseLocalStorageRecorder.load_machine_config(keys)

    @staticmethod
    def local_run(keys: dict[str, str]) -> dict | None:
        """Run the recorder"""
        args = keys["args"]  # must be there.
        cli = keys["cli"]  # must be there.
        config_data = cli.get_config_data()
        debug = hasattr(args, "debug") and args.debug
        if debug:
            ic(config_data)
        recorder_class = keys["parameters"]["RecorderClass"]
        machine_config_class = keys["parameters"]["MachineConfigClass"]
        output_file = str(Path(args.datadir) / config_data["OutputFile"])
        # collector_class = keys['parameters']['CollectorClass'] # unused for now
        # recorders have the machine_id so they need to find the
        # matching machine configuration file.
        kwargs = {
            "machine_config": cli.handler_mixin.load_machine_config(
                {
                    "machine_config_file": str(
                        Path(args.configdir) / args.machine_config,
                    ),
                    "offline": args.offline,
                    "class": machine_config_class,
                },
            ),
            "timestamp": config_data["Timestamp"],
            "input_file": str(Path(args.datadir) / args.inputfile),
            "offline": args.offline,
            "args": args,
        }
        if (
            "InputFileKeys" in config_data
            and "storage" in config_data["InputFileKeys"]
            and config_data["InputFileKeys"]["storage"]
        ):
            kwargs["storage_description"] = config_data["InputFileKeys"]["storage"]

        def record(recorder: BaseLocalStorageRecorder, **kwargs):
            recorder.record()

        def extract_counters(**kwargs):
            recorder = kwargs.get("recorder")
            if recorder:
                return recorder.get_counts()
            else:
                return {}

        recorder = recorder_class(**kwargs)

        def capture_performance(
            task_func: Callable[..., Any],
            output_file_name: Path | str = None,
        ):
            perf_data = IndalekoPerformanceDataCollector.measure_performance(
                task_func,
                source=IndalekoSourceIdentifierDataModel(
                    Identifier=recorder.get_recorder_service_uuid(),
                    Version=recorder.get_recorder_service_version(),
                    Description=recorder.get_recorder_service_description(),
                ),
                description=recorder.get_recorder_service_description(),
                MachineIdentifier=uuid.UUID(kwargs["machine_config"].machine_id),
                process_results_func=extract_counters,
                input_file_name=str(Path(args.datadir) / args.inputfile),
                output_file_name=output_file_name,
                recorder=recorder,
            )
            if args.performance_db or args.performance_file:
                perf_recorder = IndalekoPerformanceDataRecorder()
                if args.performance_file:
                    perf_file = str(
                        Path(args.datadir) / config_data["PerformanceDataFile"],
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
        capture_performance(record)
        # Step 2: record the time to save the object data.
        if args.debug:
            ic("Writing object data to file")
        capture_performance(
            recorder.write_object_data_to_file,
            output_file_name=output_file,
        )
        # Step 3: record the time to save the edge data.
        if args.debug:
            ic("Writing edge data to file")
        capture_performance(recorder.write_edge_data_to_file, recorder.output_edge_file)

        # Free that memory before running arangoimport!
        proc = psutil.Process(os.getpid())
        memory_before = proc.memory_info()
        if args.debug:
            ic(f"Memory usage before deleting recorder: {memory_before.rss}")
            ic(memory_before)
        recorder.reset_data()
        gc.collect()
        memory_after = proc.memory_info()
        if args.debug:
            ic(f"Memory usage after deleting recorder: {memory_after.rss}")
            ic(memory_after)

        if args.arangoimport and args.bulk:
            ic(
                "Warning: both arangoimport and bulk upload specified.  Using arangoimport ONLY.",
            )
        if args.arangoimport:
            # Step 4: upload the data to the database using the arangoimport utility
            if args.debug:
                ic("Using arangoimport to load object data")
            capture_performance(recorder.arangoimport_object_data)
            if args.debug:
                ic("Using arangoimport to load relationship data")
            capture_performance(recorder.arangoimport_relationship_data)
        elif args.bulk:
            # Step 5: upload the data to the database using the bulk uploader
            if args.debug:
                ic("Using bulk uploader to load object data")
            capture_performance(recorder.bulk_upload_object_data)
            if args.debug:
                ic("Using bulk uploader to load relationship data")
            capture_performance(recorder.bulk_upload_relationship_data)

    @staticmethod
    def local_recorder_runner(
        collector_class: BaseStorageCollector,
        recorder_class: BaseStorageRecorder,
        machine_config_class: IndalekoMachineConfig,
    ) -> None:
        """This is the CLI handler for local storage recorders."""
        runner = IndalekoCLIRunner(
            cli_data=IndalekoBaseCliDataModel(
                RegistrationServiceName=recorder_class.get_recorder_service_registration_name(),
                FileServiceName=recorder_class.get_recorder_service_file_name(),
                InputFileKeys={
                    "plt": collector_class.get_collector_platform_name(),
                    "svc": collector_class.get_collector_service_file_name(),
                },
            ),
            handler_mixin=recorder_class.local_recorder_mixin,
            Run=recorder_class.local_run,
            RunParameters={
                "CollectorClass": collector_class,
                "MachineConfigClass": machine_config_class,
                "RecorderClass": recorder_class,
            },
        )
        runner.run()

    def record(self) -> None:
        """
        This function processes and records the collector file and emits the data needed to
        upload to the database.
        """
        self.normalize()
        assert len(self.dir_data) + len(self.file_data) > 0, "No data to record"
        self.build_dirmap()
        self.build_edges()
        kwargs = {
            "machine": self.machine_id,
            "platform": getattr(self, "platform", self.get_recorder_platform_name()),
            "service": self.recorder_data.ServiceFileName,
            "collection": IndalekoDBCollections.Indaleko_Object_Collection,
            "timestamp": self.timestamp,
            "output_dir": self.data_dir,
        }
        if self.storage_description:
            kwargs["storage"] = self.storage_description

        self.output_object_file = self.generate_output_file_name(**kwargs)
        kwargs["collection"] = IndalekoDBCollections.Indaleko_Relationship_Collection
        self.output_edge_file = self.generate_output_file_name(**kwargs)
