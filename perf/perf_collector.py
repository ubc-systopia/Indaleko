"""
This module provides a base for the IndalekoPerformance data object.

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
import time
import uuid

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from data_models import (
    IndalekoPerformanceDataModel,
    IndalekoRecordDataModel,
    IndalekoSourceIdentifierDataModel,
)
from perf.source_code_version import IndalekoGitInfo
from utils.misc.data_management import encode_binary_data


# pylint: enable=wrong-import-position


class IndalekoPerformanceDataCollector:
    """
    The IndalekoPerformanceData class is used to collect, store,
    and query performance data gathered by Indaleko tools for
    further analysis.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the object."""
        self.perf_data: IndalekoPerformanceDataModel = IndalekoPerformanceDataModel(
            **kwargs,
        )

    @staticmethod
    def measure_performance(
        task_func: Callable[..., Any],
        source: IndalekoSourceIdentifierDataModel,
        description: str,
        MachineIdentifier: uuid.UUID | None,  # noqa: N803
        process_results_func: Callable[..., dict[str, int | float | str]] | None = None,
        input_file_name: str | None = None,
        output_file_name: str | None = None,
        *args: object | None,
        **kwargs: dict[str, Any] | None,
    ) -> "IndalekoPerformanceDataCollector":
        """Measure the performance of a function."""
        process = psutil.Process(os.getpid())
        start_time = datetime.now(UTC).isoformat()
        start_user_time = process.cpu_times().user
        start_system_time = process.cpu_times().system
        start_io_counters = process.io_counters() if hasattr(process, "io_counters") else None
        start_memory = process.memory_info().rss  # Resident Set Size (RSS) memory
        start_thread_count = process.num_threads()
        if input_file_name is not None and Path(input_file_name).exists():
            input_file_size = Path(input_file_name).stat().st_size
        else:
            input_file_size = None
        results_data = {}
        try:
            """Run the task."""
            start_clock = time.perf_counter()
            if output_file_name:
                result = task_func(*args, output_file_name=output_file_name, **kwargs)
            else:
                result = task_func(*args, **kwargs)
            end_clock = time.perf_counter()
            if process_results_func is not None:
                try:
                    results_data = process_results_func(
                        *args,
                        output_file_name=output_file_name,
                        **kwargs,
                        result=result,
                    )
                except TypeError as e:
                    ic(f"{process_results_func} is not a callable type: {e} ")
            elapsed_time = end_clock - start_clock
        except Exception as e:
            ic(
                f"measure_performance (calling {task_func} with {args} and {kwargs}): {e}",
            )
            result = None
            end_clock = time.perf_counter()
            elapsed_time = end_clock - start_clock
            raise

        end_time = datetime.now(UTC).isoformat()
        end_user_time = process.cpu_times().user
        end_system_time = process.cpu_times().system
        end_io_counters = process.io_counters() if hasattr(process, "io_counters") else None
        end_memory = process.memory_info().rss  # Resident Set Size (RSS) memory
        end_thread_count = process.num_threads()
        output_file_size = None
        if output_file_name is not None and os.path.exists(output_file_name):
            output_file_size = os.stat(output_file_name).st_size

        kwargs_data = {}
        for key, value in kwargs.items():
            kwargs_data[str(key)] = str(value)
        data = {}
        data["description"] = description
        if MachineIdentifier:
            data["machine_id"] = str(MachineIdentifier)
        else:
            data["machine_id"] = None
        data["args"] = args
        data["kwargs"] = (kwargs_data,)
        data["start_time"] = start_time
        data["end_time"] = end_time
        data["elapsed_time"] = elapsed_time
        data["user_cpu_time"] = end_user_time - start_user_time
        data["system_cpu_time"] = end_system_time - start_system_time
        data["peak_memory_usage"] = max(start_memory, end_memory)
        data["input_file_name"] = input_file_name
        data["input_file_size"] = input_file_size
        data["output_file_name"] = output_file_name
        data["output_file_size"] = output_file_size
        if start_io_counters and end_io_counters:
            data["io_read_bytes"] = end_io_counters.read_bytes - start_io_counters.read_bytes
            data["io_write_bytes"] = end_io_counters.write_bytes - start_io_counters.write_bytes
        else:
            data["io_read_bytes"] = 0
            data["io_write_bytes"] = 0
        data["thread_count"] = max(start_thread_count, end_thread_count)
        data["result"] = result
        data["additional_data"] = {
            **results_data,
            "InputFileName": input_file_name,
            "OutputFileName": output_file_name,
            "SourceVersionInformation": IndalekoGitInfo.get_framework_source_version_data(
                as_json=True,
            ),
        }

        record = IndalekoRecordDataModel(
            SourceIdentifier=source,
            Timestamp=end_time,
            Attributes=data,
            Data=encode_binary_data(json.dumps(data)),
        )

        return IndalekoPerformanceDataCollector(
            Record=record,
            SourceIdentifier=source,
            MachineConfigurationId=MachineIdentifier,
            StartTimestamp=start_time,
            EndTimestamp=end_time,
            ElapsedTime=data["elapsed_time"],
            UserCPUTime=data["user_cpu_time"],
            SystemCPUTime=data["system_cpu_time"],
            InputSize=data["input_file_size"],
            OutputSize=data["output_file_size"],
            PeakMemoryUsage=data["peak_memory_usage"],
            IOReadBytes=data["io_read_bytes"],
            IOWriteBytes=data["io_write_bytes"],
            ThreadCount=data["thread_count"],
            AdditionalData=data["additional_data"],
        )

    def start(self) -> None:
        """Start the performance data collection."""


    def stop(self) -> None:
        """Stop the performance data collection."""

    @staticmethod
    def deserialize(data: dict) -> "IndalekoPerformanceDataCollector":
        """Deserialize a dictionary to an object."""
        return IndalekoPerformanceDataCollector(**data)

    def serialize(self) -> dict:
        """Serialize the object to a dictionary."""
        doc = json.loads(self.perf_data.model_dump_json())
        doc["_key"] = str(uuid.uuid4())
        return doc

    test_data = {
        "Record": {
            "SourceIdentifier": {
                "Identifier": "1697394b-0f8f-44b4-91c0-a0fbd9d77feb",
                "Version": "1.0",
            },
            "Timestamp": datetime.now(UTC),
            "Attributes": {},
            "Data": encode_binary_data(b""),
        },
        "MachineConfigurationId": "f7a439ec-c2d0-4844-a043-d8ac24d9ac0b",
        "StartTimestamp": "2024-12-15 15:55:35.786212+00:00",
        "EndTimestamp": "2024-12-15 15:56:06.200578+00:00",
        "UserCPUTime": 0.02,
        "SystemCPUTime": 0.221,
        "PeakMemoryUsage": 3152 * 1024,
        "IOReadBytes": int(4.2 * 1024 * 1024),
        "IOWriteBytes": int(3.9 * 1024),
        "ThreadCount": 1,
    }


def main() -> None:
    """Test code for the IndalekoPerformanceData class."""
    ic("IndalekoPerformanceData test code")
    perf_data: IndalekoPerformanceDataCollector = IndalekoPerformanceDataCollector(
        Record={
            "SourceIdentifier": {
                "Identifier": "1697394b-0f8f-44b4-91c0-a0fbd9d77feb",
                "Version": "1.0",
            },
            "Timestamp": datetime.now(UTC),
            "Attributes": {},
            "Data": encode_binary_data(b""),
        },
        MachineConfigurationId="f7a439ec-c2d0-4844-a043-d8ac24d9ac0b",
        StartTimestamp="2024-12-15 15:55:35.786212+00:00",
        EndTimestamp="2024-12-15 15:56:06.200578+00:00",
        UserCPUTime=0.02,
        SystemCPUTime=0.221,
        PeakMemoryUsage=3152 * 1024,
        IOReadBytes=int(4.2 * 1024 * 1024),
        IOWriteBytes=int(3.9 * 1024),
        ThreadCount=1,
        AdditionalData={
            "SourceVersionInformation": IndalekoGitInfo.get_framework_source_version_data(
                as_json=True,
            ),
        },
    )
    ic(perf_data.serialize())


if __name__ == "__main__":
    main()
