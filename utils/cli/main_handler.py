'''
This module provides a base class for common CLI functionality.

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
import sys

from typing import Type, Union, TypeVar
from abc import ABC

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from platforms.machine_config import IndalekoMachineConfig
from storage.recorders.base import BaseStorageRecorder
from storage.collectors.base import BaseStorageCollector
import utils.misc.directory_management
from utils.cli.data_models.data_model import IndalekoBaseCliDataModel
from utils.misc.file_name_management import find_candidate_files
from utils.misc.data_management import encode_binary_data
from utils import IndalekoLogging
from utils.misc.directory_management import indaleko_default_config_dir, indaleko_default_data_dir, indaleko_default_log_dir
from utils.misc.file_name_management import indaleko_file_name_prefix
# pylint: enable=wrong-import-position

class IndalekoMainHandler:
    """Base class for handling main function logic in collectors and recorders"""

    def __init__(self,
                 handler_config : IndalekoBaseCliDataModel = IndalekoBaseCliDataModel(),
                 debug : bool = False
                ) -> None:
        """
            Initialize the main handler with specific service and config classes

            Args:
                service_class: Type of the service (BaseStorageCollector or BaseStorageRecorder subclass)
                machine_config_class: Type of machine configuration (IndalekoMachineConfig subclass)
        """
        self.debug = debug
        ic(handler_config)
        self.handler_config = handler_config
        self.config_data = json.loads(self.handler_config.model_dump_json())
        if self.debug:
            ic(self.config_data)

    def find_machine_config_files(self,
                                  config_dir: str,
                                  prefix : str = indaleko_file_name_prefix,
                                  suffix : str = 'ini',
                                  keywords : list[str] = []) -> list:
        """Find machine configuration files"""
        candidates = [fname for fname, _ in find_candidate_files(keywords, config_dir)]
        if prefix:
            candidates = [fname for fname in candidates if fname.startswith(prefix)]
        if suffix:
            candidates = [fname for fname in candidates if fname.endswith(suffix)]
        return candidates

    def find_data_files(self,
                        data_dir : str,
                        tags= dict[str, str],
                        prefix : str = indaleko_file_name_prefix,
                        suffix : str = 'json'
                        ) -> list:
        '''Find data files with the relevant tags.'''
        tag_list = [f'{key}={value}' for key, value in tags.items()]
        candidates = [fname for fname, _ in find_candidate_files(tag_list, data_dir)]

    def setup_argument_parser(self) -> argparse.ArgumentParser:
        """Create the base argument parser with common arguments"""
        pre_parser = argparse.ArgumentParser(add_help=False)
        pre_parser.add_argument('--configdir',
                          default=self.config_data['ConfigDirectory'],
                          help='Path to the config directory')
        pre_parser.add_argument('--datadir',
                          default=self.config_data['DataDirectory'],
                          help='Path to the data directory')
        pre_parser.add_argument('--logdir',
                          default=self.config_data['LogDirectory'],
                          help='Path to the log directory')
        pre_parser.add_argument('--loglevel',
                          type=int,
                          default=self.config_data['LogLevel'],
                          choices=IndalekoLogging.get_logging_levels(),
                          help='Logging level to use')
        pre_parser.add_argument('--performance_file',
                          default=False,
                          action='store_true',
                          help='Record performance data to a file')
        pre_parser.add_argument('--performance_db',
                          default=False,
                          action='store_true',
                          help='Record performance data to the database')
        pre_args, unknown = pre_parser.parse_known_args()
        if pre_args.configdir != self.config_data['ConfigDirectory']:
            self.config_data['ConfigDirectory'] = pre_args.configdir
        if pre_args.datadir != self.config_data['DataDirectory']:
            self.config_data['DataDirectory'] = pre_args.datadir
        if pre_args.logdir != self.config_data['LogDirectory']:
            self.config_data['LogDirectory'] = pre_args.logdir
        config_candidates = self.find_machine_config_files(pre_args.configdir)
        self.config_data['DBConfigChoices'] = config_candidates
        pre_parser.add_argument('--configfile',
                                choices=config_candidates,
                                default=config_candidates[-1],
                                help='Machine configuration to use')
        pre_parser.add_argument('--platform',
                                default=self.config_data['Platform'],
                                help='Platform to use')
        pre_args, unknown = pre_parser.parse_known_args()
        # Now we know the platform, we can find the potential data file(s)
        if self.debug:
            ic(self.config_data)
            ic(unknown)

        return pre_parser

    def setup_logging(self, args):
        """Configure logging based on arguments"""
        #log_file_name = service.generate_file_name(
        #    target_dir=args.logdir,
        #    suffix='.log'
        #)
        #logging.basicConfig(
        #    filename=log_file_name,
        #    level=args.loglevel,
        #    format='%(asctime)s - %(levelname)s - %(message)s',
        #    force=True
        #)
        #return log_file_name
        return 'foo.log'

    def load_machine_config(self, args):
        """Load machine configuration"""
        config_files = self.machine_config_class.find_config_files(args.configdir)
        if not config_files:
            raise ValueError(f'No config files found in {args.configdir}')
        default_config = self.machine_config_class.get_most_recent_config_file(args.configdir)
        return self.machine_config_class.load_config_from_file(config_file=default_config)

def main():
    '''Test the main handler'''
    handler = IndalekoMainHandler()
    pre_parser = handler.setup_argument_parser()
    pre_args, unknown = pre_parser.parse_known_args()
    ic(pre_args)
    ic(unknown)

if __name__ == '__main__':
    main()
