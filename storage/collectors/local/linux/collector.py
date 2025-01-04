'''
This module handles metadata collection from local Linux file systems.

Indaleko Linux Local Collector
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
import argparse
import inspect
import os
import sys
import uuid

from pathlib import Path
from typing import Union

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models import IndalekoSourceIdentifierDataModel
from db.service_manager import IndalekoServiceManager
from perf.perf_collector import IndalekoPerformanceDataCollector
from perf.perf_recorder import IndalekoPerformanceDataRecorder
from platforms.linux.machine_config import IndalekoLinuxMachineConfig
from storage.collectors.base import BaseStorageCollector
from utils.i_logging import IndalekoLogging
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
from utils.cli.base import IndalekoBaseCLI
from utils.cli.runner import IndalekoCLIRunner
from utils.misc.file_name_management import generate_file_name, extract_keys_from_file_name
# pylint: enable=wrong-import-position



class IndalekoLinuxLocalCollector(BaseStorageCollector):
    '''
    This is the class that collects metadata from Linux local file systems.
    '''
    linux_platform = 'Linux'
    linux_local_collector_name = 'fs_collector'

    indaleko_linux_local_collector_uuid = 'bef019bf-b762-4297-bbe2-bf79a65027ae'
    indaleko_linux_local_collector_service_name = 'Linux Local Collector'
    indaleko_linux_local_collector_service_description = 'This service collects local filesystem metadata of a Linux machine.'
    indaleko_linux_local_collector_service_version = '1.0'
    indaleko_linux_local_collector_service_type = IndalekoServiceManager.service_type_storage_collector

    indaleko_linux_local_collector_service ={
        'service_name' : indaleko_linux_local_collector_service_name,
        'service_description' : indaleko_linux_local_collector_service_description,
        'service_version' : indaleko_linux_local_collector_service_version,
        'service_type' : indaleko_linux_local_collector_service_type,
        'service_identifier' : indaleko_linux_local_collector_uuid,
    }

    def __init__(self, **kwargs):
        assert 'machine_config' in kwargs, 'machine_config must be specified'
        self.machine_config = kwargs['machine_config']
        if 'machine_id' not in kwargs:
            kwargs['machine_id'] = self.machine_config.machine_id
        self.offline = False
        if 'offline' in kwargs:
            self.offline = kwargs['offline']
            del self.offline
        super().__init__(**kwargs,
                         platform=IndalekoLinuxLocalCollector.linux_platform,
                         collector_name=IndalekoLinuxLocalCollector.linux_local_collector_name,
                         **IndalekoLinuxLocalCollector.indaleko_linux_local_collector_service
        )

    @staticmethod
    def generate_linux_collector_file_name(**kwargs) -> str:
        '''Generate a file name for the Linux local collector'''
        if 'platform' not in kwargs:
            kwargs['platform'] = IndalekoLinuxLocalCollector.linux_platform
        if 'collector_name' not in kwargs:
            kwargs['collector_name'] = IndalekoLinuxLocalCollector.linux_local_collector_name
        assert 'machine_id' in kwargs, 'machine_id must be specified'
        return BaseStorageCollector.generate_collector_file_name(**kwargs)

def main():
    '''This is the new CLI based utility for executing local Linux metadata collection.'''
    class linux_local_collector_mixin(IndalekoBaseCLI.default_handler_mixin):
        @staticmethod
        def load_machine_config(keys: dict[str, str]) -> IndalekoLinuxMachineConfig:
            '''Load the machine configuration'''
            debug = keys.get('debug', False)
            if (debug):
                ic(f'linux_local_collector_mixin.load_machine_config: {keys}')
            if 'machine_config_file' not in keys:
                raise ValueError(f'{inspect.currentframe().f_code.co_name}: machine_config_file must be specified')
            offline = keys.get('offline', False)
            return IndalekoLinuxMachineConfig.load_config_from_file(
                config_file=str(keys['machine_config_file']),
                offline=offline)

    @staticmethod
    def linux_local_run(keys: dict[str, str]) -> Union[dict, None]:
        '''Run the collector'''
        args = keys['args'] # must be there.
        cli = keys['cli'] # must be there.
        config_data = cli.get_config_data()
        debug = hasattr(args, 'debug') and args.debug
        if debug:
            ic(config_data)
        kwargs = {
            'machine_config': cli.handler_mixin.load_machine_config(
                {
                    'machine_config_file' : str(Path(args.configdir) / args.machine_config),
                    'offline' : args.offline
                }
            ),
            'timestamp': config_data['Timestamp'],
            'path': args.path,
            'offline': args.offline
        }
        def collect(collector : IndalekoLinuxLocalCollector):
            data = collector.collect()
            output_file = Path(args.datadir) / args.outputfile
            collector.write_data_to_file(data, str(output_file))
        def extract_counters(**kwargs):
            collector = kwargs.get('collector')
            if collector:
                return ic(collector.get_counts())
            else:
                return {}
        collector = IndalekoLinuxLocalCollector(**kwargs)
        perf_data = IndalekoPerformanceDataCollector.measure_performance(
            collect,
            source=IndalekoSourceIdentifierDataModel(
                Identifier=collector.service_identifier,
                Version = collector.service_version,
                Description=collector.service_description),
            description=collector.service_description,
            MachineIdentifier=uuid.UUID(kwargs['machine_config'].machine_id),
            process_results_func=extract_counters,
            input_file_name=None,
            output_file_name=str(Path(args.datadir) / args.outputfile),
            collector=collector
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

    @staticmethod
    def add_linux_local_parameters(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        '''Add the parameters for the local Linux collector'''
        default_path = os.path.expanduser('~')
        if default_path == '~':
            default_path = os.path.abspath(os.sep)
        parser.add_argument('--path',
                            help=f'Path to the directory from which to collect metadata {default_path}',
                            type=str,
                            default=default_path)
        return parser

    runner = IndalekoCLIRunner(
        cli_data=IndalekoBaseCliDataModel(Service=IndalekoLinuxLocalCollector.linux_local_collector_name),
        handler_mixin=linux_local_collector_mixin,
        features=IndalekoBaseCLI.cli_features(input=False),
        additional_parameters=add_linux_local_parameters,
        Run=linux_local_run
    )
    runner.run()

if __name__ == '__main__':
    main()
