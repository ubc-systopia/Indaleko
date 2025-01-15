'''
This is the common class library for Indaleko storage collectors (that is, agents that
collect data from storage locations into an intermediate format for further processing).

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

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
import stat
import datetime
import logging
import jsonlines
import json
import sys
import uuid

from icecream import ic
from typing import Union

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
# from data_models import IndalekoServiceDataModel
from db import IndalekoServiceManager
from storage.collectors.data_model import IndalekoStorageCollectorDataModel
from utils.misc.directory_management import indaleko_default_log_dir, indaleko_default_data_dir, indaleko_default_config_dir
from utils.misc.file_name_management import indaleko_file_name_prefix, generate_file_name, extract_keys_from_file_name
# pylint: enable=wrong-import-position


class BaseStorageCollector:
    '''
    This is the base class for Indaleko storage collectors.  It provides fundamental
    mechanisms for managing the data and configuration files that are used by
    the collectors.
    '''
    default_collector_data = IndalekoStorageCollectorDataModel(
        CollectorPlatformName = None,
        CollectorServiceName = 'Indaleko Generic Collector',
        CollectorServiceUUID = uuid.UUID('4a80a080-9cc9-4856-bf43-7b646557ac2d'),
        CollectorServiceVersion = '1.0',
        CollectorServiceDescription = 'This is the base (non-specialized) Indaleko storage collector. You should not see it in the database.'
    )

    # define the parameters for the generic collector service.  These should be
    # overridden by the derived classes.

    # we use a common file naming mechanism.  These are overridable defaults.
    default_file_prefix = indaleko_file_name_prefix
    default_file_suffix = '.jsonl'

    counter_values = (
        'output_count',
        'dir_count',
        'file_count',
        'special_count',
        'error_count',
        'access_error_count',
        'encoding_count',
        'not_found_count',
        'good_symlink_count',
        'bad_symlink_count',
    )

    cli_handler_mixin = None # there is no default handler mixin

    def __init__(self, **kwargs):
        if 'offline' in kwargs:
            self.offline = kwargs['offline']
            del kwargs['offline']
        else:
            self.offline = False
        # ic(self.offline)
        self.file_prefix = kwargs.get('file_prefix', BaseStorageCollector.default_file_prefix).replace('-', '_')
        self.file_suffix = kwargs.get('file_suffix', BaseStorageCollector.default_file_suffix).replace('-', '_')
        self.data_dir = kwargs.get('data_dir', indaleko_default_data_dir)
        assert os.path.isdir(self.data_dir), f'{self.data_dir} must be an existing directory'
        self.config_dir = kwargs.get('config_dir', indaleko_default_config_dir)
        assert os.path.isdir(self.data_dir), f'{self.data_dir} must be an existing directory'
        self.log_dir = kwargs.get('log_dir', indaleko_default_log_dir)
        assert os.path.isdir(self.data_dir), f'{self.data_dir} must be an existing directory'
        self.timestamp = kwargs.get('timestamp', datetime.datetime.now(datetime.timezone.utc).isoformat())
        assert isinstance(self.timestamp, str), 'timestamp must be a string'
        self.collector_data = kwargs['collector_data'] # blow up if not defined
        if 'machine_id' in kwargs:
            self.machine_id = kwargs['machine_id']
        if 'storage_description' in kwargs:
            assert isinstance(kwargs['storage_description'], str), \
                f'storage_description must be a string, not {type(kwargs["storage_description"])}'
            self.storage_description = kwargs['storage_description']
        if 'path' in kwargs:
            self.path = kwargs['path']
        else:
            self.path = os.path.expanduser('~')
        self.collector_service = None
        if not self.offline:
            self.collector_service = IndalekoServiceManager()\
                .lookup_service_by_identifier(str(self.get_collector_service_identifier()))
            if self.collector_service is None:
                self.collector_service = IndalekoServiceManager()\
                    .register_service(
                    service_name=self.get_collector_service_name(),
                    service_id=str(self.get_collector_service_identifier()),
                    service_description=self.get_collector_service_description(),
                    service_version=self.get_collector_service_version(),
                    service_type=self.get_collector_service_type(),
                )
        assert self.collector_service is not None or self.offline,\
            "Collector service does not exist, not in offline mode"
        for count in self.counter_values:
            setattr(self, count, 0)

    @classmethod
    def get_collector_data(cls) -> IndalekoStorageCollectorDataModel:
        '''This function returns the collector data.'''
        return cls.collector_data

    @classmethod
    def get_collector_platform_name(cls) -> Union[str, None]:
        '''This function returns the collector platform, or None if not applicable.'''
        return cls.collector_data.CollectorPlatformName

    @classmethod
    def get_collector_name(cls) -> str:
        '''This function returns the collector name.'''
        return cls.collector_data.CollectorPlatformName

    @classmethod
    def get_collector_service_name(cls) -> str:
        '''This function returns the service name.'''
        return cls.collector_data.CollectorServiceName

    @classmethod
    def get_collector_service_description(cls) -> str:
        '''This function returns the service description.'''
        return cls.collector_data.CollectorServiceDescription

    @classmethod
    def get_collector_service_version(cls) -> str:
        '''This function returns the service version.'''
        return cls.collector_data.CollectorServiceVersion

    @classmethod
    def get_collector_service_type(cls) -> str:
        '''This function returns the service type.'''
        return cls.collector_data.CollectorServiceType

    @classmethod
    def get_collector_service_identifier(cls) -> uuid.UUID:
        '''This function returns the service identifier.'''
        return cls.collector_data.CollectorServiceUUID

    @classmethod
    def get_collector_cli_handler_mixin(cls):
        '''This function returns the cli handler mixin that should be used.'''
        return cls.cli_handler_mixin


    @staticmethod
    def find_collector_files(
            search_dir : str,
            prefix : str = default_file_prefix,
            suffix : str = default_file_suffix) -> list:
        '''This function finds the files to ingest:
            search_dir: path to the search directory
            prefix: prefix of the collector file
            suffix: suffix of the collector file (default is .json)
        '''
        assert search_dir is not None, 'search_dir must be a valid path'
        assert os.path.isdir(search_dir), 'search_dir must be a valid directory'
        assert prefix is not None, 'prefix must be a valid string'
        assert suffix is not None, 'suffix must be a valid string'
        return [x for x in os.listdir(search_dir)
                if x.startswith(prefix)
                and x.endswith(suffix) and 'collector-' in x]

    def get_counts(self):
        '''
        Retrieves counters about the collector.
        '''
        return {x : getattr(self, x) for x in BaseStorageCollector.counter_values}

    @staticmethod
    def generate_collector_file_name(**kwargs) -> str:
        '''This will generate a file name for the collector output file.'''
        # platform : str, target_dir : str = None, suffix : str = None) -> str:
        ic(f'generate_collector_file_name: {kwargs}')
        assert 'collector_name' in kwargs, 'collector_name must be specified'
        platform = None
        if 'platform' in kwargs:
            if not isinstance(kwargs['platform'], str):
                raise ValueError('platform must be a string')
            platform = kwargs['platform'].replace('-', '_')
        collector_name = kwargs.get('collector_name', 'unknown_collector').replace('-', '_')
        if not isinstance(collector_name, str):
            raise ValueError('collector_name must be a string')
        machine_id = kwargs.get('machine_id', None)
        storage_description = None
        if 'storage_description' in kwargs:
            storage_description = str(uuid.UUID(kwargs['storage_description']).hex)
        timestamp = kwargs.get('timestamp',
                               datetime.datetime.now(datetime.timezone.utc).isoformat())
        assert isinstance(timestamp, str), 'timestamp must be a string'
        target_dir = indaleko_default_data_dir
        if 'target_dir' in kwargs:
            target_dir = kwargs['target_dir']
        suffix = kwargs.get('suffix', BaseStorageCollector.default_file_suffix)
        kwargs = {
            'service' : collector_name,
            'timestamp' : timestamp,
        }
        if platform:
            kwargs['platform'] = platform
        if storage_description is not None:
            kwargs['storage'] = storage_description
        if machine_id is not None:
            kwargs['machine'] = machine_id
        kwargs['suffix'] = suffix
        ic(f'calling generate_file_name with {kwargs}')
        name = generate_file_name(**kwargs)
        return os.path.join(target_dir,name)

    @staticmethod
    def extract_metadata_from_collector_file_name(file_name : str) -> dict:
        '''
        This script extracts metadata from a collector file name, based upon
        the format used by generate_collector_file_name.
        '''
        data = extract_keys_from_file_name(file_name)
        if data is None:
            raise ValueError("Filename format not recognized")
        if 'machine' in data:
            data['machine'] = str(uuid.UUID(data['machine']))
        if 'storage' in data:
            data['storage'] = str(uuid.UUID(data['storage']))
        return data

    def build_stat_dict(self, name: str, root : str) -> tuple:
        '''This function builds a stat dict for a given file.'''
        file_path = os.path.join(root, name)
        if not os.path.exists(file_path):
            if not name in os.listdir(root):
                logging.warning('File %s does not exist in directory %s', file_path, root)
                self.not_found_count += 1
            elif os.path.lexists(file_path):
                logging.warning('File %s is a broken symlink', file_path)
                self.bad_symlink_count += 1
            else:
                logging.warning('File %s exists in directory %s but not accessible', file_path, root)
                self.access_error_count += 1
            return None

        lstat_data = None
        try:
            lstat_data = os.lstat(file_path)
            stat_data = os.stat(file_path)
        except Exception as e: # pylint: disable=broad-except
            # at least for now, we just skip errors
            logging.warning('Unable to stat %s : %s', file_path, e)
            if lstat_data is not None:
                self.bad_symlink_count += 1
            else:
                self.error_count += 1
            return None
        if stat_data.st_ino != lstat_data.st_ino:
            logging.info('File %s is a symlink, collecting symlink data', file_path)
            self.good_symlink_count += 1
            stat_data = lstat_data
        elif stat.S_ISDIR(stat_data.st_mode):
            self.dir_count += 1
        elif stat.S_ISREG(stat_data.st_mode):
            self.file_count += 1
        elif stat.S_ISLNK(stat_data.st_mode):
            raise ValueError('Symlinks should have been handled above')
        else:
            self.special_count += 1
            return None # don't process special files

        stat_dict = {key : getattr(stat_data, key) \
                    for key in dir(stat_data) if key.startswith('st_')}
        stat_dict['Name'] = name
        stat_dict['Path'] = root
        stat_dict['URI'] = os.path.join(root, name)
        stat_dict['Collector'] = str(self.service_identifier)
        stat_dict['ObjectIdentifier'] = str(uuid.uuid4())
        return stat_dict

    @staticmethod
    def convert_to_serializable(data):
        if isinstance(data, (int, float, str, bool, type(None))):
            return data
        elif isinstance(data, list):
            return [BaseStorageCollector.convert_to_serializable(item) for item in data]
        elif isinstance(data, dict):
            return {key: BaseStorageCollector.convert_to_serializable(value) for key, value in data.items()}
        else:
            if hasattr(data, '__dict__'):
                return BaseStorageCollector.convert_to_serializable(data.__dict__)
            return None


    def collect(self) -> list:
        '''
        This is the main function for the collector.  Can be overridden
        for platforms that require additional processing.
        '''
        data = []
        for root, dirs, files in os.walk(self.path):
            for name in dirs + files:
                entry = self.build_stat_dict(name, root)
                if entry is not None:
                    data.append(entry)
        return data


    def write_data_to_file(self, data : list, output_file : str, jsonlines_output : bool = True) -> None:
        '''This function writes the data to the output file.'''
        assert data is not None, 'data must be a valid list'
        assert 'unknown' not in output_file, f'unknown should not be present in the file name {output_file}'
        assert output_file is not None, 'output_file must be a valid string'
        if jsonlines_output:
            with jsonlines.open(output_file, 'w') as output:
                for entry in data:
                    try:
                        try:
                            output.write(entry)
                        except Exception as e:
                            ic(f'Writing entry {entry} failed due to {e}', entry)
                            raise e
                        logging.debug('Wrote entry %s.', entry)
                        self.output_count += 1
                    except UnicodeEncodeError as e:
                        logging.error('Writing entry %s to %s failed due to encoding issues', entry, output_file)
                        ic('Writing entry %s to %s failed due to encoding issues', entry, output_file)
                        self.encoding_count += 1
            logging.info('Wrote jsonlines file %s.', output_file)
        else:
            json.dump(data, output_file, indent=4)
            logging.info('Wrote json %s.', output_file)




def main():
    """Test code for this module."""
    collector = BaseStorageCollector()
    output_file = collector.generate_collector_file_name(
        collector_name = 'test_collector',
    )
    ic(output_file)
    with open(output_file, 'wt', encoding='utf-8-sig') as output:
        output.write('Hello, world!\n')
        print(f'Wrote {output_file}')
    metadata = collector.extract_metadata_from_collector_file_name(output_file)
    print(json.dumps(metadata, indent=4))

if __name__ == "__main__":
    main()
