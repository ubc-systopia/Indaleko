"""
This class is used to manage the configuration information for a Windows
machine.

Indaleko Windows Machine Configuration
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
"""
import os
import json
import uuid
import datetime
import argparse
import re
import arango

from icecream import ic

from Indaleko import Indaleko
from IndalekoMachineConfigDataModel import IndalekoMachineConfigDataModel
from IndalekoMachineConfig import IndalekoMachineConfig
from IndalekoRecordDataModel import IndalekoRecordDataModel
from IndalekoDataModel import IndalekoDataModel

class IndalekoWindowsMachineConfig(IndalekoMachineConfig):
    '''
    The IndalekoWindowsMachineConfig class is used to capture information about
    a Windows machine.  It is a specialization of the IndalekoMachineConfig
    class, which is shared across all platforms.
    '''

    windows_machine_config_file_prefix = 'windows-hardware-info'
    windows_machine_config_uuid_str = '3360a328-a6e9-41d7-8168-45518f85d73e'
    windows_machine_config_service_name = "Windows Machine Configuration"
    windows_machine_config_service_description = \
        "This service provides the configuration information for a Windows machine."
    windows_machine_config_service_version = "1.0"

    windows_machine_config_service = {
        'service_name' : windows_machine_config_service_name,
        'service_description' : windows_machine_config_service_description,
        'service_version' : windows_machine_config_service_version,
        'service_type' : 'Machine Configuration',
        'service_identifier' : windows_machine_config_uuid_str,
    }



    def __init__(self : 'IndalekoWindowsMachineConfig',
                 **kwargs):
        ic(kwargs)
        self.service_registration = IndalekoMachineConfig.register_machine_configuration_service(
            **IndalekoWindowsMachineConfig.windows_machine_config_service
        )
        self.db = kwargs.get('db', None)
        super().__init__(**kwargs)
        self.volume_data = {}

    @staticmethod
    def find_config_files(directory : str, prefix : str = None, suffix : str = '.json') -> list:
        '''This looks for configuration files in the given directory.'''
        if prefix is None:
            prefix = IndalekoWindowsMachineConfig.windows_machine_config_file_prefix
        return IndalekoMachineConfig.find_config_files(
            directory,
            prefix
        )

    @staticmethod
    def find_configs_in_db(source_id : str = windows_machine_config_uuid_str) -> list:
        '''Find the machine configurations in the database for Windows.'''
        return [
            IndalekoMachineConfig.serialize(config)
            for config in IndalekoMachineConfig.lookup_machine_configurations(source_id=source_id)
        ]

    @staticmethod
    def load_config_from_file(config_dir : str = None,
                              config_file : str = None) -> 'IndalekoWindowsMachineConfig':
        config_data ={}
        if config_dir is None and config_file is None:
            # nothing specified, so we'll search and find
            config_dir = IndalekoWindowsMachineConfig.default_config_dir
        if config_file is None:
            # now we have a config_dir, so we'll find the most recent file
            assert config_dir is not None, 'config_dir must be specified'
            config_file = IndalekoWindowsMachineConfig.get_most_recent_config_file(config_dir)
        if config_file is not None:
            _, guid, timestamp = IndalekoWindowsMachineConfig.get_guid_timestamp_from_file_name(
                config_file)
            assert os.path.exists(config_file), f'Config file {config_file} does not exist'
            assert os.path.isfile(config_file), f'Config file {config_file} is not a file'
            with open(config_file, 'rt', encoding='utf-8-sig') as fd:
                config_data = json.load(fd)
            if 'MachineUUID' not in config_data:
                config_data['MachineUUID'] = config_data['MachineGuid']
            assert str(guid) == config_data['MachineUUID'],\
                  f'GUID mismatch: {guid} != {config_data["MachineUUID"]}'
        ic(config_data)
        software = IndalekoMachineConfigDataModel.Software(
            OS = config_data['OperatingSystem']['Caption'],
            Version = config_data['OperatingSystem']['Version'],
            Architecture = config_data['OperatingSystem']['OSArchitecture'],
            Hostname = config_data['Hostname'],
        )
        hardware = IndalekoMachineConfigDataModel.Hardware(
            CPU = config_data['CPU']['Name'],
            Version = '',
            Cores = config_data['CPU']['Cores'],
        )
        captured = IndalekoMachineConfigDataModel.Captured(
            Label = IndalekoMachineConfig.indaleko_machine_config_captured_label_uuid,
            Value = timestamp
        )
        platform = IndalekoMachineConfigDataModel.Platform(
            software = software,
            hardware = hardware,
        )
        record = IndalekoRecordDataModel.IndalekoRecord(
            SourceIdentifier = IndalekoDataModel.SourceIdentifier(
                Identifier = IndalekoWindowsMachineConfig.windows_machine_config_service['service_identifier'],
                Version = IndalekoWindowsMachineConfig.windows_machine_config_service['service_version'],
                Description = IndalekoWindowsMachineConfig.windows_machine_config_service['service_description']
            ),
            Timestamp = timestamp,
            Data = Indaleko.encode_binary_data(config_data),
            Attributes = config_data
        )
        machine_config_data = {
            'Platform' : IndalekoMachineConfigDataModel.Platform.serialize(platform),
            'Captured' : IndalekoMachineConfigDataModel.Captured.serialize(captured),
            'Record' : IndalekoRecordDataModel.IndalekoRecord.serialize(record),
        }
        if 'MachineUUID' not in machine_config_data:
            machine_config_data['MachineUUID'] = config_data['MachineGuid']
        if 'Hostname' not in machine_config_data:
            machine_config_data['Hostname'] = config_data['Hostname']
        config = IndalekoWindowsMachineConfig(data=machine_config_data)
        ic(IndalekoMachineConfigDataModel.MachineConfig.serialize(config.machine_config))
        config.write_config_to_db()
        if hasattr(config, 'extract_volume_info'):
            getattr(config, 'extract_volume_info')()
        return config

    @staticmethod
    def get_guid_timestamp_from_file_name(file_name : str) -> tuple:
        '''
        Get the machine configuration captured by powershell.
        Note that this PS script requires admin privileges so it might
        be easier to do this in an application that elevates on Windows so it
        can be done dynamically.  For now, we assume it has been captured.
        '''
        # Regular expression to match the GUID and timestamp
        pattern = r"(?:.*[/\\])?windows-hardware-info-(?P<guid>[a-fA-F0-9\-]+)-(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.\d+Z)\.json"
        match = re.match(pattern, file_name)

        assert match, f'Filename format not recognized for {file_name}.'
        guid = uuid.UUID(match.group("guid"))
        timestamp = match.group("timestamp").replace("-", ":")
        assert timestamp[-1] == 'Z', 'Timestamp must end with Z'
        # %f can only handle up to 6 digits and it seems Windows gives back
        # more sometimes. Note this truncates, it doesn't round.  I doubt
        # it matters.
        timestamp_parts = timestamp.split('.')
        fractional_part = timestamp_parts[1][:6] # truncate to 6 digits
        ymd, hms = timestamp_parts[0].split('T')
        timestamp = ymd.replace(':', '-') + 'T' + hms + '.' + fractional_part + '+00:00'
        timestamp = datetime.datetime.fromisoformat(timestamp)
        return (file_name, guid, timestamp)

    @staticmethod
    def get_most_recent_config_file(config_dir : str) -> str:
        '''Get the most recent machine configuration file.'''
        candidates = [x for x in os.listdir(config_dir) if
                      x.startswith('windows-hardware-info') and x.endswith('.json')]
        assert len(candidates) > 0, 'At least one windows-hardware-info file should exist'
        candidate_files = [(timestamp, filename)
                           for filename, guid, timestamp in
                           [IndalekoWindowsMachineConfig.get_guid_timestamp_from_file_name(x)
                            for x in candidates]]
        candidate_files.sort(key=lambda x: x[0])
        candidate = candidate_files[0][1]
        if config_dir is not None:
            candidate = os.path.join(config_dir, candidate)
        return candidate

    class WindowsDriveInfo:
        '''This class is used to capture information about a Windows drive.'''
        WindowsDriveInfo_UUID_str = 'a0b3b3e0-0b1a-4e1f-8b1a-4e1f8b1a4e1f'
        WindowsDriveInfo_UUID = uuid.UUID(WindowsDriveInfo_UUID_str)
        WindowsDriveInfo_Version = '1.0'
        WindowsDriveInfo_Description = 'Windows Drive Info'

        def __init__(self, machine_id : str, platform : dict, drive_data : dict, captured: dict) -> None:
            assert 'GUID' not in drive_data, 'GUID should not be in drive_data'
            assert 'UniqueId' in drive_data, 'UniqueId must be in drive_data'
            assert Indaleko.validate_uuid_string(machine_id), 'machine_id must be a valid UUID'
            self.machine_id = machine_id
            self.attributes = drive_data.copy()
            self.volume_guid = str(uuid.uuid4())
            if self.attributes['UniqueId'].startswith('\\\\?\\Volume{'):
                self.volume_guid = self.__find_volume_guid__(drive_data['UniqueId'])
            self.attributes['GUID'] = self.volume_guid
            ic(self.attributes)
            self.machine_config = IndalekoMachineConfigDataModel.MachineConfig(
                Platform=IndalekoMachineConfigDataModel.Platform.deserialize(platform),
                Captured=IndalekoMachineConfigDataModel.Captured.deserialize(captured),
                Record=IndalekoRecordDataModel.IndalekoRecord(
                    SourceIdentifier=IndalekoDataModel.SourceIdentifier(
                        Identifier=self.WindowsDriveInfo_UUID_str,
                        Version=self.WindowsDriveInfo_Version,
                        Description=self.WindowsDriveInfo_Description
                    ),
                    Timestamp=datetime.datetime.fromisoformat(captured['Value']),
                    Data=Indaleko.encode_binary_data(drive_data),
                    Attributes=drive_data
                ),
            )
            return

        @staticmethod
        def __find_volume_guid__(vol_name : str) -> str:
            assert vol_name is not None, 'Volume name cannot be None'
            assert isinstance(vol_name, str), 'Volume name must be a string'
            assert vol_name.startswith('\\\\?\\Volume{')
            return vol_name[11:-2]

        def get_vol_guid(self):
            '''Return the GUID of the volume.'''
            return self.volume_guid

        def serialize(self) -> dict:
            '''Serialize the WindowsDriveInfo object.'''
            assert isinstance(self.machine_config, IndalekoMachineConfigDataModel.MachineConfig)
            config_data = IndalekoMachineConfigDataModel.MachineConfig.serialize(self.machine_config)
            if hasattr(self, 'machine_id'):
                config_data['MachineUUID'] = self.machine_id
            config_data['_key'] = self.get_vol_guid()
            return config_data

        def to_dict(self):
            '''Return the WindowsDriveInfo object as a dictionary.'''
            return self.serialize()

        def __getitem__(self, key):
            '''Return the item from the dictionary.'''
            return self.attributes[key]

    def extract_volume_info(self: 'IndalekoWindowsMachineConfig') -> None:
        '''Extract the volume information from the machine configuration.'''
        ic('Extracting volume information')
        config_data = self.serialize()
        volume_info = config_data['Record']['Attributes']['VolumeInfo']
        machine_id = config_data['Record']['Attributes']['MachineUUID']
        captured = config_data['Captured']
        platform = config_data['Platform']
        ic(volume_info)
        for volume in volume_info:
            wdi = self.WindowsDriveInfo(machine_id, platform, volume, captured)
            ic(volume)
            assert wdi.get_vol_guid() not in self.volume_data,\
                  f'Volume GUID {wdi.get_vol_guid()} already in volume_data'
            self.volume_data[wdi.get_vol_guid()] = wdi
        return

    def get_volume_info(self: 'IndalekoWindowsMachineConfig') -> dict:
        '''This returns the volume information.'''
        return self.volume_data

    def map_drive_letter_to_volume_guid(self: 'IndalekoWindowsMachineConfig',
                                        drive_letter : str) -> str:
        '''Map a drive letter to a volume GUID.'''
        assert drive_letter is not None, 'drive_letter must be a valid string'
        assert len(drive_letter) == 1, 'drive_letter must be a single character'
        drive_letter = drive_letter.upper()
        for vol in self.get_volume_info().values():
            if vol['DriveLetter'] == drive_letter:
                return vol['GUID']
        return None

    def write_volume_info_to_db(self: 'IndalekoWindowsMachineConfig',
                                volume_data : WindowsDriveInfo) -> bool:
        '''Write the volume information to the database.'''
        assert isinstance(volume_data, self.WindowsDriveInfo), \
            'volume_data must be a WindowsDriveInfo'
        success = False
        try:
            self.collection.insert(volume_data.serialize(), overwrite=True)
            success = True
        except arango.exceptions.DocumentInsertError as error:
            print(f'Error inserting volume data: {error}')
            print(volume_data.serialize())
        return success

    def write_config_to_db(self, overwrite : bool = True) -> None:
        '''Write the machine configuration to the database.'''
        super().write_config_to_db(overwrite=overwrite)
        for _, vol_data in self.volume_data.items():
            if not self.write_volume_info_to_db(vol_data):
                print('DB write failed, aborting')
                break


def main():
    '''This is the main handler for the Indaleko Windows Machine Config
    service.'''
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
        configs = IndalekoWindowsMachineConfig.find_configs_in_db()
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
    if args.delete:
        assert args.uuid is not None, \
            'UUID must be specified when deleting a machine configuration.'
        assert Indaleko.validate_uuid_string(args.uuid),\
            f'UUID {args.uuid} is not a valid UUID.'
        print(f'Deleting machine configuration with UUID {args.uuid}')
        IndalekoWindowsMachineConfig.delete_config_in_db(args.uuid)
        return
    if args.files:
        print('Listing machine configuration files in the default directory.')
        files = IndalekoWindowsMachineConfig.find_config_files(
            IndalekoWindowsMachineConfig.default_config_dir)
        for file in files:
            print(file)
        return
    if args.add:
        print('Adding machine configuration to the database.')
        config = IndalekoWindowsMachineConfig.load_config_from_file()
        config.write_config_to_db()

        return

if __name__ == "__main__":
    main()
