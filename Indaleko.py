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
from IndalekoObjectSchema import IndalekoObjectSchema
from IndalekoServicesSchema import IndalekoServicesSchema
from IndalekoRelationshipSchema import IndalekoRelationshipSchema
from IndalekoMachineConfigSchema import IndalekoMachineConfigSchema

class Indaleko:
    '''This class defines constants used by Indaleko.'''
    default_data_dir = './data'
    default_config_dir = './config'
    default_log_dir = './logs'

    Indaleko_Objects = 'Objects'
    Indaleko_Relationships = 'Relationships'
    Indaleko_Services = 'Services'
    Indaleko_MachineConfig = 'MachineConfig'

    Collections = {
        Indaleko_Objects: {
            'schema' : IndalekoObjectSchema.get_schema(),
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
            'schema' : IndalekoRelationshipSchema.get_schema(),
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
            'schema' : IndalekoServicesSchema.get_schema(),
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
            'schema' : IndalekoMachineConfigSchema.get_schema(),
            'edge' : False,
            'indices' : { },
        }
    }

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
        prefix = 'indaleko'
        suffix = 'jsonl'
        if 'max_len' in kwargs:
            max_len = kwargs['max_len']
            if isinstance(max_len, str):
                max_len = int(max_len)
            if not isinstance(max_len, int):
                raise ValueError('max_len must be an integer')
            del kwargs['max_len']
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if 'platform' not in kwargs:
            raise ValueError('platform must be specified')
        platform = kwargs['platform']
        del kwargs['platform']
        if 'service' not in kwargs:
            raise ValueError('service must be specified')
        service = kwargs['service']
        del kwargs['service']
        if 'timestamp' in kwargs:
            ts = kwargs['timestamp']
            del kwargs['timestamp']
        if 'prefix' in kwargs:
            prefix = kwargs['prefix']
            del kwargs['prefix']
        if 'suffix' in kwargs:
            suffix = kwargs['suffix']
            del kwargs['suffix']
        if '-' in prefix:
            raise ValueError('prefix must not contain a hyphen')
        if '-' in suffix:
            raise ValueError('suffix must not contain a hyphen')
        if suffix.startswith('.'):
            suffix = suffix[1:] # avoid ".." for suffix
        if '-' in platform:
            raise ValueError('platform must not contain a hyphen')
        if '-' in service:
            raise ValueError('service must not contain a hyphen')
        name = prefix
        name += f'-plt={platform}'
        name += f'-svc={service}'
        for key, value in kwargs.items():
            if '-' in key or '-' in value:
                raise ValueError(f'key and value must not contain a hyphen: {key, value}')
            name += f'-{key}={value}'
        name += f'-ts={ts.replace(':','#').replace('-','_')}'
        name += f'.{suffix}'
        if len(name) > max_len:
            raise ValueError('file name is too long' + '\n' + name + '\n' + str(len(name)))
        return name

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
        platform = fields.pop(0)
        if not platform.startswith('plt='):
            raise ValueError('platform field must start with plt=')
        data['platform'] = platform[4:]
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
        data['timestamp'] = ts_field.replace('_','-').replace('#',':')
        ts_check = datetime.datetime.fromisoformat(data['timestamp'])
        if ts_check is None:
            raise ValueError('timestamp is not valid')
        while len(fields) > 0:
            field = fields.pop(0)
            if '=' not in field:
                raise ValueError('field must be of the form key=value')
            key, value = field.split('=')
            data[key] = value
        return data

def main():
    """Test code for Indaleko.py"""
    print('Test 1: generate a file name')
    name = Indaleko.generate_file_name(platform='test', service='test')
    print(name)
    print('Test 2: extract keys from file name')
    print(Indaleko.extract_keys_from_file_name(name))

if __name__ == "__main__":
    main()
