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
import arango
import re
import argparse

from icecream import ic

from IndalekoDBConfig import IndalekoDBConfig
from IndalekoMachineConfig import IndalekoMachineConfig
from Indaleko import Indaleko
from IndalekoRecordDataModel import IndalekoRecordDataModel
from IndalekoDataModel import IndalekoDataModel
from IndalekoMachineConfigDataModel import IndalekoMachineConfigDataModel


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
        ic(kwargs)
        super().__init__(**kwargs)
        self.attributes = kwargs.get('attributes', {})
        self.machine_id = kwargs.get('machine_id', None)
        self.data = kwargs.get('data', None)
        self.volume_data = kwargs.get('volume_data', {})
        self.volume_data = {}

    def __old_init__(self : 'IndalekoMacOSMachineConfig',
                 timestamp : datetime = None,
                 db : IndalekoDBConfig = None):
        super().__init__(timestamp=timestamp,
                         db=db,
                         **IndalekoMacOSMachineConfig.macos_machine_config_service)
        self.volume_data = {}

    @staticmethod
    def find_config_files(directory : str) -> list:
        '''This looks for configuration files in the given directory.'''
        ic(directory)
        return [x for x in os.listdir(directory)
                if x.startswith(IndalekoMacOSMachineConfig.macos_machine_config_file_prefix)
                and x.endswith('.json')]

    @staticmethod
    def find_configs_in_db(source_id) -> list:
        return IndalekoMachineConfig.find_configs_in_db(source_id=source_id)

    @staticmethod
    def load_config_from_file(config_dir : str = None,
                              config_file : str = None) -> 'IndalekoMacOSMachineConfig':
        config_data = {}
        if config_dir is None and config_file is None:
            config_dir = IndalekoMacOSMachineConfig.default_config_dir
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
                ic(config_data)
            assert str(guid) == config_data['MachineGuid'], \
                  f'GUID mismatch: {guid} != {config_data["MachineGuid"]}'
        config = IndalekoMacOSMachineConfig(
            os=config_data['OperatingSystem']['Caption'],
            arch=config_data['OperatingSystem']['OSArchitecture'],
            os_version=config_data['OperatingSystem']['Version'],
            cpu=config_data['CPU']['Name'],
            cpu_version=config_data['CPU']['Name'],
            cpu_cores=config_data['CPU']['Cores'],
            source_id=IndalekoMacOSMachineConfig.macos_machine_config_service['service_identifier'],
            source_version=IndalekoMacOSMachineConfig.macos_machine_config_service['service_version'],
            timestamp=timestamp.isoformat(),
            attributes=config_data,
            data=Indaleko.encode_binary_data(config_data),
            machine_id=config_data['MachineGuid'],
            Record = IndalekoRecordDataModel.IndalekoRecord(
                SourceIdentifier = IndalekoDataModel.SourceIdentifier(
                    Identifier=IndalekoMacOSMachineConfig.macos_machine_config_service['service_identifier'],
                    Version=IndalekoMacOSMachineConfig.macos_machine_config_service['service_version'],
                    Description=IndalekoMacOSMachineConfig.macos_machine_config_service['service_description']
                ),
                Timestamp = datetime.datetime.now(datetime.timezone.utc),
                Data = Indaleko.encode_binary_data(config_data),
                Attributes = config_data
            )
        )
        config.extract_volume_info()
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

    class MacOSDriveInfo:
        '''This class is used to capture information about a macOS drive.'''
        MacOSDriveInfo_UUID_str = 'e23f71d8-0973-455b-af20-b9bc6ee8ebd6' # created manually
        MacOSDriveInfo_UUID = uuid.UUID(MacOSDriveInfo_UUID_str)
        MacOSDriveInfo_Version = '1.0'
        MacOSDriveInfo_Description = 'macOS Drive Info'

        def __init__(self, machine_id : str, drive_data : dict, captured: IndalekoMachineConfigDataModel.Captured) -> None:
            assert 'GUID' not in drive_data, 'GUID should not be in drive_data'
            assert 'UniqueId' in drive_data, 'UniqueId must be in drive_data'
            assert drive_data['UniqueId'].startswith('/dev/')
            drive_data['GUID'] = self.__find_volume_guid__(drive_data['UniqueId'])
            self.machine_id = machine_id
            self.indaleko_record = IndalekoRecordDataModel.IndalekoRecord(
                SourceIdentifier = IndalekoDataModel.SourceIdentifier(
                    Identifier = self.MacOSDriveInfo_UUID_str,
                    Version = self.MacOSDriveInfo_Version,
                    Description = self.MacOSDriveInfo_Description
                ),
                Timestamp = captured.Value,
                Data = Indaleko.encode_binary_data(drive_data),
                Attributes = drive_data
            )
            assert isinstance(captured, IndalekoMachineConfigDataModel.Captured), 'captured must be a dict'
            self.captured = captured
            ic(self.indaleko_record)
            self.config_object = IndalekoMachineConfigDataModel.MachineConfig(
                Captured = self.captured,
                Record = self.indaleko_record
            )

        @staticmethod
        def __find_volume_guid__(vol_name : str) -> str:
            assert vol_name is not None, 'Volume name cannot be None'
            assert isinstance(vol_name, str), 'Volume name must be a string'
            assert vol_name.startswith('/dev/')  # based on distutil list
            return vol_name[5:]  # extracting the name after /dev/, e.g. /dev/[volume name]

        def get_vol_guid(self):
            '''Return the GUID of the volume.'''
            return self.get_attributes()['GUID']

        def get_attributes(self) -> dict:
            '''Return the attributes of the volume.'''
            return self.indaleko_record.Attributes

        def to_dict(self) -> dict:
            '''Return a dictionary representation of this object.'''
            return self.serialize()

        def to_json(self) -> dict:
            '''Return a JSON representation of this object.'''
            return self.serialize()

        def serialize(self) -> dict:
            '''Serialize the MacOSDriveInfo object to a dictionary.'''
            obj = IndalekoMachineConfigDataModel.MachineConfig(
                Captured = self.captured,
                Record = self.indaleko_record,
            )
            config_data = IndalekoMachineConfigDataModel.MachineConfig.serialize(obj)
            if isinstance(config_data, tuple):
                assert len(config_data) == 1, 'Serialized data is a multi-entry tuple'
                config_data = config_data[0]
            if hasattr(self, 'machine_id'):
                config_data['MachineId'] = self.machine_id
            config_data['_key'] = self.get_vol_guid()
            return config_data

    def extract_volume_info(self: 'IndalekoMacOSMachineConfig') -> None:
        '''Extract the volume information from the machine configuration.'''
        for volume_data in self.get_attributes()['VolumeInfo']:
            mdi = self.MacOSDriveInfo(self.machine_id, volume_data, self.captured)
            assert mdi.get_vol_guid() not in self.volume_data, \
                  f'Volume GUID {mdi.get_vol_guid()} already in volume_data'
            self.volume_data[mdi.get_vol_guid()] = mdi

    def get_volume_info(self: 'IndalekoMacOSMachineConfig') -> dict:
        '''This returns the volume information.'''
        return self.volume_data

    def map_drive_letter_to_volume_guid(self: 'IndalekoMacOSMachineConfig', drive_letter : str) -> str:
        '''Map a drive letter to a volume GUID.'''
        # Drive letters are not used in macOS
        return None

    def write_volume_info_to_db(self: 'IndalekoMacOSMachineConfig',
                                volume_data : MacOSDriveInfo) -> bool:
        '''Write the volume information to the database.'''
        assert isinstance(volume_data, self.MacOSDriveInfo), \
            'volume_data must be a MacOSDriveInfo'
        success = False
        try:
            self.collection.insert(volume_data.serialize(), overwrite=True)
            success = True
        except arango.exceptions.DocumentInsertError as error:
            print(f'Error inserting volume data: {error}')
            print(volume_data.serialize())
        return success

    def write_config_to_db(self) -> None:
        '''Write the machine configuration to the database.'''
        super().write_config_to_db()
        for _, vol_data in self.volume_data.items():
            if not self.write_volume_info_to_db(vol_data):
                print('DB write failed, aborting')
                break

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
            hostname = 'unknown'
            if 'hostname' in config:
                hostname = config['hostname']
            print('Configuration for machine:', hostname)
            print(f'\t    UUID: {config["_key"]}')
            print(f'\tCaptured: {config["Captured"]["Value"]}')
            print(f'\tPlatform: {config["Platform"]["software"]["OS"]}')
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
        assert os.path.exists(IndalekoMacOSMachineConfig.default_config_dir), f'config path {IndalekoMacOSMachineConfig.default_config_dir} does not exists'
        print('Listing machine configuration files in the default directory.')
        files = IndalekoMacOSMachineConfig.find_config_files(
            IndalekoMacOSMachineConfig.default_config_dir)
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
