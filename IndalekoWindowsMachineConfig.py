import os
import json
from IndalekoRecord import IndalekoRecord
from IndalekoDBConfig import IndalekoDBConfig
from IndalekoMachineConfig import IndalekoMachineConfig
import uuid
import datetime
import msgpack
import argparse
import re
import base64

class IndalekoWindowsMachineConfig(IndalekoMachineConfig):
    '''
    The IndalekoWindowsMachineConfig class is used to capture information about
    a Windows machine.  It is a specialization of the IndalekoMachineConfig
    class, which is shared across all platforms.
    '''

    WindowsMachineConfigFilePrefix = 'windows-hardware-info'

    WindowsMachineConfig_UUID = '3360a328-a6e9-41d7-8168-45518f85d73e'

    WindowsMachineConfigService = {
        'name': 'WindowsMachineConfig',
        'description': 'This service provides the configuration information for a Windows machine.',
        'version': '1.0',
        'identifier': WindowsMachineConfig_UUID,
        'created': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'type': 'Indexer',
    }



    def __init__(self : 'IndalekoWindowsMachineConfig', timestamp : datetime = None, db : IndalekoDBConfig = None):
        super().__init__(timestamp=timestamp, db=db)
        self.extract_volume_info()

    @staticmethod
    def find_config_files(dir : str) -> list:
        return [x for x in os.listdir(dir)
                if x.startswith(IndalekoWindowsMachineConfig.WindowsMachineConfigFilePrefix)
                and x.endswith('.json')]

    @staticmethod
    def load_config_from_file(config_dir : str = None, config_file : str = None) -> 'IndalekoWindowsMachineConfig':
        config_data ={}
        if config_dir is None and config_file is None:
            # nothing specified, so we'll search and find
            config_dir = IndalekoWindowsMachineConfig.DefaultConfigDir
        if config_file is None:
            # now we have a config_dir, so we'll find the most recent file
            assert config_dir is not None, 'config_dir must be specified'
            config_file = IndalekoWindowsMachineConfig.get_most_recent_config_file(config_dir)
            config_file = os.path.join(config_dir, config_file)
        if config_file is not None:
            _, guid, timestamp = IndalekoWindowsMachineConfig.get_guid_timestamp_from_file_name(config_file)
            print(42, timestamp)
            assert os.path.exists(config_file), f'Config file {config_file} does not exist'
            assert os.path.isfile(config_file), f'Config file {config_file} is not a file'
            with open(config_file, 'rt', encoding='utf-8-sig') as fd:
                config_data = json.load(fd)
            assert str(guid) == config_data['MachineGuid'], f'GUID mismatch: {guid} != {config_data["MachineGuid"]}'
        print(json.dumps(config_data, indent=4))
        config = IndalekoWindowsMachineConfig.build_config( os=config_data['OperatingSystem']['Caption'],
                                                            arch=config_data['OperatingSystem']['OSArchitecture'],
                                                            os_version=config_data['OperatingSystem']['Version'],
                                                            cpu=config_data['CPU']['Name'],
                                                            cpu_version=config_data['CPU']['Name'],
                                                            cpu_cores=config_data['CPU']['Cores'],
                                                            source_id=IndalekoWindowsMachineConfig.WindowsMachineConfigService['identifier'],
                                                            source_version=IndalekoWindowsMachineConfig.WindowsMachineConfigService['version'],
                                                            timestamp=timestamp.isoformat(),
                                                            attributes=config_data,
                                                            data=base64.b64encode(msgpack.packb(config_data)).decode('ascii'),
                                                            machine_id=config_data['MachineGuid']
                                                        )
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
        candidates = [x for x in os.listdir(config_dir) if x.startswith('windows-hardware-info') and x.endswith('.json')]
        assert len(candidates) > 0, 'At least one windows-hardware-info file should exist'
        candidate_files = [(timestamp, filename) for filename, guid, timestamp in [IndalekoWindowsMachineConfig.get_guid_timestamp_from_file_name(x) for x in candidates]]
        candidate_files.sort(key=lambda x: x[0])
        candidate = candidate_files[0][1]
        print(candidate)
        if config_dir is not None:
            candidate = os.path.join(config_dir, candidate)
        return candidate

    def write_config_to_db(self) -> None:
        '''
        This method writes the configuration to the database.
        '''
        assert hasattr(self, 'machine_id'), 'machine_id must be set before writing to the database.'
        assert self.validate_uuid_string(self.machine_id), f'machine_id {self.machine_id} is not a valid UUID.'
        self.collection.insert(self.to_json(), overwrite=True)

    class WindowsDriveInfo(IndalekoRecord):

        WindowsDriveInfo_UUID_str = 'a0b3b3e0-0b1a-4e1f-8b1a-4e1f8b1a4e1f'
        WindowsDriveInfo_UUID = uuid.UUID(WindowsDriveInfo_UUID_str)
        WindowsDriveInfo_Version = '1.0'
        WindowsDriveInfo_Description = 'Windows Drive Info'

        def __init__(self, drive_data : dict) -> None:
            assert 'GUID' not in drive_data, 'GUID should not be in drive_data'
            assert 'UniqueId' in drive_data, 'UniqueId must be in drive_data'
            assert drive_data['UniqueId'].startswith('\\\\?\\Volume{')
            drive_data['GUID'] = self.__find_volume_guid__(drive_data['UniqueId'])
            super().__init__(msgpack.packb(drive_data),
                             drive_data,
                             {
                                'Identifier' : self.WindowsDriveInfo_UUID_str,
                                'Version' : self.WindowsDriveInfo_Version,
                             })


        @staticmethod
        def __find_volume_guid__(vol_name : str) -> str:
            assert vol_name is not None, 'Volume name cannot be None'
            assert type(vol_name) is str, 'Volume name must be a string'
            assert vol_name.startswith('\\\\?\\Volume{')
            return vol_name[11:-2]

        def get_vol_guid(self):
            return self.get_attributes()['GUID']

    def extract_volume_info(self: 'IndalekoWindowsMachineConfig') -> None:
        self.volume_data = {}
        for voldata in self.config_data['VolumeInfo']:
            wdi = self.WindowsDriveInfo(voldata)
            assert wdi.get_vol_guid() not in self.volume_data, f'Volume GUID {wdi.get_vol_guid()} already in volume_data'
            self.volume_data[wdi.get_vol_guid()] = wdi

    def get_volume_info(self: 'IndalekoWindowsMachineConfig') -> dict:
        return self.volume_data


def main():
    parser = argparse.ArgumentParser()
    config_file = IndalekoWindowsMachineConfig.get_most_recent_config_file(IndalekoWindowsMachineConfig.DefaultConfigDir)
    print(config_file)
    _, guid, timestamp = IndalekoWindowsMachineConfig.get_guid_timestamp_from_file_name(config_file)
    file_record = IndalekoWindowsMachineConfig.load_config_from_file(IndalekoWindowsMachineConfig.DefaultConfigDir, config_file)
    print('file_record:')
    print(file_record.to_dict())
    assert parser is not None, 'Parser must  be valid'
    # db_record = IndalekoWindowsMachineConfig.load_config_from_db(str(guid))
    # if db_record is None:
    #    print(f'GUID {guid} not found in database')
    #else:
    #    print(f'GUID {guid} found in database')
    #    print(db_record.to_json())

if __name__ == "__main__":
    main()
