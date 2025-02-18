"""
This module defines a baseline common model for command line utilities
in Indaleko.

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
import logging
import os
import platform
import psutil
import sys

from datetime import datetime, timezone
from typing import List, Type, TypeVar, Union, Tuple, Annotated
from pathlib import Path
from icecream import ic

from pydantic import BaseModel, Field, AwareDatetime, field_validator, FieldValidationInfo, BeforeValidator, ConfigDict

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

T = TypeVar('T', bound='IndalekoCommandLineDataModel')

# pylint: disable=wrong-import-position
from utils import IndalekoLogging  # noqa: E402
from utils.misc.directory_management import indaleko_default_config_dir, indaleko_default_data_dir, \
    indaleko_default_log_dir  # noqa: E402
from utils.misc.file_name_management import generate_file_name  # noqa: E402
from db import IndalekoDBConfig  # noqa: E402
# pylint: enable=wrong-import-position


def check_directory(value: str) -> str:
    '''Check the directory to make sure it exists.'''
    ic(f'check_directory called: {value}')
    if not os.path.exists(value):
        raise ValueError(f'Directory {value} does not exist.')
    return value


def av(value: str) -> str:
    '''After validation for the directory.'''
    ic('av called')
    return value


class IndalekoCommandLineDataModel(BaseModel):
    '''
    This forms a base class for command line operations
    in Indaleko.
    '''

    model_config = ConfigDict(validate_default=True, validation_error_cause=True)

    Platform: str = platform.system().casefold()

    CommandLine: list = psutil.Process().cmdline()

    Timestamp: AwareDatetime = datetime.now(timezone.utc)

    ConfigurationDir: Annotated[str, BeforeValidator(check_directory)] = indaleko_default_config_dir

    DBConfigurationFileChoices: List[str] = Field(default=[])

    DBConfigurationFile: str = IndalekoDBConfig.default_db_config_file

    MachineConfigurationFile: Union[str, None] = None

    MachineConfigurationFileChoices: List[str] = []

    DataDir: str = indaleko_default_data_dir

    LogDir: str = indaleko_default_log_dir

    LoggingLevels: List[str] = IndalekoLogging.get_logging_levels()

    LogLevel: Union[int, None] = logging.DEBUG

    InputFileChoices: List[str] = []

    InputFile: Union[str, None] = None

    OutputFile: Union[str, None] = None

    def __init__(self, *args, **kwargs):
        '''Initialize the object.'''
        super().__init__(*args, **kwargs)

    @field_validator('Timestamp', mode='before')
    @classmethod
    def validate_timestamp(cls: Type[T], value: AwareDatetime, info: FieldValidationInfo) -> AwareDatetime:
        '''Validate the timestamp.'''
        if value is None:
            value = datetime.now(timezone.utc)
        if isinstance(value, AwareDatetime) or isinstance(value, datetime):
            return value
        ts = datetime.fromisoformat(value)
        if not isinstance(ts, AwareDatetime):
            raise ValueError(f'Timestamp {ts} is not an AwareDatetime.')
        return ts

    @field_validator('ConfigurationDir', 'DataDir', 'LogDir', mode='before')
    @classmethod
    def validate_dir(cls: Type[T], value: str, info: FieldValidationInfo) -> str:
        '''Validate the directory.'''
        if not os.path.exists(value):
            raise ValueError(f'Directory {value} does not exist.')
        return value

    @field_validator('DBConfigurationFile', 'MachineConfigurationFile', 'InputFile', mode='before')
    @classmethod
    def validate_configuration_file(cls: Type[T], value: str, info: FieldValidationInfo) -> str:
        '''Validate the database configuration file.'''
        ic(value)
        ic(info)
        if value is None or os.path.exists(value):
            return value
        raise ValueError(f'Database configuration file {value} does not exist. {info}')

    @staticmethod
    def find_relevant_files(
        directory: str,
        substrings: List[str] = ['indaleko', 'jsonl']
    ) -> List[str]:
        '''Find files in the directory with the given suffix.'''
        directory_path = Path(directory)
        return [
            str(file_path) for file_path in directory_path.iterdir()
            if all(substring in file_path.name for substring in substrings)
        ]

    @staticmethod
    def default_output_file(**kwargs) -> str:
        '''Generate a default output file name.'''
        assert 'prefix' in kwargs, 'prefix is missing.'
        assert 'service' in kwargs, 'service is missing.'
        assert 'suffix' in kwargs, 'suffix is missing.'
        return generate_file_name(**kwargs)

    @staticmethod
    def parse_command_line() -> Tuple[argparse.Namespace, argparse.ArgumentParser, 'IndalekoCommandLineDataModel']:
        '''Parse the command line arguments.'''
        ic(IndalekoLogging.get_logging_levels())
        cmd_data = IndalekoCommandLineDataModel()
        ic(cmd_data)
        pre_parser = argparse.ArgumentParser(add_help=False)
        # First, let's process the directories
        pre_parser.add_argument('--platform',
                                help='The platform of the system providing the data', default=cmd_data.Platform)
        pre_parser.add_argument(
            '--configdir',
            help='Path to the config directory',
            default=cmd_data.ConfigurationDir
        )
        pre_parser.add_argument(
            '--datadir',
            help='Path to the data directory',
            default=cmd_data.DataDir
        )
        pre_parser.add_argument(
            '--logdir',
            help='Path to the log directory',
            default=cmd_data.LogDir
        )
        pre_args, _ = pre_parser.parse_known_args()
        data = cmd_data.model_dump()
        if pre_args.platform != cmd_data.Platform:
            data['Platform'] = pre_args.platform
        if pre_args.configdir != cmd_data.ConfigurationDir:
            assert os.path.exists(pre_args.configdir), f'Configuration directory {pre_args.configdir} does not exist.'
            data['ConfigurationDir'] = pre_args.configdir
        if pre_args.datadir != cmd_data.DataDir:
            assert os.path.exists(pre_args.datadir), f'Data directory {pre_args.datadir} does not exist.'
            data['DataDir'] = pre_args.datadir
        if pre_args.logdir != cmd_data.LogDir:
            assert os.path.exists(pre_args.logdir), f'Configuration directory {pre_args.logdir} does not exist.'
            data['LogDir'] = pre_args.logdir
        # now let's find the options for the configuration files
        data['DBConfigurationFileChoices'] = \
            IndalekoCommandLineDataModel.find_relevant_files(
                data['ConfigurationDir'],
                ['indaleko', 'db', 'config', 'ini']
            )
        data['MachineConfigurationFileChoices'] = \
            IndalekoCommandLineDataModel.find_relevant_files(
                data['ConfigurationDir'],
                [data['Platform'], 'hardware', 'info', 'json']
            )
        data['InputFileChoices'] = \
            IndalekoCommandLineDataModel.find_relevant_files(
                data['DataDir'],
                ['indaleko', str(platform.system()), 'jsonl']
            )
        data['InputFileName'] = data['InputFileChoices'][-1]
        data['OutputFile'] = IndalekoCommandLineDataModel.default_output_file(
            prefix='indaleko',
            service='cmd',
            suffix='jsonl',
            timestamp=str(data['Timestamp'])
        )
        pre_parser = argparse.ArgumentParser(add_help=False, parents=[pre_parser])
        # now we can add the input file and output file names
        pre_parser.add_argument('--inputfile',
                                help='The input file to process',
                                choices=data['InputFileChoices'],
                                default=data['InputFileName'])
        pre_parser.add_argument('--outputfile',
                                help='The output file to write',
                                default=data['OutputFile'])
        pre_args, _ = pre_parser.parse_known_args()
        data['InputFileName'] = pre_args.inputfile
        data['OutputFile'] = pre_args.outputfile
        ic(data)
        cmd_data = IndalekoCommandLineDataModel(**data)
        return pre_args, pre_parser, cmd_data


def main():
    '''This allows testing the data model.'''
    IndalekoCommandLineDataModel.parse_command_line()


if __name__ == '__main__':
    main()
