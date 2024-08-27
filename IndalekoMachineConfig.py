'''
Indaleko Machine Configuration class.

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
#import datetime
#import json
#import uuid
#import socket
#import platform
#import os
#import logging
#import re

# import arango

from icecream import ic

from IndalekoMachineConfigDataModel import IndalekoMachineConfigDataModel
from Indaleko import Indaleko
from IndalekoDataModel import IndalekoDataModel
from IndalekoServiceDataModel import IndalekoServiceDataModel
from IndalekoServiceManager import IndalekoServiceManager

class IndalekoMachineConfig:
    '''
    This class provides the generic base for capturing a machine
    configuration
    '''

    def __init__(self,
                 **kwargs):
        '''Initialize the machine configuration'''
        if not hasattr(self, 'source'): # override in derived classes
            self.source_identifier = None
        self.machine_config = IndalekoMachineConfigDataModel.MachineConfig.deserialize(**kwargs)

    @staticmethod
    def register_machine_configuration_service(**kwargs):
        '''Register the machine configuration service'''
        return IndalekoServiceManager().register_service(
            service_name = kwargs['service_name'],
            service_description = kwargs['service_description'],
            service_version = kwargs['service_version'],
            service_type = kwargs.get('service_type', 'Machine Configuration'),
            service_id = kwargs.get('service_identifier', None),
        )

def register_handler(args : argparse.Namespace) -> None:
    '''Register a test machine configuration.'''
    IndalekoMachineConfig.register_machine_configuration_service(
        service_name = 'Test Machine Configuration',
        service_description = 'Test Config',
        service_version = '1.0.2',
        service_identifier='05567376-0f4f-4d40-97f1-3ac5f764fcf3'
    )
    ic(args)

def list_handler(args : argparse.Namespace) -> None:
    '''List all machine configurations.'''
    ic(args)

def main():
    '''Interact with the IndalekoMachineConfig class.'''
    parser = argparse.ArgumentParser(description='Indaleko Machine Configuration')
    command_subparser = parser.add_subparsers(title='commands', dest='command')
    command_register = command_subparser.add_parser('register', help='Register a test machine configuration')
    command_register.set_defaults(func=register_handler)
    command_list = command_subparser.add_parser('list', help='List all machine configurations')
    command_list.set_defaults(func=list_handler)
    parser.set_defaults(func=list_handler)
    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()
