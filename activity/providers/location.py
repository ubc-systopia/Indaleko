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
import logging
import os
import sys

def __get_project_root() -> str:
    '''Get the root of the project'''
    if 'project_root' in globals():
        return project_root
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    sys.path.append(current_path)
    return current_path

project_root = __get_project_root()

from .. import provider_base

class LocationProvider(ProviderBase):
    '''This is a location activity data provider for Indaleko.'''

    def __init__(self, **kwargs):
        '''Set up the location activity data provider.'''


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
