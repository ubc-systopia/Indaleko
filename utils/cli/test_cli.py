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
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from uuid import UUID

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
from utils.misc.file_name_management import find_candidate_files, generate_file_name, extract_keys_from_file_name
from utils import IndalekoLogging
# pylint: enable=wrong-import-position

class IndalekoBaseCLI:
    """Base class for handling main function logic in collectors and recorders"""

    class cli_features:
        '''This class provides a set of features requested for the CLI'''
        debug = True
        db_config = True
        machine_config = True
        configdir = db_config or machine_config
        input = True
        output = True
        datadir = input or output
        logging = True
        performance = True
        platform = True

        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                if hasattr(self, key):
                    assert isinstance(value, bool), f'Value must be a boolean: {key, value}'
                    setattr(self, key, value)
                else:
                    raise AttributeError(f'Unknown attribute: {key}')

    def __init__(self,
                 cli_data : IndalekoBaseCliDataModel = IndalekoBaseCliDataModel(),
                 handler_mixin : Union[IndalekoHandlermixin, None] = None,
                 cli_features : Union['IndalekoBaseCLI.cli_features', None] = None) -> None:
        """
            Initialize the main handler with specific service and config classes

            Args:
                service_class: Type of the service (BaseStorageCollector or BaseStorageRecorder subclass)
                machine_config_class: Type of machine configuration (IndalekoMachineConfig subclass)
        """
        self.features = cli_features
        if not self.features:
            self.features = IndalekoBaseCLI.cli_features() # default features
        self.pre_parser = argparse.ArgumentParser(add_help=False)
        self.config_data = json.loads(cli_data.model_dump_json())
        ic(self.config_data)
        self.handler_mixin = handler_mixin
        if not self.handler_mixin:
            self.handler_mixin = IndalekoBaseCLI.default_handler_mixin
        for feature in dir(self.cli_features):
            if feature.startswith('__'):
                continue
            setup_func_name = f'setup_{feature}_parser'
            ic(feature, setup_func_name)
            setup_func = getattr(self, setup_func_name, None)
            ic(setup_func)
            if not setup_func:
                ic(f'Unknown feature: {feature}')
                continue
            setup_func()
        self.args = None

    def get_args(self) -> argparse.Namespace:
        '''This method is used to get the arguments'''
        if not self.args:
            parser = argparse.ArgumentParser(parents=[self.pre_parser], add_help=True)
            self.args = parser.parse_args()
        return self.args

    def setup_debug_parser(self) -> 'IndalekoBaseCLI':
        '''This method is used to set up the debug parser'''
        pre_args, _ = self.pre_parser.parse_known_args()
        if hasattr(pre_args, 'debug'): # only process it once
            return
        if not hasattr(pre_args, 'debug'):
            self.pre_parser.add_argument('--debug',
                                default=False,
                                action='store_true',
                                help='Debug mode (default=False)')
        return self

    def setup_configdir_parser(self) -> 'IndalekoBaseCLI':
        '''This method is used to set up the config directory parser'''
        pre_args, _ = self.pre_parser.parse_known_args()
        if hasattr(pre_args, 'configdir'): # only process it once
            return
        if not hasattr(pre_args, 'configdir'):
            self.pre_parser.add_argument('--configdir',
                                default=self.config_data['ConfigDirectory'],
                                help=f'Path to the config directory (default={self.config_data["ConfigDirectory"]})')
        return self

    def setup_datadir_parser(self) -> 'IndalekoBaseCLI':
        '''This method is used to set up the data directory parser'''
        pre_args, _ = self.pre_parser.parse_known_args()
        if hasattr(pre_args, 'datadir'): # only process it once
            return
        if not hasattr(pre_args, 'datadir'):
            self.pre_parser.add_argument('--datadir',
                                default=self.config_data['DataDirectory'],
                                help=f'Path to the data directory (default={self.config_data["DataDirectory"]})')
        return self

    def setup_logging_parser(self) -> 'IndalekoBaseCLI':
        '''This method is used to set up the logging parser'''
        pre_args, _ = self.pre_parser.parse_known_args()
        if not hasattr(pre_args, 'logdir'):
            self.pre_parser.add_argument('--logdir',
                                default=self.config_data['LogDirectory'],
                                help=f'Path to the log directory (default={self.config_data["LogDirectory"]})')
            self.pre_parser.add_argument('--loglevel',
                                type=int,
                                default=self.config_data['LogLevel'],
                                choices=IndalekoLogging.get_logging_levels(),
                                help=f'Logging level to use (default={IndalekoLogging.map_logging_level_to_type(self.config_data["LogLevel"])})')
        return self

    def setup_db_config_parser(self) -> 'IndalekoBaseCLI':
        '''This method is used to set up the database configuration parser'''
        pre_args, _ = self.pre_parser.parse_known_args()
        if hasattr(pre_args, 'db_config'): # only process it once
            return
        if not hasattr(pre_args, 'db_config'):
            self.config_data['DBConfigChoices'] = self.handler_mixin.find_db_config_files(self.config_data['ConfigDirectory'])
            default_db_config = self.handler_mixin.get_default_file(
                self.config_data['ConfigDirectory'],
                self.config_data['DBConfigChoices']
            )
            self.pre_parser.add_argument('--db_config',
                                    choices=self.config_data['DBConfigChoices'],
                                    default=default_db_config,
                                    help='Database configuration to use')
            self.pre_parser.add_argument('--offline',
                                    default=self.config_data['Offline'],
                                    action='store_true',
                                    help='Offline mode (default=False)')
            return self

    def setup_machine_config_parser(self) -> 'IndalekoBaseCLI':
        '''This method is used to set up the machine configuration parser'''
        pre_args, _ = self.pre_parser.parse_known_args()
        if hasattr(pre_args, 'machine_config'):
            return
        if not hasattr(pre_args, 'platform'):
            self.setup_platform_parser() # ordering dependency.
            pre_args, _ = self.pre_parser.parse_known_args()
        self.config_data['MachineConfigChoices'] = self.handler_mixin.find_machine_config_files(self.config_data['ConfigDirectory'], pre_args.platform)
        default_machine_config_file = self.handler_mixin.get_default_file(
            self.config_data['ConfigDirectory'],
            self.config_data['MachineConfigChoices']
        )
        self.pre_parser.add_argument('--machine_config',
                                choices=self.config_data['MachineConfigChoices'],
                                default=default_machine_config_file,
                                help='Machine configuration to use')
        pre_args, _ = self.pre_parser.parse_known_args()
        self.config_data['MachineConfigFile'] = pre_args.machine_config
        self.config_data['MachineConfigFileKeys'] = extract_keys_from_file_name(pre_args.machine_config)
        return self

    def setup_platform_parser(self) -> 'IndalekoBaseCLI':
        '''This method is used to set up the platform parser'''
        pre_args, _ = self.pre_parser.parse_known_args()
        if hasattr(pre_args, 'platform'): # only process it once
            return # already added
        self.pre_parser.add_argument('--platform',
                                default=self.config_data['Platform'],
                                help=f'Platform to use (default={self.config_data["Platform"]})')
        pre_args, _ = self.pre_parser.parse_known_args()
        self.config_data['Platform'] = pre_args.platform
        return self

    def setup_output_parser(self) -> 'IndalekoBaseCLI':
        '''This method is used to set up the output parser'''
        if not self.config_data.get('Service'):
            return # there can be no output file without a service name
        pre_args, _ = self.pre_parser.parse_known_args()
        if hasattr(pre_args, 'outputfile'): # only process it once
            return
        output_file = self.handler_mixin.generate_output_file_name(self.config_data)
        self.pre_parser.add_argument('--outputfile',
                        default=output_file,
                        help=f'Output file to use (default = {output_file})')
        pre_args, _ = self.pre_parser.parse_known_args()
        self.config_data['OutputFile'] = pre_args.outputfile
        return self

    def setup_performance_parser(self) -> 'IndalekoBaseCLI':
        '''This method is used to set up the performance parser'''
        if not self.config_data.get('Service'):
            return # there can be no perf data without a service name
        self.pre_parser.add_argument('--performance_file',
                            default=False,
                            action='store_true',
                            help='Record performance data to a file (default=False)')
        self.pre_parser.add_argument('--performance_db',
                            default=False,
                            action='store_true',
                            help='Record performance data to the database (default=False)')
        pre_args, _ = self.pre_parser.parse_known_args()
        if pre_args.performance_file:
            self.config_data['PerformanceFile'] = self.handler_mixin.generate_perf_file_name(self.config_data)
        if pre_args.performance_db:
            self.config_data['PerformanceDB'] = True
        return self

    def setup_input_parser(self) -> 'IndalekoBaseCLI':
        '''This method is used to set up the input parser'''
        pre_args, _ = self.pre_parser.parse_known_args()
        if hasattr(pre_args, 'inputfile'): # only process it once
            return
        self.config_data['InputFilePrefix'] = IndalekoConstants.default_prefix
        self.config_data['InputFileSuffix'] = 'jsonl'
        input_file_keys = self.config_data['InputFileKeys']
        if self.config_data['InputFileKeys']:
            if 'prefix' in input_file_keys:
                self.config_data['InputFilePrefix'] = input_file_keys['prefix']
                del input_file_keys['prefix']
            if 'suffix' in input_file_keys:
                self.config_data['InputFileSuffix'] = input_file_keys['suffix']
                del input_file_keys['suffix']
        if not input_file_keys:
            input_file_keys = {}
            if 'Platform' in self.config_data:
                input_file_keys = {'plt': self.config_data['Platform'] }
            ic(self.config_data)
            if 'MachineConfigFileKeys' in self.config_data and 'machine' in self.config_data['MachineConfigFileKeys']:
                input_file_keys['machine'] = self.config_data['MachineConfigFileKeys']['machine']
            if 'ts' not in input_file_keys: # this logic only works for files with timestamps
                input_file_keys['ts'] = ''
        self.config_data['InputFileChoices'] = self.handler_mixin.find_data_files(
            self.config_data['DataDirectory'],
            input_file_keys,
            self.config_data['InputFilePrefix'],
            self.config_data['InputFileSuffix']
        )
        if self.config_data['InputFileChoices']:
            self.config_data['InputFile'] = self.handler_mixin.get_default_file(
                self.config_data['DataDirectory'],
                self.config_data['InputFileChoices']
            )
            self.pre_parser.add_argument('--inputfile',
                                    choices=self.config_data['InputFileChoices'],
                                    default=self.config_data['InputFile'],
                                    help='Input file to use')
        pre_args, _ = self.pre_parser.parse_known_args()
        self.config_data['InputFileKeys'] = extract_keys_from_file_name(pre_args.inputfile)
        # default timestamp is: 1) from the file, 2) from the config, 3) current time
        ic(input_file_keys)
        timestamp = self.config_data['InputFileKeys'].get('timestamp', None)
        if not timestamp:
            timestamp = datetime.now(timezone.utc).isoformat()
        self.pre_parser.add_argument(
            '--timestamp',
            type=str,
            default=timestamp,
            help='Timestamp to use')
        pre_args, _ = self.pre_parser.parse_known_args()
        try:
            timestamp = datetime.fromisoformat(self.config_data['Timestamp'])
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
        except ValueError:
            ic(f'Invalid timestamp: {pre_args.timestamp}')
            raise ValueError(f'Invalid timestamp: {pre_args.timestamp}')
        self.config_data['Timestamp'] = pre_args.timestamp

    def get_config_data(self : 'IndalekoBaseCLI') -> dict[str, Any]:
        '''This method is used to get the configuration data'''
        return self.config_data


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
            ic(valid_files)
            return str(max(valid_files, key=lambda f: f.stat().st_mtime).name)

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
                return None
            if platform is None:
                return []
            ic(find_candidate_files([platform, '_machine_config'], str(config_dir)))
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
            ic(selection_keys)
            return [
                fname for fname, _ in find_candidate_files(selection_keys, str(data_dir))
                if fname.startswith(prefix) and fname.endswith(suffix) and all([key in fname for key in selection_keys])
            ]

        @staticmethod
        def generate_output_file_name(keys : dict[str,str]) -> str:
            '''This method is used to generate an output file name.  Note
            that it assumes the keys are in the desired format. Don't just
            pass in configuration data.'''
            if 'service' not in keys and 'Service' in keys:
                keys['service'] = keys['Service']
                del keys['Service']
            if 'suffix' not in keys:
                keys['suffix'] = 'jsonl'
            return generate_file_name(**keys)

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
    ic(cli.config_data)
    args = cli.get_args()
    ic(args)
    ic(cli.get_config_data())

if __name__ == '__main__':
    main()
