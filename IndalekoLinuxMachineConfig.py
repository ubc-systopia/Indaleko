'''
This module is used to manage the Linux Machine configuration information.

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

import subprocess
import argparse
import json
import uuid
#import psutil # see https://psutil.readthedocs.io/en/latest/
import netifaces # see https://pypi.org/project/netifaces/
import datetime
import logging
import platform
import os

from Indaleko import Indaleko
from IndalekoMachineConfig import IndalekoMachineConfig

class IndalekoLinuxMachineConfig(IndalekoMachineConfig):
    '''
    The IndalekoLinuxMachineConfig class is used to capture information about a
    Linux machine.  It is a specialization of the IndalekoMachineConfig class,
    which is shared across all platforms.
    '''

    linux_machine_config_file_prefix='linux-hardware-info'
    linux_machine_config_uuid_str='c18f5758-357e-46d2-ba60-67720deaac5f'
    linux_machine_config_service_name='Linux Machine Configuration'
    linux_machine_config_service_description='Linux Machine Configuration Service'
    linux_machine_config_service_version='1.0'

    linux_machine_config_service = {
        'service_name': linux_machine_config_service_name,
        'service_description': linux_machine_config_service_description,
        'service_version': linux_machine_config_service_version,
        'service_type': 'Machine Configuration',
        'service_identifier': linux_machine_config_uuid_str,
    }

    @staticmethod
    def execute_command(command):
        '''
        Execute a command and return the output.
        '''
        if not isinstance(command, list):
            raise Exception(f"Command must be a list: {command}")
        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT)
            return output.decode().strip()
        except subprocess.CalledProcessError as error:
            raise Exception(f"Error executing {command}: {error.output.decode().strip()}")

    @staticmethod
    def gather_system_information():
        system_info = {}
        system_info['UUID'] = str(uuid.UUID(open('/etc/machine-id').read().strip()))
        return system_info

    @staticmethod
    def parse_ip_addr_output():
        output = IndalekoLinuxMachineConfig.execute_command(['ip', 'addr'])
        interfaces = {}
        interface_info = {}
        lines = output.split('\n')
        while len(lines) > 0: # sometimes we need multiple lines
            line = lines.pop(0)
            if 'mtu' in line:
                if len(interface_info) > 0:
                    interfaces[interface_info['name']] = interface_info
                interface_info = {}
                line.strip()
                _, interface_name, interface_data = line.split(':')
                interface_info['name'] = interface_name.strip()
                interface_data = [d.strip() for d in interface_data.split(' ') if len(d.strip()) > 0]
                if not interface_data[0].startswith('<') or not interface_data[0].endswith('>'):
                    raise Exception(f"Unexpected format for interface data: {interface_data}")
                interface_flags = interface_data.pop(0)[1:-1].split(' ')
                interface_info['flags'] = interface_flags
                while len(interface_data) > 0:
                    key = interface_data.pop(0)
                    value = interface_data.pop(0)
                    interface_info[key] = value
            elif 'inet6' in line:
                interface_data = [d.strip() for d in line.split(' ') if len(d.strip()) > 0]
                inet6_flags = []
                while len(interface_data) > 0:
                    key = interface_data.pop(0)
                    if key == 'inet6':
                        inet6_addr = interface_data.pop(0)
                    else:
                        inet6_flags.append(key)
                line = lines.pop(0) # next line is continuation
                if 'valid_lft' not in line:
                    raise Exception(f"Unexpected format for interface data: {line}")
                interface_data = [d.strip() for d in line.split(' ') if len(d.strip()) > 0]
                inet6_data = {}
                while len(interface_data) > 0:
                    key = interface_data.pop(0)
                    inet6_data[key] = interface_data.pop(0)
                if 'inet6' not in interface_info:
                    interface_info['inet6'] = []
                interface_info['inet6'].append({
                  'address': inet6_addr,
                    'flags': inet6_flags,
                    'data': inet6_data,
                })
            elif 'inet' in line:
                interface_data = [d.strip() for d in line.split(' ') if len(d.strip()) > 0]
                inet4_flags = []
                while len(interface_data) > 0:
                    key = interface_data.pop(0)
                    if key == 'inet':
                        inet4_addr = interface_data.pop(0)
                    else:
                        inet4_flags.append(key)
                line = lines.pop(0) # next line is continuation
                if 'valid_lft' not in line:
                    raise Exception(f"Unexpected format for interface data: {line}")
                interface_data = [d.strip() for d in line.split(' ') if len(d.strip()) > 0]
                inet4_data = {}
                while len(interface_data) > 0:
                    key = interface_data.pop(0)
                    inet4_data[key] = interface_data.pop(0)
                if 'inet' not in interface_info:
                    interface_info['inet'] = []
                interface_info['inet'].append({
                  'address': inet4_addr,
                    'flags': inet4_flags,
                    'data': inet4_data,
                })
            elif 'brd' in line:
                interface_data = [d.strip() for d in line.split(' ') if len(d.strip()) > 0]
                while len(interface_data) > 0:
                    key = interface_data.pop(0)
                    if len(interface_data) == 0:
                        continue
                    interface_info[key] = interface_data.pop(0)
        if len(interface_info) > 0:
            interfaces[interface_info['name']] = interface_info
        return interfaces


    @staticmethod
    def extract_some_data1():
        cpu_data = {
            l.split(':')[0].strip() : l.split(':')[1].strip() \
                for l in IndalekoLinuxMachineConfig.execute_command(['lscpu']).split('\n')
        }
        ram_data = {
            l.split(':')[0].strip() : l.split(':')[1].strip() \
                for l in open('/proc/meminfo', 'r').readlines()
        }
        disk_data = {
            l.split(':')[0].strip() : l.split(':')[1].strip() \
                for l in IndalekoLinuxMachineConfig.execute_command(['blkid']).split('\n')
        }
        net_data = IndalekoLinuxMachineConfig.parse_ip_addr_output()
        return cpu_data, ram_data, disk_data, net_data

    @staticmethod
    def add_command_handler(args) -> None:
        '''
        Add a machine configuration.
        '''
        print(f"Add command handler: {args}")

    @staticmethod
    def list_command_handler(args) -> None:
        '''
        List machine configurations.
        '''
        print(f"List command handler: {args}")
        return IndalekoMachineConfig.find_configs_in_db(
            source_id = IndalekoLinuxMachineConfig.linux_machine_config_uuid_str
            )

    @staticmethod
    def delete_command_handler(args) -> None:
        '''
        Delete a machine configuration.
        '''
        print(f"Delete command handler: {args}")

def old_main():
    parse = argparse.ArgumentParser()
    parse.add_argument('--configdir', type=str, default='./config', help='Directory where configuration data is written.')
    parse.add_argument('--timestamp', type=str,
                       default=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       help='Timestamp to use')
    args = parse.parse_args()
    print(f"Config dir: {args.configdir}")
    print(json.dumps(IndalekoLinuxMachineConfig.gather_system_information(),indent=4))
    cpu_data, ram_data, disk_data, net_data = IndalekoLinuxMachineConfig.extract_some_data1()
    print(json.dumps(cpu_data, indent=4))
    print(json.dumps(ram_data, indent=4))
    print(json.dumps(disk_data, indent=4))
    print(json.dumps(net_data, indent=4))


def main():
    '''UI implementation for Linux machine configuration processing.'''
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--log', type=str, default=None, help='Log file name to use')
    pre_parser.add_argument('--configdir',
                            default=Indaleko.default_config_dir,
                            type=str,
                            help='Configuration directory to use')
    pre_parser.add_argument('--timestamp',
                            type=str,
                            help='Timestamp to use')
    pre_args, _ = pre_parser.parse_known_args()
    if pre_args.timestamp is None:
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    else:
        timestamp=pre_args.timestamp
        Indaleko.validate_timestamp(timestamp)
    if pre_args.configdir is None:
        config_dir = Indaleko.default_config_dir
    else:
        config_dir = pre_args.configdir
    if not os.path.isdir(config_dir):
        raise Exception(f"Configuration directory does not exist: {config_dir}")
    log_file_name = None
    if pre_args.log is None:
        file_name = Indaleko.generate_file_name(
            suffix='log',
            platform=platform.system(),
            service='machine_config',
            timestamp=timestamp)
        log_file_name = os.path.join(Indaleko.default_log_dir, file_name)
    else:
        log_file_name = pre_args.log
    parser = argparse.ArgumentParser(parents=[pre_parser], description='Indaleko Linux Machine Config')
    subparsers = parser.add_subparsers(dest='command', required=True)
    parser_add = subparsers.add_parser('add', help='Add a machine config')
    parser_add.add_argument('--platform', type=str, default=platform.system(), help='Platform to use')
    parser_list = subparsers.add_parser('list', help='List machine configs')
    parser_list.add_argument('--files', default=False, action='store_true', help='Source ID')
    parser_list.add_argument('--db', type=str, default=True, help='Source ID')
    parser_delete = subparsers.add_parser('delete', help='Delete a machine config')
    parser_delete.add_argument('--platform', type=str, default=platform.system(), help='Platform to use')
    args = parser.parse_args()
    if log_file_name is not None:
        logging.basicConfig(filename=log_file_name, level=logging.DEBUG)
        logging.info('Starting Indaleko Linux Machine Config')
        logging.info(f"Logging to {log_file_name}")
        logging.critical('Critical logging enabled')
        logging.error('Error logging enabled')
        logging.warning('Warning logging enabled')
        logging.info('Info logging enabled')
        logging.debug('Debug logging enabled')
    if args.command == 'add':
        IndalekoLinuxMachineConfig.add_command_handler(args)
    elif args.command == 'list':
        IndalekoLinuxMachineConfig.list_command_handler(args)
    elif args.command == 'delete':
        IndalekoLinuxMachineConfig.delete_command_handler(args)
    else:
        logging.error('Unexpected command: %s', args.command)
        raise Exception(f"Unexpected command: {args.command}")
    if log_file_name is not None:
        logging.info('Done with Indaleko Linux Machine Config')

if __name__ == '__main__':
    main()

