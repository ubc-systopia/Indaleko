'''
This module provides a base class for common CLI functionality.

Indaleko Windows Local Recorder
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
'''
from pathlib import Path
import os
import sys

from typing import Union, Any, Callable
from abc import ABC, abstractmethod

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from platforms.machine_config import IndalekoMachineConfig
from perf.perf_collector import IndalekoPerformanceDataCollector
# pylint: enable=wrong-import-position

class IndalekoHandlermixin(ABC):
    """Class for providing callback processing for the main handler"""

    @abstractmethod
    def get_default_file(data_directory: Union[str, Path], candidates : list[Union[str, Path]]) -> Union[str, None]:
        '''Pick the preferred/default file from a list of candidates (None if the list is empty)'''

    @abstractmethod
    def find_db_config_files(config_dir: Union[str, Path]) -> Union[list[str], None]:
        '''This method is used to find database configuration files'''

    @abstractmethod
    def find_machine_config_files(
        config_dir : Union[str, Path],
        platform : str = None,
        machine_id : str = None) -> Union[list[str], None]:
        '''
        This method is used to find machine configuration files

        Inputs:
            - config_dir: The directory where the configuration files are stored
            - platform: The platform of the machine
            - machine_id: The machine ID

        Returns:
            - A list of file names

        Notes: If the platform is not provided, it may be inferred from the machine ID
        or the current platform.  If the machine ID is provided and a platform is
        provided, both must match for the file to be considered a candidate.
        '''

    @abstractmethod
    def find_data_files(data_dir: Union[str, Path],
                        keys : dict[str,str],
                        prefix : str,
                        suffix : str) -> Union[list[str], None]:
        '''This method is used to find data files'''

    @abstractmethod
    def generate_output_file_name(keys : dict[str, str]) -> str:
        '''This method is used to generate an output file name'''


    @abstractmethod
    def generate_log_file_name(keys : dict[str,str]) -> str:
        '''This method is used to generate a log file name'''

    @abstractmethod
    def generate_perf_file_name(keys : dict[str,str]) -> str:
        '''This method is used to generate a performance file name'''

    @abstractmethod
    def load_machine_config(keys : dict[str,str]) -> IndalekoMachineConfig:
        '''This method is used to load a machine configuration'''

    @abstractmethod
    def extract_filename_metadata(file_name : str) -> dict:
        '''This method is used to parse the file name.'''
