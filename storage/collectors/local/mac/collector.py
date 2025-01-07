'''
This module collects local file system metadata from the Mac local file
system.

Indaleko Mac Local Collector
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
import datetime
import inspect
import os
import logging
import platform
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
from platforms.mac.machine_config import IndalekoMacOSMachineConfig
from storage.collectors.base import BaseStorageCollector
from storage.collectors.data_model import IndalekoStorageCollectorDataModel
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
from utils.cli.base import IndalekoBaseCLI
from utils.cli.runner import IndalekoCLIRunner
from utils.i_logging import IndalekoLogging
from utils.misc.directory_management import indaleko_default_config_dir, indaleko_default_data_dir, indaleko_default_log_dir
from utils.misc.file_name_management import find_candidate_files
# pylint: enable=wrong-import-position


class IndalekoMacLocalCollector(BaseStorageCollector):
    '''
    This is the class that indexes Mac local file systems.
    '''
    mac_platform = 'Mac'
    mac_local_collector_name = 'fs_collector'

    indaleko_mac_local_collector_uuid = '14d6c989-0d1e-4ccc-8aea-a75688a6bb5f'
    indaleko_mac_local_collector_service_name = 'Mac Local Storage Collector'
    indaleko_mac_local_collector_service_description = 'This service collects metadata from the local filesystems of a Mac machine.'
    indaleko_mac_local_collector_service_version = '1.0'
    indaleko_mac_local_collector_service_type = IndalekoServiceManager.service_type_storage_collector

    indaleko_mac_local_collector_service ={
        'service_name' : indaleko_mac_local_collector_service_name,
        'service_description' : indaleko_mac_local_collector_service_description,
        'service_version' : indaleko_mac_local_collector_service_version,
        'service_type' : indaleko_mac_local_collector_service_type,
        'service_identifier' : indaleko_mac_local_collector_uuid,
    }

    mac_local_collector_data = IndalekoStorageCollectorDataModel(
        CollectorPlatformName = mac_platform,
        CollectorServiceName = indaleko_mac_local_collector_service_name,
        CollectorServiceDescription = indaleko_mac_local_collector_service_description,
        CollectorServiceUUID = uuid.UUID(indaleko_mac_local_collector_uuid),
        CollectorServiceVersion = indaleko_mac_local_collector_service_version,
    )

    def __init__(self, **kwargs):
        assert 'machine_config' in kwargs, 'machine_config must be specified'
        self.machine_config = kwargs['machine_config']
        if 'machine_id' not in kwargs:
            kwargs['machine_id'] = self.machine_config.machine_id
        super().__init__(**kwargs,
                         platform=IndalekoMacLocalCollector.mac_platform,
                         collector_name=IndalekoMacLocalCollector.mac_local_collector_name,
                         **IndalekoMacLocalCollector.indaleko_mac_local_collector_service
        )

        self.dir_count=0
        self.file_count=0

    def generate_mac_collector_file_name(self, **kwargs) -> str:
        if 'platform' not in kwargs:
            kwargs['platform'] = IndalekoMacLocalCollector.mac_platform
        if 'collector_name' not in kwargs:
            kwargs['collector_name'] = IndalekoMacLocalCollector.mac_local_collector_name
        if 'machine_id' not in kwargs:
            kwargs['machine_id'] = uuid.UUID(self.machine_config.machine_id).hex
        return BaseStorageCollector.generate_collector_file_name(**kwargs)


    def build_stat_dict(self, name: str, root : str, last_uri = None) -> tuple:
        '''
        Given a file name and a root directory, this will return a dict
        constructed from the file system metadata ("stat") for that file.
        Returns: dict_stat, last_uri
        '''

        file_path = os.path.join(root, name)

        if last_uri is None:
            last_uri = file_path
        try:
            stat_data = os.stat(file_path)
        except Exception as e: # pylint: disable=broad-except
            # at least for now, we just skip errors
            logging.warning('Unable to stat %s : %s', file_path, e)
            self.error_count += 1
            return None

        stat_dict = {key : getattr(stat_data, key) \
                    for key in dir(stat_data) if key.startswith('st_')}
        stat_dict['Name'] = name
        stat_dict['Path'] = root
        stat_dict['URI'] = os.path.join(root, name)
        stat_dict['Collector'] = str(self.service_identifier)

        return (stat_dict, last_uri)


    def collect(self) -> list:
        data = []
        last_uri = None

        # indexing path itself has to have a root node
        root_entry= self.build_stat_dict(os.path.basename(self.path), os.path.dirname(self.path), last_uri)
        if root_entry:
            data.append(root_entry[0])
            last_uri=root_entry[1]

        for root, dirs, files in os.walk(self.path):
            for name in dirs + files:
                entry = self.build_stat_dict(name, root, last_uri)
                if name in dirs:
                    self.dir_count += 1
                else:
                    self.file_count += 1
                if entry is not None:
                    data.append(entry[0])
                    last_uri = entry[1]
        return data

class local_collector_mixin(IndalekoBaseCLI.default_handler_mixin):
    @staticmethod
    def load_machine_config(keys: dict[str, str]) -> IndalekoMacOSMachineConfig:
        '''Load the machine configuration'''
        if keys.get('debug'):
            ic(f'local_collector_mixin.load_machine_config: {keys}')
        if 'machine_config_file' not in keys:
            raise ValueError(f'{inspect.currentframe().f_code.co_name}: machine_config_file must be specified')
        offline = keys.get('offline', False)
        return IndalekoMacOSMachineConfig.load_config_from_file(
            config_file=str(keys['machine_config_file']),
            offline=offline)

    @staticmethod
    def find_machine_config_files(
            config_dir : Union[str, Path],
            platform : str,
            debug : bool = False
        ) -> Union[list[str], None]:
        '''Find the machine configuration files'''
        if debug:
            ic(f'find_machine_config_files: config_dir = {config_dir}')
            ic(f'find_machine_config_files:   platform = {platform}')
        if not Path(config_dir).exists():
            return None
        if platform is None:
            return []
        return [
            fname for fname, _ in find_candidate_files([platform, '-hardware-info'], str(config_dir))
            if fname.endswith('.json')
        ]

    @staticmethod
    def extract_filename_metadata(file_name):
        # the mac uses non-standard naming for machine config files, so we have to handle that here.
        if not file_name.startswith(IndalekoMacOSMachineConfig.macos_machine_config_file_prefix):
            return IndalekoBaseCLI.default_handler_mixin.extract_filename_metadata(file_name)
        # macos-hardware-info-f6ff7c7f-b4d7-484f-9b58-1ad2820a8d85-2024-12-04T00-44-25.583891Z.json
        assert file_name.endswith('.json') # if not, generalize this
        prefix_length = len(IndalekoMacOSMachineConfig.macos_machine_config_file_prefix)
        machine_id = uuid.UUID(file_name[prefix_length+1:prefix_length+37]).hex
        timestamp = file_name[prefix_length+38:-5]
        keys = {
            'platform' : platform.system(),
            'service' : 'macos_machine_config',
            'machine' : machine_id,
            'timestamp' : timestamp,
            'suffix' : '.json',
        }
        return keys

    @staticmethod
    def get_collector(**kwargs) -> BaseStorageCollector:
        '''Return the collector object to use.'''
        return IndalekoMacLocalCollector(**kwargs)


@staticmethod
def local_run(keys: dict[str, str]) -> Union[dict, None]:
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
        def collect(collector : IndalekoMacLocalCollector):
            data = collector.collect()
            output_file = Path(args.datadir) / args.outputfile
            collector.write_data_to_file(data, str(output_file))
        def extract_counters(**kwargs):
            collector = kwargs.get('collector')
            if collector:
                return ic(collector.get_counts())
            else:
                return {}
        # collector = IndalekoMacLocalCollector(**kwargs)
        collector = local_collector_mixin.get_collector(**kwargs)
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
def add_mac_local_parameters(parser : argparse.ArgumentParser) -> argparse.ArgumentParser:
    '''Add the paramters for the local Mac collector.'''
    default_path = os.path.expanduser('~')
    if default_path == '~':
        default_path = os.path.abspath(os.sep)
    parser.add_argument('--path',
                        help=f'Path to the directory from which to collect metadata {default_path}',
                        type=str,
                        default=default_path)
    return parser


def main():
    '''This is the CLI handler for the Mac local storage collector.'''

    runner = IndalekoCLIRunner(
        cli_data=IndalekoBaseCliDataModel(
            Service=IndalekoMacLocalCollector.mac_local_collector_name,
            Platform='macos'
        ),
        handler_mixin=local_collector_mixin,
        features=IndalekoBaseCLI.cli_features(input=False),
        additional_parameters=add_mac_local_parameters,
        Run=local_run,
    )
    runner.run()

if __name__ == '__main__':
    main()
