'''
This module provides a test cli for exercising the components.

Indaleko Windows Local Recorder
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
import json
import logging
import os
from pathlib import Path
import sys

from typing import Type, Union, TypeVar, Any
from abc import ABC

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from constants import IndalekoConstants
from utils.cli.data_model import IndalekoBaseCliDataModel
from utils.cli.handlermixin import IndalekoHandlermixin
from utils.misc.file_name_management import find_candidate_files, generate_file_name
from utils import IndalekoLogging
from utils.misc.directory_management import indaleko_default_config_dir, indaleko_default_data_dir, indaleko_default_log_dir
# pylint: enable=wrong-import-position

class IndalekoBaseCLI:
    """Base class for handling main function logic in collectors and recorders"""

    def __init__(self,
                 cli_data : IndalekoBaseCliDataModel = IndalekoBaseCliDataModel(),
                 handler_mixin : IndalekoHandlermixin = None) -> None:
        """
            Initialize the main handler with specific service and config classes

            Args:
                service_class: Type of the service (BaseStorageCollector or BaseStorageRecorder subclass)
                machine_config_class: Type of machine configuration (IndalekoMachineConfig subclass)
        """
        self.pre_parser = argparse.ArgumentParser(add_help=False)
        self.config_data = json.loads(cli_data.model_dump_json())
        self.handler_mixin = handler_mixin
        if not self.handler_mixin:
            self.handler_mixin = IndalekoBaseCLI.default_handler_mixin
        # set up the initial parser
        self.setup_baseline_pre_parser()
        self.setup_input_files_parser()

    def setup_baseline_pre_parser(self) -> 'IndalekoBaseCLI':
        '''This method is used to set up the baseline parser'''
        self.pre_parser.add_argument('--configdir',
                          default=self.config_data['ConfigDirectory'],
                          help='Path to the config directory')
        self.pre_parser.add_argument('--datadir',
                          default=self.config_data['DataDirectory'],
                          help='Path to the data directory')
        self.pre_parser.add_argument('--logdir',
                          default=self.config_data['LogDirectory'],
                          help='Path to the log directory')
        self.pre_parser.add_argument('--loglevel',
                          type=int,
                          default=self.config_data['LogLevel'],
                          choices=IndalekoLogging.get_logging_levels(),
                          help='Logging level to use')
        if self.config_data['PerformanceDataFile']:
            self.pre_parser.add_argument('--performance_file',
                            default=False,
                            action='store_true',
                            help='Record performance data to a file')
        if self.config_data['RecordPerformanceInDB']:
            self.pre_parser.add_argument('--performance_db',
                            default=False,
                            action='store_true',
                            help='Record performance data to the database')
        if self.config_data['Platform']:
            self.pre_parser.add_argument('--platform',
                                    default=self.config_data['Platform'],
                                    help='Platform to use')
        if self.config_data['Offline']:
            self.pre_parser.add_argument('--offline',
                                    default=self.config_data['Offline'],
                                    action='store_true',
                                    help='Offline mode')
        return self

    def setup_input_files_parser(self : 'IndalekoBaseCLI') -> 'IndalekoBaseCLI':
        '''This method is used to set up the input files parser'''
        pre_args, _ = self.pre_parser.parse_known_args()
        if pre_args.configdir != self.config_data.get('ConfigDirectory'):
            self.config_data['ConfigDirectory'] = pre_args.configdir
        if pre_args.datadir != self.config_data.get('DataDirectory'):
            self.config_data['DataDirectory'] = pre_args.datadir
        if pre_args.logdir != self.config_data.get('LogDirectory'):
            self.config_data['LogDirectory'] = pre_args.logdir
        self.config_data['DBConfigChoices'] = self.handler_mixin.find_db_config_files(self.config_data['ConfigDirectory'])
        default_db_config = self.handler_mixin.get_default_file(
            self.config_data['ConfigDirectory'],
            self.config_data['DBConfigChoices']
        )
        self.pre_parser.add_argument('--db_config',
                                choices=self.config_data['DBConfigChoices'],
                                default=default_db_config,
                                help='Database configuration to use')
        ic(pre_args.platform)
        ic(self.config_data['ConfigDirectory'])
        self.config_data['MachineConfigChoices'] = self.handler_mixin.find_machine_config_files(self.config_data['ConfigDirectory'], pre_args.platform)
        default_machine_config = self.handler_mixin.get_default_file(
            self.config_data['ConfigDirectory'],
            self.config_data['MachineConfigChoices']
        )
        self.pre_parser.add_argument('--machine_config',
                                choices=self.config_data['MachineConfigChoices'],
                                default=default_machine_config,
                                help='Machine configuration to use')
        return self

    def setup_output_files(self : 'IndalekoBaseCLI') -> 'IndalekoBaseCLI':
        '''This method is used to set up the output files'''
        pre_args, _ = self.pre_parser.parse_known_args()
        cli_data = IndalekoBaseCliDataModel(**self.config_data)
        IndalekoBaseCLI.generate_output_file_name()
        if pre_args.outputfile:
            self.config_data['OutputFile'] = pre_args.outputfile
        else:
            self.config_data['OutputFile'] = self.handler_mixin.generate_output_file_name(self.config_data)
        return self

    class default_handler_mixin(IndalekoHandlermixin):
        '''Default handler mixin for the CLI'''

        @staticmethod
        def get_default_file(data_directory: Union[str, Path], candidates : list[Union[str, Path]]) -> str:
            '''
            This method is used to get the most recently modified file.  Default implementation is to
            return the most recently modified file.
            '''
            if isinstance(data_directory, str):
                data_directory = Path(data_directory)
            if not data_directory.exists():
                raise FileNotFoundError(f'Data directory does not exist: {data_directory}')
            valid_files = [data_directory / fname for fname in candidates if (data_directory / fname).is_file()]
            return str(max(valid_files, key=lambda f: f.stat().st_mtime))

        @staticmethod
        def find_db_config_files(config_dir : Union[str, Path]) -> Union[list[str], None]:
            ic(config_dir)
            if not Path(config_dir).exists():
                return None
            return[
                fname for fname, _ in find_candidate_files(['db'], str(config_dir))
                if fname.startswith(IndalekoConstants.default_prefix) and fname.endswith('.ini')
            ]

        @staticmethod
        def find_machine_config_files(config_dir : Union[str, Path], platform : str) -> Union[list[str], None]:
            ic(config_dir)
            if not Path(config_dir).exists():
                ic(f'{config_dir} does not exist')
                return None
            if platform is None:
                return []
            ic(find_candidate_files([platform, '_machine_config'], str(config_dir)))
            ic('foo')
            return [
                fname for fname, _ in find_candidate_files([platform, '_machine_config'], str(config_dir))
                if fname.endswith('.json')
            ]

        @staticmethod
        def find_data_files(data_dir: Union[str, Path],
                        keys : dict[str,str],
                        prefix : str,
                        suffix : str) -> Union[list[str], None]:
            '''This method is used to find data files'''
            if not Path(data_dir).exists():
                return None
            selection_keys = [f'{key}={value}' for key, value in keys.items()]
            return [
                fname for fname, _ in find_candidate_files(selection_keys, str(data_dir))
                if fname.startswith(prefix) and fname.endswith(suffix)
            ]

        @staticmethod
        def generate_output_file_name(keys : dict[str,str]) -> str:
            '''This method is used to generate an output file name'''
            if 'suffix' not in keys:
                keys['suffix'] = 'jsonl'
            return generate_file_name(keys)

        @staticmethod
        def generate_log_file_name(keys : dict[str,str]) -> str:
            '''This method is used to generate a log file name'''
            if 'suffix' not in keys:
                keys['suffix'] = 'log'
            return generate_file_name(keys)

        @staticmethod
        def generate_perf_file_name(keys: dict[str,str]) -> str:
            '''This method is used to generate a performance file name'''
            if 'svc' in keys:
                keys['svc'] = keys['svc'] +'_perf'
            return generate_file_name(keys)

def main():
    '''Test the main handler'''
    cli = IndalekoBaseCLI()
    # pre_parser = handler.setup_argument_parser()
    # pre_args, unknown = pre_parser.parse_known_args()
    # ic(pre_args)
    ic(cli)

if __name__ == '__main__':
    main()
