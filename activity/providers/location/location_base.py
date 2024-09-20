'''
This module is a location activity data provider for Indaleko.

Project Indaleko
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
import logging
import os
import sys

from abc import abstractmethod
from typing import List, Dict, Any

if os.environ.get('INDALEKO_ROOT') is None:
    print('adding root')
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# This logic is part of what allows me to execute it locally or as part of the
# overall package/project.  It's a bit of a hack, but it works.
try:
    from activity import ProviderBase
except ImportError:
    from .provider_base import ProviderBase



class LocationProvider(ProviderBase):
    '''This is a location activity data provider for Indaleko.'''

    @abstractmethod
    def get_location_name(self) -> Any:
        '''Get the location'''

    @abstractmethod
    def get_coordinates(self) -> Dict[str, float]:
        '''Get the coordinates for the location'''

    @abstractmethod
    def get_location_history(
        self,
        start_time : datetime.datetime,
        end_time : datetime.datetime) -> List[Dict[str, Any]]:
        '''Get the location history for the location'''

    @abstractmethod
    def get_distance(self, location1: Dict[str, float], location2: Dict[str, float]) -> float:
        '''Get the distance between two locations'''


def main():
    '''This is a test interface for the location provider.'''
    parser = argparse.ArgumentParser(description='Location provider test interface')
    parser.add_argument('--logdir',
                        type=str,
                        default=LocationProvider.default_log_dir,
                        help='Directory for log files')
    parser.add_argument('--log', type=str, default=None, help='Log file name')
    parser.add_argument('--loglevel', type=int, default = logging.DEBUG,
                        choices= LocationProvider.get_logging_levels(),
                        help='Logging level')
    command_subparser = parser.add_subparsers(dest='command', help='Command to execute')
    parser_list = command_subparser.add_parser('list', help='List the data providers available')
    parser_list.add_argument('--providerdir',
                             type=str,
                             )
    parser_list.set_defaults(func=LocationProvider.list_data_providers)
    parser.set_defaults(func=LocationProvider.list_data_providers)
    args=parser.parse_args()
    args.func(args)
    args = parser.parse_args()
    parser.add_argument('--config', type=str, help='Configuration file for the location provider')

if __name__ == '__main__':
    def __get_project_root() -> str:
        '''Get the root of the project'''
        current_path = os.path.dirname(os.path.abspath(__file__))
        while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
            current_path = os.path.dirname(current_path)
        return current_path

    if 'INDALEKO_ROOT' not in os.environ:
        project_root = __get_project_root()
        os.environ['INDALEKO_ROOT'] = project_root
        sys.path.append(project_root)

    # now we can import modules from the project root
    from Indaleko import Indaleko
    from IndalekoLogging import IndalekoLogging

    from activity.provider_base import ProviderBase
    main()
