'''
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
import os
import json
import uuid
import datetime
import re
import argparse

from typing import Union
from icecream import ic

from IndalekoDBConfig import IndalekoDBConfig
from IndalekoMachineConfig import IndalekoMachineConfig
from Indaleko import Indaleko
from IndalekoRecordDataModel import IndalekoRecordDataModel
from IndalekoDataModel import IndalekoDataModel
from IndalekoMachineConfigDataModel import IndalekoMachineConfigDataModel
from IndalekoRecordDataModel import IndalekoRecordDataModel


class IndalekoMacOSMachineConfig(IndalekoMachineConfig):
    '''
    The IndalekoMacOSMachineConfig class is used to capture information about
    a macOS machine. It is a specialization of the IndalekoMachineConfig
    class, which is shared across all platforms.
    '''

    macos_machine_config_file_prefix = 'macos-hardware-info'

    macos_machine_config_uuid_str = '8a948e74-6e43-4a6e-91c0-0cb5fd97355e'

    macos_machine_config_service = {
        'service_name': 'MacOSMachineConfig',
        'service_description': 'This service provides the configuration information for a macOS machine.',
        'service_version': '1.0',
        'service_identifier': macos_machine_config_uuid_str,
        'service_type': 'Indexer',
    }

    def __init__(self : 'IndalekoMacOSMachineConfig', **kwargs):
        self.service_registration = IndalekoMachineConfig.register_machine_configuration_service(
            **IndalekoMacOSMachineConfig.macos_machine_config_service
        )
        super().__init__(**kwargs)

    @staticmethod
    def find_configs_in_db(source_id : Union[str, None] = None) -> list:
        '''Find the machine configurations in the database for Windows.'''
        if source_id is None:
            source_id = IndalekoMacOSMachineConfig.macos_machine_config_uuid_str
        return IndalekoMachineConfig.find_configs_in_db(source_id)

    
    @staticmethod
    def find_config_files(directory : str, prefix : str = None, suffix : str = '.json') -> list:
        '''This looks for configuration files in the given directory.'''
        if prefix is None:
            prefix = IndalekoMacOSMachineConfig.macos_machine_config_uuid_str
        return IndalekoMachineConfig.find_config_files(
            directory,
            prefix,
            suffix=suffix
        )


    @staticmethod
    def load_config_from_file(config_dir : str = None,
                              config_file : str = None) -> 'IndalekoMacOSMachineConfig':
        config_data = {}
        if config_dir is None and config_file is None:
            config_dir = Indaleko.default_config_dir
        if config_file is None:
            assert config_dir is not None, 'config_dir must be specified'
            config_file = IndalekoMacOSMachineConfig.get_most_recent_config_file(config_dir)
        if config_file is not None:
            _, guid, timestamp = IndalekoMacOSMachineConfig.get_guid_timestamp_from_file_name(
                config_file)
            assert os.path.exists(config_file), f'Config file {config_file} does not exist'
            assert os.path.isfile(config_file), f'Config file {config_file} is not a file'
            with open(config_file, 'rt', encoding='utf-8-sig') as fd:
                config_data = json.load(fd)
            assert str(guid) == config_data['MachineGuid'], \
                  f'GUID mismatch: {guid} != {config_data["MachineGuid"]}'
        assert len(config_data) > 0, 'No configuration data found'
        record = IndalekoRecordDataModel.IndalekoRecord(
            SourceIdentifier = IndalekoDataModel.SourceIdentifier(
                Identifier=IndalekoMacOSMachineConfig.macos_machine_config_service['service_identifier'],
                Version=IndalekoMacOSMachineConfig.macos_machine_config_service['service_version'],
                Description=IndalekoMacOSMachineConfig.macos_machine_config_service['service_description']
            ),
            Timestamp = datetime.datetime.now(datetime.timezone.utc),
            Data = Indaleko.encode_binary_data(config_data),
            Attributes = config_data
        )
        captured = IndalekoMachineConfigDataModel.Captured(
            Value = timestamp,
            Label = IndalekoMachineConfig.indaleko_machine_config_captured_label_str
        )
        platform = IndalekoMachineConfigDataModel.Platform(
            software = IndalekoMachineConfigDataModel.Software(
                OS = config_data['OperatingSystem']['Caption'],
                Version = config_data['OperatingSystem']['Version'],
                Architecture = config_data['OperatingSystem']['OSArchitecture']
            ),
            hardware = IndalekoMachineConfigDataModel.Hardware(
                CPU = config_data['CPU']['Name'],
                Version = 'Unknown',
                Cores = config_data['CPU']['Cores']
            )
        )
        machine_config_data = {
            'Platform' : IndalekoMachineConfigDataModel.Platform.serialize(platform),
            'Captured' : IndalekoMachineConfigDataModel.Captured.serialize(captured),
            'Record' : IndalekoRecordDataModel.IndalekoRecord.serialize(record),
        }
        ic(config_data.keys())
        if 'MachineUUID' not in machine_config_data:
            machine_config_data['MachineUUID'] = config_data['MachineGuid']
        if 'Hostname' not in machine_config_data:
            machine_config_data['Hostname'] = config_data.get('hostname', 'Unknown')
        config = IndalekoMacOSMachineConfig(data=machine_config_data)
        ic(IndalekoMachineConfigDataModel.MachineConfig.serialize(config.machine_config))
        return config

    @staticmethod
    def get_guid_timestamp_from_file_name(file_name : str) -> tuple:
        '''
        Use file name to extract the guid
        '''
        # Regular expression to match the GUID and timestamp
        pattern = r"(?:.*[/\\])?macos-hardware-info-(?P<guid>[a-fA-F0-9\-]+)-(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.\d+Z)\.json"
        match = re.match(pattern, file_name)

        assert match, f'Filename format not recognized for {file_name}.'

        guid = uuid.UUID(match.group("guid"))

        timestamp = match.group("timestamp").replace("-", ":")
        assert timestamp[-1] == 'Z', 'Timestamp must end with Z'

        timestamp_parts = timestamp.split('.')
        fractional_part = timestamp_parts[1][:6]  # truncate to 6 digits
        ymd, hms = timestamp_parts[0].split('T')
        timestamp = ymd.replace(':', '-') + 'T' + hms + '.' + fractional_part + '+00:00'
        timestamp = datetime.datetime.fromisoformat(timestamp)

        return (file_name, guid, timestamp)

    @staticmethod
    def get_most_recent_config_file(config_dir : str) -> str:
        '''Get the most recent machine configuration file.'''
        candidates = [x for x in os.listdir(config_dir) if
                      x.startswith('macos-hardware-info') and x.endswith('.json')]
        assert len(candidates) > 0, 'At least one macos-hardware-info file should exist'
        candidate_files = [(timestamp, filename)
                           for filename, guid, timestamp in
                           [IndalekoMacOSMachineConfig.get_guid_timestamp_from_file_name(x)
                            for x in candidates]]
        candidate_files.sort(key=lambda x: x[0])
        candidate = candidate_files[0][1]
        if config_dir is not None:
            candidate = os.path.join(config_dir, candidate)
        return candidate


    def write_config_to_db(self) -> None:
        '''Write the machine configuration to the database.'''
        super().write_config_to_db()

def main():
    '''Main function for the Indaleko macOS Machine Config service.'''
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('--delete', '-d', action='store_true',
                        help='Delete the machine configuration if it exists in the database.')
    parser.add_argument('--uuid', '-u', type=str, default=None,
                        help='The UUID of the machine.')
    parser.add_argument('--list', '-l', action='store_true',
                        help='List the machine configurations in the database.')
    parser.add_argument('--files', '-f', action='store_true',
                        help='List the machine configuration files in the default directory.')
    parser.add_argument('--add', '-a', action='store_true',
                        help='Add a machine configuration (from the file) to the database.')
    args = parser.parse_args()

    if args.list:
        print('Listing machine configurations in the database.')

        configs = IndalekoMacOSMachineConfig.find_configs_in_db(IndalekoMacOSMachineConfig.macos_machine_config_uuid_str)
        for config in configs:
            hostname = 'Unknown'
            if 'hostname' in config:
                hostname = config['hostname']
            print('Configuration for machine:', hostname)
            print(json.dumps(config, indent=4))
        return

    if args.delete:
        assert args.uuid is not None, \
            'UUID must be specified when deleting a machine configuration.'
        assert IndalekoMacOSMachineConfig.validate_uuid_string(args.uuid), \
            f'UUID {args.uuid} is not a valid UUID.'
        print(f'Deleting machine configuration with UUID {args.uuid}')
        IndalekoMacOSMachineConfig.delete_config_in_db(args.uuid)
        return

    if args.files:
        assert os.path.exists(Indaleko.default_config_dir), f'config path {Indaleko.default_config_dir} does not exists'
        print('Listing machine configuration files in the default directory.')
        files = IndalekoMacOSMachineConfig.find_config_files(
            Indaleko.default_config_dir,
            IndalekoMacOSMachineConfig.macos_machine_config_file_prefix)
        for file in files:
            print(file)
        return

    if args.add:
        print('Adding machine configuration to the database.')
        config = IndalekoMacOSMachineConfig.load_config_from_file()
        config.write_config_to_db()
        return

if __name__ == "__main__":
    main()
