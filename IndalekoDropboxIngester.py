'''
IndalekoDropboxIngester.py

This script is used to ingest the files that have been indexed from Dropbox.  It
will create a JSONL file with the ingested metadata suitable for uploading to
the Indaleko database.

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
from icecream import ic
import logging
import os
import json
import jsonlines
import msgpack


from IndalekoIngester import IndalekoIngester
from Indaleko import Indaleko
from IndalekoDropboxIndexer import IndalekoDropboxIndexer
from IndalekoServices import IndalekoService
import IndalekoLogging
from IndalekoObject import IndalekoObject
from IndalekoUnix import UnixFileAttributes
from IndalekoWindows import IndalekoWindows
from IndalekoRelationshipContains import IndalekoRelationshipContains
from IndalekoRelationshipContained import IndalekoRelationshipContainedBy


class IndalekoDropboxIngester(IndalekoIngester):
    '''
    This class handles ingestion of metadata from the Indaleko Dropbox indexer.
    '''

    dropbox_ingester_uuid = '389ce9e0-3924-4cd1-be8d-5dc4b268e668'
    dropbox_ingester_service = IndalekoService.create_service_data(
        service_name = 'Dropbox Ingester',
        service_description = 'This service ingests captured index info from Dropbox.',
        service_version = '1.0',
        service_type = 'Ingester',
        service_identifier = dropbox_ingester_uuid,
    )

    dropbox_platform = IndalekoDropboxIndexer.dropbox_platform
    dropbox_ingester = 'dropbox_ingester'

    def __init__(self, **kwargs) -> None:
        if 'input_file' not in kwargs:
            raise ValueError('input_file must be specified')
        if 'timestamp' not in kwargs:
            raise ValueError('timestamp must be specified')
        if 'platform' not in kwargs:
            raise ValueError('platform must be specified')
        for key, value in self.dropbox_ingester_service.items():
            if key not in kwargs:
                kwargs[key] = value
        super().__init__(**kwargs)
        self.input_file = kwargs['input_file']
        if 'user_id' not in kwargs:
            raise ValueError('user_id must be specified')
        self.user_id = kwargs['user_id']
        if 'output_file' not in kwargs:
            self.output_file = self.generate_file_name()
        else:
            self.output_file = kwargs['output_file']
        self.indexer_data = []
        self.source = {
            'Identifier' : self.dropbox_ingester_uuid,
            'Version' : '1.0',
        }

    def load_indexer_data_from_file(self) -> None:
        '''This function loads the indexer data from the file.'''
        if self.input_file is None:
            raise ValueError('input_file must be specified')
        if self.input_file.endswith('.jsonl'):
            with jsonlines.open(self.input_file) as reader:
                for entry in reader:
                    self.indexer_data.append(entry)
        elif self.input_file.endswith('.json'):
            with open(self.input_file, 'r', encoding='utf-8-sig') as file:
                self.indexer_data = json.load(file)
        else:
            raise ValueError(f'Input file {self.input_file} is an unknown type')
        if not isinstance(self.indexer_data, list):
            raise ValueError('indexer_data is not a list')


    def normalize_index_data(self, data : dict ) -> IndalekoObject:
        '''
        Given some metadata, this will create a record that can be inserted into the
        Object collection.
        '''
        if data is None:
            raise ValueError('Data cannot be None')
        if not isinstance(data, dict):
            raise ValueError('Data must be a dictionary')
        if 'ObjectIdentifier' not in data:
            raise ValueError('Data must contain an ObjectIdentifier')
        if 'user_id' not in data:
            data['user_id'] = self.user_id
        timestamps = []
        size = 0
        if 'FolderMetadata' in data:
            unix_file_attributes = UnixFileAttributes.FILE_ATTRIBUTES['S_IFDIR']
            windows_file_attributes = IndalekoWindows.FILE_ATTRIBUTES['FILE_ATTRIBUTE_DIRECTORY']
        if 'FileMetadata' in data:
            unix_file_attributes = UnixFileAttributes.FILE_ATTRIBUTES['S_IFREG']
            windows_file_attributes = IndalekoWindows.FILE_ATTRIBUTES['FILE_ATTRIBUTE_NORMAL']
            timestamps = [
                {
                    'Label' : IndalekoObject.MODIFICATION_TIMESTAMP,
                    'Value' : data['client_modified'],
                    'Description' : 'Client Modified'
                },
                {
                    'Label' : IndalekoObject.CHANGE_TIMESTAMP,
                    'Value' : data['server_modified'],
                    'Description' : 'Server Modified'
                },
            ]
            size = data['size']
        kwargs = {
            'source' : self.source,
            'raw_data' : msgpack.packb(bytes(json.dumps(data).encode('utf-8'))),
            'URI' : 'https://www.dropbox.com/home' + data['path_display'],
            'Path' : data['path_display'],
            'ObjectIdentifier' : data['ObjectIdentifier'],
            'Timestamps' : timestamps,
            'Size' : size,
            'Attributes' : data,
            'UnixFileAttributes' : UnixFileAttributes.map_file_attributes(unix_file_attributes),
            'WindowsFileAttributes' : IndalekoWindows.map_file_attributes(windows_file_attributes),
        }
        return IndalekoObject(**kwargs)

    def generate_output_file_name(self, **kwargs) -> str:
        '''
        Given a set of parameters, generate a file name for the output
        file.
        '''
        output_dir = None
        if 'output_dir' in kwargs:
            output_dir = kwargs['output_dir']
            del kwargs['output_dir']
        if output_dir is None:
            output_dir = self.data_dir
        kwargs['ingester'] = self.ingester
        name = Indaleko.generate_file_name(**kwargs)
        return os.path.join(output_dir, name)

    def generate_file_name(self, target_dir : str = None, suffix = None) -> str:
        '''This will generate a file name for the ingester output file.'''
        if suffix is None:
            suffix = self.file_suffix
        kwargs = {
        'prefix' : self.file_prefix,
        'suffix' : suffix,
        'platform' : self.platform,
        'user_id' : self.user_id,
        'service' : 'ingest',
        'ingester' : self.ingester,
        'collection' : 'Objects',
        'timestamp' : self.timestamp,
        'output_dir' : target_dir,
        }
        if self.storage_description is not None:
            kwargs['storage'] = str(uuid.UUID(self.storage_description).hex)
        return self.generate_output_file_name(**kwargs)

    def ingest(self) -> None:
        '''
        This method ingests the metadata from the Dropbox indexer file and
        writes it to a JSONL file.
        '''
        self.load_indexer_data_from_file()
        dir_data_by_path = {}
        dir_data = []
        file_data = []
        for item in self.indexer_data:
            obj = self.normalize_index_data(item)
            assert 'Path' in obj.args
            if 'S_IFDIR' in obj.args['UnixFileAttributes'] or \
               'FILE_ATTRIBUTE_DIRECTORY' in obj.args['WindowsFileAttributes']:
                if 'path_display' not in item:
                    logging.warning('Directory object does not have a path: %s', item)
                    continue # skip
                dir_data_by_path[item['path_display']] = obj
                dir_data.append(obj)
                self.dir_count += 1
            else:
                file_data.append(obj)
                self.file_count += 1
        dirmap = {}
        for item in dir_data:
            dirmap[item.args['Path']] = item.args['ObjectIdentifier']
        dir_edges = []
        source = {
            'Identifier' : self.dropbox_ingester_uuid,
            'Version' : '1.0',
        }
        for item in dir_data + file_data:
            if 'Path' not in item.args:
                ic(item.args)
                raise ValueError('Path not found in item')
            parent = item.args['Path']
            if parent not in dirmap:
                logging.warning('Parent directory not found: %s', parent)
                continue # skip an unknown parent
            parent_id = dirmap[parent]
            dir_edge = IndalekoRelationshipContains(
                relationship = \
                    IndalekoRelationshipContains.DIRECTORY_CONTAINS_RELATIONSHIP_UUID_STR,
                object1 = {
                    'collection' : 'Objects',
                    'object' : item.args['ObjectIdentifier'],
                },
                object2 = {
                    'collection' : 'Objects',
                    'object' : parent_id,
                },
                source = source
            )
            dir_edges.append(dir_edge)
            self.edge_count += 1
            dir_edge = IndalekoRelationshipContainedBy(
                relationship = \
                    IndalekoRelationshipContainedBy.CONTAINED_BY_DIRECTORY_RELATIONSHIP_UUID_STR,
                object1 = {
                    'collection' : 'Objects',
                    'object' : parent_id,
                },
                object2 = {
                    'collection' : 'Objects',
                    'object' : item.args['ObjectIdentifier'],
                },
                source = source
            )
            dir_edges.append(dir_edge)
            self.edge_count += 1
        # Save the data to the ingester output file
        self.write_data_to_file(dir_data + file_data, self.output_file)
        load_string = self.build_load_string(
            collection='Objects',
            file=self.output_file
        )
        logging.info('Load string: %s', load_string)
        print('Load string: ', load_string)
        edge_file = self.generate_output_file_name(
            platform=self.platform,
            service='ingest',
            collection='Relationships',
            timestamp=self.timestamp,
            output_dir=self.data_dir,
        )
        load_string = self.build_load_string(
            collection='Relationships',

        )
        self.write_data_to_file(dir_edges, edge_file)
        logging.info('Load string: %s', load_string)
        print('Load string: ', load_string)
        return

def main():
    '''This is the main handler for the Dropbox ingester.'''
    logging_levels = Indaleko.get_logging_levels()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--configdir',
                            help='Path to the config directory',
                            default=Indaleko.default_config_dir)
    pre_parser.add_argument('--logdir', '-l',
                            help='Path to the log directory',
                            default=Indaleko.default_log_dir)
    pre_parser.add_argument('--loglevel',
                            type=int,
                            default=logging.DEBUG,
                            choices=logging_levels,
                            help='Logging level to use (lower number = more logging)')
    pre_parser.add_argument('--datadir',
                            help='Path to the data directory',
                            default=Indaleko.default_data_dir,
                            type=str)
    pre_args , _ = pre_parser.parse_known_args()
    indaleko_logging = IndalekoLogging.IndalekoLogging(
        platform=IndalekoDropboxIngester.dropbox_platform,
        service_name ='ingester',
        log_dir = pre_args.logdir,
        log_level = pre_args.loglevel,
        timestamp = timestamp,
        suffix = 'log'
    )
    log_file_name = indaleko_logging.get_log_file_name()
    ic(log_file_name)
    indexer = IndalekoDropboxIndexer()
    indexer_files = indexer.find_indexer_files(pre_args.datadir)
    ic(indexer_files)
    parser = argparse.ArgumentParser(parents=[pre_parser])
    parser.add_argument('--input',
                        choices=indexer_files,
                        default=indexer_files[-1],
                        help='Dropbox index data file to ingest')
    args=parser.parse_args()
    ic(args)
    input_metadata = IndalekoDropboxIndexer.extract_metadata_from_indexer_file_name(args.input)
    ic(input_metadata)
    input_timestamp = timestamp
    if 'timestamp' in input_metadata:
        input_timestamp = input_metadata['timestamp']
    input_platform = IndalekoDropboxIngester.dropbox_platform
    if 'platform' in input_metadata:
        input_platform = input_metadata['platform']
    if input_platform != IndalekoDropboxIngester.dropbox_platform:
        ic(f'Input platform {input_platform} does not match expected platform {IndalekoDropboxIngester.dropbox_platform}')
    file_prefix = IndalekoIngester.default_file_prefix
    if 'file_prefix' in input_metadata:
        file_prefix = input_metadata['file_prefix']
    file_suffix = IndalekoIngester.default_file_suffix
    if 'file_suffix' in input_metadata:
        file_suffix = input_metadata['file_suffix']
    input_file = os.path.join(args.datadir, args.input)
    ingester = IndalekoDropboxIngester(
        timestamp=input_timestamp,
        platform=input_platform,
        ingester=IndalekoDropboxIngester.dropbox_ingester,
        file_prefix=file_prefix,
        file_suffix=file_suffix,
        data_dir=args.datadir,
        input_file=input_file,
        log_dir=args.logdir,
        user_id=input_metadata['user_id']
    )
    output_file = ingester.generate_file_name()
    logging.info('Indaleko Dropbox Ingester started.')
    logging.info(f'Input file: {input_file}')
    logging.info(f'Output file: {output_file}')
    logging.info(args)
    ingester.ingest()
    total=0
    for count_type, count_value in ingester.get_counts().items():
        logging.info('%s: %d', count_type, count_value)
        total += count_value
    logging.info('Total: %d', total)
    logging.info('Indaleko Dropbox Ingester completed.')


if __name__ == '__main__':
    main()
