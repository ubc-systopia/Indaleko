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
import datetime
import json
import uuid
import socket
import platform
import os
import logging
import re

import arango

from icecream import ic

from IndalekoCollections import IndalekoCollections
from IndalekoDBConfig import IndalekoDBConfig
from IndalekoMachineConfigSchema import IndalekoMachineConfigSchema
from IndalekoDataModel import IndalekoDataModel
from IndalekoRecordDataModel import IndalekoRecordDataModel
from IndalekoMachineConfigDataModel import IndalekoMachineConfigDataModel
from Indaleko import Indaleko
from IndalekoServiceManager import IndalekoServiceManager
from IndalekoRecordDataModel import IndalekoRecordDataModel
from IndalekoDataModel import IndalekoDataModel
from IndalekoMachineConfigDataModel import IndalekoMachineConfigDataModel
from IndalekoLogging import IndalekoLogging


class IndalekoMachineConfig:
    """
    This is the generic class for machine config.  It should be used to create
    platform specific machine configuration classes.
    """

    indaleko_machine_config_uuid_str = "e65e412e-7862-4d81-affd-2bbd4f6b9a01"
    indaleko_machine_config_uuid = uuid.UUID(indaleko_machine_config_uuid_str)
    indaleko_machine_config_version_str = "1.0"
    indaleko_machine_config_captured_label_str = "eb7eaeed-6b21-4b6a-a586-dddca6a1d5a4"
    indaleko_machine_config_captured_label_uuid = uuid.UUID(indaleko_machine_config_captured_label_str)

    Schema = IndalekoMachineConfigSchema().get_json_schema()

    def __new_init__(self, **kwargs):
        '''This is the constructor for the IndalekoMachineConfig class.'''
        self.args = kwargs
        if 'Record' not in kwargs:
            ic(kwargs)
            self.legacy_constructor()
        else:
            self.machine_config = IndalekoMachineConfigDataModel.MachineConfig.deserialize(
                kwargs
            )

    def legacy_constructor(self):
        '''Create an object using the old format.'''
        raise NotImplementedError('This method has not been implemented yet.')

    def __init__(self, **kwargs):
        '''Set up a new machine configuration object.'''
        self.args = kwargs
        self.timestamp = kwargs.get('timestamp', datetime.datetime.now(datetime.UTC))
        if isinstance(self.timestamp, str):
            assert Indaleko.validate_iso_timestamp(
                self.timestamp
            ), f'Timestamp {self.timestamp} is not a valid ISO timestamp'
            self.timestamp = datetime.datetime.fromisoformat(self.timestamp)
        assert isinstance(self.timestamp, datetime.datetime), f'Timestamp must be a datetime object, not {type(self.timestamp)}'
        if 'Record' not in kwargs:
            record = IndalekoRecordDataModel.IndalekoRecord(
                Data=kwargs['raw_data'],
                Attributes=kwargs['Attributes'],
                SourceIdentifier=IndalekoDataModel.SourceIdentifier(
                    Identifier=kwargs['source']['Identifier'],
                    Version=kwargs['source']['Version'],
                    Description=None
                ),
                Timestamp = self.timestamp
            )
            kwargs['Record'] = IndalekoRecordDataModel.IndalekoRecord.serialize(record)
            del kwargs['raw_data']
            del kwargs['Attributes']
            del kwargs['source']
            if 'timestamp' in kwargs:
                del kwargs['timestamp']
        machine_id = kwargs['machine_id'] # UUID to use for this machine
        assert Indaleko.validate_uuid_string(
            machine_id
        ), f"machine_id {machine_id} is not a valid UUID."
        self.machine_id = machine_id
        del kwargs['machine_id']
        self.hostname = kwargs.get('hostname', machine_id)
        ic(kwargs)
        self.machine_config = IndalekoMachineConfigDataModel.MachineConfig.deserialize(kwargs)
        if 'db' in kwargs:
            db = kwargs['db']
        else:
            db = IndalekoDBConfig()
        if 'collection' in kwargs:
            self.collection = kwargs['collection']
        else:
            self.collection = IndalekoCollections(db_config=db).get_collection(Indaleko.Indaleko_MachineConfig)



    def __init_2__(self, **kwargs):
        '''This is the constructor for the IndalekoMachineConfig class.'''
        self.args = kwargs
        assert 'Record' in kwargs, 'Record must be provided in initialization.'
        timestamp = kwargs.get('timestamp', datetime.datetime.now(datetime.timezone.utc))
        if isinstance(timestamp, str):
            assert Indaleko.validate_iso_timestamp(
                timestamp
            ), f'Timestamp {timestamp} is not a valid ISO timestamp'
            timestamp = datetime.datetime.fromisoformat(timestamp)
        self.captured = IndalekoMachineConfigDataModel.Captured(
            Label = IndalekoMachineConfig.indaleko_machine_config_captured_label_uuid,
            Value = timestamp,
        )
        ic(kwargs)
        self.platform = IndalekoMachineConfigDataModel.Platform(
            software = IndalekoMachineConfigDataModel.Software(
                OS = kwargs.get('os', None),
                Version = kwargs.get('os_version', None),
                Architecture = kwargs.get('arch', None),
            ),
            hardware = IndalekoMachineConfigDataModel.Hardware(
                CPU = kwargs.get('cpu', None),
                Version = kwargs.get('cpu_version', None),
                Cores = kwargs.get('cpu_cores', None),
            )
        )
        self.indaleko_record = kwargs.get('Record', None)
        db = kwargs.get('db', IndalekoDBConfig())
        self.collection = kwargs.get('collection', IndalekoCollections(db_config=db).get_collection(Indaleko.Indaleko_MachineConfig))
        assert isinstance(self.captured, IndalekoMachineConfigDataModel.Captured)
        assert isinstance(self.indaleko_record, IndalekoRecordDataModel.IndalekoRecord)
        assert isinstance(self.platform, IndalekoMachineConfigDataModel.Platform) or self.platform is None, f'Platform must be a Platform object, not {type(self.platform)}'
        self.machine_config = IndalekoMachineConfigDataModel.MachineConfig(
            Platform=self.platform,
            Captured=self.captured,
            Record=self.indaleko_record,
        )



    def __old_init__(
        self: "IndalekoMachineConfig",
        timestamp: datetime = None,
        db: IndalekoDBConfig = None,
        **kwargs
    ):
        """
        Constructor for the IndalekoMachineConfig class. Takes a
        set of configuration data as a parameter and initializes the object.
        """
        self.machine_id = None
        if timestamp is None:
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.data_source = None
        self.set_source()
        self.timestamp = timestamp
        if isinstance(self.timestamp, str):
            assert Indaleko.validate_iso_timestamp(
                self.timestamp
            ), f'Timestamp {self.timestamp} is not a valid ISO timestamp'
            self.timestamp = datetime.datetime.fromisoformat(self.timestamp)
        self.attributes = {}
        self.data = Indaleko.encode_binary_data(b"")
        self.indaleko_record = None
        self.captured = {
            "Label": "Timestamp",
            "Value": timestamp,
        }
        collections = IndalekoCollections(db_config=db)
        self.collection = collections.get_collection(Indaleko.Indaleko_MachineConfig)
        assert self.collection is not None, "MachineConfig collection does not exist."
        service_name = "Indaleko Machine Config Service"
        if "service_name" in kwargs:
            service_name = kwargs["service_name"]
        service_identifier = self.indaleko_machine_config_uuid_str
        if "service_identifier" in kwargs:
            service_identifier = kwargs["service_identifier"]
        service_description = None
        if "service_description" in kwargs:
            service_description = kwargs["service_description"]
        service_version = self.indaleko_machine_config_version_str
        if "service_version" in kwargs:
            service_version = kwargs["service_version"]
        service_type = "Machine Configuration"
        if "service_type" in kwargs:
            service_type = kwargs["service_type"]
        self.machine_config_service = IndalekoServiceManager().register_service(
            service_name=service_name,
            service_id=service_identifier,
            service_description=service_description,
            service_version=service_version,
            service_type=service_type
        )
        assert self.machine_config_service is not None, "MachineConfig service does not exist."

    @staticmethod
    def find_config_files(directory : str, prefix : str) -> list:
        '''This looks for configuration files in the given directory.'''
        if not isinstance(prefix, str):
            raise AssertionError(f'prefix must be a string, not {type(prefix)}')
        if not isinstance(directory, str):
            raise AssertionError(f'directory must be a string, not {type(directory)}')
        return [x for x in os.listdir(directory)
                if x.startswith(prefix)
                and x.endswith('.json')]

    @staticmethod
    def get_guid_timestamp_from_file_name(file_name : str, prefix : str, suffix : str = 'json') -> tuple:
        '''
        Get the machine configuration captured by powershell.
        Note that this PS script requires admin privileges so it might
        be easier to do this in an application that elevates on Windows so it
        can be done dynamically.  For now, we assume it has been captured.
        '''
        if not isinstance(file_name, str):
            raise AssertionError(f'file_name must be a string, not {type(file_name)}')
        if not isinstance(prefix, str):
            raise AssertionError(f'prefix must be a string, not {type(prefix)}')
        if suffix[0] == '.':
            suffix = suffix[1:]
        # Regular expression to match the GUID and timestamp
        pattern = f"(?:.*[/])?{prefix}-(?P<guid>[a-fA-F0-9\\-]+)-(?P<timestamp>\\d{4}-\\d{2}-\\d{2}T\\d{2}-\\d{2}-\\d{2}\\.\\d+Z)\\.{suffix}"
        match = re.match(pattern, file_name)
        assert match, f'Filename format not recognized for {file_name} with re {pattern}.'
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
    def get_most_recent_config_file(config_dir : str, prefix : str, suffix : str = '.json') -> str:
        '''Get the most recent machine configuration file.'''
        candidates = [x for x in os.listdir(config_dir) if
                    x.startswith(prefix) and x.endswith(suffix)]
        assert len(candidates) > 0, f'At least one {prefix} file should exist'
        candidate_files = [(timestamp, filename)
                        for filename, guid, timestamp in
                        [IndalekoMachineConfig.get_guid_timestamp_from_file_name(x, prefix, suffix)
                            for x in candidates]]
        candidate_files.sort(key=lambda x: x[0])
        candidate = candidate_files[0][1]
        if config_dir is not None:
            candidate = os.path.join(config_dir, candidate)
        return candidate


    def set_platform(self, platform_data: dict) -> None:
        """
        This method sets the platform information for the machine.
        """
        assert isinstance(
            platform_data, dict
        ), f"platform must be a dict (not {type(platform_data)})"
        assert "software" in platform_data, "platform must contain a software field"
        assert isinstance(
            platform_data["software"], dict
        ), f'platform["software"] must be a dictionary, not {type(platform_data["software"])}'
        assert isinstance(
            platform_data["software"]["OS"], str
        ), f'platform must contain a string OS field, not {type(platform_data["software"]["OS"])}'
        assert isinstance(
            platform_data["software"]["Version"], str
        ), "platform must contain a string version field"
        assert isinstance(
            platform_data["software"]["Architecture"], str
        ), "platform must contain a string architecture field"
        assert "hardware" in platform_data, "platform must contain a hardware field"
        assert isinstance(
            platform_data["hardware"], dict
        ), 'platform["hardware"] must be a dictionary'
        assert isinstance(
            platform_data["hardware"]["CPU"], str
        ), "platform must contain a string CPU field"
        assert isinstance(
            platform_data["hardware"]["Version"], str
        ), "platform must contain a string version field"
        assert isinstance(
            platform_data["hardware"]["Cores"], int
        ), "platform must contain an integer cores field"
        self.platform = platform_data
        return self


    def parse_config_file(self) -> None:
        """
        This method parses the configuration data from the config file.
        """
        raise AssertionError("This method should be overridden by the derived classes.")

    def set_machine_id(self, machine_id) -> None:
        """
        This method sets the machine ID for the machine configuration.
        """
        if isinstance(machine_id, str):
            assert Indaleko.validate_uuid_string(
                machine_id
            ), f"machine_id {machine_id} is not a valid UUID."
        elif isinstance(machine_id, uuid.UUID):
            machine_id = str(machine_id)
        self.machine_id = machine_id
        return self

    def get_machine_id(self) -> str:
        """
        This method returns the machine ID for the machine configuration.
        """
        if hasattr(self, "machine_id"):
            return self.machine_id
        return None

    def set_source(self, identifier : str = None, version : str = None, description : str = "") -> None:
        '''Set the source attribution for the machine configuration.'''
        if identifier is None:
            identifier = IndalekoMachineConfig.indaleko_machine_config_uuid_str
        if version is None:
            version = IndalekoMachineConfig.indaleko_machine_config_version_str
        self.data_source = IndalekoDataModel.SourceIdentifier(
            Identifier=identifier,
            Version=version,
            Description="Machine configuration data"
        )

    def set_attributes(self, attributes: dict) -> None:
        """
        This method sets the attributes for the machine configuration.
        """
        if isinstance(attributes, dict):
            self.attributes = attributes
        self.indaleko_record = None # force recompute
        return self

    def get_attributes(self) -> dict:
        '''Return the current attributes'''
        return self.attributes

    def get_indaleko_record(self) -> IndalekoRecordDataModel.IndalekoRecord:
        """Returns the Indaleko record for the machine configuration."""
        if self.indaleko_record is None:
            self.indaleko_record = IndalekoRecordDataModel.IndalekoRecord(
                self.data_source,
                Timestamp=self.timestamp,
                Attributes={},
                Data=Indaleko.encode_binary_data(b""),
            )
        return self.indaleko_record

    def set_base64_data(self, data: bytes) -> None:
        """
        This method sets the base64 encoded data for the machine configuration.
        """
        if isinstance(data, bytes):
            self.data = Indaleko.encode_binary_data(data)
            self.indaleko_record = None # force recompute
        return self


    def write_config_to_db(self) -> None:
        """
        This method writes the configuration to the database.
        """
        assert hasattr(
            self, "machine_id"
        ), "machine_id must be set before writing to the database."
        assert Indaleko.validate_uuid_string(
            self.machine_id
        ), f"machine_id {self.machine_id} is not a valid UUID."
        assert isinstance(self.machine_config, IndalekoMachineConfigDataModel.MachineConfig), f"machine_config is not a MachineConfig object, it is {type(self.machine_config)}"
        new_config = IndalekoMachineConfigDataModel.MachineConfig.serialize(self.machine_config)
        try:
            self.collection.insert(new_config, overwrite=True)
        except arango.exceptions.DocumentInsertError as e:
            print(f"Error inserting document: {e}")
            print(f"Document: {new_config}")
            raise e
        ic('wrote config to db')

    @staticmethod
    def load_config_from_file() -> dict:
        """
        This method creates a new IndalekoMachineConfig object from an
        existing config file.  This must be overridden by the platform specific
        machine configuration implementation.
        """
        raise AssertionError("This method should be overridden by the derived classes.")

    @staticmethod
    def find_configs_in_db(source_id : str) -> list:
        """
        This method finds all the machine configs with given source_id.
        """
        if not Indaleko.validate_uuid_string(source_id):
            raise AssertionError(f"source_id {source_id} is not a valid UUID.")
        collections = IndalekoCollections()
        # Using spaces in names complicates things, but this does work.
        cursor = collections.db_config.db.aql.execute(
            f'FOR doc IN {Indaleko.Indaleko_MachineConfig} FILTER '+\
             'doc.Record["SourceIdentifier"].Identifier == ' +\
             '@source_id RETURN doc',
            bind_vars={'source_id': source_id})
        entries = [entry for entry in cursor]
        return entries

    @staticmethod
    def delete_config_in_db(machine_id: str) -> None:
        """
        This method deletes the specified machine config from the database.
        """
        assert Indaleko.validate_uuid_string(
            machine_id
        ), f"machine_id {machine_id} is not a valid UUID."
        IndalekoCollections().get_collection(Indaleko.Indaleko_MachineConfig).delete(machine_id)



    @staticmethod
    def deserialize(self) -> "IndalekoMachineConfig":
        '''Deserialize a dictionary to an object.'''
        return IndalekoMachineConfig(**self)


    def serialize(self) -> dict:
        """
        This method deserializes the machine config.
        """
        if hasattr(self, "machine_config"):
            serialized_data = IndalekoMachineConfigDataModel.MachineConfig.serialize(self.machine_config)
        else:
            serialized_data = {
                "Platform": self.platform,
                "Captured": self.captured,
                "Record" : IndalekoRecordDataModel.IndalekoRecord.serialize(self.get_indaleko_record()),
            }
        if isinstance(serialized_data, tuple):
            assert len(serialized_data) == 1, 'Serialized data is a multi-entry tuple.'
            serialized_data = serialized_data[0]
        if isinstance(serialized_data, dict):
            serialized_data['_key'] = self.machine_id
            serialized_data['hostname'] = self.hostname
        return ic(serialized_data)


    def to_dict(self) -> dict:
        """
        This method returns the dictionary representation of the machine config.
        """
        return self.serialize()

    def to_json(self, indent: int = 4) -> str:
        """
        This method returns the JSON representation of the machine config.
        """
        return json.dumps(self.to_dict(), indent=indent)

    @staticmethod
    def build_config(**kwargs) -> "IndalekoMachineConfig":
        """This method builds a machine config from the specified parameters."""
        assert "os" in kwargs, "OS must be specified"
        assert isinstance(kwargs["os"], str), "OS must be a string"
        assert "arch" in kwargs, "Architecture must be specified"
        assert isinstance(kwargs["arch"], str), "Architecture must be a string"
        assert "os_version" in kwargs, "OS version must be specified"
        assert isinstance(kwargs["os_version"], str), "OS version must be a string"
        assert "cpu" in kwargs, "CPU must be specified"
        assert isinstance(kwargs["cpu"], str), "CPU must be a string"
        assert "cpu_version" in kwargs, "CPU version must be specified"
        assert isinstance(kwargs["cpu_version"], str), "CPU version must be a string"
        assert "cpu_cores" in kwargs, "CPU cores must be specified"
        assert isinstance(kwargs["cpu_cores"], int), "CPU cores must be an integer"
        assert "source_id" in kwargs, "source must be specified"
        assert isinstance(kwargs["source_id"], str), "source must be a dict"
        assert "source_version" in kwargs, "source version must be specified"
        assert isinstance(
            kwargs["source_version"], str
        ), "source version must be a string"
        assert "attributes" in kwargs, "Attributes must be specified"
        assert "data" in kwargs, "Data must be specified"
        assert "machine_id" in kwargs, "Machine ID must be specified"
        if "timestamp" in kwargs:
            assert Indaleko.validate_iso_timestamp(
                kwargs["timestamp"]
            ), f'Timestamp {kwargs["timestamp"]} is not a valid ISO timestamp'
            timestamp = kwargs["timestamp"]
        else:
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if "machine_config" not in kwargs:
            machine_config = IndalekoMachineConfig(**kwargs)
        else:
            machine_config = kwargs["machine_config"]
        return ic(machine_config)

def get_script_name(platform_name : str = platform.system()) -> str:
    '''This routine returns the name of the script.'''
    script_name = f'Indaleko{platform_name}MachineConfig.py'
    return script_name


def check_linux_prerequisites() -> None:
    '''This routine checks that the Linux system prerequisites are met.'''
    # Linux has no pre-requisites at the current time.
    return True

def check_macos_prerequisites() -> None:
    '''This routine checks that the MacOS system prerequisites are met.'''
    # TBD
    return False

def check_windows_prerequisites(config_dir : str = Indaleko.default_config_dir) -> None:
    '''This routine checks that the Windows system prerequisites are met.'''
    # This is tough to do cleanly, since the default name is defined in
    # IndalekoWindowsMachineConfig.py and that includes this file.
    candidates = [x for x in os.listdir(config_dir) if x.startswith('windows')]
    if len(candidates) == 0:
        print(f'No Windows machine config files found in {config_dir}')
        print('To create a Windows machine config, run: '+ \
              'windows-hardware-info.ps1 from an elevated PowerShell prompt.')
        print('Note: this will require enable execution of PowerShell scripts.')
    return False

def add_command(args: argparse.Namespace) -> None:
    '''This routine adds a machine config to the database.'''
    logging.info('Adding machine config for %s', args.platform)
    if args.platform == 'Linux':
        check_linux_prerequisites()
        logging.info('Linux prerequisites met')
        cmd_string = f'python3 {get_script_name(args.platform)}'
        cmd_string += f' --configdir {args.configdir}'
        cmd_string += f' --timestamp {args.timestamp}'
        logging.info('Recommending: <%s> for Linux machine config', cmd_string)
        print(f'Please run:\n\t{cmd_string}')
    elif args.platform == 'Darwin':
        check_macos_prerequisites()
    elif args.platform == 'Windows':
        check_windows_prerequisites()
    return

def list_command(args: argparse.Namespace) -> None:
    '''This routine lists the machine configs in the database.'''
    print(args)
    return

def delete_command(args: argparse.Namespace) -> None:
    '''This routine deletes a machine config from the database.'''
    print(args)
    return

def test_command(args: argparse.Namespace) -> None:
    '''This routine tests the machine config functionality.'''
    print(args)
    test_machine_config_data = {
        "machine_id" : "f7a439ec-c2d0-4844-a043-d8ac24d9ac0b",
        "Record" : {
            "SourceIdentifier": {
                "Identifier": "8a948e74-6e43-4a6e-91c0-0cb5fd97355e",
                "Version": "1.0",
                "Description": "This service provides the configuration information for a macOS machine."
            },
            "Timestamp": "2024-08-09T07:52:59.839237+00:00",
            "Attributes": {
                "MachineGuid": "f7a439ec-c2d0-4844-a043-d8ac24d9ac0b",
            },
            "Data": "xx"
        },
        "Captured" : {
            "Label": "eb7eaeed-6b21-4b6a-a586-dddca6a1d5a4",
            "Value": "2024-08-08T21:26:22.418196+00:00"
        },
        "Platform" : {
            "software": {
                "OS": "Linux",
                "Version": "5.4.0-104-generic",
                "Architecture": "x86_64"
            },
            "hardware": {
                "CPU": "Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz",
                "Version": "06_9E_09",
                "Cores": 8
            }
        }
    }
    machine_config = IndalekoMachineConfig.deserialize(test_machine_config_data)
    print(json.dumps(machine_config.serialize(), indent=4))

def main():
    '''Interact with the InalekoMachineConfig class.'''
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--timestamp',
                            type=str,
                            default=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            help='Timestamp to use')
    pre_parser.add_argument('--configdir',
                            type=str,
                            default=Indaleko.default_config_dir,
                            help='Configuration directory to use')
    pre_parser.add_argument('--logdir',
                            type=str,
                            default=Indaleko.default_log_dir,
                            help='Directory into which to write logs')
    pre_parser.add_argument('--loglevel',
                            type=int,
                            default=logging.DEBUG,
                            choices=IndalekoLogging.get_logging_levels(),
                            help='Log level')
    pre_args, _ = pre_parser.parse_known_args()
    parser = argparse.ArgumentParser(description='Indaleko Machine Config',
                                     parents=[pre_parser])
    if Indaleko.validate_iso_timestamp(pre_args.timestamp):
        timestamp = datetime.datetime.fromisoformat(pre_args.timestamp)
    else:
        raise AssertionError(f'Timestamp {pre_args.timestamp} is not a valid ISO timestamp')
    log_file_name = Indaleko.generate_file_name(
        suffix='log',
        platform=platform.system(),
        service='machine_config',
        timestamp=timestamp.isoformat()
    )
    parser.add_argument('--log', type=str, default=log_file_name, help='Log file name to use')
    subparsers = parser.add_subparsers(dest='command')
    parser_test = subparsers.add_parser('test', help='Test the machine config functionality')
    parser_test.set_defaults(func=test_command)
    parser.set_defaults(func=test_command)
    args = parser.parse_args()
    indaleko_logging = IndalekoLogging(
        service_name='IndalekoMachineConfig',
        log_level=pre_args.loglevel,
        log_file=args.log,
        log_dir=pre_args.logdir
    )
    assert indaleko_logging is not None, 'Unable to start logging'
    logging.info('Starting IndalekoMachineConfig')
    logging.debug(args)
    args.func(args)
    logging.info('IndalekoMachineConfig: done processing.')




def old_main():
    '''
    This is the main function for the IndalekoMachineConfig class.
    '''
    timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    file_name = Indaleko.generate_file_name(
        suffix='log',
        platform=platform.system(),
        service='machine_config',
        timestamp=timestamp)
    default_log_file = os.path.join(Indaleko.default_log_dir, file_name)
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)
    parser_add = subparsers.add_parser('add', help='Add a machine config')
    parser_add.add_argument('--platform',
                            type=str,
                            default=platform.system(),
                            help='Platform to use')
    parser_list = subparsers.add_parser('list', help='List machine configs')
    parser_list.add_argument('--files',
                             default=False,
                             action='store_true',
                             help='Source ID')
    parser_list.add_argument('--db',
                             type=str,
                             default=True,
                             help='Source ID')
    parser_delete = subparsers.add_parser('delete', help='Delete a machine config')
    parser_delete.add_argument('--platform',
                               type=str,
                               default=platform.system(),
                               help='Platform to use')
    parser.add_argument(
        '--log',
        type=str,
        default=default_log_file,
        help='Log file name to use')
    parser.add_argument('--configdir',
                        type=str,
                        default=Indaleko.default_config_dir,
                        help='Configuration directory to use')
    parser.add_argument('--timestamp', type=str,
                       default=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       help='Timestamp to use')
    args = parser.parse_args()
    if args.log is not None:
        logging.basicConfig(filename=args.log, level=logging.DEBUG)
        logging.info('Starting Indaleko Machine Config')
        logging.info('Logging to %s', args.log)  # Fix: Use lazy % formatting
    if args.command == 'add':
        add_command(args)
    elif args.command == 'list':
        list_command(args)
    elif args.command == 'delete':
        delete_command(args)
    else:
        raise AssertionError(f'Unknown command {args.command}')
    logging.info('Done with Indaleko Machine Config')

if __name__ == "__main__":
    main()
