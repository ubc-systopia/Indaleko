'''
This is the common class library for Indaleko Indexers (that is, agents that
index data from storage locations.)

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
import stat
import datetime
import logging
import jsonlines
import json
import uuid
from Indaleko import Indaleko
from IndalekoServiceManager import IndalekoServiceManager

class IndalekoIndexer:
    '''
    This is the base class for Indaleko Indexers.  It provides fundamental
    mechanisms for managing the data and configuration files that are used by
    the indexers.
    '''
    indaleko_generic_indexer_uuid = '4a80a080-9cc9-4856-bf43-7b646557ac2d'
    indaleko_generic_indexer_service_name = "Indaleko Generic Indexer"
    indaleko_generic_indexer_service_description = "This is the base (non-specialized) Indaleko Indexer. You should not see it in the database."
    indaleko_generic_indexer_service_version = '1.0'

    # define the parameters for the generic indexer service.  These should be
    # overridden by the derived classes.
    indaleko_generic_indexer_service = {
        'service_name' : indaleko_generic_indexer_service_name,
        'service_description' : indaleko_generic_indexer_service_description,
        'service_version' : indaleko_generic_indexer_service_version,
        'service_type' : 'Indexer',
        'service_identifier' : indaleko_generic_indexer_uuid,
    }

    # we use a common file naming mechanism.  These are overridable defaults.
    default_file_prefix = 'indaleko'
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

    def __init__(self, **kwargs):
        if 'file_prefix' in kwargs:
            self.file_prefix = kwargs['file_prefix']
        else:
            self.file_prefix = IndalekoIndexer.default_file_prefix
        self.file_prefix = self.file_prefix.replace('-', '_')
        if 'file_suffix' in kwargs:
            self.file_suffix = kwargs['file_suffix'].replace('-', '_')
        else:
            self.file_suffix = IndalekoIndexer.default_file_suffix
        self.file_suffix = self.file_suffix.replace('-', '_')
        if 'data_dir' in kwargs:
            self.data_dir = kwargs['data_dir']
        else:
            self.data_dir = Indaleko.default_data_dir
        assert os.path.isdir(self.data_dir), f'{self.data_dir} must be an existing directory'
        if 'config_dir' in kwargs:
            self.config_dir = kwargs['config_dir']
        else:
            self.config_dir = Indaleko.default_config_dir
        assert os.path.isdir(self.data_dir), f'{self.data_dir} must be an existing directory'
        if 'log_dir' in kwargs:
            self.log_dir = kwargs['log_dir']
        else:
            self.log_dir = Indaleko.default_log_dir
        assert os.path.isdir(self.data_dir), f'{self.data_dir} must be an existing directory'
        if 'timestamp' in kwargs:
            self.timestamp = kwargs['timestamp']
        else:
            self.timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if 'platform' in kwargs:
            self.platform = kwargs['platform']
        if 'indexer_name' in kwargs:
            assert isinstance(kwargs['indexer_name'], str), 'indexer_name must be a string'
            self.indexer_name = kwargs['indexer_name']
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
        self.service_name = IndalekoIndexer.indaleko_generic_indexer_service_name
        if 'service_name' in kwargs:
            self.service_name = kwargs['service_name']
        self.service_description = \
            self.indaleko_generic_indexer_service_description
        if 'service_description' in kwargs:
            self.service_description = kwargs['service_description']
        self.service_version = self.indaleko_generic_indexer_service_version
        if 'service_version' in kwargs:
            self.service_version = kwargs['service_version']
        self.service_type = 'Indexer'
        if 'service_type' in kwargs:
            self.service_type = kwargs['service_type']
        self.service_identifier = self.indaleko_generic_indexer_uuid
        if 'service_identifier' in kwargs:
            self.service_identifier = kwargs['service_identifier']
        self.indexer_service = IndalekoServiceManager().register_service(
            service_name=self.service_name,
            service_id=self.service_identifier,
            service_description=self.service_description,
            service_version=self.service_version,
            service_type=self.service_type
        )
        assert self.indexer_service is not None, "Indexer service does not exist."
        for count in IndalekoIndexer.counter_values:
            setattr(self, count, 0)

    @staticmethod
    def find_indexer_files(
            search_dir : str,
            prefix : str = default_file_prefix,
            suffix : str = default_file_suffix) -> list:
        '''This function finds the files to ingest:
            search_dir: path to the search directory
            prefix: prefix of the file to ingest
            suffix: suffix of the file to ingest (default is .json)
        '''
        assert search_dir is not None, 'search_dir must be a valid path'
        assert os.path.isdir(search_dir), 'search_dir must be a valid directory'
        assert prefix is not None, 'prefix must be a valid string'
        assert suffix is not None, 'suffix must be a valid string'
        return [x for x in os.listdir(search_dir)
                if x.startswith(prefix)
                and x.endswith(suffix) and 'indexer' in x]

    def get_counts(self):
        '''
        Retrieves counters about the indexer.
        '''
        return {x : getattr(self, x) for x in IndalekoIndexer.counter_values}

    @staticmethod
    def generate_indexer_file_name(**kwargs) -> str:
        '''This will generate a file name for the indexer output file.'''
        # platform : str, target_dir : str = None, suffix : str = None) -> str:
        platform = 'unknown_platform'
        if 'platform' in kwargs:
            platform = kwargs['platform']
        if not isinstance(platform, str):
            raise ValueError('platform must be a string')
        platform = platform.replace('-', '_')
        indexer_name = 'unknown_indexer'
        if 'indexer_name' in kwargs:
            indexer_name = kwargs['indexer_name']
        if not isinstance(indexer_name, str):
            raise ValueError('indexer_name must be a string')
        indexer_name = indexer_name.replace('-', '_')
        indexer_name = indexer_name.replace('-', '_')
        machine_id = str(uuid.UUID('00000000-0000-0000-0000-000000000000').hex)
        if 'machine_id' in kwargs:
            machine_id = str(uuid.UUID(kwargs['machine_id']).hex)
        storage_description = None
        if 'storage_description' in kwargs:
            storage_description = str(uuid.UUID(kwargs['storage_description']).hex)
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if 'timestamp' in kwargs:
            timestamp = kwargs['timestamp']
        target_dir = Indaleko.default_data_dir
        if 'target_dir' in kwargs:
            target_dir = kwargs['target_dir']
        suffix = None
        if 'suffix' in kwargs:
            suffix = kwargs['suffix']
        kwargs = {
            'platform' : platform,
            'service' : indexer_name,
            'machine' : machine_id,
            'timestamp' : timestamp,
        }
        if storage_description is not None:
            kwargs['storage'] = storage_description
        if 'suffix' in kwargs:
            kwargs['suffix'] = kwargs['suffix']
        name = Indaleko.generate_file_name(**kwargs)
        return os.path.join(target_dir,name)

    @staticmethod
    def extract_metadata_from_indexer_file_name(file_name : str) -> dict:
        '''
        This script extracts metadata from an indexer file name, based upon
        the format used by generate_indexer_file_name.
        '''
        data = Indaleko.extract_keys_from_file_name(file_name)
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
            logging.info('File %s is a symlink, indexing symlink data', file_path)
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
            return None # don't index special files

        stat_dict = {key : getattr(stat_data, key) \
                    for key in dir(stat_data) if key.startswith('st_')}
        stat_dict['Name'] = name
        stat_dict['Path'] = root
        stat_dict['URI'] = os.path.join(root, name)
        stat_dict['Indexer'] = self.service_identifier
        stat_dict['ObjectIdentifier'] = str(uuid.uuid4())
        return stat_dict

    @staticmethod
    def convert_to_serializable(data):
        if isinstance(data, (int, float, str, bool, type(None))):
            return data
        elif isinstance(data, list):
            return [IndalekoIndexer.convert_to_serializable(item) for item in data]
        elif isinstance(data, dict):
            return {key: IndalekoIndexer.convert_to_serializable(value) for key, value in data.items()}
        else:
            if hasattr(data, '__dict__'):
                return IndalekoIndexer.convert_to_serializable(data.__dict__)
            return None




    def index(self) -> list:
        '''
        This is the main indexing function for the indexer.  Can be overriden
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
        assert output_file is not None, 'output_file must be a valid string'
        if jsonlines_output:
            with jsonlines.open(output_file, 'w') as output:
                for entry in data:
                    try:
                        output.write(entry)
                        logging.debug('Wrote entry %s.', entry)
                        self.output_count += 1
                    except UnicodeEncodeError as e:
                        logging.error('Writing entry %s to %s failed due to encoding issues', entry, output_file)
                        self.encoding_count += 1
            logging.info('Wrote jsonlines file %s.', output_file)
        else:
            json.dump(data, output_file, indent=4)
            logging.info('Wrote json %s.', output_file)

def main():
    """Test code for this module."""
    indexer = IndalekoIndexer()
    output_file = indexer.generate_indexer_file_name()
    with open(output_file, 'wt', encoding='utf-8-sig') as output:
        output.write('Hello, world!\n')
        print(f'Wrote {output_file}')
    metadata = indexer.extract_metadata_from_indexer_file_name(output_file)
    print(json.dumps(metadata, indent=4))

if __name__ == "__main__":
    main()
