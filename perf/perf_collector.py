'''
This module provides a base for the IndalekoPerformance data object.

Project Indaleko
Copyright (C) 2024 Tony Mason

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

'''
import json
import os
import psutil
import sys
import time
import uuid

from datetime import datetime, timezone
from typing import Dict, Any, Callable, Union

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from data_models import IndalekoPerformanceDataModel, IndalekoSourceIdentifierDataModel, IndalekoRecordDataModel
from utils.misc.data_management import encode_binary_data
# pylint: enable=wrong-import-position

class IndalekoPerformanceDataCollector:
    '''
    The IndalekoPerformanceData class is used to collect, store,
    and query performance data gathered by Indaleko tools for
    further analysis.
    '''

    def __init__(self, *args, **kwargs):
        '''Initialize the object.'''
        self.perf_data : IndalekoPerformanceDataModel = IndalekoPerformanceDataModel(**kwargs)

    @staticmethod
    def measure_performance(
        task_func : Callable[..., Any],
        source: IndalekoSourceIdentifierDataModel,
        description: str,
        MachineIdentifier: Union[uuid.UUID, None],
        process_results_func : Callable[..., Dict[str, Union[int, float, str]]] = None,
        input_file_name: Union[str, None] = None,
        output_file_name: Union[str, None] = None,
        *args: Union[Any, None],
        **kwargs: Union[Dict[str, Any], None]
    ) -> 'IndalekoPerformanceDataCollector':
        '''Measure the performance of a function.'''
        process = psutil.Process(os.getpid())
        start_time = datetime.now(timezone.utc).isoformat()
        start_user_time = process.cpu_times().user
        start_system_time = process.cpu_times().system
        if hasattr(process, 'io_counters'):
            start_io_counters = process.io_counters()
        else:
            start_io_counters = None
        start_memory = process.memory_info().rss  # Resident Set Size (RSS) memory
        start_thread_count = process.num_threads()
        input_file_size = None
        if input_file_name is not None and os.path.exists(input_file_name):
            input_file_size = os.stat(input_file_name).st_size
        results_data = {}
        try:
            '''Run the task.'''
            start_clock = time.perf_counter()
            result = task_func(*args, **kwargs)
            end_clock = time.perf_counter()
            if process_results_func is not None:
                try:
                    results_data = process_results_func(*args, **kwargs, result=result)
                except TypeError as e:
                    ic(f'{process_results_func} is not a callable type: {e} ')
            elapsed_time = end_clock - start_clock
        except Exception as e:
            ic(e)
            result = None
            end_clock = time.perf_counter()
            elapsed_time = end_clock - start_clock

        end_time = datetime.now(timezone.utc).isoformat()
        end_user_time = process.cpu_times().user
        end_system_time = process.cpu_times().system
        if hasattr(process, 'io_counters'):
            end_io_counters = process.io_counters()
        else:
            end_io_counters = None
        end_memory = process.memory_info().rss  # Resident Set Size (RSS) memory
        end_thread_count = process.num_threads()
        output_file_size = None
        if output_file_name is not None and os.path.exists(output_file_name):
            output_file_size = os.stat(output_file_name).st_size

        kwargs_data = {}
        for key, value in kwargs.items():
            kwargs_data[str(key)] = str(value)
        data = {}
        data['description'] = description
        if MachineIdentifier:
            data['machine_id'] = str(MachineIdentifier)
        else:
            data['machine_id'] = None
        data['args'] = args
        data['kwargs'] = kwargs_data,
        data['start_time'] = start_time
        data['end_time'] = end_time
        data['elapsed_time'] = elapsed_time
        data['user_cpu_time'] = end_user_time - start_user_time
        data['system_cpu_time'] = end_system_time - start_system_time
        data['peak_memory_usage'] = max(start_memory, end_memory)
        data['input_file_name'] = input_file_name
        data['input_file_size'] = input_file_size
        data['output_file_name'] = output_file_name
        data['output_file_size'] = output_file_size
        if start_io_counters and end_io_counters:
            data['io_read_bytes'] = end_io_counters.read_bytes - start_io_counters.read_bytes
            data['io_write_bytes'] = end_io_counters.write_bytes - start_io_counters.write_bytes
        else:
            data['io_read_bytes'] = 0
            data['io_write_bytes'] = 0
        data['thread_count'] = max(start_thread_count, end_thread_count)
        data['result'] = result
        data['additional_data'] = {
            **results_data,
            'InputFileName': input_file_name,
            'OutputFileName': output_file_name
        }

        record = IndalekoRecordDataModel(
            SourceIdentifier = source,
            Timestamp = end_time,
            Attributes = data,
            Data = encode_binary_data(json.dumps(data))
        )


        return IndalekoPerformanceDataCollector(
            Record = record,
            SourceIdentifier = source,
            MachineConfigurationId = MachineIdentifier,
            StartTimestamp = start_time,
            EndTimestamp = end_time,
            ElapsedTime = data['elapsed_time'],
            UserCPUTime = data['user_cpu_time'],
            SystemCPUTime = data['system_cpu_time'],
            InputSize = data['input_file_size'],
            OutputSize = data['output_file_size'],
            PeakMemoryUsage = data['peak_memory_usage'],
            IOReadBytes = data['io_read_bytes'],
            IOWriteBytes = data['io_write_bytes'],
            ThreadCount = data['thread_count'],
            AdditionalData = data['additional_data']
        )

    @staticmethod
    def deserialize(data: dict) -> 'IndalekoPerformanceDataCollector':
        '''Deserialize a dictionary to an object.'''
        return IndalekoPerformanceDataCollector(**data)

    def serialize(self) -> dict:
        '''Serialize the object to a dictionary.'''
        doc = json.loads(self.perf_data.model_dump_json())
        doc['_key'] = str(uuid.uuid4())
        return doc

    test_data = {
        'Record' : {
            'SourceIdentifier': {
                'Identifier': '1697394b-0f8f-44b4-91c0-a0fbd9d77feb',
                'Version': '1.0'
            },
            'Timestamp': datetime.now(timezone.utc),
            'Attributes': {
            },
            'Data': encode_binary_data(b'')
        },
        'MachineConfigurationId' : 'f7a439ec-c2d0-4844-a043-d8ac24d9ac0b',
        'StartTimestamp' : '2024-12-15 15:55:35.786212+00:00',
        'EndTimestamp' : '2024-12-15 15:56:06.200578+00:00',
        'UserCPUTime' : 0.02,
        'SystemCPUTime' : 0.221,
        'PeakMemoryUsage' : 3152 * 1024,
        'IOReadBytes' : int(4.2 * 1024 * 1024),
        'IOWriteBytes' : int(3.9 * 1024),
        'ThreadCount' : 1,
    }


def main():
    """Test code for the IndalekoPerformanceData class."""
    ic('IndalekoPerformanceData test code')
    perf_data : IndalekoPerformanceDataCollector = IndalekoPerformanceDataCollector(
        Record = {
            'SourceIdentifier': {
                'Identifier': '1697394b-0f8f-44b4-91c0-a0fbd9d77feb',
                'Version': '1.0'
            },
            'Timestamp': datetime.now(timezone.utc),
            'Attributes': {
            },
            'Data': encode_binary_data(b'')
        },
        MachineConfigurationId = 'f7a439ec-c2d0-4844-a043-d8ac24d9ac0b',
        StartTimestamp = '2024-12-15 15:55:35.786212+00:00',
        EndTimestamp = '2024-12-15 15:56:06.200578+00:00',
        UserCPUTime = 0.02,
        SystemCPUTime = 0.221,
        PeakMemoryUsage = 3152 * 1024,
        IOReadBytes = int(4.2 * 1024 * 1024),
        IOWriteBytes = int(3.9 * 1024),
        ThreadCount = 1,
    )
    ic(perf_data.serialize())

if __name__ == "__main__":
    main()
