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
from pathlib import Path
import shutil
import sys
import tempfile
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
from utils.misc.directory_management import indaleko_default_log_dir, indaleko_default_data_dir, \
    indaleko_default_config_dir
from utils.misc.file_name_management import indaleko_file_name_prefix, generate_file_name, extract_keys_from_file_name
# pylint: enable=wrong-import-position


class BaseStorageCollector:
    '''
    This is the base class for Indaleko storage collectors.  It provides fundamental
    mechanisms for managing the data and configuration files that are used by
    the collectors.
    '''
    default_collector_data = IndalekoStorageCollectorDataModel(
        PlatformName=None,
        ServiceRegistrationName='Indaleko Generic Collector',
        ServiceFileName='collector',
        ServiceUUID=uuid.UUID('4a80a080-9cc9-4856-bf43-7b646557ac2d'),
        ServiceVersion='1.0',
        ServiceDescription='Base Indaleko storage collector. Do not use.',
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

    cli_handler_mixin = None  # there is no default handler mixin

    # local requires it, cloud does not
    requires_machine_config = True

    def __init__(self, **kwargs):
        if self.requires_machine_config:
            assert 'machine_config' in kwargs, 'machine_config must be specified'
            self.machine_config = kwargs['machine_config']
            if 'machine_id' not in kwargs:
                kwargs['machine_id'] = self.machine_config.machine_id
        self.debug = kwargs.get('debug', False)
        self.offline = False
        if 'offline' in kwargs:
            self.offline = kwargs['offline']
            del kwargs['offline']
        if self.debug:
            ic(self.offline)
        if 'collector_data' in kwargs:
            self.collector_data = kwargs['collector_data']
        assert hasattr(self, 'collector_data'), 'collector_data must either be passed in or created in derived class'
        self.platform = kwargs.get('platform', self.collector_data.PlatformName)
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
        assert hasattr(self, 'collector_data'), 'Must be created by derived class'
        self.machine_id = None
        self.storage_description = None
        if self.requires_machine_config:
            if 'machine_id' in kwargs:
                self.machine_id = kwargs['machine_id']
            else:
                assert 'machine_config' in kwargs, 'machine_config must be specified'
                self.machine_config = kwargs['machine_config']
                self.machine_id = self.machine_config.machine_id
            assert hasattr(self, 'machine_id')
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
                    service_name=self.get_collector_service_registration_name(),
                    service_id=str(self.get_collector_service_identifier()),
                    service_description=self.get_collector_service_description(),
                    service_version=self.get_collector_service_version(),
                    service_type=self.get_collector_service_type(),
                )
        assert self.collector_service is not None or self.offline, \
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
        return cls.collector_data.PlatformName

    @classmethod
    def get_collector_service_registration_name(cls) -> str:
        '''This function returns the service name for registration'''
        return cls.collector_data.ServiceRegistrationName

    @classmethod
    def get_collector_service_file_name(cls) -> str:
        '''This function returns the service name for file construction.'''
        return cls.collector_data.ServiceFileName

    @classmethod
    def get_collector_service_description(cls) -> str:
        '''This function returns the service description.'''
        return cls.collector_data.ServiceDescription

    @classmethod
    def get_collector_service_version(cls) -> str:
        '''This function returns the service version.'''
        return cls.collector_data.ServiceVersion

    @classmethod
    def get_collector_service_type(cls) -> str:
        '''This function returns the service type.'''
        return cls.collector_data.ServiceType

    @classmethod
    def get_collector_service_identifier(cls) -> uuid.UUID:
        '''This function returns the service identifier.'''
        return cls.collector_data.ServiceUUID

    @classmethod
    def get_collector_cli_handler_mixin(cls):
        '''This function returns the cli handler mixin that should be used.'''
        return cls.cli_handler_mixin

    @staticmethod
    def find_collector_files(
            search_dir: str,
            prefix: str = default_file_prefix,
            suffix: str = default_file_suffix) -> list:
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
        return {x: getattr(self, x) for x in BaseStorageCollector.counter_values}

    def generate_collector_file_name(self: 'BaseStorageCollector', **kwargs) -> str:
        '''Generate a file name for the Linux local collector'''
        if 'platform' not in kwargs:
            kwargs['platform'] = self.collector_data.PlatformName
        if 'collector_name' not in kwargs:
            kwargs['collector_name'] = self.collector_data.ServiceRegistrationFileName
        if 'machine_id' not in kwargs:
            if not hasattr(self, 'machine_id'):
                ic(f'type(cls): {type(self)}')
                ic(f'dir(cls): {dir(self)}')
            kwargs['machine_id'] = self.machine_id  # must be there!
        assert 'machine_id' in kwargs, 'machine_id must be specified'
        return BaseStorageCollector.__generate_collector_file_name(**kwargs)

    @staticmethod
    def __generate_collector_file_name(**kwargs) -> str:
        '''This will generate a file name for the collector output file.'''
        # platform : str, target_dir : str = None, suffix : str = None) -> str:
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
            'service': collector_name,
            'timestamp': timestamp,
        }
        if platform:
            kwargs['platform'] = platform
        if machine_id is not None:
            kwargs['machine'] = machine_id
        if storage_description is not None:
            kwargs['storage'] = storage_description
        kwargs['suffix'] = suffix
        name = generate_file_name(**kwargs)
        return os.path.join(target_dir, name)

    @staticmethod
    def extract_metadata_from_collector_file_name(file_name: str) -> dict:
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

    def build_stat_dict(self, name: str, root: str) -> tuple:
        '''This function builds a stat dict for a given file.'''
        file_path = os.path.join(root, name)
        if not os.path.exists(file_path):
            if name not in os.listdir(root):
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
        except Exception as e:  # pylint: disable=broad-except
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
            return None  # don't process special files

        stat_dict = {
            key: getattr(stat_data, key)
            for key in dir(stat_data) if key.startswith('st_')
        }
        stat_dict['Name'] = name
        stat_dict['Path'] = root
        stat_dict['URI'] = os.path.join(root, name)
        stat_dict['Collector'] = str(self.get_collector_service_identifier())
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

    def collect(self, **kwargs) -> None:
        '''
        This is the main function for the collector.  Can be overridden
        for platforms that require additional processing.
        '''
        data = []
        count = 0
        for root, dirs, files in os.walk(self.path):
            try:
                root.encode('utf-8')
            except UnicodeEncodeError as e:
                logging.warning('Unable to encode directory %s : %s * skipping', root, e)
                ic(f'Unable to encode directory {root} : {e} * skipping')
                self.encoding_count += 1
                continue
            for name in dirs + files:
                try:
                    name.encode('utf-8')
                except UnicodeEncodeError as e:
                    logging.warning('Unable to encode name %s (path %s) : %s * skipping',
                                    name,
                                    root,
                                    e)
                    ic(f'Unable to encode name {name} (path {root}) : {e} * skipping')
                    self.encoding_count += 1
                    continue
                entry = self.build_stat_dict(name, root)
                if entry is not None:
                    data.append(entry)
                    count += 1
                if self.debug and count % 10000 == 0:
                    print('Processed', count, 'entries, continuing')
        self.data = data
        if self.debug:
            print('Processed', count, 'entries (complete)')
        self.output_count = count

    @staticmethod
    def write_data_to_file(
        collector: 'BaseStorageCollector',
        output_file_name: str = None
    ) -> None:
        '''Write the data to a file'''
        if output_file_name is None:
            if hasattr(collector, 'output_file_name'):
                output_file_name = collector.output_file_name
            else:
                output_file_name = collector.generate_collector_file_name()
                ic('Warning: implicit output file name being used')
                assert False
        data_file_name, count = collector.record_data_in_file(
            collector.data,
            collector.data_dir,
            output_file_name
        )
        logging.info('Wrote %d entries to %s', count, data_file_name)
        if hasattr(collector, 'output_count'):
            collector.output_count += count

    @staticmethod
    def __write_data_to_file(data: list, file_name: str = None, jsonlines_output: bool = True) -> int:
        '''
        This will write the given data to the specified file.

        Inputs:
            * data: the data to write
            * file_name: the name of the file to write to
            * jsonlines_output: whether to write the data in JSONLines format

        Returns:
            The number of records written to the file.
        '''
        if data is None:
            raise ValueError('data must be specified')
        if file_name is None:
            raise ValueError('file_name must be specified')
        output_count = 0
        if jsonlines_output:
            with jsonlines.open(file_name, mode='w') as writer:
                for entry in data:
                    try:
                        writer.write(entry)
                        output_count += 1
                    except TypeError as err:
                        logging.error('Error writing entry to JSONLines file: %s', err)
                        logging.error('Entry: %s', entry)
                        logging.error('Output count: %d', output_count)
                        logging.error('Data size %d', len(data))
                        raise err
                    except UnicodeEncodeError as err:
                        logging.error('Error writing entry to JSONLines file: %s', err)
                        logging.error('Entry: %s', entry)
                        logging.error('Output count: %d', output_count)
                        logging.error('Data size %d', len(data))
                        ic(f'Error writing entry to JSONLines file: \n\t{entry}\n\t{err}')
                        continue  # ignoring
            logging.info('Wrote JSONLines data to %s', file_name)
            print('Wrote JSONLines data to', file_name)
        else:
            json.dump(data, file_name, indent=4)
            print('Wrote JSON data to', file_name)
            logging.info('Wrote JSON data to %s', file_name)
        return output_count

    @staticmethod
    def record_data_in_file(
        data: list,
        dir_name: Union[Path, str],
        preferred_file_name: Union[Path, str, None] = None
    ) -> tuple[str, int]:
        '''
        Record the specified data in a file.

        Inputs:
            - data: The data to record
            - preferred_file_name: The preferred file name (if any)

        Returns:
            - The name of the file where the data was recorded
            - The number of entries that were written to the file

        Notes:
            A temporary file is always created to hold the data, and then it is renamed to the
            preferred file name if it is provided.
        '''
        temp_file_name = ""
        with tempfile.NamedTemporaryFile(dir=dir_name, delete=False) as tf:
            temp_file_name = tf.name
        count = BaseStorageCollector.__write_data_to_file(data, temp_file_name)
        if preferred_file_name is None:
            return temp_file_name, count
        # try to rename the file
        try:
            if os.path.exists(preferred_file_name):
                os.remove(preferred_file_name)
            shutil.move(temp_file_name, preferred_file_name)
            print(f'Renamed {temp_file_name} to {preferred_file_name}')
        except (
            FileNotFoundError,
            PermissionError,
            FileExistsError,
            OSError
        ) as e:
            logging.error('Unable to rename temp file %s to %s : %s', temp_file_name, preferred_file_name, e)
            ic(f'Unable to rename temp file {temp_file_name} to output file {preferred_file_name}')
            ic(f'Error: {e}')
            preferred_file_name = temp_file_name
        return preferred_file_name, count


def main():
    """Test code for this module."""
    collector = BaseStorageCollector()
    output_file = collector.generate_collector_file_name(
        collector_name='test_collector',
    )
    ic(output_file)
    with open(output_file, 'wt', encoding='utf-8-sig') as output:
        output.write('Hello, world!\n')
        print(f'Wrote {output_file}')
    metadata = collector.extract_metadata_from_collector_file_name(output_file)
    print(json.dumps(metadata, indent=4))


if __name__ == "__main__":
    main()
