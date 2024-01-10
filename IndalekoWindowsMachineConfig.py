import os
import json
from IndalekoRecord import IndalekoRecord
from IndalekoSource import IndalekoSource
from IndalekoCollections import IndalekoCollection, IndalekoCollections
from IndalekoDBConfig import IndalekoDBConfig
from IndalekoMachineConfig import IndalekoMachineConfig
import uuid
import datetime
import msgpack

class IndalekoWindowsMachineConfig(IndalekoMachineConfig):
    '''
    The IndalekoWindowsMachineConfig class is used to capture information about
    a Windows machine.  It is a subclass of IndalekoMachineConfig, which is
    shared across all platforms.
    '''

    WindowsMachineConfigFilePrefix = 'windows-hardware-info'

    def __init__(self : 'IndalekoWindowsMachineConfig'):
        '''
        This is a somewhat complex constructor.  The data it returns must be in
        the format of a record returned from the database.  However, if there is
        no entry in the database, one must be constructed from some external
        source, e.g., a "configuration file" of some sort.

        Thus, the process is:

            1. Given a machine_id, look for it in the database.
            2. If this is not found, take a config file and build a d
        '''
        pass

    @staticmethod
    def create_config_from_db(machine_id : str) -> 'IndalekoWindowsMachineConfig':
        '''
        This method creates a new IndalekoWindowsMachineConfig object from an
        existing database entry.
        '''
        assert IndalekoRecord.validate_uuid_string(machine_id), 'machine_id must be a valid UUID'
        pass

    @staticmethod
    def create_config_from_file(config_file : str) -> 'IndalekoWindowsMachineConfig':
        '''
        This method creates a new IndalekoWindowsMachineConfig object from an
        existing config file.
        '''
        pass

    @staticmethod
    def create_config_from_description(description: dict) -> 'IndalekoWindowsMachineConfig':
        '''
        This method creates a new IndalekoWindowsMachineConfig object from an
        existing description.
        '''
        pass

    def old_stuff(self):
        return
        # There are two sources of machine configuration data:
        # 1. The database
        # 2. The config file
        # I want to handle the four permutations of this as gracefully as
        # possible.
        # If neither, we're done - this is an error.
        # If we have a config file and the data is in the database, we use the
        # database and verify if they are the same.  We don't handle the
        # mismatch case yet.
        # If we have a config file and the data is not in the database, we add
        # it to the database.
        # Right now, we don't have another way to extract the machine ID except
        # from the config file, so the "no config file" isn't really handled.
        #
        # Step 1: find the config file.
        self.config_dir = IndalekoMachineConfig.DefaultConfigDir
        if 'config_dir' in kwargs:
            if kwargs['config_dir'] is not None and os.path.isdir(kwargs['config_dir']):
                self.config_dir = kwargs['config_dir']
        if 'config_file' in kwargs and kwargs['config_file'] is not None:
            if self.config_dir is not None:
                config_file = os.path.join(self.config_dir, kwargs['config_file'])
                assert os.path.exists(config_file) and os.path.isfile(config_file), f'Config file {config_file} does not exist'
        else:
            assert self.config_dir is not None, 'No config file or directory specified'
            config_file = self.find_config_files(self.config_dir)[-1]
        self.config_file = config_file
        if self.config_dir is None:
            self.config_file_data = self.load_config_file(self.config_file)
        else:
            self.config_file_data = self.load_config_file(os.path.join(self.config_dir, self.config_file))
        # Step 2: let's see if the machine ID was passed into us
        machine_id = None
        if 'machine_id' in kwargs and IndalekoRecord.validate_uuid_string(kwargs['machine_id']):
            machine_id = kwargs['machine_id']
        if machine_id is None:
            machine_id =self.config_file_data['MachineGuid']
        # Step 2: see if we can find this in the database
        self.machine_config_collection = None
        if 'collection' in kwargs:
            self.machine_config_collection = kwargs['collection']
        elif 'db' in kwargs:
            self.machine_config_collection = IndalekoCollections(db=kwargs['db'])['MachineConfig']
        else:
            self.machine_config_collection = IndalekoCollections().get_collection('MachineConfig')
        assert self.machine_config_collection is not None, 'MachineConfig collection not found'
        self.config_db_data = self.machine_config_collection.find_entries(_key=machine_id)
        if self.config_db_data is not None and len(self.config_db_data) > 0:
            assert type(self.config_db_data) is list, 'config_db_data should be a list'
            self.config_data = self.config_db_data[0]
        elif self.config_file_data is not None and len(self.config_file_data) > 0:
            self.config_data = self.config_file_data
            self.machine_config_collection.add_record(self.config_data)
        return

    staticmethod
    def add_config_to_db(config_data : dict, source : dict, timestamp : datetime = None) -> 'IndalekoWindowsMachineConfig':
        '''
        This method takes the name of a config file, loads it, and adds it to
        the database.
        '''
        pass


    def add_config_to_db(self: 'IndalekoWindowsMachineConfig', config_data : dict, source : dict, timestamp : datetime = None) -> None:
        assert type(source) is dict, 'source must be a dict'
        assert 'Identifier' in source, 'source must contain an Identifier field'
        assert 'Version' in source, 'source must contain a Version field'
        assert 'MachineGuid' in config_data, 'MachineGuid must be in config_data'
        assert 'OperatingSystem' in config_data, 'OperatingSystem must be in config_data'
        assert 'CPU' in config_data, 'CPU must be in config_data'
        if timestamp is None:
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        config_info = {
            'platform' : {
                'software' : {
                    'OS' : config_data['OperatingSystem']['Caption'],
                    'Architecture' : config_data['OperatingSystem']['OSArchitecture'],
                    'Version' : config_data['OperatingSystem']['Version']
                },
                'hardware' : {
                    'CPU' : config_data['CPU']['Name'],
                    'Version' : config_data['CPU']['Name'],
                    'Cores' : config_data['CPU']['Cores'],
                },
            },
            'source' : source['identifier'],
            'version' : source['version'],
            'captured' : {
                'Label' : 'Timestamp',
                'Value' : timestamp,
            },
            'Attributes' : config_data,
            'Data' : config_data.decode('ascii'),
            '_key' : config_data['MachineGuid']
        }
        assert self.machine_config_collection is not None, 'MachineConfig collection not found'
        self.machine_config_collection.add_record(config_data)
        return

    @staticmethod
    def find_config_files(dir : str) -> list:
        return [x for x in os.listdir(dir)
                if x.startswith(IndalekoWindowsMachineConfig.WindowsMachineConfigFilePrefix)
                and x.endswith('.json')]


    @staticmethod
    def load_config_file(file: str) -> dict:
        config_data = None
        assert os.path.exists(file) and os.path.isfile(file), 'config file does not exit or is not a file'
        with open(file, 'rt', encoding='utf-8-sig') as fd:
            config_data = json.load(fd)
        return config_data


    def set_config_file(self : 'IndalekoWindowsMachineConfig', config_file : str) -> None:
        self.config_file = os.path.join(self.config_dir, config_file)
        self.config_data = IndalekoWindowsMachineConfig.load_config_file(self.config_file)
        return

    def get_config_data(self : 'IndalekoWindowsMachineConfig') -> dict:
        assert self.config_file is not None, 'No config file specified/found'
        if self.config_dir is not None:
            config_file = os.path.join(self.config_dir, self.config_file)
        else:
            config_file = self.config_file
        if self.config_data is None:
            self.config_data = IndalekoWindowsMachineConfig.load_config_file(config_file)[0]
        return self.config_data

    def find_config_files(self : 'IndalekoWindowsMachineConfig', config_dir  : str  = './config') -> list:
        return [x for x in os.listdir(config_dir) if x.startswith(self.WindowsMachineConfigFilePrefix) and x.endswith('.json')]

    def get_config_dir(self : 'IndalekoWindowsMachineConfig') -> str:
        return self.config_dir

    def get_config_file(self : 'IndalekoWindowsMachineConfig') -> str:
        return self.config_file


    def __find_hw_info_file__(self : 'IndalekoWindowsMachineConfig', configdir : str = './config'):
        candidates = [x for x in os.listdir(configdir) if x.startswith(self.WindowsMachineConfigFilePrefix) and x.endswith('.json')]
        assert len(candidates) > 0, 'At least one windows-hardware-info file should exist'
        for candidate in candidates:
            file, guid, timestamp = self.get_guid_timestamp_from_file_name(candidate)
        return configdir + '/' + candidates[-1]

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

    @staticmethod
    def get_guid_timestamp_from_file_name(file_name : str) -> tuple:
        '''
        Get the machine configuration captured by powershell.
        Note that this PS script requires admin privileges so it might
        be easier to do this in an application that elevates on Windows so it
        can be done dynamically.  For now, we assume it has been captured.
        '''
        # Regular expression to match the GUID and timestamp
        pattern = r"windows-hardware-info-(?P<guid>[a-fA-F0-9\-]+)-(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.\d+Z)\.json"
        match = re.match(pattern, file_name)
        assert match, 'Filename format not recognized.'
        guid = uuid.UUID(match.group("guid"))
        timestamp = match.group("timestamp").replace("-", ":")
        # %f can only handle up to 6 digits and it seems Windows gives back
        # more sometimes. Note this truncates, it doesn't round.  I doubt
        # it matters.
        decimal_position = timestamp.rindex('.')
        if len(timestamp) - decimal_position - 2 > 6:
            timestamp = timestamp[:decimal_position + 7] + "Z"
        timestamp = datetime.datetime.strptime(timestamp, "%Y:%m:%dT%H:%M:%S.%fZ")
        return (file_name, guid, timestamp)

    @staticmethod
    def get_most_recent_config_file(config_dir : str):
        candidates = [x for x in os.listdir(config_dir) if x.startswith('windows-hardware-info') and x.endswith('.json')]
        assert len(candidates) > 0, 'At least one windows-hardware-info file should exist'
        candidate_files = [(timestamp, filename) for filename, guid, timestamp in [IndalekoWindowsMachineConfig.get_guid_timestamp_from_file_name(x) for x in candidates]]
        candidate_files.sort(key=lambda x: x[0])
        return candidate_files[0][1]
