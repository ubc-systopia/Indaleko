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
#import netifaces # see https://pypi.org/project/netifaces/
import datetime
import logging
import platform
import os
import socket
import sys

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
# from Indaleko import Indaleko
from Indaleko import Indaleko
from platforms.machine_config import IndalekoMachineConfig
from data_models.record import IndalekoRecordDataModel
from data_models.source_identifer import IndalekoSourceIdentifierDataModel
from data_models.timestamp import IndalekoTimestampDataModel
# from IndalekoDataModel import IndalekoDataModel
from platforms.data_models.hardware import Hardware
from platforms.data_models.software import Software
from platforms.data_models.machine_platform import MachinePlatform

# pylint: enable=wrong-import-position


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
                 **kwargs):
        '''Constructor for the IndalekoLinuxMachineConfig class'''
        self.service_registration = IndalekoMachineConfig.register_machine_configuration_service(
            **IndalekoLinuxMachineConfig.linux_machine_config_service
        )
        super().__init__(**kwargs)

    @staticmethod
    def find_configs_in_db(source_id : str = linux_machine_config_uuid_str) -> list:
        '''Find the machine configurations in the database for Linux.'''
        return [
            IndalekoMachineConfig.serialize(config)
            for config in IndalekoMachineConfig.lookup_machine_configurations(source_id=source_id)
        ]

    @staticmethod
    def find_config_files(directory : str, prefix : str = None, suffix : str = '.json') ->list:
        '''Find all of the configuration files in the specified directory.'''
        if prefix is None:
            prefix = IndalekoLinuxMachineConfig.linux_machine_config_file_prefix
        return IndalekoMachineConfig.find_config_files(
            directory=directory,
            prefix=prefix,
            suffix=suffix
        )

    @staticmethod
    def execute_command(command):
        '''
        Execute a command and return the output.
        '''
        if not isinstance(command, list):
            raise ValueError(f"Command must be a list: {command}")
        try:
            output = subprocess.check_output(command, stderr=subprocess.STDOUT)
            return output.decode().strip()
        except subprocess.CalledProcessError as error:
            print(f"Error executing {command}: {error.output.decode().strip()}")
            raise error

    @staticmethod
    def gather_system_information():
        '''Get information about the running kernel.'''
        system_info = {}
        system_info['UUID'] = str(uuid.UUID(open('/etc/machine-id').read().strip()))
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
    def extract_config_data():
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
            print(f'Configuration file already exists: {config_file}')
            print('aborting')
            exit(1)
        with open(config_file, 'wt', encoding='utf-8-sig') as config_fd:
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
        platform_name = IndalekoLinuxMachineConfig.linux_platform
        if 'platform' in kwargs:
            platform_name = kwargs['platform']
            del kwargs['platform']
        service = kwargs['service']
        del kwargs['service']
        prefix = IndalekoLinuxMachineConfig.linux_machine_config_file_prefix
        if 'prefix' in kwargs:
            prefix = kwargs['prefix']
            del kwargs['prefix']

        fname = Indaleko.generate_file_name(
            suffix=suffix,
            platform=platform_name,
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
        config_data = {}
        if config_dir is None and config_file is None:
            # nothing specified, so let's search and find
            config_dir = Indaleko.default_config_dir
        if config_file is None:
            assert config_dir is not None, 'config_dir must be specified'
            config_file = IndalekoLinuxMachineConfig.get_most_recent_config_file(config_dir)
        if config_file is not None:
            file_metadata = Indaleko.extract_keys_from_file_name(config_file)
            file_uuid = uuid.UUID(file_metadata['machine'])
            with open(config_file, 'rt', encoding='utf-8-sig') as config_fd:
                config_data = json.load(config_fd)
            machine_uuid = uuid.UUID(config_data['MachineUUID'])
            ic(machine_uuid)
            if machine_uuid != file_uuid:
                print('Machine UUID in file name does not match UUID in config file')
                print(f"\tFile name: {file_uuid}")
                print(f"\tConfig file: {machine_uuid}")
        if 'MachineUUID' not in config_data:
            config_data['MachineUUID'] = str(file_uuid)
        ic(config_data)
        ic(file_metadata)
        timestamp = datetime.datetime.fromisoformat(file_metadata['timestamp'])
        software = Software(
            OS=config_data['OSInfo']['operating_system'],
            Version=config_data['OSInfo']['kernel_version'],
            Architecture=config_data['CPU']['Architecture'],
            Hostname=config_data['Hostname'],
        )
        hardware = Hardware(
            CPU=config_data['CPU']['Model name'],
            Cores=int(config_data['CPU']['CPU(s)']),
            Version=config_data['CPU']['Model'],
        )
        captured = IndalekoTimestampDataModel(
            Label = IndalekoMachineConfig.indaleko_machine_config_captured_label_uuid,
            Value = timestamp
        )
        record = IndalekoRecordDataModel(
            SourceIdentifier = IndalekoSourceIdentifierDataModel(
                Identifier = IndalekoLinuxMachineConfig.\
                    linux_machine_config_service['service_identifier'],
                Version = IndalekoLinuxMachineConfig.\
                    linux_machine_config_service['service_version'],
                Description = IndalekoLinuxMachineConfig.\
                    linux_machine_config_service['service_description'],
            ),
            Timestamp = timestamp,
            Data = Indaleko.encode_binary_data(config_data),
            Attributes = config_data,
        )
        machine_config_data = {
            'Hardware' : hardware.serialize(),
            'Software' : software.serialize(),
            'Record' : record.serialize(),
            'Captured' : captured.serialize(),
        }
        if 'MachineUUID' not in machine_config_data:
            machine_config_data['MachineUUID'] = str(file_uuid)
        if 'Hostname' not in machine_config_data:
            machine_config_data['Hostname'] = config_data['Hostname']
        config = IndalekoLinuxMachineConfig(**machine_config_data)
        ic(MachinePlatform.serialize(config.machine_config))
        config.write_config_to_db()
        if hasattr(config, 'extract_volume_info'):
            getattr(config, 'extract_volume_info')(config_data)
        return config

    def write_config_to_db(self, overwrite : bool = True) -> None:
        ic(self.machine_id)
        assert self.machine_id is not None, 'Machine ID must be specified'
        assert Indaleko.validate_uuid_string(self.machine_id), 'Machine ID must be a valid UUID'
        super().write_config_to_db(overwrite=overwrite)
        # Should we add storage data here?

    @staticmethod
    def capture_machine_data(config_dir : str = Indaleko.default_config_dir,
                             timestamp : str = datetime.datetime.now(datetime.timezone.utc).isoformat(),
                             platform: str = None) -> str:
        '''Capture the machine data and write it to the specified file.'''
        if platform is None:
            platform = IndalekoLinuxMachineConfig.linux_platform
        cpu_data, ram_data, disk_data, net_data = IndalekoLinuxMachineConfig.extract_config_data()
        sys_data = IndalekoLinuxMachineConfig.gather_system_information()
        linux_config = {
            'MachineUUID': sys_data['UUID'],
            'OSInfo': sys_data['OSInfo'],
            'Hostname' : socket.gethostname(),
        }
        linux_config['CPU'] = cpu_data
        linux_config['RAM'] = ram_data
        linux_config['Disk'] = disk_data
        linux_config['Network'] = net_data
        print(linux_config['MachineUUID'])
        machine_uuid = uuid.UUID(linux_config['MachineUUID'])
        config_file_name = IndalekoLinuxMachineConfig.generate_config_file_name(
            config_dir=config_dir,
            timestamp=timestamp,
            platform=platform,
            machine=machine_uuid.hex,
            service=IndalekoLinuxMachineConfig.linux_machine_config_service_file_name,
        )
        IndalekoLinuxMachineConfig.save_config_to_file(config_file_name, linux_config)
        return config_file_name

    @staticmethod
    def capture_command_handler(args) -> None:
        '''
        Capture current machine configuration.
        '''
        print(f'Capture command handler: {args}')
        config_file = IndalekoLinuxMachineConfig.capture_machine_data(
            platform=args.platform,
            timestamp=args.timestamp,
            config_dir=args.configdir,
        )
        ic(config_file)

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
            config_file = IndalekoLinuxMachineConfig.capture_machine_data(
                platform=args.platform,
                timestamp=args.timestamp,
                config_dir=args.configdir,
            )
        else:
            if args.config is not None:
                config_file = args.config
            else:
                config_file = IndalekoLinuxMachineConfig.get_most_recent_config_file(args.configdir)
            config = IndalekoLinuxMachineConfig.load_config_from_file(config_file=config_file)
        assert isinstance(config, IndalekoLinuxMachineConfig), \
            f"Unexpected config type: {type(config)}"
        # Now to add the configuration to the database
        config.write_config_to_db(overwrite=True)
        return


    @staticmethod
    def list_command_handler(args) -> None:
        '''
        List machine configurations.
        '''
        print(f"List command handler: {args}")
        configs = IndalekoLinuxMachineConfig.find_configs_in_db()
        if len(configs) == 0:
            print('No machine configurations found in the database')
            return
        for config in configs:
            hostname = 'unknown'
            if 'hostname' in config:
                hostname = config['hostname']
            print(json.dumps(config, indent=4))
            print('Configuration for machine:', hostname)
            print(f'\t    UUID: {config["_key"]}')
            print(f'\tCaptured: {config["Captured"]["Value"]}')
            print(f'\tPlatform: {config["Platform"]["software"]["OS"]}')
            return


    @staticmethod
    def delete_command_handler(args) -> None:
        '''
        Delete a machine configuration.
        '''
        print(f"Delete command handler: {args}")


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
    if platform.system() != 'Linux':
        ic('Warning: foreign import of Linux configuration.')
    log_file_name = None
    if pre_args.log is None:
        file_name = Indaleko.generate_file_name(
            suffix='log',
            platform='Linux', # Note: this is the platform of the machine where the config came from.
            service='machine_config',
            timestamp=timestamp)
        log_file_name = os.path.join(Indaleko.default_log_dir, file_name)
    else:
        log_file_name = pre_args.log
    parser = argparse.ArgumentParser(parents=[pre_parser], description='Indaleko Linux Machine Config')
    subparsers = parser.add_subparsers(dest='command', required=True)
    parser_capture = subparsers.add_parser('capture', help='Capture machine configuration')
    parser_capture.add_argument('--platform', type=str, default=platform.system(), help='Platform to use')
    parser_capture.add_argument('--timestamp', type=str, default=timestamp, help='Timestamp to use')
    parser_capture.add_argument('--configdir', type=str, default=config_dir, help='Configuration directory to use')
    parser_capture.set_defaults(func=IndalekoLinuxMachineConfig.capture_command_handler)
    parser_add = subparsers.add_parser('add', help='Add a machine config')
    parser_add.add_argument('--platform', type=str, default=platform.system(), help='Platform to use')
    parser_add.add_argument('--config', type=str, default=None, help='Config file to use')
    parser_add.add_argument('--create',
                            default=False,
                            action='store_true',
                            help='Create a new config file for current machine.')
    parser_add.set_defaults(func=IndalekoLinuxMachineConfig.add_command_handler)
    parser_list = subparsers.add_parser('list', help='List machine configs')
    parser_list.add_argument('--files', default=False, action='store_true', help='Source ID')
    parser_list.add_argument('--db', type=str, default=True, help='Source ID')
    parser_list.set_defaults(func=IndalekoLinuxMachineConfig.list_command_handler)
    parser_delete = subparsers.add_parser('delete', help='Delete a machine config')
    parser_delete.add_argument('--platform', type=str, default=platform.system(), help='Platform to use')
    parser_delete.set_defaults(func=IndalekoLinuxMachineConfig.delete_command_handler)
    parser.set_defaults(func=IndalekoLinuxMachineConfig.list_command_handler)
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
    args.func(args)
    if log_file_name is not None:
        logging.info('Done with Indaleko Linux Machine Config')

if __name__ == '__main__':
    main()