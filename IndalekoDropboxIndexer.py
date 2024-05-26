'''
IndalekoDropboxIndexer.py

This script is used to index the files in the Dropbox folder of the user. It
will create a JSONL file with the metadata of the files in the Dropbox folder.
The JSOLN file will be used by the IndalekoDropboxIngester.py to load data into
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
import dropbox
from icecream import ic
import json
import logging
import os
import requests
import time
from urllib.parse import urlencode, parse_qs, urlparse
import uuid

from Indaleko import Indaleko
from IndalekoIndexer import IndalekoIndexer
import IndalekoLogging as IndalekoLogging

class IndalekoDropboxIndexer(IndalekoIndexer):

    dropbox_platform='Dropbox'
    dropbox_indexer_name='dropbox_indexer'

    indaleko_dropbox_indexer_uuid = '7c18f9c7-9153-427a-967a-55d942ac1f10'
    indaleko_dropbox_indexer_service_name = 'Dropbox Indexer'
    indaleko_dropbox_indexer_service_description = 'This service indexes the Dropbox folder of the user.'
    indaleko_dropbox_indexer_service_version = '1.0'
    indaleko_dropbox_indexer_service_type = 'Indexer'

    dropbox_config_file='dropbox_config.json'
    dropbox_token_file='dropbox_token.json'
    dropbox_redirect_url='http://localhost:8669'
    dropbox_auth_url = 'https://www.dropbox.com/oauth2/authorize'
    dropbox_token_url = 'https://api.dropboxapi.com/oauth2/token'

    indaleko_dropbox_local_indexer_service = {
        'service_name': indaleko_dropbox_indexer_service_name,
        'service_description': indaleko_dropbox_indexer_service_description,
        'service_version': indaleko_dropbox_indexer_service_version,
        'service_type': indaleko_dropbox_indexer_service_type,
        'service_identifier': indaleko_dropbox_indexer_uuid,
    }

    def __init__(self, **kwargs):
        self.config_dir = kwargs.get('config_dir', Indaleko.default_config_dir)
        self.dropbox_config_file = os.path.join(self.config_dir, IndalekoDropboxIndexer.dropbox_config_file)
        self.dropbox_token_file = os.path.join(self.config_dir, IndalekoDropboxIndexer.dropbox_token_file)
        self.dropbox_config = None
        self.load_dropbox_config()
        logging.debug('Dropbox config: %s', self.dropbox_config)
        self.dropbox_credentials = None
        self.load_dropbox_credentials()
        if self.dropbox_credentials is None:
            logging.debug('No Dropbox credentials found, reconstructing.')
            self.query_user_for_credentials()
        if self.dropbox_credentials is not None:
            self.refresh_access_token()
        self.dbx = dropbox.Dropbox(self.dropbox_credentials['token'])
        self.user_info = self.dbx.users_get_current_account()
        ic(self.user_info)
        super().__init__(**kwargs,
                         platform=IndalekoDropboxIndexer.dropbox_platform,
                         indexer_name=IndalekoDropboxIndexer.dropbox_indexer_name,
                         **IndalekoDropboxIndexer.indaleko_dropbox_local_indexer_service
        )
        pass

    def get_user_id(self):
        '''This method returns the user id.'''
        assert hasattr(self.user_info, 'email'), f'{dir(self.user_info)}'
        return self.user_info.email

    def load_dropbox_credentials(self) -> 'IndalekoDropboxIndexer':
        '''This method retrieves the stored credentials.'''
        try:
            with open(self.dropbox_token_file, 'rt') as f:
                self.dropbox_credentials = json.load(f)
            logging.debug('Loaded Dropbox credentials from %s', self.dropbox_token_file)
        except FileNotFoundError:
            self.dropbox_credentials = None
            logging.warning('No Dropbox credentials found in %s', self.dropbox_token_file)
        return self

    def store_dropbox_credentials(self) -> 'IndalekoDropboxIndexer':
        '''This method stores the credentials.'''
        assert self.dropbox_credentials is not None, 'No credentials to store'
        with open(self.dropbox_token_file, 'wt') as f:
            json.dump(self.dropbox_credentials, f, indent=4)
        return self

    def set_dropbox_credentials(self, credentials : dict) -> 'IndalekoDropboxIndexer':
        '''This method sets the credentials.'''
        self.dropbox_credentials = credentials
        return self

    def query_user_for_credentials(self) -> 'IndalekoDropboxIndexer':
        '''This method queries the user for credentials.'''
        params = {
            'response_type': 'code',
            'client_id': self.dropbox_config['app_key'],
            'token_access_type': 'offline'
        }
        auth_request_url = f'{IndalekoDropboxIndexer.dropbox_auth_url}?{urlencode(params)}'

        print('Please visit the following URL to authorize this application:', auth_request_url)
        auth_code = input('Enter the authorization code here: ').strip()
        data = {
            'code': auth_code,
            'grant_type': 'authorization_code',
            'client_id': self.dropbox_config['app_key'],
            'client_secret': self.dropbox_config['app_secret'],
        }
        response = requests.post(IndalekoDropboxIndexer.dropbox_token_url, data=data)
        response.raise_for_status()
        response_data = response.json()
        if 'access_token' not in response_data or 'refresh_token' not in response_data or 'expires_in' not in response_data or 'refresh_token' not in response_data:
            raise ValueError(f'Invalid response from Dropbox {response_data}')
        self.dropbox_credentials = {
            'token': response_data['access_token'],
            'refresh_token': response_data['refresh_token'],
            'expires_at': time.time() + response_data['expires_in']
        }
        return self


    def get_dropbox_credentials(self, refresh : bool = False):
        '''
        This method retrieves the Dropbox credentials.
        '''
        if self.dropbox_credentials is None:
            self.load_dropbox_credentials()
        if self.dropbox_credentials is None:
            self.query_user_for_credentials()
            self.store_dropbox_credentials()
        if self.dropbox_credentials is not None and not refresh:
            return self.dropbox_credentials

        assert os.path.exists(self.dropbox_token_file), f'File {self.dropbox_token_file} does not exist, aborting'
        data = json.load(open(self.dropbox_token_file, 'rt'))
        return data['token']

    def is_token_expired(self) -> bool:
        '''
        This method checks if the token is expired.
        '''
        if self.dropbox_credentials is None:
            return True
        if 'expires_at' not in self.dropbox_credentials:
            return True
        return time.time() > self.dropbox_credentials['expires_at']

    def refresh_access_token(self) -> 'IndalekoDropboxIndexer':
        '''
        This method refreshes the access token.
        '''
        logging.debug('Refresh token called with credentials:' , self.dropbox_credentials)
        if self.dropbox_credentials is None:
            raise ValueError('No credentials to refresh')
        if 'refresh_token' not in self.dropbox_credentials:
            raise ValueError('No refresh token to refresh')
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.dropbox_credentials['refresh_token'],
            'client_id': self.dropbox_config['app_key'],
            'client_secret': self.dropbox_config['app_secret']
        }
        response = requests.post(IndalekoDropboxIndexer.dropbox_token_url, data=data)
        response.raise_for_status()
        logging.debug('Response:', response.json())
        response_data = response.json()
        self.dropbox_credentials = {
            'token': response_data['access_token'],
            'refresh_token': self.dropbox_credentials['refresh_token'],
            'expires_at': time.time() + response_data['expires_in']
        }
        logging.debug('Updated credentials:', self.dropbox_credentials)
        self.store_dropbox_credentials()
        return self

    def load_dropbox_config(self) -> 'IndalekoDropboxIndexer':
        '''
        This method extracts the dropbox application configuration.  Config file
        must exist.
        '''
        if self.dropbox_config is not None:
            return self.dropbox_config
        if not os.path.exists(self.dropbox_config_file):
            logging.critical('Config file %s does not exist, aborting', self.dropbox_config_file)
            raise FileNotFoundError(f'Config file {self.dropbox_config_file} does not exist, aborting')
        self.dropbox_config = json.load(open(self.dropbox_config_file, 'rt', encoding='utf-8'))
        assert 'app_key' in self.dropbox_config, 'app_key not found in config file'
        assert 'app_secret' in self.dropbox_config, 'app_secret not found in config file'
        logging.debug('Loaded Dropbox config file: %s', self.dropbox_config_file)
        return self

    def store_dropbox_config(self, app_id : str, app_secret : str) -> 'IndalekoDropboxIndexer':
        '''
        This method stores the Dropbox configuration.
        '''
        self.config = {
            'app_key': app_id,
            'app_secret': app_secret
        }
        with open(self.dropbox_config_file, 'wt', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4)
        return self

    @staticmethod
    def generate_indexer_file_name(**kwargs):
        '''
        This method generates the name of the file that will contain the metadata
        of the files in the Dropbox folder.
        '''
        assert 'user_id' in kwargs, 'No user_id found in kwargs'
        return Indaleko.generate_file_name(**kwargs)

    @staticmethod
    def convert_to_serializable(data):
        if isinstance(data, (int, float, str, bool, type(None))):
            return data
        elif isinstance(data, list):
            return [IndalekoDropboxIndexer.convert_to_serializable(item) for item in data]
        elif isinstance(data, dict):
            return {key: IndalekoDropboxIndexer.convert_to_serializable(value) for key, value in data.items()}
        else:
            if hasattr(data, '__dict__'):
                return IndalekoDropboxIndexer.convert_to_serializable(data.__dict__)
            return None


    def build_stat_dict(self,  obj : dropbox.files) -> dict:
        '''
        This method builds a dictionary with the metadata of a file stored in
        dropbox.
        '''
        metadata_fields_of_interest = (
            'DeletedMetadata',
            'ExportMetadata',
            'FileLockMetadata',
            'FileMetadata',
            'FolderMetadata',
            'MediaMetadata',
            'Metadata',
            'MetadataV2',
            'MinimalFileLinkMetadata',
            'PhotoMetadata',
            'VideoMetadata',
        )
        metadata = {
            'Indexer' : IndalekoDropboxIndexer.indaleko_dropbox_indexer_uuid,
            'ObjectIdentifier' : str(uuid.uuid4())
        }
        fields = []
        for foi in metadata_fields_of_interest:
            if isinstance(obj, getattr(dropbox.files, foi)):
                metadata[foi] = True
                data = getattr(dropbox.files, foi)
                for field in data._field_names_:
                    if field not in fields:
                        fields.append(field)
        for field in fields:
            if not hasattr(obj, field):
                logging.warning('Field %s not found in %s (but listed)', field, obj)
                continue
            attr = getattr(obj, field)
            if isinstance(attr, datetime.datetime):
                metadata[field] = attr.isoformat()
                continue
            value = IndalekoDropboxIndexer.convert_to_serializable(attr)
            if value is None:
                continue
            metadata[field] = value
        return metadata

    def index(self):
        '''This is the indexer for Dropbox'''
        ic('Indexing Dropbox')
        try:
            metadata_list = []
            cursor = None
            while True:
                result = self.dbx.files_list_folder('', recursive=False)
                while True:
                    try:
                        result = self.dbx.files_list_folder_continue(
                            cursor) if cursor else self.dbx.files_list_folder('', recursive=False)
                    except dropbox.exceptions.ApiError as e:
                        if 'expired_access_token' in str(e):
                            ic('Refreshing access token')
                            self.refresh_access_token()
                            self.dbx = dropbox.Dropbox(self.dropbox_credentials['token'])
                            continue
                    for entry in result.entries:
                        metadata = self.build_stat_dict(entry)
                        ic(metadata)
                        metadata_list.append(metadata)
                    if not result.has_more:
                        break
                    cursor = result.cursor
                if not result.has_more:
                    break
        except dropbox.exceptions.ApiError as e:
            logging.error(f"Error enumerating folder, exception {e}")
            print(f"Error enumerating folder, exception {e}")
        return metadata_list


def main():
    logging_levels = Indaleko.get_logging_levels()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    pre_parser = argparse.ArgumentParser(add_help=False)
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
    pre_args, _ = pre_parser.parse_known_args()
    indaleko_logging = IndalekoLogging.IndalekoLogging(platform=IndalekoDropboxIndexer.dropbox_platform,
                                                       service_name='indexer',
                                                       log_dir=pre_args.logdir,
                                                       log_level=pre_args.loglevel,
                                                       timestamp=timestamp,
                                                       suffix='log')
    log_file_name = indaleko_logging.get_log_file_name()
    ic(log_file_name)
    indexer = IndalekoDropboxIndexer(timestamp=timestamp)

    output_file_name = IndalekoDropboxIndexer.generate_indexer_file_name(
            platform=IndalekoDropboxIndexer.dropbox_platform,
            user_id=indexer.get_user_id(),
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
                        default=Indaleko.default_data_dir)
    parser.add_argument('--path',
                        help='Path to the directory to index',
                        type=str,
                        default='')
    args = parser.parse_args()
    output_file = os.path.join(args.datadir, args.output)
    logging.info('Indaleko Dropbox Indexer started.')
    logging.info('Output file: %s', output_file)
    logging.info('Indexing: %s', args.path)
    logging.info(args)
    data = indexer.index()
    indexer.write_data_to_file(data, output_file)
    for count_type, count_value in indexer.get_counts().items():
        logging.info('Count %s: %s', count_type, count_value)
    logging.info('Indaleko Dropbox Indexer finished.')

if __name__ == '__main__':
    main()
