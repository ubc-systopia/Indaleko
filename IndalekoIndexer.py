'''
This is the common class library for Indaleko Indexers (that is, agents that
index data from storage locations.)
'''
import os
import datetime
import logging
import jsonlines
import json
import re

from Indaleko import Indaleko
from IndalekoServices import IndalekoService

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
        self.indexer_service = IndalekoService(
            service_name=self.service_name,
            service_identifier=self.service_identifier,
            service_description=self.service_description,
            service_version=self.service_version,
            service_type=self.service_type
        )
        assert self.indexer_service is not None, "Indexer service does not exist."

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
                and x.endswith(suffix) and 'indexer' in x]

    def generate_indexer_file_name(self, target_dir : str = None) -> str:
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

    @staticmethod
    def extract_metadata_from_indexer_file_name(file_name : str) -> dict:
        '''
        This script extracts metadata from an indexer file name, based upon
        the format used by generate_indexer_file_name.
        '''
        base_file_name, file_suffix = os.path.splitext(os.path.basename(file_name))

        # Define the regular expression pattern to match the structured filename
        pattern = (
            r'(?P<file_prefix>[^-]+)-'
            r'platform=(?P<platform>[^-]+)-'
            r'indexer=(?P<indexer>[^-]+)-'
            r'machine=(?P<machine_id>[^-]+)-'
            r'storage=(?P<storage_description>[^-]+)-'
            r'timestamp=(?P<timestamp>.+)'
        )
        # Match the pattern to the filename
        match = re.match(pattern, base_file_name)
        if not match:
            raise ValueError("Filename format not recognized")
        # Extract the metadata into a dictionary
        metadata = match.groupdict()
        # Perform any necessary post-processing (e.g., replacing underscores back with hyphens)
        for key in metadata:
            metadata[key] = metadata[key].replace('_', '-')
        if 'timestamp' in metadata:
            # 2024-01-15T19-47-11.670000+00-00
            timestamp = metadata['timestamp'].replace('-', ':')
            timestamp_parts = timestamp.split('.')
            fractional_part = timestamp_parts[1][:6] # truncate to 6 digits
            ymd, hms = timestamp_parts[0].split('T')
            timestamp = ymd.replace(':', '-') + 'T' + hms + '.' + fractional_part + '+00:00'
            metadata['timestamp'] = timestamp
        metadata['file_suffix'] = file_suffix
        return metadata

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
        stat_dict['Name'] = name
        stat_dict['Path'] = root
        stat_dict['URI'] = os.path.join(last_uri, name)
        stat_dict['Indexer'] = self.service_identifier
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
    output_file = indexer.generate_indexer_file_name()
    with open(output_file, 'wt', encoding='utf-8-sig') as output:
        output.write('Hello, world!\n')
        print(f'Wrote {output_file}.')
    metadata = indexer.extract_metadata_from_indexer_file_name(output_file)
    print(json.dumps(metadata, indent=4))

if __name__ == "__main__":
    main()
