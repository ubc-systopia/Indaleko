'''
IndalekoGDriveIndexer.py

This script is used to index the files in the Google Drive folder of Indaleko.
It will create a JSONL file with the metadata of the files in the Dropbox
folder.
The JSONL file will be used by the IndalekoGDriveIngester.py to load data into
the database.

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
from googleapiclient.discovery import build, HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from icecream import ic
import json
import logging
import os
import sys
from urllib.parse import urlencode, parse_qs, urlparse

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from utils.i_logging import IndalekoLogging
from utils.misc.file_name_management import generate_file_name
from utils.misc.directory_management import indaleko_default_data_dir, indaleko_default_config_dir, indaleko_default_log_dir
from storage.collectors.base import BaseStorageCollector
from platforms.windows.machine_config import IndalekoWindowsMachineConfig
# pylint: enable=wrong-import-position


class IndalekoGDriveIndexer(BaseStorageCollector):
    gdrive_platform = "GoogleDrive"
    gdrive_indexer_name = "gdrive_indexer"

    indaleko_gdrive_indexer_uuid = '74c82969-6bbb-4450-97f5-44d65c65e133'
    indaleko_gdrive_indexer_service_name = 'Google Drive Indexer'
    indaleko_gdrive_indexer_service_description = 'Indexes the Google Drive folder for Indaleko.'
    indaleko_gdrive_indexer_service_version = '1.0'
    indaleko_gdrive_indexer_service_type = 'Indexer'

    SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
              'https://www.googleapis.com/auth/userinfo.profile',
              'openid',
              'https://www.googleapis.com/auth/userinfo.email']

    FILE_METADATA_FIELDS = [
        'kind',
        'driveId',
        'fileExtension',
        'md5Checksum',
        'viewedByMe',
        'mimeType',
        'exportLinks',
        'parents',
        'thumbnailLink',
        'shared',
        'headRevisionId',
        'webViewLink',
        'webContentLink',
        'size',
        'spaces',
        'id',
        'name',
        'description',
        'starred',
        'trashed',
        'explicitlyTrashed',
        'createdTime',
        'modifiedTime',
        'modifiedByMeTime',
        'viewedByMeTime',
        'sharedWithMeTime',
        'quotaBytesUsed',
        'version',
        'originalFilename',
        'ownedByMe',
        'fullFileExtension',
        'properties',
        'appProperties',
        'capabilities',
        'hasAugmentedPermissions',
        'trashingUser',
        'thumbnailVersion',
        'modifiedByMe',
        'imageMediaMetadata',
        'videoMediaMetadata',
        'shortcutDetails',
        'contentRestrictions',
        'resourceKey',
        'linkShareMetadata',
        'labelInfo',
        'sha1Checksum',
        'sha256Checksum'
    ]

    gdrive_config_file = 'gdrive_config.json'
    gdrive_token_file = 'gdrive_token.json'


    indaleko_gdrive_indexer_service = {
        'uuid': indaleko_gdrive_indexer_uuid,
        'name': indaleko_gdrive_indexer_service_name,
        'description': indaleko_gdrive_indexer_service_description,
        'version': indaleko_gdrive_indexer_service_version,
        'type': indaleko_gdrive_indexer_service_type
    }

    def __init__(self, **kwargs):
        self.email = None
        self.config_dir = kwargs.get('config_dir', indaleko_default_config_dir)
        self.gdrive_config_file = os.path.join(self.config_dir, IndalekoGDriveIndexer.gdrive_config_file)
        assert os.path.exists(self.gdrive_config_file), \
            f'No GDrive config file found at {self.gdrive_config_file}'
        self.gdrive_token_file = \
            os.path.join(self.config_dir, IndalekoGDriveIndexer.gdrive_token_file)
        self.gdrive_config = None
        self.load_gdrive_config()
        self.gdrive_credentials = None
        self.load_gdrive_credentials()
        super().__init__(**kwargs,
                         indexer_name=IndalekoGDriveIndexer.gdrive_indexer_name,
                         **IndalekoGDriveIndexer.indaleko_gdrive_indexer_service)

    def load_gdrive_config(self) -> 'IndalekoGDriveIndexer':
        '''This method loads the GDrive configuration'''
        with open(self.gdrive_config_file, 'rt') as f:
            self.gdrive_config = json.load(f)
        return self

    def load_gdrive_credentials(self) -> 'IndalekoGDriveIndexer':
        '''This method gets the GDrive credentials'''
        if os.path.exists(self.gdrive_token_file):
            logging.debug('Loading GDrive credentials from %s', self.gdrive_token_file)
            self.gdrive_credentials = Credentials.from_authorized_user_file(self.gdrive_token_file, IndalekoGDriveIndexer.SCOPES)
        if not self.gdrive_credentials or not self.gdrive_credentials.valid:
            if self.gdrive_credentials and self.gdrive_credentials.expired and self.gdrive_credentials.refresh_token:
                self.gdrive_credentials.refresh(Request())
            else:
                self.query_user_for_credentials()
            self.store_gdrive_credentials()
        return self

    def store_gdrive_credentials(self) -> 'IndalekoGDriveIndexer':
        '''This method stores the credentials'''
        assert self.gdrive_credentials is not None, 'No credentials to store'
        with open(self.gdrive_token_file, 'wt') as f:
            f.write(self.gdrive_credentials.to_json())
        return self

    def query_user_for_credentials(self) -> 'IndalekoGDriveIndexer':
        '''This method queries the user for credentials'''
        flow = InstalledAppFlow.from_client_config(self.gdrive_config, IndalekoGDriveIndexer.SCOPES)
        self.gdrive_credentials = flow.run_local_server(port=0)
        return self

    def get_email(self) -> str:
        '''This method returns the email address associated with the
        credentials'''
        if self.email is None:
            service = build('people', 'v1', credentials=self.gdrive_credentials)
            results = service.people().get(resourceName='people/me', personFields='emailAddresses').execute()
            email = 'dummy@dummy.com'
            if 'emailAddresses' not in results:
                logging.warning('No email addresses found in %s', results)
            else:
                if len(results['emailAddresses']) > 1:
                    logging.info('More than one email address found in %s', results)
                email = results['emailAddresses'][0]['value']
            self.email = email
        return self.email

    @staticmethod
    def generate_windows_indexer_file_name(**kwargs):
        '''
        This method generates the name of the file that will contain the metadata
        of the files in the Dropbox folder.
        '''
        assert 'user_id' in kwargs, 'No user_id found in kwargs'
        return generate_file_name(**kwargs)

    def build_stat_dict(self, entry: dict) -> dict:
        '''This builds the stat dict for the entry'''
        return entry


    def index(self, recursive=True) -> list:
        '''
        This method indexes Google Drive.
        '''
        if self.gdrive_credentials is None:
            self.load_gdrive_credentials()
        page_token = None
        field_to_use = 'nextPageToken, files({})'.format(
            ', '.join(IndalekoGDriveIndexer.FILE_METADATA_FIELDS))
        metadata_list = []
        service = None

        while True:
            if service is None:
                service = build('drive', 'v3', credentials=self.gdrive_credentials)
            try:
                results = service.files().list(fields=field_to_use, pageToken=page_token).execute()
            except HttpError as error:
                # this should handle a token expiration by refreshing it
                if error.resp.status == 401:
                    self.load_gdrive_credentials()
                    continue
                else:
                    raise error
            for entry in results.get('files', []):
                metadata = self.build_stat_dict(entry)
                metadata_list.append(metadata)
            page_token = results.get('nextPageToken', None)
            if not page_token:
                break
        self.metadata = metadata_list
        return self.metadata

    @staticmethod
    def find_collector_files(
            search_dir : str,
            prefix : str = BaseStorageCollector.default_file_prefix,
            suffix : str = BaseStorageCollector.default_file_suffix) -> list:
        '''This function finds the files to ingest:
            search_dir: path to the search directory
            prefix: prefix of the file to ingest
            suffix: suffix of the file to ingest (default is .json)
        '''
        prospects = BaseStorageCollector.find_collector_files(search_dir, prefix, suffix)
        return [f for f in prospects if IndalekoGDriveIndexer.gdrive_platform in f]


def main():
    logging_levels = IndalekoLogging.get_logging_levels()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--configdir',
                            help='Path to the config directory',
                            default=indaleko_default_config_dir)
    pre_parser.add_argument('--logdir', '-l',
                            help='Path to the log directory',
                            default=indaleko_default_log_dir)
    pre_parser.add_argument('--loglevel',
                            type=int,
                            default=logging.DEBUG,
                            choices=logging_levels,
                            help='Logging level to use (lower number = more logging)')
    pre_args, _ = pre_parser.parse_known_args()
    indaleko_logging = IndalekoLogging(platform=IndalekoGDriveIndexer.gdrive_platform,
                                        service_name='indexer',
                                        log_dir=pre_args.logdir,
                                        log_level=pre_args.loglevel,
                                        timestamp=timestamp,
                                        suffix='log')
    log_file_name = indaleko_logging.get_log_file_name()
    ic(log_file_name)
    indexer = IndalekoGDriveIndexer(timestamp=timestamp)
    output_file_name = IndalekoGDriveIndexer.generate_windows_indexer_file_name(
            platform=IndalekoGDriveIndexer.gdrive_platform,
            user_id=indexer.get_email(),
            service='indexer',
            timestamp=timestamp,
            suffix='jsonl'
        )
    parser = argparse.ArgumentParser(parents=[pre_parser])
    parser.add_argument('--output', type=str, default=output_file_name,
                        help='Name and location of where to save the fetched metadata')
    parser.add_argument('--datadir',
                        '-d',
                        help='Path to the data directory',
                        default=indaleko_default_data_dir)
    parser.add_argument('--path',
                        help='Path to the directory to index',
                        type=str,
                        default='')
    parser.add_argument('--norecurse',
                        help='Disable recursive directory indexing (for testing).',
                        default=False,
                        action='store_true')
    args = parser.parse_args()
    ic(args)
    output_file = os.path.join(args.datadir, args.output)
    logging.info('Indaleko GDrive Indexer started.')
    logging.info('Output file: %s', output_file)
    logging.info('Indexing: %s', args.path)
    logging.info(args)
    data = indexer.index(recursive= (not args.norecurse))
    indexer.write_data_to_file(data, output_file)
    for count_type, count_value in indexer.get_counts().items():
        logging.info('Count %s: %s', count_type, count_value)
    logging.info('Indaleko GDrive Indexer finished.')

if __name__ == '__main__':
    main()
