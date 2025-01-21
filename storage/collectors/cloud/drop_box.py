'''
drop_box.py

This script is used to scan the files in the Dropbox folder of the user. It
will create a JSONL file with the metadata of the files in the Dropbox folder.
The JSONL file will be used by the dropbox recorder to load data into
the database.

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
import dropbox
import json
import logging
import os
from pathlib import Path
import requests
import sys
import time
from urllib.parse import urlencode, parse_qs, urlparse
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
from data_models import IndalekoSourceIdentifierDataModel
from db import IndalekoServiceManager
from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
from utils.cli.runner import IndalekoCLIRunner
from utils.i_logging import IndalekoLogging
from utils.misc.file_name_management import generate_file_name
from utils.misc.directory_management import indaleko_default_data_dir, indaleko_default_config_dir, indaleko_default_log_dir
from storage.collectors.base import BaseStorageCollector
from storage.collectors.cloud.cloud_base import BaseCloudStorageCollector
from storage.collectors.data_model import IndalekoStorageCollectorDataModel
from perf.perf_collector import IndalekoPerformanceDataCollector
from perf.perf_recorder import IndalekoPerformanceDataRecorder
# pylint: enable=wrong-import-position


class IndalekoDropboxCloudStorageCollector(BaseCloudStorageCollector):

    dropbox_platform='Dropbox'
    dropbox_collector_name='collector'

    indaleko_dropbox_collector_uuid = '7c18f9c7-9153-427a-967a-55d942ac1f10'
    indaleko_dropbox_collector_service_name = 'Dropbox Collector'
    indaleko_dropbox_collector_service_description = 'This service indexes the Dropbox of the user.'
    indaleko_dropbox_collector_service_version = '1.0'
    indaleko_dropbox_collector_service_type = IndalekoServiceManager.service_type_storage_collector

    dropbox_config_file='dropbox_config.json'
    dropbox_token_file='dropbox_token.json'
    dropbox_redirect_url='http://localhost:8669'
    dropbox_auth_url = 'https://www.dropbox.com/oauth2/authorize'
    dropbox_token_url = 'https://api.dropboxapi.com/oauth2/token'

    indaleko_dropbox_collector_service = {
        'service_name': indaleko_dropbox_collector_service_name,
        'service_description': indaleko_dropbox_collector_service_description,
        'service_version': indaleko_dropbox_collector_service_version,
        'service_type': indaleko_dropbox_collector_service_type,
        'service_identifier': indaleko_dropbox_collector_uuid,
    }

    collector_data = IndalekoStorageCollectorDataModel(
        CollectorPlatformName=dropbox_platform,
        CollectorServiceName=dropbox_collector_name,
        CollectorServiceUUID=uuid.UUID(indaleko_dropbox_collector_uuid),
        CollectorServiceVersion=indaleko_dropbox_collector_service_version,
        CollectorServiceDescription=indaleko_dropbox_collector_service_description,
    )

    def __init__(self, **kwargs):
        '''This is the constructor for the Dropbox collector.'''
        for key, value in self.indaleko_dropbox_collector_service.items():
            if key not in kwargs:
                kwargs[key] = value
        if 'platform' not in kwargs:
            kwargs['platform'] = self.dropbox_platform
        if 'collector_data' not in kwargs:
            kwargs['collector_data'] = self.collector_data
        self.config_dir = kwargs.get('config_dir', indaleko_default_config_dir)
        self.dropbox_config_file = str(Path(self.config_dir) / IndalekoDropboxCloudStorageCollector.dropbox_config_file)
        self.dropbox_token_file = str(Path(self.config_dir) / IndalekoDropboxCloudStorageCollector.dropbox_token_file)
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
        super().__init__(**kwargs)

    def old__init__(self, **kwargs):
        self.config_dir = kwargs.get('config_dir', indaleko_default_config_dir)
        self.dropbox_config_file = os.path.join(self.config_dir, IndalekoDropboxCloudStorageCollector.dropbox_config_file)
        self.dropbox_token_file = os.path.join(self.config_dir, IndalekoDropboxCloudStorageCollector.dropbox_token_file)
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
        if 'platform' not in kwargs:
            kwargs['platform'] = IndalekoDropboxCloudStorageCollector.dropbox_platform
        if 'collector_data' not in kwargs:
            kwargs['collector_data'] = IndalekoDropboxCloudStorageCollector.collector_data
        super().__init__(**kwargs,
                         collector_name=IndalekoDropboxCloudStorageCollector.dropbox_collector_name,
                         **IndalekoDropboxCloudStorageCollector.indaleko_dropbox_collector_service
        )

    def get_user_id(self):
        '''This method returns the user id.'''
        assert hasattr(self.user_info, 'email'), f'{dir(self.user_info)}'
        return self.user_info.email

    def load_dropbox_credentials(self) -> 'IndalekoDropboxCloudStorageCollector':
        '''This method retrieves the stored credentials.'''
        try:
            with open(self.dropbox_token_file,
                      'rt',
                      encoding='utf-8-sig') as f:
                self.dropbox_credentials = json.load(f)
            logging.debug('Loaded Dropbox credentials from %s', self.dropbox_token_file)
        except FileNotFoundError:
            self.dropbox_credentials = None
            logging.warning('No Dropbox credentials found in %s', self.dropbox_token_file)
        return self

    def store_dropbox_credentials(self) -> 'IndalekoDropboxCloudStorageCollector':
        '''This method stores the credentials.'''
        assert self.dropbox_credentials is not None, 'No credentials to store'
        with open(self.dropbox_token_file, 'wt', encoding='utf-8-sig') as f:
            json.dump(self.dropbox_credentials, f, indent=4)
        return self

    def set_dropbox_credentials(self, credentials : dict) -> 'IndalekoDropboxCloudStorageCollector':
        '''This method sets the credentials.'''
        self.dropbox_credentials = credentials
        return self

    def query_user_for_credentials(self) -> 'IndalekoDropboxCloudStorageCollector':
        '''This method queries the user for credentials.'''
        params = {
            'response_type': 'code',
            'client_id': self.dropbox_config['app_key'],
            'token_access_type': 'offline'
        }
        auth_request_url = f'{IndalekoDropboxCloudStorageCollector.dropbox_auth_url}?{urlencode(params)}'

        print('Please visit the following URL to authorize this application:', auth_request_url)
        auth_code = input('Enter the authorization code here: ').strip()
        data = {
            'code': auth_code,
            'grant_type': 'authorization_code',
            'client_id': self.dropbox_config['app_key'],
            'client_secret': self.dropbox_config['app_secret'],
        }
        response = requests.post(
            IndalekoDropboxCloudStorageCollector.dropbox_token_url,
            data=data,
            timeout=10)
        response.raise_for_status()
        response_data = response.json()
        assert 'expires_in' in response_data, 'No expires_in in response'
        if 'access_token' not in response_data and 'refresh_token' not in response_data:
            ic(response_data)
            raise ValueError(f'Invalid response from Dropbox {response_data}')
        self.dropbox_credentials = {
            'expires_at' : time.time() + response_data['expires_in'],
        }
        if 'access_token' in response_data:
            self.dropbox_credentials['token'] = response_data['access_token']
        if 'refresh_token' in response_data:
            self.dropbox_credentials['refresh_token'] = response_data['refresh_token']
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
        data = json.load(open(self.dropbox_token_file, 'rt', encoding='utf-8-sig'))
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

    def refresh_access_token(self) -> 'IndalekoDropboxCloudStorageCollector':
        '''
        This method refreshes the access token.
        '''
        logging.debug('Refresh token called with credentials: %s',
                      self.dropbox_credentials)
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
        response = requests.post(IndalekoDropboxCloudStorageCollector.dropbox_token_url,
                                 data=data,
                                 timeout=10)
        response.raise_for_status()
        logging.debug('Response: %s', response.json())
        response_data = response.json()
        self.dropbox_credentials = {
            'token': response_data['access_token'],
            'refresh_token': self.dropbox_credentials['refresh_token'],
            'expires_at': time.time() + response_data['expires_in']
        }
        logging.debug('Updated credentials: %s', self.dropbox_credentials)
        self.store_dropbox_credentials()
        return self

    def load_dropbox_config(self) -> 'IndalekoDropboxCloudStorageCollector':
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

    def store_dropbox_config(self, app_id : str, app_secret : str) -> 'IndalekoDropboxCloudStorageCollector':
        '''
        This method stores the Dropbox configuration.
        '''
        self.dropbox_config = {
            'app_key': app_id,
            'app_secret': app_secret
        }
        with open(self.dropbox_config_file, 'wt', encoding='utf-8') as f:
            json.dump(self.dropbox_config, f, indent=4)
        return self

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
            'Indexer' : IndalekoDropboxCloudStorageCollector.indaleko_dropbox_collector_uuid,
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
            value = IndalekoDropboxCloudStorageCollector.convert_to_serializable(attr)
            if value is None:
                continue
            metadata[field] = value
        return metadata

    def collect(self, recursive=True):
        '''This is the indexer for Dropbox'''
        try:
            metadata_list = []
            cursor = None
            while True:
                result = self.dbx.files_list_folder('', recursive=recursive)
                while True:
                    try:
                        result = self.dbx.files_list_folder_continue(
                            cursor) if cursor else self.dbx.files_list_folder('', recursive=recursive)
                    except dropbox.exceptions.ApiError as e:
                        if 'expired_access_token' in str(e):
                            ic('Refreshing access token')
                            self.refresh_access_token()
                            self.dbx = dropbox.Dropbox(self.dropbox_credentials['token'])
                            continue
                    for entry in result.entries:
                        metadata = self.build_stat_dict(entry)
                        metadata_list.append(metadata)
                        if 'FileMetadata' in metadata:
                            self.file_count += 1
                            if self.file_count % 1000 == 0:
                                ic(self.file_count)
                        elif 'FolderMetadata' in metadata:
                            self.dir_count += 1
                            if self.dir_count % 1000 == 0:
                                ic(self.dir_count)
                        elif 'MinimalFileLinkMetadata' in metadata:
                            self.good_symlink_count += 1
                        else:
                            self.special_counts += 1
                    if not result.has_more:
                        break
                    cursor = result.cursor
                if not result.has_more:
                    break
        except dropbox.exceptions.ApiError as e:
            logging.error("Error enumerating folder, exception %s", e)
            print(f"Error enumerating folder, exception {e}")
        self.data = metadata_list
        return metadata_list

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
        return [f for f in prospects if IndalekoDropboxCloudStorageCollector.dropbox_platform in f]

    class dropbox_collector_mixin(BaseCloudStorageCollector.cloud_collector_mixin):
        '''This is the mixin for the Dropbox collector.'''

        @staticmethod
        def generate_output_file_name(keys : dict[str,str]) -> str:
            '''This method is used to generate an output file name.  Note
            that it assumes the keys are in the desired format. Don't just
            pass in configuration data.'''
            if not keys.get('UserId'):
                collector = IndalekoDropboxCloudStorageCollector(
                    config_dir = keys['ConfigDirectory']
                )
                keys['UserId'] = collector.get_user_id()
            return BaseCloudStorageCollector.cloud_collector_mixin.generate_output_file_name(keys)

    cli_handler_mixin = dropbox_collector_mixin

def main():
    '''This is the entry point for using the Dropbox collector.'''
    BaseCloudStorageCollector.cloud_collector_runner(
        IndalekoDropboxCloudStorageCollector,
    )
if __name__ == '__main__':
    main()
