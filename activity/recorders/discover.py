'''
This is the activity data provider recorder discovery mechanism.

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
'''

import argparse
import logging
import os
from pathlib import Path
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
from activity.collectors.discover import IndalekoActivityDataProviderCollectorDiscovery
from activity.collectors.known_semantic_attributes import KnownSemanticAttributes
from Indaleko import Indaleko
from utils import IndalekoLogging
# pylint: enable=wrong-import-position


class IndalekoActivityDataProviderRecorderDiscovery:
    '''
    The Indaleko activity data providers are dynamically recognized and added to
    the database.  This class provides the mechanism to discover and add new
    data providers.
    '''

    default_config_dir = None  # os.path.join(os.environ['INDALEKO_ROOT'], Indaleko.default_config_dir)
    default_data_dir = None  # os.path.join(os.environ['INDALEKO_ROOT'], Indaleko.default_data_dir)
    default_log_dir = None  # os.path.join(os.environ['INDALEKO_ROOT'], Indaleko.default_log_dir)
    default_recorder_provider_dir = str(Path(os.environ['INDALEKO_ROOT']) / 'activity' / 'recorders')
    default_collector_provider_dir = IndalekoActivityDataProviderCollectorDiscovery.default_provider_dir

    def __init__(self, **kwargs):
        '''Set up the recorder discovery mechanism'''
        self.collectors = IndalekoActivityDataProviderCollectorDiscovery.\
            find_collectors(
                kwargs.get(
                    'collector_dir',
                    IndalekoActivityDataProviderCollectorDiscovery.default_collector_dir
                )
            )
        for dir_name in ['config_dir', 'data_dir', 'log_dir']:
            if dir_name in kwargs:
                setattr(self, dir_name, kwargs[dir_name])
            else:
                if os.environ['INDALEKO_ROOT'] is not None:
                    setattr(
                        self, dir_name,
                        os.path.join(
                            os.environ['INDALEKO_ROOT'],
                            getattr(Indaleko, f'default_{dir_name}')
                        )
                    )
                else:
                    setattr(
                        self,
                        dir_name,
                        getattr(Indaleko, f'default_{dir_name}')
                    )
        self.provider_dir = kwargs.get(
            'provider_dir',
            IndalekoActivityDataProviderRecorderDiscovery.default_recorder_provider_dir
        )
        self.config_dir = kwargs.get(
            'config_dir',
            IndalekoActivityDataProviderRecorderDiscovery.default_config_dir
        )
        self.data_dir = kwargs.get(
            'data_dir',
            IndalekoActivityDataProviderRecorderDiscovery.default_data_dir
        )
        self.log_dir = kwargs.get(
            'log_dir',
            IndalekoActivityDataProviderRecorderDiscovery.default_log_dir
        )
        self.data_providers = \
            IndalekoActivityDataProviderRecorderDiscovery.find_data_providers(self.provider_dir)

    @staticmethod
    def find_data_providers(
        collector_provider_dir: Union[str, None] = None,
        recorder_provider_dir: Union[str, None] = None
    ) -> list:
        '''Find the data providers in the specified directory'''
        if recorder_provider_dir is None:
            recorder_provider_dir = IndalekoActivityDataProviderRecorderDiscovery.default_recorder_provider_dir
        if collector_provider_dir is None:
            collector_provider_dir = IndalekoActivityDataProviderRecorderDiscovery.default_collector_provider_dir
        collector_data_providers = IndalekoActivityDataProviderCollectorDiscovery.\
            find_data_providers(collector_provider_dir)
        recorder_data_providers = []
        # Step 1: Build a list of subdirectories
        subdirectories = [f.name for f in os.scandir(recorder_provider_dir) if f.is_dir() and not f.name.startswith('_')]
        ic(subdirectories)
        ic(collector_data_providers)
        ic(dir(collector_data_providers[0]['module']))
        return recorder_data_providers
        for subdir in subdirectories:
            module = KnownSemanticAttributes.safe_import(f'activity.collectors.{subdir}')
            if hasattr(module, 'activity_providers'):
                for provider in module.activity_providers():
                    recorder_data_providers.append({
                        'category': subdir,
                        'collector_provider_class': provider,
                        'recorder_provider_class': provider,
                        'module': module
                    })
        return recorder_data_providers

    @staticmethod
    def initialize_project() -> bool:
        '''Initialize the project'''
        ic('Initialize project')

    @staticmethod
    def list_data_providers(args: argparse.Namespace):
        '''List the data providers available'''
        discovery = IndalekoActivityDataProviderRecorderDiscovery()
        for provider in discovery.data_providers:
            ic(provider)

    @staticmethod
    def show_registrations(args: argparse.Namespace):
        '''Show the existing registrations for the data providers'''
        ic(f'Show registrations: {args}')


def main():
    '''
    This is the interactive interface to the activity data provider discovery
    mechanism.
    '''
    ic(IndalekoActivityDataProviderRecorderDiscovery.find_data_providers())
    exit(0)
    parser = argparse.ArgumentParser(description='Indaleko Activity Data Provider Discovery Tool')
    parser.add_argument('--logdir',
                        type=str,
                        default=IndalekoActivityDataProviderRecorderDiscovery.default_log_dir,
                        help='Directory for log files')
    parser.add_argument('--log', type=str, default=None, help='Log file name')
    parser.add_argument('--loglevel', type=int, default=logging.DEBUG,
                        choices=IndalekoLogging.get_logging_levels(),
                        help='Logging level')
    command_subparser = parser.add_subparsers(dest='command', help='Command to execute')
    parser_list = command_subparser.add_parser('list', help='List the data providers available')
    parser_list.add_argument('--providerdir',
                             type=str,
                             default=IndalekoActivityDataProviderRecorderDiscovery.default_recorder_provider_dir,
                             help='Directory for the data providers '
                             f'(default: {IndalekoActivityDataProviderRecorderDiscovery.default_recorder_provider_dir})'
                             )
    parser_list.set_defaults(func=IndalekoActivityDataProviderRecorderDiscovery.list_data_providers)
    parser.set_defaults(func=IndalekoActivityDataProviderRecorderDiscovery.list_data_providers)
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
