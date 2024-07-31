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
from IndalekoDBConfig import IndalekoDBConfig

class IndalekoLinuxMachineConfig(IndalekoMachineConfig):
    '''
    The IndalekoLinuxMachineConfig class is used to capture information about a
    Linux machine.  It is a specialization of the IndalekoMachineConfig class,
    which is shared across all platforms.
    '''
    linux_platform = 'Linux'
    linux_machine_config_file_prefix='linux_hardware_info'
    linux_machine_config_uuid_str='c18f5758-357e-46d2-ba60-67720deaac5f'
    linux_machine_config_service_name='Linux Machine Configuration'
    linux_machine_config_service_file_name = 'linux_machine_config'
    linux_machine_config_service_description='Linux Machine Configuration Service'
    linux_machine_config_service_version='1.0'

    linux_machine_config_service = {
        'service_name': linux_machine_config_service_name,
        'service_description': linux_machine_config_service_description,
        'service_version': linux_machine_config_service_version,
        'service_type': 'Machine Configuration',
        'service_identifier': linux_machine_config_uuid_str,
    }

    def __init__(self : 'IndalekoLinuxMachineConfig',
                 timestamp : datetime = None,
                 db : IndalekoDBConfig = None) -> None:
        '''Constructor for the IndalekoLinuxMachineConfig class'''
        super().__init__(timestamp=timestamp,
                         db=db,
                         **IndalekoLinuxMachineConfig.linux_machine_config_service)

    @staticmethod
    def find_config_files(config_dir):
        '''Find all of the configuration files in the specified directory.'''
        return IndalekoMachineConfig.find_config_files(
            config_dir,
            IndalekoLinuxMachineConfig.linux_machine_config_file_prefix
        )

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
        '''Get information about the running kernel.'''
        os_info = {}
        uname_operations = {
            'kernel_name': '-s',
            'nodename': '-n',
            'kernel_release': '-r',
            'kernel_version': '-v',
            'machine': '-m',
            'processor': '-p',
            'hardware_platform': '-i',
            'operating_system': '-o',
        }
        for key,arg in uname_operations.items():
            os_info[key] = IndalekoLinuxMachineConfig.execute_command(['uname', arg])
        system_info['OSInfo'] = os_info
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
    def save_config_to_file(config_file : str, config = dict) -> None:
        '''
        Given a configuration file name and a configuration, save the
        configuration in to the specified file.
        '''
        if os.path.exists(config_file):
            print('Configuration file already exists: %s' % config_file)
            print('aborting')
            exit(1)
        with open(config_file, 'w') as config_fd:
            json.dump(config, config_fd, indent=4)

    @staticmethod
    def generate_config_file_name(**kwargs) -> str:
        '''
        Given a configuration directory, timestamp, platform, and service,
        generate a configuration file name.
        '''
        config_dir = Indaleko.default_config_dir
        if 'config_dir' in kwargs:
            config_dir = kwargs['config_dir']
            del kwargs['config_dir']
        suffix = 'json'
        if 'suffix' in kwargs:
            suffix = kwargs['suffix']
            del kwargs['suffix']
        platform = IndalekoLinuxMachineConfig.linux_platform
        if 'platform' in kwargs:
            platform = kwargs['platform']
            del kwargs['platform']
        if 'service' in kwargs:
            service = kwargs['service']
            del kwargs['service']
        prefix = IndalekoLinuxMachineConfig.linux_machine_config_file_prefix
        if 'prefix' in kwargs:
            prefix = kwargs['prefix']
            del kwargs['prefix']

        fname = Indaleko.generate_file_name(
            suffix=suffix,
            platform=platform,
            service=service,
            prefix=prefix,
            **kwargs
        )
        return os.path.join(config_dir, fname)

    @staticmethod
    def get_most_recent_config_file(config_dir):
        '''
        Given a configuration directory and a prefix, find the most recent
        configuration file.
        '''
        files = IndalekoLinuxMachineConfig.find_config_files(config_dir)
        if len(files) == 0:
            return None
        files = sorted(files)
        candidate = files[-1]
        if config_dir is not None:
            candidate = os.path.join(config_dir, candidate)
        return candidate

    @staticmethod
    def load_config_from_file(config_dir : str = None,
                              config_file : str = None) -> 'IndalekoLinuxMachineConfig':
        """
        This method creates a new IndalekoMachineConfig object from an
        existing config file.
        """
        if config_dir is None and config_file is None:
            # nothing specified, so let's search and find
            config_dir = Indaleko.default_config_dir
        if config_file is None:
            assert config_dir is not None, 'config_dir must be specified'
            config_file = IndalekoLinuxMachineConfig.get_most_recent_config_file(config_dir)
        assert os.path.exists(config_file), f"Config file does not exist: {config_file}"
        file_metadata = Indaleko.extract_keys_from_file_name(config_file)
        file_uuid = uuid.UUID(file_metadata['machine'])
        with open(config_file, 'rt', encoding='utf-8-sig') as config_fd:
            config_data = json.load(config_fd)
        machine_uuid = uuid.UUID(config_data['MachineUUID'])
        if machine_uuid != file_uuid:
            print('Machine UUID in file name does not match UUID in config file')
            print(f"File name: {file_uuid}")
            print(f"Config file: {machine_uuid}")
        config = IndalekoLinuxMachineConfig.build_config(
            machine_config=IndalekoLinuxMachineConfig(),
            os=config_data['OSInfo']['operating_system'],
            arch=config_data['CPU']['Architecture'],
            os_version=config_data['OSInfo']['kernel_version'],
            cpu=config_data['CPU']['Model name'],
            cpu_version=config_data['CPU']['Model'],
            cpu_cores=int(config_data['CPU']['CPU(s)']),
            source_id=IndalekoLinuxMachineConfig.linux_machine_config_service['service_identifier'],
            source_version=IndalekoLinuxMachineConfig.linux_machine_config_service['service_version'],
            timestamp=file_metadata['timestamp'],
            attributes=config_data,
            data=Indaleko.encode_binary_data(config_data),
            machine_id=file_uuid
        )
        # Should we do processing of the net/disk data?
        return config

    def write_config_to_db(self) -> None:
        assert self.machine_id is not None, 'Machine ID must be specified'
        super().write_config_to_db()
        # Should we add storage data here?

    @staticmethod
    def add_command_handler(args) -> None:
        '''
        Add a machine configuration.
        '''
        print(f"Add command handler: {args}")
        existing_configs = IndalekoLinuxMachineConfig.find_config_files(args.configdir)
        if len(existing_configs) == 0:
            if not args.create:
                print(f'No configuration files found in {args.configdir} and --create was not specified')
                print('aborting')
                return
            cpu_data, ram_data, disk_data, net_data = IndalekoLinuxMachineConfig.extract_some_data1()
            sys_data = IndalekoLinuxMachineConfig.gather_system_information()
            linux_config = {
                'MachineUUID': sys_data['UUID'],
                'OSInfo': sys_data['OSInfo'],
            }
            linux_config['CPU'] = cpu_data
            linux_config['RAM'] = ram_data
            linux_config['Disk'] = disk_data
            linux_config['Network'] = net_data
            print(linux_config['MachineUUID'])
            machine_uuid = uuid.UUID(linux_config['MachineUUID'])
            config = IndalekoLinuxMachineConfig.generate_config_file_name(
                config_dir=args.configdir,
                timestamp=args.timestamp,
                platform=args.platform,
                machine=machine_uuid.hex,
                service=IndalekoLinuxMachineConfig.linux_machine_config_service_file_name,
            )
        else:
            if (args.config is not None):
                config_file = args.config
            else:
                config_file = IndalekoLinuxMachineConfig.get_most_recent_config_file(args.configdir)
            config = IndalekoLinuxMachineConfig.load_config_from_file(config_file=config_file)
        assert isinstance(config, IndalekoLinuxMachineConfig), f"Unexpected config type: {type(config)}"
        # Now to add the configuration to the database
        config.write_config_to_db()
        return


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
    parser_add.add_argument('--config', type=str, default=None, help='Config file to use')
    parser_add.add_argument('--create',
                            default=False,
                            action='store_true',
                            help='Create a new config file for current machine.')
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

