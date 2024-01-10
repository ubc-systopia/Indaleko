import argparse
import json
import os
from IndalekoRecord import IndalekoRecord
from IndalekoCollections import IndalekoCollections
from IndalekoDBConfig import IndalekoDBConfig
from IndalekoMachineConfigSchema import IndalekoMachineConfigSchema
import datetime

class IndalekoMachineConfig(IndalekoRecord):
    '''
    This is the generic class for machine config.  It should be used to create
    platform specific machine configuration classes.
    '''

    DefaultConfigDir = './config'
    IndalekoMachineConfig_UUID_str = '811c33bb-b7ce-4903-a441-1c2d228a38ec'
    IndalekoMachineConfig_version_str = '1.0.0'

    Schema = IndalekoMachineConfigSchema

    def __init__(self: 'IndalekoMachineConfig', timestamp : datetime = None, db : IndalekoDBConfig = None):
        '''
        Constructor for the IndalekoMachineConfig class. Takes a
        set of configuration data as a parameter and initializes the object.
        '''
        if timestamp is None:
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        super().__init__(b'', {},
                        {
                            'Identifier' : IndalekoMachineConfig.IndalekoMachineConfig_UUID_str,
                            'Version' : IndalekoMachineConfig.IndalekoMachineConfig_version_str
                        })
        self.platform = {}
        self.captured = {
            'Label' : 'Timestamp',
            'Value' : timestamp,
        }
        collections = IndalekoCollections(db_config=db)
        self.collection = collections.get_collection('MachineConfig')
        assert self.collection is not None, 'MachineConfig collection does not exist.'

    def set_platform(self, platform : dict) -> None:
        '''
        This method sets the platform information for the machine.
        '''
        assert type(platform) is dict, f'platform must be a dict (not {type(platform)})'
        assert 'software' in platform, 'platform must contain a software field'
        assert type(platform['software']) is dict, f'platform["software"] must be a dictionary, not {type(platform["software"])}'
        assert type(platform['software']['OS']) is str, f'platform must contain a string OS field, not {type(platform["software"]["OS"])}'
        assert type(platform['software']['Version']) is str, 'platform must contain a string version field'
        assert type(platform['software']['Architecture']) is str, 'platform must contain a string architecture field'
        assert 'hardware' in platform, 'platform must contain a hardware field'
        assert type(platform['hardware']) is dict, 'platform["hardware"] must be a dictionary'
        assert type(platform['hardware']['CPU']) is str, 'platform must contain a string CPU field'
        assert type(platform['hardware']['Version']) is str, 'platform must contain a string version field'
        assert type(platform['hardware']['Cores']) is int, 'platform must contain an integer cores field'
        self.platform = platform
        return self

    def get_platform(self) -> dict:
        '''
        This method returns the platform information for the machine.
        '''
        if hasattr(self, 'platform'):
            return self.platform
        return None

    def set_captured(self, timestamp : datetime) -> None:
        '''
        This method sets the timestamp for the machine configuration.
        '''
        if type(timestamp) is dict:
            assert 'Label' in timestamp, 'timestamp must contain a Label field'
            assert timestamp['Label'] == 'Timestamp', 'timestamp must have a Label of Timestamp'
            assert 'Value' in timestamp, 'timestamp must contain a Value field'
            assert type(timestamp['Value']) is str, 'timestamp must contain a string Value field'
            assert self.validate_iso_timestamp(timestamp['Value']), f'timestamp {timestamp["Value"]} is not a valid ISO timestamp'
            self.captured = {
                'Label' : 'Timestamp',
                'Value' : timestamp['Value'],
            }
        elif type(timestamp) is datetime:
            timestamp = timestamp.isoformat()
        else:
            assert type(timestamp) is str, f'timestamp must be a string or timestamp (not {type(timestamp)})'
        self.captured = {
            'Label' : 'Timestamp',
            'Value' : timestamp,
        }
        return self

    def get_captured(self) -> datetime:
        '''
        This method returns the timestamp for the machine configuration.
        '''
        if hasattr(self, 'captured'):
            return self.captured
        return None

    def parse_config_file(self, config_data : dict) -> None:
        '''
        This method parses the configuration data from the config file.
        '''
        assert False, 'This method should be overridden by the derived classes.'

    @staticmethod
    def load_config_from_file(config_file : str) -> dict:
        '''
        This method creates a new IndalekoMachineConfig object from an
        existing config file.
        '''
        assert config_file is not None, "No config file specified."
        assert os.path.exists(config_file), f"Config file {config_file} does not exist."
        assert os.path.isfile(config_file), f"Config file {config_file} is not a file."
        with open(config_file, 'rt', encoding='utf-8-sig') as fd:
            config_data = json.load(fd)
        # we don't have enough information here to build a valid record yet.
        return config_data # TODO: get enough info to build a valid record!

    @staticmethod
    def load_config_from_db(machine_id : str) -> 'IndalekoMachineConfig':
        '''
        This method loads the configuration from the database.
        '''
        assert IndalekoMachineConfig.validate_uuid_string(machine_id), f'machine_id {machine_id} is not a valid UUID.'
        collections = IndalekoCollections()
        machine_config_collection = collections.get_collection('MachineConfig')
        entries = machine_config_collection.find_entries(_key=machine_id)
        if len(entries) == 0:
            return None # not found
        assert len(entries) == 1, f'Found {len(entries)} entries for machine_id {machine_id} - multiple entries case not handled.'
        entry = entries[0]
        print(json.dumps(entry['platform'], indent=4))
        machine_config = IndalekoMachineConfig()
        machine_config.set_platform(entry['platform'])
        # temporary: I've changed the shape of the database, so I'll need to
        # work around it temporarily
        if type(entry['source'] is str) and 'version' in entry:
            machine_config.set_source({
                'Identifier' : entry['source'],
                'Version' : entry['version'],
            })
        else:
            assert type(entry['source']) is dict, f'entry["source"] must be a dict, not {type(entry["source"])}'
            machine_config.set_source(entry['source'])
        machine_config.set_captured(entry['captured'])
        machine_config.set_base64_data(entry['Data'])
        machine_config.set_attributes(entry['Attributes'])
        return machine_config

    def to_json(self, indent : int = 4) -> str:
        '''
        This method returns the JSON representation of the machine config.
        '''
        record = super().to_dict()
        record['platform'] = self.platform
        record['captured'] = self.captured
        return json.dumps(record, indent=indent)



def main():
    starttime = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    parser = argparse.ArgumentParser()
    logfile = f'indalekomachineconfig-test-{starttime}.log'
    parser = argparse.ArgumentParser(description='Test base class for MachineConfig for the Indaleko database.')
    parser.add_argument('--machine_id', '-m', help='Machine ID to load from database', default='2e169bb7-0024-4dc1-93dc-18b7d2d28190')
    parser.add_argument('--log', '-l', help='Log file to use', default=logfile)
    parser.add_argument('--logdir', help='Log directory to use', default='./logs')
    args = parser.parse_args()
    if args.machine_id is not None:
        assert IndalekoMachineConfig.validate_uuid_string(args.machine_id), f'machine_id {args.machine_id} is not a valid UUID.'
        # look it up in the database
        machine_config = IndalekoMachineConfig.load_config_from_db(args.machine_id)
        print(machine_config.to_json())


if __name__ == "__main__":
    main()



