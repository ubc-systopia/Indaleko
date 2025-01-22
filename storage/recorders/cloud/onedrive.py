'''
This module handles data ingestion into Indaleko from the One Drive data
collector.

Indaleko OneDrive Data Recorder
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
import json
import os
import sys
import uuid

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from db import IndalekoServiceManager
from platforms.unix import UnixFileAttributes
from platforms.windows_attributes import IndalekoWindows
from storage import IndalekoObject
from storage.collectors.cloud.onedrive import IndalekoOneDriveCloudStorageCollector
from storage.recorders.data_model import IndalekoStorageRecorderDataModel
from storage.recorders.cloud.cloud_base import BaseCloudStorageRecorder
from utils.misc.file_name_management import find_candidate_files, extract_keys_from_file_name
from utils.misc.data_management import encode_binary_data
# pylint: enable=wrong-import-position


class IndalekoOneDriveCloudStorageRecorder(BaseCloudStorageRecorder):
    '''
    This class provides the OneDrive Ingester for Indaleko.
    '''

    onedrive_recorder_uuid = 'c15afa0f-5e5a-4a5b-82ab-8adb0311dfaf'
    onedrive_recorder_service = {
        'service_name': 'Microsoft OneDrive Ingester',
        'service_description': 'This service ingests metadata from OneDrive into Indaleko.',
        'service_version': '1.0.0',
        'service_type': IndalekoServiceManager.service_type_storage_recorder,
        'service_identifier': onedrive_recorder_uuid,
    }

    onedrive_platform = IndalekoOneDriveCloudStorageCollector.onedrive_platform
    onedrive_recorder = 'recorder'

    recorder_data = IndalekoStorageRecorderDataModel(
        RecorderPlatformName=onedrive_platform,
        RecorderServiceName=onedrive_recorder,
        RecorderServiceUUID=uuid.UUID(onedrive_recorder_uuid),
        RecorderServiceVersion=onedrive_recorder_service['service_version'],
        RecorderServiceDescription=onedrive_recorder_service['service_description'],
    )

    def __init__(self, **kwargs: dict) -> None:
        '''Initialize the OneDrive Drive Ingester'''
        for key, value in self.onedrive_recorder_service.items():
            if key not in kwargs:
                kwargs[key] = value
        if 'platform' not in kwargs:
            kwargs['platform'] = self.onedrive_platform
        if 'recorder' not in kwargs:
            kwargs['recorder'] = self.onedrive_recorder
        if 'user_id_ not in kwargs':
            assert 'input_file' in kwargs
            keys = extract_keys_from_file_name(kwargs['input_file'])
            assert 'userid' in keys, f'userid not found in input file name: {kwargs["input_file"]}'
            self.user_id = keys['userid']
        else:
            self.user_id = kwargs['user_id']
        super().__init__(**kwargs)
        self.output_file = kwargs.get('output_file', self.generate_file_name())
        self.source = {
            'Identifier': self.dropbox_recorder_uuid,
            'Version': self.dropbox_recorder_service['service_version'],
        }
        # self.dir_data.append(self.build_dummy_root_dir_entry())

    def find_collector_files(self) -> list:
        '''This function finds the files produced by the collector.'''
        if self.data_dir is None:
            raise ValueError('data_dir must be specified')
        candidates = find_candidate_files(
            [
                IndalekoOneDriveCloudStorageCollector.dropbox_platform,
                IndalekoOneDriveCloudStorageCollector.dropbox_collector_name
            ],
            self.data_dir
        )
        if self.debug:
            ic(candidates)
        return candidates

    @staticmethod
    def extract_uuid_from_etag(etag: str) -> uuid.UUID:
        '''Extract the UUID from the eTag'''
        if etag is None:
            raise ValueError('etag is required')
        if not isinstance(etag, str):
            raise ValueError('etag must be a string')
        match = re.search(r'\{([a-f0-9-]+)\}', etag, re.IGNORECASE)
        if match is None:
            return None
        return uuid.UUID(match.group(1))

    def normalize_index_data(self, data: dict) -> dict:
        '''Normalize the index data'''
        if data is None:
            raise ValueError('data is required')
        if not isinstance(data, dict):
            raise ValueError('data must be a dictionary')
        if 'eTag' in data:
            oid = self.extract_uuid_from_etag(data['eTag'])
        else:
            ic('No eTag in data, generating a new UUID')
            oid = uuid.uuid4()
            # "eTag": "\"{4F181015-B1D6-4793-8104-806A631830FF},1\""
            data['eTag'] = '"{' + str(oid) + '},1"'
            ic(data['eTag'])
        # assert data['parentReference']['path'].strip() == '/drive/root:', \
        #    f'Only root is supported\n{data['parentReference']['path']}\n{json.dumps(data, indent=2)}'
        path = '/' + data['parentReference']['name'] + '/' + data['name']
        timestamps = []
        if 'fileSystemInfo' in data:
            if 'createdDateTime' in data['fileSystemInfo']:
                timestamps.append(
                    {
                        'Label': IndalekoObject.CREATION_TIMESTAMP,
                        'Value' : datetime.datetime\
                            .fromisoformat(data['fileSystemInfo']['createdDateTime'])\
                                .isoformat(),
                        'Description' : 'Creation Time',
                    }
                )
            if 'lastModifiedDateTime' in data['fileSystemInfo']:
                # No distinction between modified and changed.
                timestamps.append(
                    {
                        'Label': IndalekoObject.MODIFICATION_TIMESTAMP,
                        'Value' : datetime.datetime\
                            .fromisoformat(data['fileSystemInfo']['lastModifiedDateTime'])\
                                .isoformat(),
                        'Description' : 'Modification Time',
                    }
                )
                timestamps.append(
                    {
                        'Label': IndalekoObject.CHANGE_TIMESTAMP,
                    'Value' : datetime.datetime\
                        .fromisoformat(data['fileSystemInfo']['lastModifiedDateTime'])\
                            .isoformat(),
                    'Description' : 'Access Time',
                    }
                )
        else:
            if 'createdDateTime' in data:
                timestamps.append(
                    {
                        'Label': IndalekoObject.CREATION_TIMESTAMP,
                        'Value' : datetime.datetime.fromisoformat(data['createdTime']).isoformat(),
                        'Description' : 'Creation Time',
                    }
                )
            if 'lastModifiedDateTime' in data:
                # No distinction between modified and changed.
                timestamps.append(
                    {
                        'Label': IndalekoObject.MODIFICATION_TIMESTAMP,
                        'Value' : datetime.datetime.fromisoformat(data['modifiedTime']).isoformat(),
                        'Description' : 'Modification Time',
                    }
                )
                timestamps.append(
                    {
                        'Label': IndalekoObject.CHANGE_TIMESTAMP,
                        'Value' : datetime.datetime.fromisoformat(data['modifiedTime']).isoformat(),
                        'Description' : 'Access Time',
                    }
                )
        if 'folder' in data:
            unix_file_attributes = UnixFileAttributes.FILE_ATTRIBUTES['S_IFDIR']
            windows_file_attributes = IndalekoWindows.FILE_ATTRIBUTES['FILE_ATTRIBUTE_DIRECTORY']
        elif 'file' in data:
            unix_file_attributes = UnixFileAttributes.FILE_ATTRIBUTES['S_IFREG']
            windows_file_attributes = IndalekoWindows.FILE_ATTRIBUTES['FILE_ATTRIBUTE_NORMAL']
        else:
            raise ValueError('Unknown file type')
        kwargs = {
            'source' : self.source,
            'raw_data' : Indaleko.encode_binary_data(bytes(json.dumps(data), 'utf-8-sig')),
            'URI' : data.get('webUrl', None),
            'Path' : path,
            'ObjectIdentifier' : str(oid),
            'Timestamps' : timestamps,
            'Size' : int(data.get('size', 0)),
            'Attributes' : data,
            'Label' : data.get('name', None),
            'PosixFileAttributes' : UnixFileAttributes.map_file_attributes(unix_file_attributes),
            'WindowsFileAttributes' : IndalekoWindows.map_file_attributes(windows_file_attributes),
        }
        # ic(kwargs)
        return IndalekoObject(**kwargs)

    @staticmethod
    def generate_ingester_file_name(**kwargs):
        '''Generate the file name for the ingester'''
        assert 'user_id' in kwargs, 'user_id is required'
        return Indaleko.generate_file_name(**kwargs)

    def ingest(self) -> None:
        '''Ingest the data from the Google Drive Indexer'''
        self.load_indexer_data_from_file()
        # We need to pre-process the data before we can normalize the data.
        dir_data = []
        file_data = []
        id_to_oid_map = {}
        for item in self.indexer_data:
            obj = self.normalize_index_data(item)
            assert 'Path' in obj.args, f'Path is required\n\n{item}\n\n{obj.args}'
            if 'S_IFDIR' in obj.args['PosixFileAttributes'] or \
                'FILE_ATTRIBUTE_DIRECTORY' in obj.args['WindowsFileAttributes']:
                id_to_oid_map[item['id']] = obj.args['ObjectIdentifier']
                dir_data.append(obj)
                self.dir_count += 1
            else:
                assert 'S_IFREG' in obj.args['PosixFileAttributes'] or \
                    'FILE_ATTRIBUTE_NORMAL' in obj.args['WindowsFileAttributes'], \
                        'Unrecognized file type'
                file_data.append(obj)
                self.file_count += 1
        dir_edges = []
        source = {
            'Identifier' : self.onedrive_recorder,
            'Version' : '1.0.0',
        }
        for item in dir_data + file_data:
            # deal with parent ref
            parent_id = item.args['Record']['Attributes']['parentReference']['id']
            parent_oid = id_to_oid_map[parent_id]
            if parent_oid == item.args['ObjectIdentifier']:
                continue # this is normal for root.  Don't need that relationship.
            dir_edge = IndalekoRelationshipContains(
                relationship = \
                    IndalekoRelationshipContains.DIRECTORY_CONTAINS_RELATIONSHIP_UUID_STR,
                object1 = {
                    'collection' : Indaleko.Indaleko_Object_Collection,
                    'object' : item.args['ObjectIdentifier'],
                },
                object2 = {
                    'collection' : Indaleko.Indaleko_Object_Collection,
                    'object' : parent_oid,
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
                    'object' : parent_oid,
                },
                object2 = {
                    'collection' : Indaleko.Indaleko_Object_Collection,
                    'object' : item.args['ObjectIdentifier'],
                },
                source = source
            )
            dir_edges.append(dir_edge)
            self.edge_count += 1
        for data in self.indexer_data:
            if 'ObjectIdentifier' not in data:
                data['ObjectIdentifier'] = str(self.extract_uuid_from_etag(data['eTag']))
            assert isinstance(data['ObjectIdentifier'], str),\
                f'ObjectIdentifier is not a string: {data["ObjectIdentifier"]}'
            assert Indaleko.validate_uuid_string(data['ObjectIdentifier']),\
                f'ObjectIdentifier is not a valid UUID: {data["ObjectIdentifier"]}'
            id_to_oid_map[data['id']] = data['ObjectIdentifier']
        # Now let's update the data with the parent object identifiers
        dir_oids = []
        for data in self.indexer_data:
            if 'parentReference' in data:
                parent_id = data['parentReference']
                parent_oid = id_to_oid_map.get(parent_id['id'], None)
                if parent_oid is not None:
                    data['parents'] = [parent_oid]
                else:
                    ic('Parent not found for: ', data)
            if 'parents' in data:
                parent_ids = data['parents']
                parent_oids = [id_to_oid_map.get(pid, None) for pid in parent_ids if pid in id_to_oid_map]
                for parent_oid in parent_oids:
                    if parent_oid not in dir_oids:
                        dir_oids.append(parent_oid)
                data['parents'] = parent_oids
            obj = self.normalize_index_data(data)
            if 'S_IFDIR' in obj.args['PosixFileAttributes']:
                dir_data.append(obj)
                self.dir_count += 1
            else:
                file_data.append(obj)
                self.file_count += 1
        source = {
            'Identifier' : self.onedrive_recorder,
            'Version' : '1.0.0',
            'Description' : self.onedrive_recorder_service['service_description'],
        }
        kwargs = {
            'platform' : self.indexer_file_metadata['platform'],
            'prefix' : self.indexer_file_metadata['prefix'],
            'service' : 'ingester',
            'suffix' : 'jsonl',
            'timestamp' : self.indexer_file_metadata.get('timestamp', self.timestamp),
            'collection' : Indaleko.Indaleko_Object_Collection,
            'user_id' : self.indexer_file_metadata['user_id']
        }
        data_file = os.path.join(self.data_dir, Indaleko.generate_file_name(**kwargs))
        kwargs['collection'] = Indaleko.Indaleko_Relationship_Collection
        edge_file = os.path.join(self.data_dir, Indaleko.generate_file_name(**kwargs))
        ic(data_file, edge_file)
        self.write_data_to_file(dir_data + file_data, data_file)
        self.write_data_to_file(dir_edges, edge_file)
        print(f'size of dir_edges: {len(dir_edges)}')
        load_string = self.build_load_string(
            collection=Indaleko.Indaleko_Object_Collection,
            file=data_file
        )
        logging.info('Load string: %s', load_string)
        ic('Object Collection load string is:\n', load_string)
        load_string = self.build_load_string(
            collection=Indaleko.Indaleko_Relationship_Collection,
            file=edge_file
        )
        logging.info('Load string: %s', load_string)
        ic('Relationship Collection load string is:\n', load_string)




def list_files(args: argparse.Namespace) -> None:
    '''List the available indexer files'''
    if len(args.strings) == 0:
        strings = [IndalekoOneDriveIndexer.onedrive_platform, 'indexer', IndalekoOneDriveIndexer.default_file_suffix]
    else:
        strings = args.strings
    print(strings)
    matched_files = Indaleko.find_candidate_files(strings, args.datadir)
    Indaleko.print_candidate_files(matched_files)

def ingest_file(args: argparse.Namespace) -> None:
    '''Ingest the specified file'''
    print('ingest_file called: ', args)
    if not hasattr(args, 'input') or args.input is None:
        print('Pick the most likely file')
        candidates = Indaleko.find_candidate_files([IndalekoOneDriveIndexer.onedrive_platform,
                                                    'indexer',
                                                    IndalekoOneDriveIndexer.default_file_suffix],
                                                    args.datadir)
    else:
        candidates = Indaleko.find_candidate_files([args.input], args.datadir)
    if len(candidates) == 0:
        print(f'No files match the filter strings: {args.strings}')
        list_files(args.strings)
        return
    if len(candidates) > 1:
        print('Multiple files match the filter strings: ', args.strings)
        Indaleko.print_candidate_files(candidates)
        return
    ingester = IndalekoOneDriveCloudStorageRecorder(
        input_file=os.path.join(args.datadir,
                                candidates[0][0]),
        data_dir=args.datadir
    )
    ingester.ingest()
    for count_type, count_value in ingester.get_counts().items():
        logging.info('%s: %d', count_type, count_value)
        ic(count_type, count_value)
    ic('Done ingesting')

def main() -> None:
    '''Provides command line processing for the IndalekoOneDriveIngester module.'''
    logging_levels = IndalekoLogging.get_logging_levels()
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--configdir',
                            help=f'Path to the config directory (default is {Indaleko.default_config_dir})',
                            default=Indaleko.default_config_dir)
    pre_parser.add_argument('--logdir',
                            help=f'Path to the log directory (default is {Indaleko.default_log_dir})',
                            default=Indaleko.default_log_dir)
    pre_parser.add_argument('--loglevel',
                        choices=logging_levels,
                        default=logging.DEBUG,
                        help='Logging level to use.')
    pre_parser.add_argument('--datadir',
                            help=f'Path to the data directory (default is {Indaleko.default_data_dir})',
                            type=str,
                            default=Indaleko.default_data_dir)
    command_subparser = pre_parser.add_subparsers(dest='command')
    parser_list = command_subparser.add_parser('list', help='List the available indexer files', )
    parser_list.add_argument('strings', nargs='*', type=str, help='Strings to search for')
    parser_list.set_defaults(func=list_files)
    parser_ingest = command_subparser.add_parser('ingest', help='Ingest the specified file')
    parser_ingest.add_argument('--input', default=None, help='Indexer file to ingest', type=str)
    parser_ingest.set_defaults(func=ingest_file)
    pre_args, _ = pre_parser.parse_known_args()
    if pre_args.command == 'list':
        list_files(pre_args)
    parser = argparse.ArgumentParser(parents=[pre_parser], description='OneDrive Metadata Ingest Management')
    parser.set_defaults(func=ingest_file)
    args = parser.parse_args()
    print(args)
    args.func(args)

if __name__ == '__main__':
    main()
