"""
This is the generic class for an Indaleko Local Storage Recorder.

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

import argparse
import inspect
import logging
import os
import sys

from typing import Union

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from platforms.machine_config import IndalekoMachineConfig
from utils.decorators import type_check
from storage.recorders import BaseStorageRecorder
# pylint: enable=wrong-import-position

class BaseLocalStorageRecorder(BaseStorageRecorder):
    '''This is the base class for all local storage recorders in Indaleko.'''

    def __init__(self, **kwargs):
        '''This is the constructor for the base local storage recorder.'''
        if 'args' in kwargs:
            self.args = kwargs['args']
            self.output_type = getattr(self.args, 'output_type', 'file')
            kwargs['storage_description'] = getattr(self.args, 'storage')
        else:
            self.args = None
            self.output_type = 'file'
        super().__init__(**kwargs)

    @staticmethod
    def load_machine_config(keys: dict[str, str]) -> IndalekoMachineConfig:
        '''Load the machine configuration'''
        if keys.get('debug'):
            ic(f'local_recorder_mixin.load_machine_config: {keys}')
        if 'machine_config_file' not in keys:
            raise ValueError(f'{inspect.currentframe().f_code.co_name}: machine_config_file must be specified')
        offline = keys.get('offline', False)
        platform_class = keys.get('class', None)
        return platform_class.load_config_from_file(
            config_file=str(keys['machine_config_file']),
            offline=offline)

    @staticmethod
    @type_check
    def get_additional_parameters(pre_parser : argparse.ArgumentParser) -> argparse.ArgumentParser:
        '''This function adds common switches for local storage recorders to a parser.'''
        default_output_type = 'file'
        output_type_choices = [default_output_type]
        output_type_help = 'Output type: file  = write to a file, '
        output_type_choices.append('incremental')
        output_type_help += 'incremental = add new entries, update changed entries in database, '
        output_type_choices.append('bulk')
        output_type_help += 'bulk = write all entries to the database using the bulk uploader interface, '
        output_type_choices.append('docker')
        output_type_help += 'docker = copy to the docker volume'
        output_type_help += f' (default={default_output_type})'
        pre_parser.add_argument('--output_type',
                                choices=output_type_choices,
                                default=default_output_type,
                                help=output_type_help)
        pre_parser.add_argument('--arangoimport',
                                default=False,
                                help='Use arangoimport to load data (default=False)',
                                action='store_true')
        pre_parser.add_argument('--bulk',
                                default=False,
                                help='Use bulk loader to load data (default=False)',
                                action='store_true')
        return pre_parser

    @staticmethod
    def get_local_storage_recorder() -> 'BaseLocalStorageRecorder':
        '''This function should be overridden: it is used to create the appropriate local storage recorder.'''
        raise NotImplementedError('This function must be overridden by the derived class')

    @staticmethod
    def execute_command(command : str) -> None:
        '''Execute a command'''
        result = os.system(command)
        logging.info('Command %s result: %d', command, result)
        print(f'Command {command} result: {result}')
