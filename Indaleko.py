"""
The purpose of this package is to define the core data types used in Indaleko.

Indaleko is a Unified Private Index (UPI) service that enables the indexing of
storage content (e.g., files, databases, etc.) in a way that extracts useful
metadata and then uses it for creating a rich index service that can be used in
a variety of ways, including improving search results, enabling development of
non-traditional data visualizations, and mining relationships between objects to
enable new insights.

Indaleko is not a storage engine.  Rather, it is a metadata service that relies
upon storage engines to provide the data to be indexed.  The storage engines can
be local (e.g., a local file system,) remote (e.g., a cloud storage service,) or
even non-traditional (e.g., applications that provide access to data in some
way, such as Discord, Teams, Slack, etc.)

Indaleko uses three distinct classes of metadata to enable its functionality:

* Storage metadata - this is the metadata that is provided by the storage
  services
* Semantic metadata - this is the metadata that is extracted from the objects,
  either by the storage service or by semantic transducers that act on the files
  when it is available on the local device(s).
* Activity context - this is metadata that captures information about how the
  file was used, such as when it was accessed, by what application, as well as
  ambient information, such as the location of the device, the person with whom
  the user was interacting, ambient conditions (e.g., temperature, humidity, the
  music the user is listening to, etc.) and even external events (e.g., current
  news, weather, etc.)

To do this, Indaleko stores information of various types in databases.  One of
the purposes of this package is to encapsulate the data types used in the system
as well as the schemas used to validate the data.

The general architecture of Indaleko attempts to be flexible, while still
capturing essential metadata that is used as part of the indexing functionality.
Thus, to that end, we define both a generic schema and in some cases a flexible
set of properties that can be extracted and stored.  Since this is a prototype
system, we have strived to "keep it simple" yet focus on allowing us to explore
a broad range of storage systems, semantic transducers, and activity data sources.

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
"""
import uuid
import datetime
import os
import platform
import logging
import socket
import ipaddress
import base64
import msgpack
import base64
import msgpack

from IndalekoObjectDataSchema import IndalekoObjectDataSchema
from IndalekoServiceSchema import IndalekoServiceSchema
from IndalekoRelationshipSchema import IndalekoRelationshipSchema
from IndalekoMachineConfigSchema import IndalekoMachineConfigSchema
from IndalekoActivityDataProviderRegistrationSchema \
    import IndalekoActivityDataProviderRegistrationSchema
from IndalekoActivityContextSchema import IndalekoActivityContextSchema
from IndalekoUserSchema import IndalekoUserSchema
from IndalekoUserRelationshipSchema import IndalekoUserRelationshipSchema

class Indaleko:
    '''This class defines constants used by Indaleko.'''
    default_data_dir = './data'
    default_config_dir = './config'
    default_log_dir = './logs'

    default_db_timeout=10

    Indaleko_Objects = 'Objects'
    Indaleko_Relationships = 'Relationships'
    Indaleko_Services = 'Services'
    Indaleko_MachineConfig = 'MachineConfig'
    Indaleko_ActivityDataProviders = 'ActivityDataProviders'
    Indaleko_ActivityContext = 'ActivityContext'
    Indaleko_Users = 'Users'
    Indaleko_User_Relationships = 'UserRelationships'

    Indaleko_Prefix = 'indaleko'

    Collections = {
        Indaleko_Objects: {
            'schema' : IndalekoObjectDataSchema().get_json_schema(),
            'edge' : False,
            'indices' : {
                'URI' : {
                    'fields' : ['URI'],
                    'unique' : True,
                    'type' : 'persistent'
                },
                'file identity' : {
                    'fields' : ['ObjectIdentifier'],
                    'unique' : True,
                    'type' : 'persistent'
                },
                'local identity' : {
                    # Question: should this be combined with other info to allow uniqueness?
                    'fields' : ['LocalIdentifier'],
                    'unique' : False,
                    'type' : 'persistent'
                },
            },
        },
        Indaleko_Relationships : {
            'schema' : IndalekoRelationshipSchema().get_json_schema(),
            'schema' : IndalekoRelationshipSchema().get_json_schema(),
            'edge' : True,
            'indices' : {
                'relationship' : {
                    'fields' : ['relationship'],
                    'unique' : False,
                    'type' : 'persistent'
                },
                'vertex1' : {
                    'fields' : ['object1'],
                    'unique' : False,
                    'type' : 'persistent'
                },
                'vertex2' : {
                    'fields' : ['object2'],
                    'unique' : False,
                    'type' : 'persistent'
                },
                'edge' : {
                    'fields' : ['object1', 'object2'],
                    'unique' : False,
                    'type' : 'persistent'
                },
            }
        },
        Indaleko_Services : {
            'schema' : IndalekoServiceSchema().get_json_schema(),
            'schema' : IndalekoServiceSchema().get_json_schema(),
            'edge' : False,
            'indices' : {
                'identifier' : {
                    'fields' : ['Name'],
                    'unique' : True,
                    'type' : 'persistent'
                },
            },
        },
        Indaleko_MachineConfig : {
            'schema' : IndalekoMachineConfigSchema().get_json_schema(),
            'edge' : False,
            'indices' : { },
        },
        Indaleko_ActivityDataProviders : {
            'schema' : IndalekoActivityDataProviderRegistrationSchema().get_json_schema(),
            'schema' : IndalekoActivityDataProviderRegistrationSchema().get_json_schema(),
            'edge' : False,
            'indices' : {
                'identifier' : {
                    'fields' : ['ActivityProvider'],
                    'unique' : True,
                    'type' : 'persistent'
                },
            },
        },
        Indaleko_ActivityContext : {
            'schema' : IndalekoActivityContextSchema().get_json_schema(),
            'schema' : IndalekoActivityContextSchema().get_json_schema(),
            'edge' : False,
            'indices' : {
                'identifier' : {
                    'fields' : ['ActivityContextIdentifier'],
                    'unique' : True,
                    'type' : 'persistent'
                },
            },
        },
       Indaleko_Users : {
            'schema' : IndalekoUserSchema().get_json_schema(),
            'schema' : IndalekoUserSchema().get_json_schema(),
            'edge' : False,
            'indices' : {
                'identifier' : {
                    'fields' : ['Identifier'],
                    'unique' : True,
                    'type' : 'persistent'
                },
            },
        },
        Indaleko_User_Relationships : {
            'schema' : IndalekoUserRelationshipSchema().get_json_schema(),
            'schema' : IndalekoUserRelationshipSchema().get_json_schema(),
            'edge' : True,
            'indices' : {
                'Identity1' : {
                    'fields' : ['Identity1'],
                    'unique' : False,
                    'type' : 'persistent'
                },
                'Identity2' : {
                    'fields' : ['Identity2'],
                    'unique' : False,
                    'type' : 'persistent'
                },
                'edge' : {
                    'fields' : ['Identity1', 'Identity2'],
                    'unique' : True,
                    'type' : 'persistent'
                },
            }
        },
    }

    @staticmethod
    def validate_ip_address(ip : str) -> bool:
        """Given a string, verify that it is in fact a valid IP address."""
        if not isinstance(ip, str):
            print(f'ip is not a string it is a {type(ip)}')
            return False
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            print('ip is not valid')
            return False

    @staticmethod
    def validate_hostname(hostname : str) -> bool:
        """Given a string, verify that it is in fact a valid hostname."""
        if not isinstance(hostname, str):
            print(f'hostname is not a string it is a {type(hostname)}')
            return False
        try:
            socket.gethostbyname(hostname)
            return True
        except socket.error:
            print('hostname is not valid')
            return False

    @staticmethod
    def create_secure_directories(directories : list = None) -> None:
        '''Create secure directories for Indaleko.'''
        if directories is None:
            directories = [Indaleko.default_data_dir,
                           Indaleko.default_config_dir,
                           Indaleko.default_log_dir]
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
            os.chmod(directory, 0o700)


    @staticmethod
    def validate_uuid_string(uuid_string : str) -> bool:
        """Given a string, verify that it is in fact a valid uuid."""
        if not isinstance(uuid_string, str):
            print(f'uuid is not a string it is a {type(uuid)}')
            return False
        try:
            uuid.UUID(uuid_string)
            return True
        except ValueError:
            print('uuid is not valid')
            return False

    @staticmethod
    def validate_iso_timestamp(source : str) -> bool:
        """Given a string, ensure it is a valid ISO timestamp."""
        valid = True
        if not isinstance(source, str):
            valid = False
        else:
            try:
                datetime.datetime.fromisoformat(source)
            except ValueError:
                valid = False
        return valid

    @staticmethod
    def generate_iso_timestamp(ts : datetime = None) -> str:
        """Given a timestamp, convert it to an ISO timestamp."""
        if ts is None:
            ts = datetime.datetime.now(datetime.timezone.utc)
        assert isinstance(ts, datetime.datetime), f'ts must be a datetime, not {type(ts)}'
        return ts.isoformat()

    @staticmethod
    def generate_iso_timestamp(ts : datetime = None) -> str:
        """Given a timestamp, convert it to an ISO timestamp."""
        if ts is None:
            ts = datetime.datetime.now(datetime.timezone.utc)
        assert isinstance(ts, datetime.datetime), f'ts must be a datetime, not {type(ts)}'
        return ts.isoformat()

    @staticmethod
    def generate_iso_timestamp_for_file(ts : str = None) -> str:
        """Create an ISO timestamp for the current time."""
        if ts is None:
            ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        ts_check = Indaleko.extract_iso_timestamp_from_file_timestamp(ts)
        if ts_check != ts: # validate that the timestamp is reversible
            raise ValueError(f'timestamp mismatch {ts} != {ts_check}')
        return f"-ts={ts.replace(':','#').replace('-','_')}"

    @staticmethod
    def extract_iso_timestamp_from_file_timestamp(file_timestamp : str) -> str:
        """Given a file timestamp, convert it to an ISO timestamp."""
        ts = file_timestamp.replace('_','-').replace('#',':')
        ts_check = datetime.datetime.fromisoformat(ts)
        if ts_check is None:
            raise ValueError('timestamp is not valid')
        return ts

    @staticmethod
    def get_logging_levels() -> list:
        """Return a list of valid logging levels."""
    if platform.python_version() < '3.12':
        logging_levels = []
        if hasattr(logging, 'CRITICAL'):
            logging_levels.append('CRITICAL')
        if hasattr(logging, 'ERROR'):
            logging_levels.append('ERROR')
        if hasattr(logging, 'WARNING'):
            logging_levels.append('WARNING')
        if hasattr(logging, 'WARN'):
            logging_levels.append('WARN')
        if hasattr(logging, 'INFO'):
            logging_levels.append('INFO')
        if hasattr(logging, 'DEBUG'):
            logging_levels.append('DEBUG')
        if hasattr(logging, 'NOTSET'):
            logging_levels.append('NOTSET')
        if hasattr(logging, 'FATAL'):
            logging_levels.append('FATAL')
    else:
        logging_levels = sorted(set(logging.getLevelNamesMapping()))

    @staticmethod
    def generate_final_name(args : list, **kwargs) -> str:
        '''
        This is a helper function for generate_file_name, which throws
        a pylint error as having "too many branches".  An explicit args list
        threw a "too many arguments" error, so this is a compromise - send in a
        list, and then unpack it manually. Why this is better is a mystery of
        the faith.
        '''
        prefix = args[0]
        target_platform = args[1]
        service = args[2]
        ts = args[3]
        suffix = args[4]
        max_len = args[5]
        name = prefix
        if '-' in prefix:
            raise ValueError('prefix must not contain a hyphen')
        if '-' in suffix:
            raise ValueError('suffix must not contain a hyphen')
        name += f'-plt={target_platform}'
        name += f'-svc={service}'
        for key, value in kwargs.items():
            assert isinstance(value, str), f'value must be a string: {key, value}'
            if '-' in key or '-' in value:
                raise ValueError(f'key and value must not contain a hyphen: {key, value}')
            name += f'-{key}={value}'
        name += ts
        name += f'.{suffix}'
        if len(name) > max_len:
            raise ValueError('file name is too long' + '\n' + name + '\n' + str(len(name)))
        return name

    @staticmethod
    def generate_file_name(**kwargs) -> str:
        '''
        Given a key/value store of labels and values, this generates a file
        name in a common format.
        Special labels:
            * prefix: string to prepend to the file name
            * platform: identifies the platform from which the data originated
            * service: identifies the service that generated the data (indexer,
              ingester, etc.)
            * timestamp: timestamp to use in the file name
            * suffix: string to append to the file name
        '''
        max_len = 255
        prefix = Indaleko.Indaleko_Prefix
        suffix = 'jsonl'
        if 'max_len' in kwargs:
            max_len = kwargs['max_len']
            if isinstance(max_len, str):
                max_len = int(max_len)
            if not isinstance(max_len, int):
                raise ValueError('max_len must be an integer')
            del kwargs['max_len']
        if 'platform' not in kwargs:
            target_platform = platform.system()
        else:
            target_platform = kwargs['platform']
            del kwargs['platform']
        if 'service' not in kwargs:
            raise ValueError('service must be specified')
        service = kwargs['service']
        del kwargs['service']
        ts = Indaleko.generate_iso_timestamp_for_file()
        if 'timestamp' in kwargs:
            ts = Indaleko.generate_iso_timestamp_for_file(kwargs['timestamp'])
            del kwargs['timestamp']
        if 'prefix' in kwargs:
            prefix = kwargs['prefix']
            del kwargs['prefix']
        if 'suffix' in kwargs:
            suffix = kwargs['suffix']
            del kwargs['suffix']
        if suffix.startswith('.'):
            suffix = suffix[1:] # avoid ".." for suffix
        if '-' in target_platform:
            raise ValueError('platform must not contain a hyphen')
        if '-' in service:
            raise ValueError('service must not contain a hyphen')
        return Indaleko.generate_final_name(
            [prefix,
            target_platform,
            service,
            ts,
            suffix,
            max_len],
            **kwargs)

    @staticmethod
    def extract_keys_from_file_name(file_name : str) -> dict:
        '''
        Given a file name, extract the keys and values from the file name.
        '''
        base_file_name, file_suffix = os.path.splitext(os.path.basename(file_name))
        file_name = base_file_name + file_suffix
        data = {}
        if not isinstance(file_name, str):
            raise ValueError('file_name must be a string')
        fields = file_name.split('-')
        prefix = fields.pop(0)
        data['prefix'] = prefix
        target_platform = fields.pop(0)
        if not target_platform.startswith('plt='):
            raise ValueError('platform field must start with plt=')
        data['platform'] = target_platform[4:]
        service = fields.pop(0)
        if not service.startswith('svc='):
            raise ValueError('service field must start with svc=')
        data['service'] = service[4:]
        trailer = fields.pop(-1)
        suffix = trailer.split('.')[-1]
        if not trailer.startswith('ts='):
            raise ValueError('timestamp field must start with ts=')
        ts_field = trailer[3:-len(suffix)-1]
        data['suffix'] = suffix
        data['timestamp'] = Indaleko.extract_iso_timestamp_from_file_timestamp(ts_field)
        while len(fields) > 0:
            field = fields.pop(0)
            if '=' not in field:
                raise ValueError('field must be of the form key=value')
            key, value = field.split('=')
            data[key] = value
        return data

    @staticmethod
    def encode_binary_data(data : bytes) -> str:
        '''Encode binary data as a string.'''
        return base64.b64encode(msgpack.packb(data)).decode('ascii')

    @staticmethod
    def decode_binary_data(data : str) -> bytes:
        '''Decode binary data from a string.'''
        return msgpack.unpackb(base64.b64decode(data))

    @staticmethod
    def find_candidate_files(input_strings : list[str], directory : str) -> list[tuple[str,str]]:
        '''Given a directory location, find a list of candidate files that match
        the input strings.'''

        @staticmethod
        def get_unique_identifier(file_name, all_files):
            """
            Generate a unique identifier for a file by finding the shortest
            unique substring from a list of candidate files.
            """
            for i in range(1, len(file_name) + 1):
                for j in range(len(file_name) - i + 1):
                    substring = file_name[j:j+i]
                    if sum(substring in f for f in all_files) == 1:
                        return substring
            return file_name

        all_files = os.listdir(directory)
        matched_files = []

        for file in all_files:
            matched_files.append((file, get_unique_identifier(file, all_files)))

        if len(input_strings) == 0:
            return matched_files

        candidates = matched_files[:]

        for input_string in input_strings:
            updated_candidates = []
            for candidate, unique_id in candidates:
                if input_string in candidate:
                    updated_candidates.append((candidate, unique_id))
            candidates = updated_candidates

        if len(candidates) > 0:
            return candidates
        return []

    @staticmethod
    def print_candidate_files(candidates : list[tuple[str,str]]) -> None:
        '''Print the candidate files in a nice format.'''
        print(candidates)
        if len(candidates) == 0:
            print('No candidate files found')
            return
        unique_id_label = 'Unique identifier'
        unique_id_label_length = len(unique_id_label)
        max_unique_id_length = unique_id_label_length
        for file, unique_id in candidates:
            if len(unique_id) > max_unique_id_length:
                max_unique_id_length = len(unique_id)
        print('Unique identifier', (max_unique_id_length-len('Unique identifier')) * ' ', 'File name')
        for file, unique_id in candidates:
            print(f'{unique_id.strip()} {(max_unique_id_length-len(unique_id))*" "} {file}')


def main():
    """Test code for Indaleko.py"""
    Indaleko.create_secure_directories()
    print('Test 1: generate a file name')
    name = Indaleko.generate_file_name(platform='test', service='test')
    print(name)
    print('Test 2: extract keys from file name')
    print(Indaleko.extract_keys_from_file_name(name))

if __name__ == "__main__":
    main()
