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
from icecream import ic
import json
import logging
import msal
import os
import pickle
import requests
import sys
import time
from urllib.parse import urlencode, parse_qs, urlparse
import uuid

from Indaleko import Indaleko
from IndalekoIndexer import IndalekoIndexer
import IndalekoLogging as IndalekoLogging


class IndalekoOneDriveIndexer(IndalekoIndexer):

    onedrive_platform = "OneDrive"
    onedrive_indexer_name = "onedrive_indexer"

    indaleko_onedrive_indexer_uuid = '4b0bdc5e-646e-4023-96c0-400281a03e54'
    indaleko_onedrive_indexer_service_name = 'OneDrive Indexer'
    indaleko_onedrive_indexer_service_description = 'Indexes the OneDrive contents for Indaleko.'
    indaleko_onedrive_indexer_service_version = '1.0'
    indaleko_onedrive_indexer_service_type = 'Indexer'

    onedrive_config_file = 'msgraph-parameters.json'
    onedrive_token_file = 'msgraph-cache.bin'


    indaleko_onedrive_indexer_service = {
        'uuid': indaleko_onedrive_indexer_uuid,
        'name': indaleko_onedrive_indexer_service_name,
        'description': indaleko_onedrive_indexer_service_description,
        'version': indaleko_onedrive_indexer_service_version,
        'type': indaleko_onedrive_indexer_service_type
    }

    class MicrosoftGraphCredentials:
        '''This encapsulates the credential management for the Microsoft Graph API.'''

        def __init__(self, config: str, cache_file: str):
            self.__chosen_account__ = -1
            self.config = json.load(open(config, 'rt'))
            self.cache_file = cache_file
            self.__load_cache__()
            self.__output_file_name__ = None
            # Note: this will prompt for credentials, if needed
            self.app = msal.PublicClientApplication(self.config['client_id'],
                                                    authority=self.config['authority'],
                                                    token_cache=self.cache
                                                    )
            self.__get_token__()

        def __get_chosen_account__(self) -> int:
            if self.__chosen_account__ < 0:
                self.__chosen_account__ = self.__choose_account__()
            return self.__chosen_account__

        def reset_chosen_account(self) -> 'IndalekoOneDriveIndexer.MicrosoftGraphCredentials':
            self.__chosen_account__ = -1
            return self

        def __load_cache__(self):
            if hasattr(self, 'cache'):
                return
            self.cache = msal.SerializableTokenCache()
            if os.path.exists(self.cache_file):
                logging.info('Cache file exists, deserializing')
                self.cache.deserialize(open(self.cache_file, 'r').read())
                logging.info(f'Loaded cache: {self.cache}')
            return self


        def __choose_account__(self) -> int:
            if self.__chosen_account__ >= 0:
                return self.__chosen_account__
            accounts = self.app.get_accounts()
            if accounts:
                choice = -1
                while choice == -1:
                    print('Pick the account to use:')
                    index = 1
                    for a in accounts:
                        print(f'{index} {a["username"]}')
                        index = index + 1
                    print(f'{index} Use a different account (login)')
                    try:
                        choice = int(input())
                        if choice == index:  # Use a different account
                            choice = -1
                            break  # done
                        choice = choice - 1
                    except ValueError:
                        choice = -1
                if choice >= 0:
                    self.__chosen_account__ = choice
            return self.__chosen_account__

        def get_account_name(self):
            if self.__output_file_name__ is None:
                assert self.__get_chosen_account__() >= 0, 'No account chosen'
                accounts = self.app.get_accounts()
                if accounts:
                    self.__output_file_name__ = accounts[self.__get_chosen_account__()].get("username")
            return self.__output_file_name__

        def get_output_file_name(self):
            return f'data/microsoft-onedrive-data-{self.get_account_name()}-{datetime.datetime.now(datetime.UTC)}-data.json'.replace(' ', '_').replace(':', '-')

        def __get_token__(self):
            if hasattr(self, 'token') and self.token is not None:
                return self.token
            self.token = None
            result = None
            accounts = self.app.get_accounts()
            logging.info(f'{len(accounts)} account(s) exist in cache, hopefully with tokens.  Checking.')
            if self.__chosen_account__ < 0 and len(accounts) > 0:
                    self.chosen_account = self.__choose_account__()
            if self.__chosen_account__ >= 0:
                result = self.app.acquire_token_silent(self.config['scope'], account=accounts[self.__chosen_account__])
            if result is None:
                logging.info('Suitable token not found in cache. Request from user.')
                flow = self.app.initiate_device_flow(scopes=self.config['scope'])
                if 'user_code' not in flow:
                    raise ValueError(f'Failed to create device flow. Err: {json.dumps(flow,indent=4)}')
                print(flow['message'])
                sys.stdout.flush()
                result = self.app.acquire_token_by_device_flow(flow)
            if 'access_token' not in result:
                print(result.get('error'))
                print(result.get('error_description'))
                print(result.get('correlation_id'))
                self.token = None
            else:
                self.token = result['access_token']
            return self.token

        def __save_cache__(self):
            if hasattr(self, 'cache') and getattr(self, 'cache') is not None:
                print(type(self.cache))
                open(self.cache_file, 'w').write(self.cache.serialize())

        def __del__(self):
            if hasattr(self, 'cache') and self.cache is not None and self.cache.has_state_changed:
                self.__save_cache__()

        def get_token(self):
            return self.__get_token__()

        def clear_token(self) -> 'IndalekoOneDriveIndexer.MicrosoftGraphCredentials':
            '''Use this to clear a stale or invalid token.'''
            self.token = None
            return self


    def __init__(self, **kwargs):
        self.config_dir = kwargs.get('configdir', Indaleko.default_config_dir)
        self.onedrive_config_file = os.path.join(self.config_dir, IndalekoOneDriveIndexer.onedrive_config_file)
        self.onedrive_token_file = os.path.join(self.config_dir, IndalekoOneDriveIndexer.onedrive_token_file)
        self.graphcreds = IndalekoOneDriveIndexer.MicrosoftGraphCredentials(
            config=self.onedrive_config_file,
            cache_file=self.onedrive_token_file
        )
        super().__init__(
            **kwargs,
            indexer_name = IndalekoOneDriveIndexer.onedrive_indexer_name,
            **IndalekoOneDriveIndexer.indaleko_onedrive_indexer_service
        )


    @staticmethod
    def generate_indexer_file_name(**kwargs):
        '''
        This method generates the name of the file that will contain the metadata
        of the files in the Dropbox folder.
        '''
        assert 'user_id' in kwargs, 'No user_id found in kwargs'
        return Indaleko.generate_file_name(**kwargs)

    def build_stat_dict(self, entry: dict) -> dict:
        '''This builds the stat dict for the entry'''
        return entry


    def index(self, recursive=True) -> list:
        '''
        This method indexes OneDrive Drive.
        '''
        ic('Indexing OneDrive Drive')
        return self.get_onedrive_metadata_recursive(
            folder_id=None,
            recurse=recursive
        )

    def get_email(self) -> str:
        '''This method returns the email address of the user'''
        return self.graphcreds.get_account_name()

    def get_onedrive_metadata_recursive(self, folder_id=None, recurse=True):
        '''This method retrieves the metadata for the OneDrive recursively.'''
        def get_headers():
            return {'Authorization':
                    f'Bearer {self.graphcreds.get_token()}'
            }
        headers = get_headers()
        metadata_list = []

        if folder_id is None:
            endpoint = 'https://graph.microsoft.com/v1.0/me/drive/root/children'
        else:
            endpoint = f'https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}/children'

        while endpoint:
            response = requests.get(endpoint, headers=headers)
            if response.status_code == 200:
                data = response.json()
                for item in data['value']:
                    metadata_list.append(item)
                    if item.get('folder'):
                        # Recursively fetch metadata for subfolder
                        subfolder_id = item['id']
                        if recurse:
                            metadata_list.extend(
                                self.get_onedrive_metadata_recursive(subfolder_id))
                endpoint = data.get('@odata.nextLink')
            else:
                logging.error(f"Error: {response.status_code} - {response.text}")
                if 401 == response.status_code: # seems to indicate a stale token
                    self.graphcreds.clear_token()
                    headers = get_headers()
                # try again
        return metadata_list


    @staticmethod
    def find_indexer_files(
            search_dir : str,
            prefix : str = IndalekoIndexer.default_file_prefix,
            suffix : str = IndalekoIndexer.default_file_suffix) -> list:
        '''This function finds the files to ingest:
            search_dir: path to the search directory
            prefix: prefix of the file to ingest
            suffix: suffix of the file to ingest (default is .json)
        '''
        prospects = IndalekoIndexer.find_indexer_files(search_dir, prefix, suffix)
        return [f for f in prospects if IndalekoOneDriveIndexer.dropbox_platform in f]


def main():
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
    pre_args, _ = pre_parser.parse_known_args()
    indaleko_logging = IndalekoLogging.IndalekoLogging(platform=IndalekoOneDriveIndexer.onedrive_indexer_name,
                                                       service_name='indexer',
                                                       log_dir=pre_args.logdir,
                                                       log_level=pre_args.loglevel,
                                                       timestamp=timestamp,
                                                       suffix='log')
    log_file_name = indaleko_logging.get_log_file_name()
    ic(log_file_name)
    indexer = IndalekoOneDriveIndexer(timestamp=timestamp)
    output_file_name = IndalekoOneDriveIndexer.generate_indexer_file_name(
            platform=IndalekoOneDriveIndexer.onedrive_platform,
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
                        default=Indaleko.default_data_dir)
    parser.add_argument('--path',
                        help='Path to the directory to index',
                        type=str,
                        default='')
    parser.add_argument('--norecurse',
                        help='Disable recursive directory indexing (for testing).',
                        default=False,
                        action='store_true')
    args = parser.parse_args()
    output_file = os.path.join(args.datadir, args.output)
    logging.info('Indaleko OneDrive Indexer started.')
    logging.info('Output file: %s', output_file)
    logging.info('Indexing: %s', args.path)
    logging.info(args)
    data = indexer.index(recursive= (not args.norecurse))
    indexer.write_data_to_file(data, output_file)
    for count_type, count_value in indexer.get_counts().items():
        logging.info('Count %s: %s', count_type, count_value)
    logging.info('Indaleko OneDrive Indexer finished.')

if __name__ == '__main__':
    main()
