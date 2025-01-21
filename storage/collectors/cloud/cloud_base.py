"""
This is the generic class for an Indaleko Cloud Storage Collector.

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
from platforms.machine_config import IndalekoMachineConfig
from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
from utils.cli.runner import IndalekoCLIRunner
from utils.decorators import type_check
from storage.collectors import BaseStorageCollector
from storage.recorders import BaseStorageRecorder
# pylint: enable=wrong-import-position

class BaseCloudStorageCollector(BaseStorageCollector):
    '''This is the base class for all cloud storage recorders in Indaleko.'''

    def __init__(self, **kwargs):
        '''This is the constructor for the base cloud storage recorder.'''
        if 'args' in kwargs:
            self.args = kwargs['args']
            self.output_type = getattr(self.args, 'output_type', 'file')
        else:
            self.args = None
            self.output_type = 'file'
        self.requires_machine_config = False
        super().__init__(**kwargs)
        self.cli_handler_mixin = BaseCloudStorageCollector.cloud_collector_mixin

    @staticmethod
    def get_cloud_storage_collector():
        '''This method returns the cloud storage collector.'''
        raise NotImplementedError('This method must be implemented by the subclass.')

    class cloud_collector_mixin(IndalekoBaseCLI.default_handler_mixin):

        @staticmethod
        def get_pre_parser() -> Union[argparse.ArgumentParser, None]:
            '''This method returns the pre-parser for the cloud storage collector.'''
            parser = argparse.ArgumentParser(add_help=False)
            default_path = '/' # root of the cloud storage
            parser.add_argument('--path',
                                type=str,
                                default=default_path,
                                help=f'The path to the cloud storage (default={default_path})')
            return parser

        @staticmethod
        def get_additional_parameters(pre_parser):
            '''This function is used to add additional parameters to the pre-parser.'''
            pre_parser.add_argument('--recurse',
                                    action='store_true',
                                    help='Recurse into subdirectories (default=False) - useful for debugging')

            return pre_parser

    cli_handler_mixin = cloud_collector_mixin

    @staticmethod
    def local_run(keys: dict[str, str]) -> Union[dict, None]:
        '''This function is used to run the cloud storage collector.'''
        args = keys['args'] # must be there
        cli = keys['cli'] # must be there
        config_data = cli.get_config_data()
        debug = hasattr(args, 'debug') and args.debug
        if debug:
            ic(f'cloud_base local_run: {config_data}')
        collector_class = keys['parameters']['CollectorClass']
        kwargs = {
            'timestamp' : config_data['Timestamp'],
            'path' : args.path,
            'recurse' : args.recurse,
            'offline' : args.offline,
        }
        collector = collector_class(**kwargs)
        def collect(collector : BaseCloudStorageCollector) -> None:
            collector.collect()
        def extract_counters(**kwargs) -> None:
            collector = kwargs.get('collector')
            if collector:
                return collector.get_counts()
            else:
                return {}
        def capture_performance(
                task_func : Callable[..., Any],
                output_file_name : Union[Path, str] = None) -> None:
            perf_data = IndalekoPerformanceDataCollector.measure_performance(
                task_func,
                source=IndalekoSourceIdentifierDataModel(
                    Identifier=collector.get_collector_service_identifier(),
                    Version = collector.get_collector_service_version(),
                    Description=collector.get_collector_service_description()
                ),
                description=collector.get_collector_service_description(),
                MachineIdentifier=None,
                process_results_func=extract_counters,
                output_file_name=output_file_name,
                collector=collector,
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
        capture_performance(collect)
        # Step 2: record the time to save the object data.
        assert hasattr(collector, 'data'), 'No data collected'
        assert len(collector.data), 'No data in set'
        if args.debug:
            ic('Writing file system metadata to file')
        capture_performance(collector.write_data_to_file)

    @staticmethod
    def cloud_collector_runner(
        collector_class : BaseStorageCollector,
    ) -> None:
        '''This function is used to run the cloud storage collector.'''
        IndalekoCLIRunner(
            cli_data = IndalekoBaseCliDataModel(
                Service=collector_class.get_collector_service_name(),
            ),
            handler_mixin=collector_class.get_collector_cli_handler_mixin(),
            features=IndalekoBaseCLI.cli_features(
                input=False,
                machine_config=False,
            ),
            Run=BaseCloudStorageCollector.local_run,
            RunParameters={
                'CollectorClass' : collector_class,
            }
        ).run()
