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
import datetime
import inspect
import logging
import uuid
import os
import sys

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
# from Indaleko import Indaleko
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
import utils.misc.directory_management
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


def old_main():
    '''This is the main handler for the Indaleko Linux Local Collector
    service.'''
    logging_levels = IndalekoLogging.get_logging_levels()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # Step 1: find the machine configuration file & set up logging
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--configdir',
                            help='Path to the config directory',
                            default=utils.misc.directory_management.indaleko_default_config_dir)
    pre_parser.add_argument('--logdir', '-l',
                            help='Path to the log directory',
                            default=utils.misc.directory_management.indaleko_default_log_dir)
    pre_parser.add_argument('--loglevel',
                            type=int,
                            default=logging.DEBUG,
                            choices=logging_levels,
                            help='Logging level to use (lower number = more logging)')
    pre_args, _ = pre_parser.parse_known_args()
    config_files = IndalekoLinuxMachineConfig.find_config_files(pre_args.configdir)
    default_config_file = IndalekoLinuxMachineConfig.get_most_recent_config_file(pre_args.configdir)
    config_file_metadata = extract_keys_from_file_name(default_config_file)
    config_platform = IndalekoLinuxLocalCollector.linux_platform
    if 'platform' in config_file_metadata:
        config_platform = config_file_metadata['platform']
    log_file_name = IndalekoLinuxLocalCollector.generate_linux_collector_file_name(
        platform=config_platform,
        collector_name=IndalekoLinuxLocalCollector.linux_local_collector_name,
        machine_id = config_file_metadata['machine'],
        target_dir=pre_args.logdir,
        timestamp=timestamp,
        suffix='log')
    logging.basicConfig(
        filename=log_file_name,
        level=pre_args.loglevel,
        format='%(asctime)s - %(levelname)s - %(message)s',
        force=True
    )
    # Step 2: figure out the default config file
    pre_parser = argparse.ArgumentParser(add_help=False, parents=[pre_parser])
    pre_parser.add_argument('--config', choices=config_files, default=default_config_file)
    pre_parser.add_argument('--path', help='Path to the directory from which to collect metadata', type=str,
                            default=os.path.expanduser('~'))
    pre_parser.add_argument('--datadir', '-d',
                            help='Path to the data directory',
                            default=utils.misc.directory_management.indaleko_default_data_dir)
    pre_parser.add_argument('--offline',
                        help='Do not require live database access',
                        default=False,
                        action='store_true')
    pre_args, _ = pre_parser.parse_known_args()

    # Step 3: now we can load the machine configuration
    machine_config = IndalekoLinuxMachineConfig.load_config_from_file(config_file=pre_args.config, offline=pre_args.offline)

    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    collector = IndalekoLinuxLocalCollector(
        machine_config=machine_config,
        timestamp=timestamp,
        path=pre_args.path,
        offline=pre_args.offline
    )
    output_file = IndalekoLinuxLocalCollector.generate_linux_collector_file_name(
        platform=config_platform,
        collector_name=IndalekoLinuxLocalCollector.linux_local_collector_name,
        machine_id = config_file_metadata['machine'],
        target_dir=pre_args.datadir,
        suffix='jsonl')
    parser= argparse.ArgumentParser(parents=[pre_parser])
    parser.add_argument('--output', '-o',
                        help='name to assign to output file',
                        default=output_file)
    parser.add_argument('--performance_file',
                        default=False,
                        action='store_true',
                        help='Record performance data to a file')
    parser.add_argument('--performance_db',
                        default=False,
                        action='store_true',
                        help='Record performance data to the database')
    args = parser.parse_args()
    output_file = args.output
    logging.info('Collecting metadata from %s ' , pre_args.path)
    logging.info('Output file %s ' , output_file)
    perf_file_name = os.path.join(
        args.datadir,
        IndalekoPerformanceDataRecorder().generate_perf_file_name(
            platform=collector.platform,
            service=collector.collector_name,
            machine=uuid.UUID(machine_config.machine_id)
        )
    )
    def extract_counters(**kwargs):
        ic(kwargs)
        collector = kwargs.get('collector')
        if collector:
            return ic(collector.get_counts())
        else:
            return {}
    def collect(collector):
        data = collector.collect()
        collector.write_data_to_file(data, output_file)
    perf_data = IndalekoPerformanceDataCollector.measure_performance(
        collect,
        source=IndalekoSourceIdentifierDataModel(
            Identifier=collector.service_identifier,
            Version = collector.service_version,
            Description=collector.service_description),
        description=collector.service_description,
        MachineIdentifier=uuid.UUID(machine_config.machine_id),
        process_results_func=extract_counters,
        input_file_name=None,
        output_file_name=output_file,
        collector=collector
    )
    if args.performance_db or args.performance_file:
        perf_recorder = IndalekoPerformanceDataRecorder()
        if args.performance_file:
            perf_recorder.add_data_to_file(perf_file_name, perf_data)
            ic('Performance data written to ', perf_file_name)
        if args.performance_db:
            perf_recorder.add_data_to_db(perf_data)
            ic('Performance data written to the database')
    for count_type, count_value in collector.get_counts().items():
        logging.info('%s: %d', count_type, count_value)
    logging.info('Done')

def main():
    '''This is the new CLI based utility for executing local Linux metadata collection.'''
    class linux_local_collector_mixin(IndalekoBaseCLI.default_handler_mixin):
        @staticmethod
        def load_machine_config(keys: dict[str, str]) -> IndalekoLinuxMachineConfig:
            '''Load the machine configuration'''
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
                ic('Performance data written to ', config_data['PerformanceDataFile'])
            if args.performance_db:
                perf_recorder.add_data_to_db(perf_data)
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
    return

    # Sketch out what the runner should do here:
    # 1. Start logging
    # 2. Load the machine configuration
    # 3. Setup performance data collection
    # 4. Run the collector inside the performance collector
    # 5. Save performance data (if requested)
    cli_runner = IndalekoCLIRunner()
    ic(cli_runner)
    return
    # start temp code
    config_files = IndalekoLinuxMachineConfig.find_config_files(pre_args.configdir)
    default_config_file = IndalekoLinuxMachineConfig.get_most_recent_config_file(pre_args.configdir)
    config_file_metadata = extract_keys_from_file_name(default_config_file)
    config_platform = IndalekoLinuxLocalCollector.linux_platform
    if 'platform' in config_file_metadata:
        config_platform = config_file_metadata['platform']
    log_file_name = IndalekoLinuxLocalCollector.generate_linux_collector_file_name(
        platform=config_platform,
        collector_name=IndalekoLinuxLocalCollector.linux_local_collector_name,
        machine_id = config_file_metadata['machine'],
        target_dir=pre_args.logdir,
        timestamp=timestamp,
        suffix='log')
    # end temp code
    logging.basicConfig(
        filename=Path(args.logdir) / args.logfile,
        level=args.loglevel,
        format='%(asctime)s - %(levelname)s - %(message)s',
        force=True
    )
    machine_config_file = str(Path(args.configdir) / args.machine_config)
    output_file = str(Path(args.datadir) / args.outputfile)
    logging.info('Starting %s', IndalekoLinuxLocalCollector.linux_local_collector_name)
    logging.info('Using configuration file %s', machine_config_file)
    logging.info('Output file is %s', output_file)
    # mac

    kwargs = {}
    if hasattr(args, 'machine_config'):
        kwargs['machine_config'] = IndalekoLinuxMachineConfig.load_config_from_file(
            config_file=str(Path(args.configdir) / args.machine_config),
            offline=args.offline)
    kwargs['timestamp'] = args.timestamp
    kwargs['path'] = args.datadir
    kwargs['offline'] = args.offline
    collector = IndalekoLinuxLocalCollector(**kwargs)
    output_file = str(Path(args.datadir) / args.outputfile)
    ic(output_file)
if __name__ == '__main__':
    main()
