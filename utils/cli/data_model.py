'''
This module handles gathering metadata from Windows local file systems.

Indaleko Windows Local Collector
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
from abc import ABC, abstractmethod
import logging
import os
import platform
import sys
from typing import Optional, List, Dict, Any
from uuid import UUID

from icecream import ic
from pydantic import Field


if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from db import IndalekoDBConfig
from utils.misc.directory_management import indaleko_default_config_dir, indaleko_default_data_dir, indaleko_default_log_dir
from utils.misc.file_name_management import indaleko_file_name_prefix
# pylint: enable=wrong-import-position

class IndalekoBaseCliDataModel(IndalekoBaseModel):
    '''Defines the base data model for the CLI'''
    Platform : str = Field(platform.system(), title='Platform', description='The platform for the machine.')
    MachineId : UUID = Field(UUID(int=0), title='MachineId', description='The unique identifier for the machine.')
    StorageId : Optional[UUID] = None
    ConfigDirectory : str = indaleko_default_config_dir
    DataDirectory : str = indaleko_default_data_dir
    LogDirectory : str = indaleko_default_log_dir
    InputFileChoices : Optional[List[str]] = []
    InputFile : Optional[str] = None
    InputFileKeys : Optional[Dict[str, str]] = {}
    OutputFile : Optional[str] = None
    LogFile : Optional[str] = None
    LogLevel : int = logging.DEBUG
    Offline : bool = False
    DBConfigChoices : Optional[List[str]] = []
    DBConfigFile : str = IndalekoDBConfig.default_db_config_file
    FilePrefix : str = indaleko_file_name_prefix
    FileSuffix : str = ''
    AdditionalOptions : Dict[str, Any] = Field({} , title='AdditionalOptions', description='Additional options for the CLI.')

    class Config:
        '''Configuration for the base CLI data model'''
        json_schema_extra = {
            'example': {
                'Platform': 'Windows',
                'MachineId': '3d49ea9c-e527-4e29-99b5-9715bbde1148',
                'StorageId': 'e45e2942-cced-486e-8800-43e75bfad8b1',
                'ConfigDirectory': indaleko_default_config_dir,
                'DataDirectory': indaleko_default_data_dir,
                'LogDirectory': indaleko_default_log_dir,
                'InputFileChoices': ['file1', 'file2'],
                'InputFile': 'file1',
                'InputFileKeys': {'key1': 'value1', 'key2': 'value2'},
                'OutputFile': 'output.txt',
                'LogFile': 'log.txt',
                'Offline': False,
                'DBConfigChoices': ['db1', 'db2'],
                'DBConfigFile': IndalekoDBConfig.default_db_config_file,
                'FilePrefix': indaleko_file_name_prefix,
                'FileSuffix': '',
            }
        }

def main():
    '''Test code for the base CLI data model'''
    ic('Testing Base CLI Data Model')
    IndalekoBaseCliDataModel.test_model_main()

if __name__ == '__main__':
    main()
