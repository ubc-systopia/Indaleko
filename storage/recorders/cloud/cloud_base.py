"""
This is the generic class for an Indaleko Cloud Storage Recorder.

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

import os
from pathlib import Path
import sys

from typing import Union, Callable, Any

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models import IndalekoSourceIdentifierDataModel
from perf.perf_collector import IndalekoPerformanceDataCollector
from perf.perf_recorder import IndalekoPerformanceDataRecorder
from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
from utils.cli.runner import IndalekoCLIRunner
from storage.collectors import BaseStorageCollector
from storage.recorders import BaseStorageRecorder
# pylint: enable=wrong-import-position


class BaseCloudStorageRecorder(BaseStorageRecorder):
    '''This is the base class for all cloud storage recorder in Indaleko.'''

    def __init__(self, **kwargs):
        '''Build a new cloud storage recorder.'''
        if 'args' in kwargs:
            self.args = kwargs['args']
            self.output_type = getattr(self.args, 'output_type', 'file')
        else:
            self.args = None
            self.output_type = 'file'
        super().__init__(**kwargs)
        self.dir_data_by_path = {}
        self.dir_data = []
        self.file_data = []
        self.dirmap = {}
        self.dir_edges = []
        self.collector_data = []

    def find_collector_files(self) -> list:
        '''
        This function is used to find the collector data files for the recorder.
        It is expected to be overridden in a subclass.
        '''
        raise NotImplementedError('This function must be overridden by the derived class')

    @staticmethod
    def get_cloud_storage_recorder() -> 'BaseCloudStorageRecorder':
        '''This function is used to get the cloud storage recorder.'''
        raise NotImplementedError('This function must be overridden by the derived class')

    class cloud_recorder_mixin(BaseStorageRecorder.base_recorder_mixin):
        '''This is the mixin for cloud storage recorders.'''

    @staticmethod
    def local_run(keys: dict[str, str]) -> Union[dict, None]:
        '''Run the recorder'''
        args = keys['args']  # must be there.
        cli = keys['cli']  # must be there.
        config_data = cli.get_config_data()
        debug = hasattr(args, 'debug') and args.debug
        if debug:
            ic(config_data)
        recorder_class = keys['parameters']['RecorderClass']
        # collector_class = keys['parameters']['CollectorClass'] # unused for now
        # recorders have the machine_id so they need to find the
        # matching machine configuration file.
        kwargs = {
            'timestamp': config_data['Timestamp'],
            'input_file': str(Path(args.datadir) / args.inputfile),
            'offline': args.offline,
            'args': args,
        }
        if 'InputFileKeys' in config_data:
            if 'storage' in config_data['InputFileKeys'] and \
                            config_data['InputFileKeys']['storage']:
                kwargs['storage_description'] = config_data['InputFileKeys']['storage']
            if 'userid' in config_data['InputFileKeys'] and \
                    config_data['InputFileKeys']['userid']:
                kwargs['userid'] = config_data['InputFileKeys']['userid']

        def record(recorder: BaseCloudStorageRecorder, **kwargs):
            recorder.record()

        def extract_counters(**kwargs):
            recorder = kwargs.get('recorder')
            if recorder:
                return recorder.get_counts()
            else:
                return {}

        recorder = recorder_class(**kwargs)

        def capture_performance(
            task_func: Callable[..., Any],
            output_file_name: Union[Path, str] = None
        ):
            perf_data = IndalekoPerformanceDataCollector.measure_performance(
                task_func,
                source=IndalekoSourceIdentifierDataModel(
                    Identifier=recorder.get_recorder_service_uuid(),
                    Version=recorder.get_recorder_service_version(),
                    Description=recorder.get_recorder_service_description()
                ),
                description=recorder.get_recorder_service_description(),
                MachineIdentifier=None,
                process_results_func=extract_counters,
                input_file_name=str(Path(args.datadir) / args.inputfile),
                output_file_name=output_file_name,
                recorder=recorder
            )
            if args.performance_db or args.performance_file:
                perf_recorder = IndalekoPerformanceDataRecorder()
                if args.performance_file:
                    perf_file = str(Path(args.datadir) / config_data['PerformanceDataFile'])
                    perf_recorder.add_data_to_file(perf_file, perf_data)
                    if (debug):
                        ic('Performance data written to ', config_data['PerformanceDataFile'])
                if args.performance_db:
                    perf_recorder.add_data_to_db(perf_data)
                    if (debug):
                        ic('Performance data written to the database')

        # Step 1: normalize the data and gather the performance.
        if args.debug:
            ic('Normalizing data')
        capture_performance(record)
        # Step 2: record the time to save the object data.
        if args.debug:
            ic('Writing object data to file')
        capture_performance(recorder.write_object_data_to_file, args.outputfile)
        # Step 3: record the time to save the edge data.
        if args.debug:
            ic('Writing edge data to file')
        capture_performance(recorder.write_edge_data_to_file, recorder.output_edge_file)

        if args.arangoimport and args.bulk:
            ic('Warning: both arangoimport and bulk upload specified.  Using arangoimport ONLY.')
        if args.arangoimport:
            # Step 4: upload the data to the database using the arangoimport utility
            if args.debug:
                ic('Using arangoimport to load object data')
            capture_performance(recorder.arangoimport_object_data)
            if args.debug:
                ic('Using arangoimport to load relationship data')
            capture_performance(recorder.arangoimport_relationship_data)
        elif args.bulk:
            # Step 5: upload the data to the database using the bulk uploader
            if args.debug:
                ic('Using bulk uploader to load object data')
            capture_performance(recorder.bulk_upload_object_data)
            if args.debug:
                ic('Using bulk uploader to load relationship data')
            capture_performance(recorder.bulk_upload_relationship_data)

    @staticmethod
    def cloud_recorder_runner(
            collector_class: BaseStorageCollector,
            recorder_class: BaseStorageRecorder) -> None:
        '''This is the CLI handler for cloud storage recorders.'''
        runner = IndalekoCLIRunner(
            cli_data=IndalekoBaseCliDataModel(
                Service=recorder_class.get_recorder_service_name(),
                InputFileKeys={
                    'plt': collector_class.get_collector_platform_name(),
                    'svc': collector_class.get_collector_service_name(),
                },
            ),
            handler_mixin=recorder_class.cloud_recorder_mixin,
            features=IndalekoBaseCLI.cli_features(
                machine_config=False,
            ),
            Run=BaseCloudStorageRecorder.local_run,
            RunParameters={
                'CollectorClass': collector_class,
                'RecorderClass': recorder_class,
            }
        )
        runner.run()
