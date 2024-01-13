'''
This is the common class library for Indaleko Indexers (that is, agents that
index data from storage locations.)
'''
import os
import datetime
import logging
import jsonlines
import json

from Indaleko import Indaleko


class IndalekoIndexer:
    '''
    This is the base class for Indaleko Indexers.  It provides fundamental
    mechanisms for managing the data and configuration files that are used by
    the indexers.
    '''

    default_file_prefix = 'indaleko'
    default_file_suffix = '.jsonl'

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
        if 'indexer' in kwargs:
            self.indexer = kwargs['indexer']
        if 'machine_id' in kwargs:
            self.machine_id = kwargs['machine_id']
        if 'storage_description' in kwargs:
            self.storage_description = kwargs['storage_description']
        if 'path' in kwargs:
            self.path = kwargs['path']
        else:
            self.path = os.path.expanduser('~')


    def find_indexer_files(self,
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
                and x.endswith(suffix)]

    def generate_index_file_name(self, target_dir : str = None) -> str:
        '''This will generate a file name for the indexer output file.'''
        if hasattr(self, 'platform'):
            platform = self.platform
        else:
            platform = 'unknown_platform'
        platform = platform.replace('-', '_')
        if hasattr(self, 'indexer'):
            indexer = self.indexer
        else:
            indexer = 'unknown_indexer'
        indexer = indexer.replace('-', '_')
        if hasattr(self, 'machine_id'):
            machine_id = self.machine_id
        else:
            machine_id = 'unknown_machine_id'
        machine_id = machine_id.replace('-', '_')
        if hasattr(self, 'storage_description'):
            storage_description = self.storage_description
        else:
            storage_description = 'unknown_storage_description'
        storage_description = storage_description.replace('-', '_')
        if hasattr(self, 'timestamp'):
            timestamp = self.timestamp
        else:
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        timestamp = timestamp.replace(':', '-')
        if target_dir is None:
            target_dir = self.data_dir
        return os.path.join(
                target_dir,
                f'{self.file_prefix}-\
                   platform={platform}-\
                   indexer={indexer}-\
                   machine={machine_id}-\
                   storage={storage_description}-\
                   timestamp={timestamp}\
                   {self.file_suffix}'.replace(' ', '')
        )

    def build_stat_dict(self, name: str, root : str) -> tuple:
        '''This function builds a stat dict for a given file.'''
        file_path = os.path.join(root, name)
        last_uri = file_path
        try:
            stat_data = os.stat(file_path)
        except Exception as e: # pylint: disable=broad-except
            # at least for now, we just skip errors
            logging.warning('Unable to stat %s : %s', file_path, e)
            return None
        stat_dict = {key : getattr(stat_data, key) for key in dir(stat_data) if key.startswith('st_')}
        stat_dict['file'] = name
        stat_dict['path'] = root
        stat_dict['URI'] = os.path.join(last_uri, name)
        return (stat_dict, last_uri)

    def index(self) -> dict:
        '''
        This is the main indexing function for the indexer.  Can be overriden
        for platforms that require additional processing.
        '''
        data = []
        for root, dirs, files in os.walk(self.path):
            for name in dirs + files:
                entry = self.build_stat_dict(name, root)
                if entry is not None:
                    data.append(entry[0])
        return data

    def write_data_to_file(self, data : list, output_file : str, jsonlines_output : bool = True) -> None:
        '''This function writes the data to the output file.'''
        assert data is not None, 'data must be a valid list'
        assert output_file is not None, 'output_file must be a valid string'
        if jsonlines_output:
            with jsonlines.open(output_file, 'w') as output:
                for entry in data:
                    output.write(entry)
            logging.info('Wrote jsonlines %s.', output_file)
        else:
            json.dump(data, output_file, indent=4)
            logging.info('Wrote json %s.', output_file)

def main():
    """Test code for this module."""
    indexer = IndalekoIndexer()
    output_file = indexer.generate_index_file_name()
    with open(output_file, 'wt', encoding='utf-8-sig') as output:
        output.write('Hello, world!\n')
        print(f'Wrote {output_file}.')

if __name__ == "__main__":
    main()
