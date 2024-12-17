'''
This script is used to index the files in a One Drive folder of Indaleko.
It will create a JSONL file with the metadata of the files in the Dropbox
folder. The JSONL file will be used by the Recorder to load data into
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
import concurrent.futures
import datetime
from icecream import ic
import json
import logging
import msal
from pyngrok import ngrok
import os
from queue import Queue
import requests
import socket
import sys
import threading
import time
from urllib.parse import urlencode, parse_qs, urlparse

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models import IndalekoSourceIdentifierDataModel
from db import IndalekoServiceManager
from utils.i_logging import IndalekoLogging
from utils.misc.file_name_management import generate_file_name
from utils.misc.directory_management import indaleko_default_data_dir, indaleko_default_config_dir, indaleko_default_log_dir
from storage.collectors.base import BaseStorageCollector
from perf.perf_collector import IndalekoPerformanceDataCollector
from perf.perf_recorder import IndalekoPerformanceDataRecorder
# pylint: enable=wrong-import-position

class IndalekoOneDriveCollector(BaseStorageCollector):
    '''This is the class for the OneDrive Collector for Indaleko.'''

    onedrive_platform = "OneDrive"
    onedrive_collector_name = "onedrive_collector"

    indaleko_onedrive_collector_uuid = '4b0bdc5e-646e-4023-96c0-400281a03e54'
    indaleko_onedrive_collector_service_name = 'OneDrive Collector'
    indaleko_onedrive_collector_service_description = 'Indexes the OneDrive contents for Indaleko.'
    indaleko_onedrive_collector_service_version = '1.0'
    indaleko_onedrive_collector_service_type = IndalekoServiceManager.service_type_storage_collector

    onedrive_config_file = 'msgraph-parameters.json'
    onedrive_token_file = 'msgraph-cache.bin'


    indaleko_onedrive_collector_service = {
        'uuid': indaleko_onedrive_collector_uuid,
        'name': indaleko_onedrive_collector_service_name,
        'description': indaleko_onedrive_collector_service_description,
        'version': indaleko_onedrive_collector_service_version,
        'type': indaleko_onedrive_collector_service_type
    }

    class MicrosoftGraphCredentials:
        '''This encapsulates the credential management for the Microsoft Graph API.'''

        def __init__(self, config: str, cache_file: str):
            self.__chosen_account__ = -1
            self.config = json.load(open(config, 'rt', encoding='utf-8-sig'))
            self.cache_file = cache_file
            self.__load_cache__()
            self.__output_file_name__ = None
            self.port = self.find_unused_tcp_port()
            try:
                self.public_url = ngrok.connect(self.port)
            except PermissionError as e:
                ic(f'Access denied trying to use port {self.port}')
                raise e
            ic(f'Public URL: {self.public_url}')
            self.redirect_uri = f'{self.public_url}/auth'
            # Note: this will prompt for credentials, if needed
            self.app = msal.PublicClientApplication(self.config['client_id'],
                                                    authority=self.config['authority'],
                                                    token_cache=self.cache
                                                    )
            self.__get_token__()

        @staticmethod
        def find_unused_tcp_port():
            '''This method finds an unused TCP port.'''
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', 0))
                return s.getsockname()[1]

        def __get_chosen_account__(self) -> int:
            if self.__chosen_account__ < 0:
                self.__chosen_account__ = self.__choose_account__()
            return self.__chosen_account__

        def reset_chosen_account(self) -> 'IndalekoOneDriveCollector.MicrosoftGraphCredentials':
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

        def clear_token(self) -> 'IndalekoOneDriveCollector.MicrosoftGraphCredentials':
            '''Use this to clear a stale or invalid token.'''
            self.token = None
            return self


    def __init__(self, **kwargs):
        self.config_dir = kwargs.get('configdir', indaleko_default_config_dir)
        self.onedrive_config_file = os.path.join(self.config_dir, IndalekoOneDriveCollector.onedrive_config_file)
        self.onedrive_token_file = os.path.join(self.config_dir, IndalekoOneDriveCollector.onedrive_token_file)
        self.graphcreds = IndalekoOneDriveCollector.MicrosoftGraphCredentials(
            config=self.onedrive_config_file,
            cache_file=self.onedrive_token_file
        )
        super().__init__(
            **kwargs,
            collector_name=IndalekoOneDriveCollector.onedrive_collector_name,
            **IndalekoOneDriveCollector.indaleko_onedrive_collector_service
        )
        self.queue = Queue()
        self.results = Queue()
        self.max_workers = kwargs.get('max_workers', 1)
        self.recurse = kwargs.get('recurse', True)
        ic(self.recurse)
        self.drives = self.get_drives()
        self.root_processed = False

    @staticmethod
    def generate_onedrive_collector_file_name(**kwargs):
        '''
        This method generates the name of the file that will contain the metadata
        of the files in the Dropbox folder.
        '''
        assert 'user_id' in kwargs, 'No user_id found in kwargs'
        return generate_file_name(**kwargs)

    def build_stat_dict(self, entry: dict) -> dict:
        '''This builds the stat dict for the entry'''
        return entry


    def collect(self) -> list:
        '''
        This method indexes OneDrive Drive.
        '''
        ic('Indexing OneDrive Drive')
        ic('Recurse: ', self.recurse)
        return self.get_onedrive_metadata()

    def get_drives(self) -> list:
        '''
        Given an authenticated user, return a list of the drives available to
        them.
        '''
        headers = self.get_headers()
        url = 'https://graph.microsoft.com/v1.0/me/drives'
        response = requests.get(url, headers=headers, timeout=(10,30))
        response.raise_for_status()
        if response.status_code == 200:
            drives = response.json().get('value', [])
            for drive in drives:
                ic(drive)
            return drives
        else:
            logging.error("Error retrieving drives: %s - %s",
                          response.status_code,
                          response.text)
            raise ValueError(f"Error retrieving drives: {response.status_code} - {response.text}")


    def get_email(self) -> str:
        '''This method returns the email address of the user'''
        return self.graphcreds.get_account_name()

    def get_headers(self) -> dict:
        '''This method returns the headers for the request with the current
        token.'''
        return {'Authorization': 'Bearer ' + self.graphcreds.get_token()}

    def fetch_directory(self, url, timeout=10):
        tid = threading.get_ident()

        ic(f'{tid}: fetch_directory called')
        headers = self.get_headers()
        params = {'$top': '999'}  # Fetch up to 999 items in a single request
        assert url is not None, 'URL is required to be non-empty'

        retries = 5
        while retries > 0:

            def FetchTimeoutException(Exception):
                pass

            try:
                ic(f'{tid} Fetching directory: {url}, retries left: {retries}')
                logging.info(f"{tid} Fetching directory: {url}")
                start = time.time()

                def trace_function(frame, event, arg):
                    if time.time() - start > timeout:
                        raise FetchTimeoutException(f'{tid} Timeout')
                    else:
                        logging.debug(ic(f'{tid} trace_function: {frame} {event} {arg}'))
                    return trace_function

                sys.settrace(trace_function)
                response = requests.get(url, headers=headers, params=params, timeout=(10,30))
                sys.settrace(None)

                ic(f"Response: {response.status_code}")
                logging.info(f"{tid} Response: {response.status_code}")
                response.raise_for_status()

                items = response.json().get('value', [])
                logging.info(f'{tid}: Fetched {len(items)} items')
                ic(f'{tid}: Fetched {len(items)} items')
                directories = []
                for item in items:
                    # Process the item
                    if 'folder' in item and self.recurse:
                        ic(f'{tid}: Found folder: {item["id"]}')
                        directories.append(item['id'])
                    self.results.put(self.build_stat_dict(item),timeout=30)
                return ic(directories)

            except requests.exceptions.Timeout as e:
                retries -= 1
                logging.error(f"{tid} Request timed out: {e}. Retrying {retries} more times.")
                ic(f"{tid}: Request timed out: {e}. Retrying {retries} more times.")
                time.sleep(5)

            except requests.exceptions.RequestException as e:
                retries -= 1
                if response is not None and 401 == response.status_code: # seems to indicate a stale token
                    logging.info(f"{tid} : Request failed (401).  Refresh token.")
                    self.graphcreds.clear_token()
                    headers = self.get_headers()
                else:
                    logging.error(f"{tid} Request failed: {e}. Retrying {retries} more times.")
                    ic(f"{tid}: Request failed: {e}. Retrying {retries} more times.")
                    time.sleep(5)  # Wait for 5 seconds before retrying
            except FetchTimeoutException as e:
                retries -= 1
                logging.error(f"{tid} Request hard timeout): {e}. Retrying {retries} more times.")
                ic(f"{tid}: Request hard timeout: {e}. Retrying {retries} more times.")
                time.sleep(5)
            finally:
                sys.settrace(None)

        logging.error(f"{tid}: Request failed after multiple attempts: {url}")
        ic(f"Request failed after multiple attempts: {url}")
        return None

    def queue_directory(self, folder_id):
        '''This method queues the directory for processing.'''
        if folder_id is None:
            url = 'https://graph.microsoft.com/v1.0/me/drive/root/children'
        else:
            url = f"https://graph.microsoft.com/v1.0/me/drive/items/{folder_id}/children"
        self.queue.put(url, timeout=30)


    def worker(self):
        '''Worker threads for retrieving the metadata of the OneDrive recursively.'''
        tid = threading.get_ident()
        ic(f'worker {tid} started')
        while True:
            ic(f'worker {tid} waiting')
            url = self.queue.get()
            ic(f'worker {tid} processing {url}: ')
            if url is None:
                ic(f'worker {tid} url is None, terminating')
                self.queue.task_done()
                break
            directories = self.fetch_directory(url)
            ic(f'worker {tid} retrieved directories: ', directories)
            if directories is None: # the fetch failed
                self.queue.put(url, timeout=30)
            elif self.recurse:
                for directory in directories:
                    self.queue_directory(directory)
                logging.info(f"worker {tid} Processed {url}")
                ic(f'worker {tid} processed: ', url)
            ic(self.queue.qsize())
            self.queue.task_done()
        ic(f'worker {tid} finished')

    def get_onedrive_metadata_mt(self, folder_id=None):
        '''This method retrieves the metadata of the OneDrive.'''
        self.results = Queue()
        self.queue_directory(folder_id)
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.worker) for _ in range(self.max_workers)]
            ic('waiting for queue to finish')
            self.queue.join()
            ic('queue finished')
            ic('adding poison pills', self.max_workers)
            for _ in (range(self.max_workers)):
                ic('putting None')
                self.queue.put(None, timeout=30)
            ic(f'waiting for futures to finish: {futures}')
            concurrent.futures.wait(futures)
            ic('futures finished')
        return [self.results.get() for _ in range(self.results.qsize())]

    @staticmethod
    def get_url_for_folder(drive_id : str = None,
                           folder_id : str = None,
                           return_children : bool = True) -> None:
        '''This method returns the URL for the folder.'''
        url = 'https://graph.microsoft.com/v1.0'
        if drive_id is None:
            url += '/me/drive/items/'
            if folder_id is None:
                url += 'root'
            else:
                url += folder_id
        else:
            url += f'/drives/{drive_id}/'
            if folder_id is not None:
                url += f'items/{folder_id}'
        if return_children:
            url += '/children'
        return url

    def fetch_onedrive_metadata(self, drive_id : str  = "me", item_id : str = "root") -> dict:
        '''This method retrieves the metadata of the object in the OneDrive.'''
        if item_id == 'root':
            url = f"https://graph.microsoft.com/v1.0/{drive_id}/drive/root"
        else:
            url = f"https://graph.microsoft.com/v1.0/{drive_id}/drive/items/{item_id}"
        headers = self.get_headers()
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error: {response.status_code} - {response.text}")
            ic(e)
            return None
        return response.json()

    def process_root(self, root : dict) -> None:
        '''This method processes the root of the OneDrive.'''
        assert isinstance(root, dict), 'Root must be a dict'
        assert not self.root_processed, 'Root already processed'
        self.results.put(self.build_stat_dict(root), timeout=30)
        ic(root)
        if 'folder' in root:
            drive_id = root['parentReference']['driveId']
            folder_id = root['id']
            url = self.get_url_for_folder(drive_id, folder_id, return_children=True)
            self.queue.put(url, timeout=30)
            ic(url)
            self.dir_count += 1
        else:
            self.file_count += 1
        ic(root)
        item = {
            'createdDateTime' : root['createdDateTime'],
            'fileSystemInfo' : root['fileSystemInfo'],
            'folder' : root['folder'],
            'id' : root['id'],
            'lastModifiedDateTime' : root['lastModifiedDateTime'],
            'name' : '', # root
            'parentReference' : root['parentReference'],
            'size' : root['size'],
            'webUrl' : root['webUrl']
        }
        item['parentReference']['path'] = '/drive/root:'
        item['parentReference']['name'] = ''
        item['parentReference']['id'] = root['id'] # root is its own parent.
        self.root_processed = True
        return item

    def get_onedrive_metadata(self, drive_id : str = None, folder_id : str = None) -> list:
        '''This method retrieves the metadata of the OneDrive.'''
        queue = []
        refresh_count = 0
        error_count = 0
        success_error_count = 0
        url = self.get_url_for_folder(drive_id=drive_id,
                                      folder_id=folder_id,
                                      return_children=False)
        queue.append(url)
        results = []
        passes = 0
        while len(queue) > 0:
            passes = passes + 1
            if 0 == passes % 100:
                ic(f'Pending queue size is {len(queue)} at pass {passes}')
            url = queue.pop()
            headers = self.get_headers()
            params = {'$top': '999'}
            try:
                response = requests.get(url, headers=headers, params=params, timeout=(10,30))
                response.raise_for_status()
            except requests.exceptions.Timeout as e:
                logging.error(ic(f"Request timed out: {e}. Retrying {url}"))
                queue.insert(0, url)
                continue
            except requests.exceptions.RequestException as e:
                logging.error("Error: %s - %s", response.status_code, response.text)
                ic(e)
                if 401 == response.status_code: # seems to indicate a stale token
                    self.graphcreds.clear_token()
                    # try again
                    ic(f'Refreshing token, url {url}')
                    queue.insert(0, url)
                    refresh_count = refresh_count + 1
                    continue
                elif 200 == response.status_code:
                    # success code, but error status raise?
                    logging.error("Error (for 200): for URL %s - %s - %s", url, response.status_code, response.text)
                    success_error_count = error_count + 1
                    # note we want to fall through and process this.
                else:
                    logging.warning(
                        ic(f"Error: for URL {url} - {response.status_code} - {response.text}")
                    )
                    error_count = error_count + 1
                    self.error_count += 1
                    continue
            if 'value' not in response.json():
                item = self.process_root(response.json())
                results.append(self.build_stat_dict(item))
                url = self.get_url_for_folder(drive_id=drive_id,
                                              folder_id=item['id'],
                                              return_children=True)
                queue.append(url)
                continue
            for item in response.json()['value']:
                if 'folder' in item and self.recurse:
                    queue.append(self.get_url_for_folder(drive_id=None, folder_id=item['id']))
                    self.dir_count += 1
                else:
                    self.file_count += 1
                # metadata = self.fetch_onedrive_metadata(drive_id="me",
                # Note: we are not using the metadata because it does not
                # provide useful additional detail.  I preserve it here to
                # explain why we are not using it.
                results.append(self.build_stat_dict(item))
        ic(f'Processed {len(results)} items, refresh_count {refresh_count}, error_count {error_count}, success_error_count {success_error_count}')
        return results


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
        return [f for f in prospects if IndalekoOneDriveCollector.dropbox_platform in f]


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
    pre_parser.add_argument('--norecurse',
                        help='Disable recursive directory indexing (for testing).',
                        default=False,
                        action='store_true')
    pre_parser.add_argument('--threads', '-t',
                            help='Number of threads to use for indexing',
                            default=1,
                            type=int)
    pre_args, _ = pre_parser.parse_known_args()
    indaleko_logging = IndalekoLogging(platform=IndalekoOneDriveCollector.onedrive_collector_name,
                                        service_name='collector',
                                        log_dir=pre_args.logdir,
                                        log_level=pre_args.loglevel,
                                        timestamp=timestamp,
                                        suffix='log')
    log_file_name = indaleko_logging.get_log_file_name()
    ic(log_file_name)
    collector = IndalekoOneDriveCollector(timestamp=timestamp, recurse=(not pre_args.norecurse), max_workers=pre_args.threads)
    output_file_name = IndalekoOneDriveCollector.generate_onedrive_collector_file_name(
            platform=IndalekoOneDriveCollector.onedrive_platform,
            user_id=collector.get_email(),
            service='collector',
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
    parser.add_argument('--performance_file',
                        default=False,
                        action='store_true',
                        help='Record performance data to a file')
    parser.add_argument('--performance_db',
                        default=False,
                        action='store_true',
                        help='Record performance data to the database')
    args = parser.parse_args()
    output_file = os.path.join(args.datadir, args.output)
    logging.info('Indaleko OneDrive Collector started.')
    logging.info('Output file: %s', output_file)
    logging.info(args)
    perf_file_name = os.path.join(
        args.datadir,
        IndalekoPerformanceDataRecorder().generate_perf_file_name(
            platform=collector.gdrive_platform,
            service=collector.gdrive_collector_name,
            machine=None,
        )
    )
    def extract_counters(**kwargs):
        ic(kwargs)
        collector = kwargs.get('collector')
        if collector:
            return ic(collector.get_counts())
        else:
            return {}
    def collect(collector):
        data = collector.collect()
        if len(data) > 0:
            collector.write_data_to_file(data, output_file)
        else:
            logging.error('No data found. File not written.')
            ic('No data found. File not written.')
    perf_data = IndalekoPerformanceDataCollector.measure_performance(
        collect,
        source=IndalekoSourceIdentifierDataModel(
            Identifier=collector.service_identifier,
            Version = collector.service_version,
            Description=collector.service_description),
        description=collector.service_description,
        MachineIdentifier=None,
        process_results_func=extract_counters,
        input_file_name=None,
        output_file_name=output_file,
        collector=collector
    )
    if args.performance_db or args.performance_file:
        perf_recorder = IndalekoPerformanceDataRecorder()
        if args.performance_file:
            perf_recorder.add_data_to_file(perf_file_name, perf_data)
            ic('Performance data written to ', perf_file_name)
        if args.performance_db:
            perf_recorder.add_data_to_db(perf_data)
            ic('Performance data written to the database')
    for count_type, count_value in collector.get_counts().items():
        logging.info('Count %s: %s', count_type, count_value)
    logging.info('Indaleko OneDrive Collector finished.')

if __name__ == '__main__':
    main()
