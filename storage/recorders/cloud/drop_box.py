'''
IndalekoDropboxRecorder.py

This script is used to ingest the files that have been indexed from Dropbox.  It
will create a JSONL file with the ingested metadata suitable for uploading to
the Indaleko database.

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
import argparse
import datetime
from icecream import ic
import json
import jsonlines
import logging
import os
import sys
import tempfile
import uuid

from icecream import ic
from typing import Any, Union, Callable

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from db import IndalekoServiceManager
from platforms.windows.machine_config import IndalekoWindowsMachineConfig
from platforms.unix import UnixFileAttributes
from platforms.windows_attributes import IndalekoWindows
from storage import IndalekoObject
from storage.collectors.cloud.drop_box import IndalekoDropboxCloudStorageCollector
from storage.recorders.data_model import IndalekoStorageRecorderDataModel
from storage.recorders.cloud.cloud_base import BaseCloudStorageRecorder
from utils.decorators import type_check
from utils.i_logging import IndalekoLogging
from utils.misc.file_name_management import find_candidate_files
from utils.misc.data_management import encode_binary_data
# pylint: enable=wrong-import-position


class IndalekoDropboxCloudStorageRecorder(BaseCloudStorageRecorder):
    '''
    This class handles ingestion of metadata from the Indaleko Dropbox indexer.
    '''

    dropbox_recorder_uuid = '389ce9e0-3924-4cd1-be8d-5dc4b268e668'
    dropbox_recorder_service = {
        'service_name' : 'Dropbox Recorder',
        'service_description' : 'This service records metadata collected from Dropbox.',
        'service_version' : '1.0',
        'service_type' : IndalekoServiceManager.service_type_storage_recorder,
        'service_identifier' : dropbox_recorder_uuid,
    }

    dropbox_platform = IndalekoDropboxCloudStorageCollector.dropbox_platform
    dropbox_recorder = 'dropbox_recorder'

    recorder_data = IndalekoStorageRecorderDataModel(
        RecorderPlatformName=dropbox_platform,
        RecorderServiceName=dropbox_recorder,
        RecorderServiceUUID=uuid.UUID(dropbox_recorder_uuid),
        RecorderServiceVersion=dropbox_recorder_service['service_version'],
        RecorderServiceDescription=dropbox_recorder_service['service_description'],
    )

    def __old_init__(self, **kwargs) -> None:
        if 'input_file' not in kwargs:
            raise ValueError('input_file must be specified')
        if 'timestamp' not in kwargs:
            raise ValueError('timestamp must be specified')
        if 'platform' not in kwargs:
            raise ValueError('platform must be specified')
        for key, value in self.dropbox_recorder_service.serialize().items():
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
            'Identifier' : self.dropbox_recorder_uuid,
            'Version' : '1.0',
        }

    def __init__(self, **kwargs) -> None:
        '''Build a new Dropbox recorder.'''
        for key, value in self.dropbox_recorder_service.items():
            if key not in kwargs:
                kwargs[key] = value
        if 'platform' not in kwargs:
            kwargs['platform'] = self.dropbox_platform
        if 'recorder' not in kwargs:
            kwargs['recorder'] = self.dropbox_recorder
        super().__init__(**kwargs)
        self.output_file = kwargs.get('output_file', self.generate_file_name())
        self.source = {
            'Identifier' : self.dropbox_recorder_uuid,
            'Version' : self.dropbox_recorder_service['service_version'],
        }

    def build_dummy_root_dir_entry(self) -> IndalekoObject:
        '''This is used to build a dummy root directory object.'''
        dummy_attributes = {
            'Indexer' : '7c18f9c7-9153-427a-967a-55d942ac1f10',
            'ObjectIdentifier' : str(uuid.uuid4()),
            'FolderMetadata' : True,
            'Metadata' : True,
            'path_lower' : '/',
            'path_display' : '/',
            'name' : '',
            'user_id' : self.user_id
        }
        return self.normalize_collector_data(dummy_attributes)

    def find_collector_files(self) -> list:
        '''This function finds the files to record:
            search_dir: path to the search directory
            prefix: prefix of the file to record
            suffix: suffix of the file to record (default is .json)
        '''
        if self.data_dir is None:
            raise ValueError('data_dir must be specified')
        return [x for x in find_candidate_files(
            [
                IndalekoDropboxCloudStorageCollector.dropbox_platform,
                IndalekoDropboxCloudStorageCollector.dropbox_collector_name
            ],
            self.data_dir)
        ]


    def normalize_collector_data(self, data : dict ) -> IndalekoObject:
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
            # ArangoDB is VERY fussy about the timestamps.  If there is no TZ
            # data, it will fail the schema validation.
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
        name = data['name']
        path = data['path_display']
        if path == '/' and name == '':
            pass # root directory
        elif path.endswith(name):
            path = os.path.dirname(path)
            assert len(path) < len(data['path_display'])
            if len(path) == 1 and path[0] == '/':
                test_path = path + name
            else:
                test_path = path + '/' + name
            assert test_path == data['path_display'], f'test_path: {test_path}, path_display: {data["path_display"]}'
        else:
            # unexpected, so let's dump some data
            ic('Path does not end with child name')
            ic(data)
            ic(name)
            ic(path)
            raise ValueError('Path does not end with child name')
        kwargs = {
            'source' : self.source,
            'raw_data' : encode_binary_data(bytes(json.dumps(data).encode('utf-8'))),
            'URI' : 'https://www.dropbox.com/home' + data['path_display'],
            'Path' : path,
            'ObjectIdentifier' : data['ObjectIdentifier'],
            'Timestamps' : timestamps,
            'Size' : size,
            'Attributes' : data,
            'Label' : name,
            'PosixFileAttributes' : UnixFileAttributes.map_file_attributes(unix_file_attributes),
            'WindowsFileAttributes' : IndalekoWindows.map_file_attributes(windows_file_attributes),
        }
        return IndalekoObject(**kwargs)

    def xx_generate_output_file_name(self, **kwargs) -> str:
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
        name = self.generate_file_name(**kwargs)
        return os.path.join(output_dir, name)

    def xx_ingest(self) -> None:
        '''
        This method ingests the metadata from the Dropbox indexer file and
        writes it to a JSONL file.
        '''
        self.load_collector_data_from_file()
        dir_data_by_path = {}
        dir_data = [self.build_dummy_root_dir_entry()]
        file_data = []
        for item in self.indexer_data:
            try:
                obj = self.normalize_collector_data(item)
            except OSError as e:
                logging.error('Error normalizing data: %s', e)
                logging.error('Data: %s', item)
                self.error_count +=1
                continue
            assert 'Path' in obj.args
            if 'S_IFDIR' in obj.args['PosixFileAttributes'] or \
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
        dirmap_lower = {}
        for item in dir_data:
            parent_name = item.args['Path']
            child_name = item.args['Label']
            if parent_name == '/':
                path = parent_name + child_name
            else:
                path = parent_name + '/' + child_name # force use of UNIX style separator
            assert path not in dirmap, f'Duplicate path: {path}'
            dirmap[path] = item.args['ObjectIdentifier']
            dirmap_lower[path.lower()] = item.args['ObjectIdentifier']
        dir_edges = []
        source = {
            'Identifier' : self.dropbox_recorder_uuid,
            'Version' : '1.0',
        }
        for item in dir_data + file_data:
            if 'Path' not in item.args:
                ic(item.args)
                raise ValueError('Path not found in item')
            parent = item.args['Path']
            if parent in dirmap:
                parent_id = dirmap[parent]
            elif parent.lower() in dirmap_lower:
                parent_id = dirmap_lower[parent.lower()]
            elif parent == '/':
                ic(f'Skipping root directory edges for: {item.args}')
                continue # skip the root directory
            else:
                ic(item.args)
                ic('Parent directory not found. aborting.')
                exit(1)
                logging.warning('Parent directory not found: %s', parent)
                continue # skip an unknown parent
            dir_edge = IndalekoRelationshipContains(
                relationship = \
                    IndalekoRelationshipContains.DIRECTORY_CONTAINS_RELATIONSHIP_UUID_STR,
                object1 = {
                    'collection' : Indaleko.Indaleko_Object_Collection,
                    'object' : item.args['ObjectIdentifier'],
                },
                object2 = {
                    'collection' : Indaleko.Indaleko_Object_Collection,
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
                    'collection' : Indaleko.Indaleko_Object_Collection,
                    'object' : parent_id,
                },
                object2 = {
                    'collection' : Indaleko.Indaleko_Object_Collection,
                    'object' : item.args['ObjectIdentifier'],
                },
                source = source
            )
            dir_edges.append(dir_edge)
            self.edge_count += 1
        # Save the data to the ingester output file
        temp_file_name = ''
        with tempfile.NamedTemporaryFile(dir=self.data_dir, delete=False) as temp_file:
            temp_file_name = temp_file.name
        self.write_data_to_file(dir_data + file_data, temp_file_name)
        try:
            if os.path.exists(self.output_file):
                os.remove(self.output_file)
            os.rename(temp_file_name, self.output_file)
        except (
            FileNotFoundError,
            PermissionError,
            FileExistsError,
            OSError,
        ) as e:
            logging.error(
                'Unable to rename temp file %s to output file %s',
                temp_file_name,
                self.output_file
            )
            print(f'Unable to rename temp file {temp_file_name} to output file {self.output_file}')
            print(e)
            self.output_file = temp_file_name
        load_string = self.build_load_string(
            collection=Indaleko.Indaleko_Object_Collection,
            file=self.output_file
        )
        logging.info('Load string: %s', load_string)
        print('Load string: ', load_string)
        with tempfile.NamedTemporaryFile(dir=self.data_dir, delete=False) as temp_file:
            temp_file_name = temp_file.name
        edge_file = self.generate_output_file_name(
            platform=self.platform,
            service='ingest',
            user_id=self.user_id,
            collection=Indaleko.Indaleko_Relationship_Collection,
            timestamp=self.timestamp,
            output_dir=self.data_dir,
        )
        self.write_data_to_file(dir_edges, edge_file)
        try:
            if os.path.exists(edge_file):
                os.remove(edge_file)
            os.rename(temp_file_name, edge_file)
        except (
            FileNotFoundError,
            PermissionError,
            FileExistsError,
            OSError,
        ) as e:
            logging.error(
                'Unable to rename temp file %s to output file %s',
                temp_file_name,
                edge_file
            )
            print(f'Unable to rename temp file {temp_file_name} to output file {edge_file}')
            print(e)
            edge_file = temp_file
        load_string = self.build_load_string(
            collection=Indaleko.Indaleko_Relationship_Collection,
            file=edge_file
        )
        logging.info('Load string: %s', load_string)
        print('Load string: ', load_string)
        return

    def get_object_path(self : 'IndalekoDropboxCloudStorageRecorder', obj : IndalekoObject) -> str:
        '''This method returns the path for the object.'''
        return obj['Path']

    def is_object_directory(self : 'IndalekoDropboxCloudStorageRecorder', obj : IndalekoObject) -> bool:
        '''This method returns True if the object is a directory.'''
        return 'S_IFDIR' in obj['PosixFileAttributes'] or 'FILE_ATTRIBUTE_DIRECTORY' in obj['WindowsFileAttributes']

def old_main():
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
        platform=IndalekoDropboxCloudStorageRecorder.dropbox_platform,
        service_name ='ingester',
        log_dir = pre_args.logdir,
        log_level = pre_args.loglevel,
        timestamp = timestamp,
        suffix = 'log'
    )
    log_file_name = indaleko_logging.get_log_file_name()
    ic(log_file_name)
    indexer = IndalekoDropboxCollector()
    indexer_files = indexer.find_indexer_files(pre_args.datadir)
    ic(indexer_files)
    parser = argparse.ArgumentParser(parents=[pre_parser])
    parser.add_argument('--input',
                        choices=indexer_files,
                        default=indexer_files[-1],
                        help='Dropbox index data file to ingest')
    args=parser.parse_args()
    ic(args)
    input_metadata = IndalekoDropboxCollector.extract_metadata_from_indexer_file_name(args.input)
    ic(input_metadata)
    input_timestamp = timestamp
    if 'timestamp' in input_metadata:
        input_timestamp = input_metadata['timestamp']
    input_platform = IndalekoDropboxCloudStorageRecorder.dropbox_platform
    if 'platform' in input_metadata:
        input_platform = input_metadata['platform']
    if input_platform != IndalekoDropboxCloudStorageRecorder.dropbox_platform:
        ic(f'Input platform {input_platform} does not match expected platform {IndalekoDropboxCloudStorageRecorder.dropbox_platform}')
    file_prefix = IndalekoIngester.default_file_prefix
    if 'file_prefix' in input_metadata:
        file_prefix = input_metadata['file_prefix']
    file_suffix = IndalekoIngester.default_file_suffix
    if 'file_suffix' in input_metadata:
        file_suffix = input_metadata['file_suffix']
    input_file = os.path.join(args.datadir, args.input)
    ingester = IndalekoDropboxCloudStorageRecorder(
        timestamp=input_timestamp,
        platform=input_platform,
        ingester=IndalekoDropboxCloudStorageRecorder.dropbox_recorder,
        file_prefix=file_prefix,
        file_suffix=file_suffix,
        data_dir=args.datadir,
        input_file=input_file,
        log_dir=args.logdir,
        user_id=input_metadata['user_id']
    )
    output_file = ingester.generate_file_name()
    logging.info('Indaleko Dropbox Ingester started.')
    logging.info('Input file: %s', input_file)
    logging.info('Output file: %s', output_file)
    logging.info(args)
    ingester.ingest()
    total=0
    for count_type, count_value in ingester.get_counts().items():
        logging.info('%s: %d', count_type, count_value)
        total += count_value
    logging.info('Total: %d', total)
    logging.info('Indaleko Dropbox Ingester completed.')

def main() -> None:
    '''This is the main handler for the Dropbox recorder.'''
    BaseCloudStorageRecorder.cloud_recorder_runner(
        IndalekoDropboxCloudStorageCollector,
        IndalekoDropboxCloudStorageRecorder,
    )

if __name__ == '__main__':
    main()
