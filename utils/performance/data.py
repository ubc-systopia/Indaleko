"""
This module provides a set of utility functions for collecting performance data
in the Indaleko system.

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

from icecream import ic
from typing import Callable, Any

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.i_perf import IndalekoPerformanceDataModel
from data_models import IndalekoRecordDataModel
from utils.misc.data_management import encode_binary_data
# pylint: enable=wrong-import-position

class IndalekoPerformance:
    '''This class provides a set of utility functions for collecting performance data.'''

from typing import Callable, Any, Tuple, Dict
from pydantic import BaseModel
from datetime import datetime
import psutil
import os
import time


class PerformanceData:
    '''
    This class builds a performance data object for Indaleko.
    '''
    def __init__(self,
        task_func: Callable[..., Any],  # A callable that takes any arguments and returns any type
        *args: Any,  # Positional arguments to be passed to the task_func
        **kwargs: Dict[str, Any]  # Keyword arguments to be passed to the task_func
        ):
        """
        Measures performance data for the given task function.

        Args:
            task_func (Callable[..., Any]): The function to be measured. Should accept *args and **kwargs.
            *args (Any): Positional arguments to pass to `task_func`.
            **kwargs (Dict[str, Any]): Keyword arguments to pass to `task_func`.

        Returns:
            PerformanceData: A PerformanceData object containing the performance data.
        """
        process = psutil.Process(os.getpid())
        start_time = datetime.now()
        start_user_time = process.cpu_times().user
        start_system_time = process.cpu_times().system
        start_io_counters = process.io_counters()
        start_memory = process.memory_info().rss  # Resident Set Size (RSS) memory
        self.start_thread_count = process.num_threads()

        # Track errors
        error_count = 0

        # Run the task
        try:
            start_clock = time.perf_counter()
            self.result = task_func(*args, **kwargs)
            end_clock = time.perf_counter()
        except Exception as e:
            self.result = None
            error_count += 1
            end_clock = time.perf_counter()

        # End measurements
        end_time = datetime.now()
        end_user_time = process.cpu_times().user
        end_system_time = process.cpu_times().system
        end_io_counters = process.io_counters()
        end_memory = process.memory_info().rss  # Check memory usage after task
        end_thread_count = process.num_threads()

        # Optional: Measure file sizes if applicable
        input_file = kwargs.get("input_file")
        output_file = kwargs.get("output_file")
        input_size = os.path.getsize(input_file) if input_file and os.path.exists(input_file) else None
        output_size = os.path.getsize(output_file) if output_file and os.path.exists(output_file) else None

        attributes = {
            'start time' : start_time.isoformat(),
            'end time' : end_time.isoformat(),
            'elapsed time' : float(end_clock - start_clock),
            'user cpu time' : float(end_user_time - start_user_time),
            'system cpu time' : float(end_system_time - start_system_time),
            'input size' : input_size,
            'output size' : output_size,
            'peak memory usage' : max(start_memory, end_memory),
            'io read bytes' : end_io_counters.read_bytes - start_io_counters.read_bytes,
            'io write bytes' : end_io_counters.write_bytes - start_io_counters.write_bytes,
            'thread count' : end_thread_count,
            'error count' : error_count,
            'result' : self.result,
        }

        self.performance_data = IndalekoPerformanceDataModel(
            Record=IndalekoRecordDataModel(
                SourceIdentifier=kwargs.get("source_identifier"),
                Timestamp=start_time,
                Attributes={},
                Data=encode_binary_data(attributes),
            ),
            StartTimestamp=start_time,
            EndTimestamp=end_time,
            ElapsedTime=end_clock - start_clock,
            UserCPUTime=end_user_time - start_user_time,
            SystemCPUTime=end_system_time - start_system_time,
            InputSize=input_size,
            OutputSize=output_size,
            PeakMemoryUsage=max(start_memory, end_memory),  # Simplified peak measurement
            IOReadBytes=end_io_counters.read_bytes - start_io_counters.read_bytes,
            IOWriteBytes=end_io_counters.write_bytes - start_io_counters.write_bytes,
            ThreadCount=end_thread_count,
            ErrorCount=error_count,
            AdditionalData=self.result,
        )

    def get_performance_data(self) -> IndalekoPerformanceDataModel:
        '''
        Returns the performance data object.
        '''
        return self.performance_data

    def get_result(self) -> Any:
        '''
        Returns the result of the task function.
        '''
        return self.result

    def serialize(self) -> Dict[str, Any]:
        '''
        Serialize the performance data to a dictionary.
        '''
        return json.loads(self.performance_data.model_dump_json())

def test_task(wait_time : int = 5) -> int:
    '''
    A simple test task function.
    '''
    time.sleep(wait_time)
    return wait_time

def main():
    '''
    This is the test code for the IndalekoPerformance class.
    '''
    source_identifier = {
        'Identifier' : '388adf3b-8a89-4fe5-80cf-a57c6edb52a6',
        'Version' : '1.0',
    }
    perf_data = PerformanceData(test_task, wait_time=3, source_identifier=source_identifier)
    ic(perf_data.serialize())

if __name__ == '__main__':
    main()
