'''
This module handles data ingestion into Indaleko from the Linux local data
indexer.

Indaleko Linux Local Ingester
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
import json
import logging
import os
import uuid

from icecream import ic

from IndalekoLogging import IndalekoLogging
from Indaleko import Indaleko
from IndalekoGDriveIndexer import IndalekoGDriveIndexer
from IndalekoIngester import IndalekoIngester
from IndalekoObject import IndalekoObject
from IndalekoRelationshipContains import IndalekoRelationshipContains
from IndalekoRelationshipContained import IndalekoRelationshipContainedBy
from IndalekoUnix import UnixFileAttributes

class IndalekoGDriveIngester(IndalekoIngester):
    '''
    This class provides the Google Drive Ingester for Indaleko.
    '''

    gdrive_ingester_uuid_str = '4d74bd0b-e502-4df8-9f9e-13ce711d60aa'
    gdrive_ingester_uuid = uuid.UUID(gdrive_ingester_uuid_str)
    gdrive_ingester_service = {
        'service_name' : 'Google Drive Ingester',
        'service_description' : 'This service ingests metadata from Google Drive into Indaleko.',
        'service_version' : '1.0.0',
        'service_type' : 'ingester',
        'service_identifier' : gdrive_ingester_uuid_str,
    }
    gdrive_ingester = 'GDrive_ingester'

    def __init__(self, **kwargs : dict) -> None:
        '''Initialize the Google Drive Ingester'''
        if 'input_file' not in kwargs:
            raise ValueError('input_file is required for the Google Drive Ingester')
        for key, value in self.gdrive_ingester_service.items():
            if key not in kwargs:
                kwargs[key] = value
        super().__init__(**kwargs)
        self.data_dir = kwargs.get('data_dir', Indaleko.default_data_dir)
        self.input_file = kwargs['input_file']
        self.indexer_file_metadata = Indaleko.extract_keys_from_file_name(self.input_file)
        self.ingester = IndalekoGDriveIngester.gdrive_ingester
        self.indexer_data = []
        self.source = {
            'Identifier' : self.gdrive_ingester_uuid_str,
            'Version' : '1.0.0',
        }
        self.ingester_service = IndalekoGDriveIngester.gdrive_ingester_service


    def normalize_index_data(self, data: dict) -> dict:
        '''Normalize the index data'''
        if data is None:
            raise ValueError('data is required')
        if not isinstance(data, dict):
            raise ValueError('data must be a dictionary')
        oid = data.get('ObjectIdentifier', uuid.uuid4())
        # This is where I have to figure out what I have and convert it to what
        # I need.
        sample_data = {
            "kind": "drive#file",
            "viewedByMe": True,
            "mimeType": "application/vnd.google-apps.spreadsheet",
            "shared": True,
            "webViewLink": "https://docs.google.com/spreadsheets/d/1_KE3Bu3C3gOyEm0mRVcJH9nEA2u2GOhfpUZOckOWmN0/edit?usp=drivesdk",
            "size": "662784",
            "spaces": ["drive"],
            "id": "1_KE3Bu3C3gOyEm0mRVcJH9nEA2u2GOhfpUZOckOWmN0",
            "name": "Arrezo",
            "starred": False,
            "trashed": False,
            "explicitlyTrashed": False,
            "createdTime": "2021-12-26T19:24:55.396Z",
            "modifiedTime": "2024-08-10T17:15:36.049Z",
            "viewedByMeTime": "2023-03-01T20:20:44.845Z",
            "sharedWithMeTime": "2023-03-01T20:20:44.845Z",
            "quotaBytesUsed": "662784",
            "version": "337248",
            "ownedByMe": False,
            "capabilities": {
                "canChangeViewersCanCopyContent": False,
                "canEdit": True,
                "canCopy": True,
                "canComment": True,
                "canAddChildren": False,
                "canDelete": False,
                "canDownload": True,
                "canListChildren": False,
                "canRemoveChildren": False,
                "canRename": True,
                "canTrash": False,
                "canReadRevisions": True,
                "canChangeCopyRequiresWriterPermission": False,
                "canMoveItemIntoTeamDrive": False,
                "canUntrash": False,
                "canModifyContent": True,
                "canMoveItemOutOfDrive": False,
                "canAddMyDriveParent": False,
                "canRemoveMyDriveParent": True,
                "canMoveItemWithinDrive": True,
                "canShare": True,
                "canMoveChildrenWithinDrive": False,
                "canModifyContentRestriction": True,
                "canChangeSecurityUpdateEnabled": False,
                "canAcceptOwnership": False,
                "canReadLabels": False,
                "canModifyLabels": False,
                "canModifyEditorContentRestriction": True,
                "canModifyOwnerContentRestriction": False,
                "canRemoveContentRestriction": False},
                "thumbnailVersion": "13733",
                "modifiedByMe": False,
                "linkShareMetadata": {
                    "securityUpdateEligible": False,
                    "securityUpdateEnabled": True
                }
            }
        timestamps = []
        if 'createdTime' in data:
            timestamps.append(
                {
                    'Label': IndalekoObject.CREATION_TIMESTAMP,
                    'Value' : datetime.datetime.fromisoformat(data['createdTime']).isoformat(),
                    'Description' : 'Creation Time',
                }
            )
        if 'modifiedTime' in data:
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
        if 'viewedByMeTime' in data:
            timestamps.append(
                {
                    'Label': IndalekoObject.ACCESS_TIMESTAMP,
                    'Value' : datetime.datetime.fromisoformat(data['viewedByMeTime']).isoformat(),
                    'Description' : 'Viewed Time',
                }
            )
        kwargs = {
            'source' : self.source,
            'raw_data' : Indaleko.encode_binary_data(bytes(json.dumps(data), 'utf-8')),
            'URI' : data.get('webViewLink', None),
            'ObjectIdentifier' : str(oid),
            'Timestamps' : timestamps,
            'Size' : int(data.get('size', 0)),
            'Attributes' : data
        }
        kwargs['UnixFileAttributes'] = \
            UnixFileAttributes.map_file_attributes(
                self.map_gdrive_attributes_to_unix_attributes(data)
            )
        if 'timestamp' not in kwargs:
            if isinstance(self.timestamp, str):
                kwargs['timestamp'] = datetime.datetime.fromisoformat(self.timestamp)
            else:
                assert isinstance(self.timestamp, datetime.datetime)
                kwargs['timestamp'] = self.timestamp
        return IndalekoObject(**kwargs)


    @staticmethod
    def map_gdrive_attributes_to_unix_attributes(data: dict) -> dict:
        '''Map Google Drive attributes to Unix attributes'''
        if data is None:
            raise ValueError('data is required')
        if not isinstance(data, dict):
            raise ValueError('data must be a dictionary')
        attributes = 0
        if 'mimeType' in data:
            if data['mimeType'] == 'application/vnd.google-apps.folder':
                attributes |= UnixFileAttributes.FILE_ATTRIBUTES['S_IFDIR']
            else:
                attributes |= UnixFileAttributes.FILE_ATTRIBUTES['S_IFREG']
        return attributes

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
        for data in self.indexer_data:
            if 'ObjectId' not in data:
                data['ObjectId'] = str(uuid.uuid4()) # add an object identifier
            id_to_oid_map[data['id']] = data['ObjectId']
        # Now let's update the data with the parent object identifiers
        dir_oids = []
        for data in self.indexer_data:
            if 'parents' in data:
                parent_ids = data['parents']
                parent_oids = [id_to_oid_map.get(pid, None) for pid in parent_ids if pid in id_to_oid_map]
                for parent_oid in parent_oids:
                    if parent_oid not in dir_oids:
                        dir_oids.append(parent_oid)
                data['parents'] = parent_oids
            obj = self.normalize_index_data(data)
            if 'S_IFDIR' in obj.args['UnixFileAttributes']:
                dir_data.append(obj)
                self.dir_count += 1
            else:
                file_data.append(obj)
                self.file_count += 1
        source = {
            'Identifier' : self.gdrive_ingester,
            'Version' : '1.0.0',
            'Description' : 'Google Drive Ingester',
        }
        dir_edges = []
        for item in dir_data + file_data:
            if hasattr(item, 'parents'):
                for parent in item.parents:
                    dir_edges.append(
                        IndalekoRelationshipContains(
                            relationship = IndalekoRelationshipContains.DIRECTORY_CONTAINS_RELATIONSHIP_UUID_STR,
                            object1 = {
                                'collection' : 'Objects',
                                'object' : parent,
                            },
                            object2 = {
                                'collection' : 'Objects',
                                'object' : item.ObjectIdentifier
                            },
                            source = source
                        )
                    )
                    self.edge_count += 1
                    dir_edges.append(
                        IndalekoRelationshipContainedBy(
                            relationship = IndalekoRelationshipContainedBy.CONTAINED_RELATIONSHIP_UUID_STR,
                            object1 = {
                                'collection' : 'Objects',
                                'object' : item.ObjectIdentifier
                            },
                            object2 = {
                                'collection' : 'Objects',
                                'object' : parent
                            },
                            source = source
                        )
                    )
                    self.edge_count += 1
        ic(self.indexer_file_metadata)
        kwargs = {
            'platform' : self.indexer_file_metadata['platform'],
            'prefix' : self.indexer_file_metadata['prefix'],
            'service' : 'ingester',
            'suffix' : 'jsonl',
            'timestamp' : self.timestamp,
            'collection' : 'Objects',
            'user_id' : self.indexer_file_metadata['user_id']
        }
        data_file = os.path.join(self.data_dir, Indaleko.generate_file_name(**kwargs))
        kwargs['collection'] = 'Relationships'
        edge_file = os.path.join(self.data_dir, Indaleko.generate_file_name(**kwargs))
        ic(data_file, edge_file)
        self.write_data_to_file(dir_data + file_data, data_file)
        self.write_data_to_file(dir_edges, edge_file)




def list_files(args: argparse.Namespace) -> None:
    '''List the available indexer files'''
    if len(args.strings) == 0:
        strings = [IndalekoGDriveIndexer.gdrive_platform, 'indexer', IndalekoGDriveIndexer.default_file_suffix]
    else:
        strings = args.strings
    print(strings)
    matched_files = Indaleko.find_candidate_files(strings, args.datadir)
    Indaleko.print_candidate_files(matched_files)

def ingest_file(args: argparse.Namespace) -> None:
    '''Ingest the specified file'''
    print('ingest_file called: ', args)
    if args.input is None:
        print('Pick the most likely file')
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
    ingester = IndalekoGDriveIngester(input_file=os.path.join(args.datadir, candidates[0][0]), data_dir=args.datadir)
    ingester.ingest()
    for count_type, count_value in ingester.get_counts().items():
        logging.info('%s: %d', count_type, count_value)
        ic(count_type, count_value)
    ic('Done ingesting')


def main() -> None:
    '''This provides command processing for the Google Drive Ingester'''
    now = datetime.datetime.now(datetime.UTC)
    timestamp=now.isoformat()
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
    parser_ingest.add_argument('--input', help='Indexer file to ingest', type=str)
    parser_ingest.set_defaults(func=ingest_file)
    pre_args, _ = pre_parser.parse_known_args()
    if pre_args.command == 'list':
        list_files(pre_args)
    parser = argparse.ArgumentParser(parents=[pre_parser], description='Google Drive Metadataa Ingest Management')
    parser.set_defaults(func=ingest_file)
    args = parser.parse_args()
    print(args)
    args.func(args)

if __name__ == '__main__':
    main()
