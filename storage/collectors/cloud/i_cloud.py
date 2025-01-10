'''
i_cloud.py

This script is used to scan the files in the Google Drive folder of Indaleko.
It will create a JSONL file with the metadata of the files in the Dropbox
folder.
The JSONL file will be used by the google drive recorder to load data into
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
from datetime import datetime, timezone
import keyring
import logging
import os
from pathlib import Path
import sys
import uuid

from getpass import getpass
from icecream import ic
from typing import Union
from pyicloud import PyiCloudService

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
from storage.collectors.data_model import IndalekoStorageCollectorDataModel
from perf.perf_collector import IndalekoPerformanceDataCollector
from perf.perf_recorder import IndalekoPerformanceDataRecorder
# pylint: enable=wrong-import-position


class IndalekoICloudCollector(BaseStorageCollector):

    icloud_platform = 'iCloud'
    icloud_collector_name = 'icloud_collector'

    indaleko_icloud_collector_uuid = 'cf8694ff-6cfe-4801-9842-4315fc7a02e6'
    indaleko_icloud_collector_service_name = 'iCloud Collector'
    indaleko_icloud_collector_service_description = 'This service indexes the iCloud folder of the user.'
    indaleko_icloud_collector_service_version = '1.0'
    indaleko_icloud_collector_service_type_identifier = IndalekoServiceManager.service_type_storage_collector

    icloud_root_folder = {
        'ObjectIdentifier': 'd0dac621-4de3-44df-a2c9-49841b86b508',
        'name': 'icloud_root_dir',
        'path_display': 'root',
        'size': 0,
        'modified': datetime.now(timezone.utc),
        'date_changed': datetime.now(timezone.utc),
        'created': datetime.now(timezone.utc),
        'last_opened': datetime.now(timezone.utc),
    }

    indaleko_icloud_local_collector_service = {
        'service_name': indaleko_icloud_collector_service_name,
        'service_description': indaleko_icloud_collector_service_description,
        'service_version': indaleko_icloud_collector_service_version,
        'service_type': indaleko_icloud_collector_service_type_identifier,
        'service_identifier': indaleko_icloud_collector_uuid,
    }

    icloud_collector_data = IndalekoStorageCollectorDataModel(
        CollectorPlatformName=icloud_platform,
        CollectorServiceName=indaleko_icloud_collector_service_name,
        CollectorServiceUUID = uuid.UUID(indaleko_icloud_collector_uuid),
        CollectorServiceVersion=indaleko_icloud_collector_service_version,
        CollectorServiceDescription=indaleko_icloud_collector_service_description
    )

    def __init__(self, **kwargs):
        # self.auth_logger = self.setup_logging()
        self.icloud_credentials = None
        self.service = None
        self.load_icloud_credentials()
        if self.icloud_credentials is None:
            logging.debug('No iCloud credentials found, reconstructing.')
            self.query_user_for_credentials()
        if self.icloud_credentials is not None:
            logging.info(f"Using iCloud credentials: {self.icloud_credentials}")
            try:
                self.service = PyiCloudService(
                    self.icloud_credentials['username'],
                    self.icloud_credentials['password']
                )
            except Exception as e:
                logging.error(f"Error initializing iCloud service: {e}")
        if 'platform' not in kwargs:
            kwargs['platform'] = IndalekoICloudCollector.icloud_platform
        if 'collector_data' not in kwargs:
            kwargs['collector_data'] = IndalekoICloudCollector.icloud_collector_data
        super().__init__(
            **kwargs,
            collector_name=IndalekoICloudCollector.icloud_collector_name,
            **IndalekoICloudCollector.indaleko_icloud_local_collector_service
        )

    def get_user_id(self):
        '''This method returns the user id.'''
        usernames = self.get_stored_usernames()
        if usernames:
            print("Stored usernames:")
            for stored_username in usernames:
                print(f"- {stored_username}")
        user_id = input("Enter your iCloud username (or press Enter to select from the list above): ").strip()
        if not user_id and usernames:
            if len(usernames) == 1:
                user_id = usernames[0]
            else:
                user_id = input("Please select a username from the list above: ").strip()
        return user_id

    def load_icloud_credentials(self):
        logging.info("Loading iCloud credentials.")
        username = keyring.get_password("iCloud", "username")
        password = keyring.get_password("iCloud", "password")
        if username and password:
            self.icloud_credentials = {'username': username, 'password': password}
            logging.info(f"Loaded credentials for username: {username}")
        return self

    def store_icloud_credentials(self) -> 'IndalekoICloudCollector':
        '''This method stores the credentials.'''
        user_id = self.get_user_id()
        password = getpass("Enter your iCloud password: ")
        self._store_credentials(user_id, password)
        self.update_stored_usernames(user_id)
        return self

    def set_icloud_credentials(self, credentials: dict) -> 'IndalekoICloudCollector':
        '''This method sets the credentials.'''
        user_id = credentials.get("username")
        password = credentials.get("password")
        self._store_credentials(user_id, password)
        self.update_stored_usernames(user_id)
        return self

    def query_user_for_credentials(self) -> 'IndalekoICloudCollector':
        '''This method queries the user for credentials.'''
        user_id = self.get_user_id()
        password = keyring.get_password('iCloud', user_id)
        if not password:
            password = getpass("Enter your iCloud password: ")
            self._store_credentials(user_id, password)
            self.update_stored_usernames(user_id)
        return user_id, password

    def get_icloud_credentials(self, refresh: bool = False):
        '''This method retrieves the iCloud credentials.'''
        return self.query_user_for_credentials()

    def _store_credentials(self, username, password):
        keyring.set_password('iCloud', username, password)
        # self.auth_logger.debug(f"Stored credentials for {username}")

    def get_stored_usernames(self):
        usernames = keyring.get_password('iCloud', 'usernames')
        return usernames.split(',') if usernames else []

    def update_stored_usernames(self, username):
        usernames = self.get_stored_usernames()
        if username not in usernames:
            usernames.append(username)
            keyring.set_password('iCloud', 'usernames', ','.join(usernames))
        return usernames

    def list_all_entries(self, service_name):
        # self.auth_logger.debug(f"Listing all entries for service '{service_name}':")
        stored_usernames = self.get_stored_usernames()
        # for stored_username in stored_usernames:
        #     self.auth_logger.debug(f"Username: {stored_username}")

    def authenticate(self):
        user_id, password = self.get_icloud_credentials()
        ic(user_id, password)
        api = PyiCloudService(user_id, password)

        if api.requires_2fa:
            code = input("Enter the code you received on one of your approved devices: ")
            result = api.validate_2fa_code(code)
            if not result:
                raise ValueError("Failed to verify security code")
            if not api.is_trusted_session:
                api.trust_session()
        return api

    @staticmethod
    def generate_icloud_collector_file_name(**kwargs):
        '''This method generates the name of the file that wiil contain the metadata
        of the files in the iCloud folder.'''
        assert 'user_id' in kwargs, 'No user_id found in kwargs'
        return generate_file_name(**kwargs)

    @staticmethod
    def convert_to_serializable(data):
        '''Converts the data into serializable form'''
        if isinstance(data, (int, float, str, bool, type(None))):
            return data
        elif isinstance(data, list):
            return [IndalekoICloudCollector.convert_to_serializable(item) for item in data]
        elif isinstance(data, dict):
            return {key: IndalekoICloudCollector.convert_to_serializable(value) for key, value in data.items()}
        else:
            if hasattr(data, '__dict__'):
                return IndalekoICloudCollector.convert_to_serializable(data.__dict__)
            return None

    def collect_metadata(self, item, item_path):
        def to_utc_iso(dt):
            # Convert to UTC and format with 'Z' suffix
            if dt is not None:
                return dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
            else:
                # Return the default UTC time with 'Z' suffix
                return datetime(1970, 1, 1, 0, 0, tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')

        metadata = {
            'name': item.name,
            'path_display': IndalekoICloudCollector.icloud_root_folder['path_display'] + '/' + item_path,
            'size': getattr(item, 'size', 0) or 0, # Default to 0 if size is None or 0
            'date_created': to_utc_iso(getattr(item, 'date_created', None)),
            'date_modified': to_utc_iso(getattr(item, 'date_modified', None)),
            'last_opened': to_utc_iso(getattr(item, 'date_last_opened', None)),
            'date_changed': to_utc_iso(getattr(item, 'date_changed', None)),
            'ObjectIdentifier': str(uuid.uuid4()),  # Generate and add a UUID for each file
            'drivewsid': getattr(item, 'drivewsid', 'Unknown'),
            'docwsid': getattr(item, 'docwsid', 'Unknown'),
            'zone': getattr(item, 'zone', 'Unknown'),
            'extension': getattr(item, 'extension', 'Unknown'),
            'parentId': getattr(item, 'parentId', 'Unknown'),
            'item_id': getattr(item, 'item_id', 'Unknown'),
            'etag': getattr(item, 'etag', 'Unknown'),
            'type': getattr(item, 'type', 'Unknown')
        }
        return metadata

    def index_directory(self, folder, path=''):
        """Recursively get the contents of a folder and write metadata to a JSON Lines file."""
        metadata_list = []
        try:
            logging.info(f"Entering folder: {path or '/'}")
            for item_name in folder.dir():
                item = folder[item_name]
                item_path = f"{path}/{item_name}"

                if item.type == 'folder':
                    # Recursively get the contents of this folder
                    metadata = self.collect_metadata(item, item_path)
                    metadata_list.append(metadata)
                    logging.debug(f"Indexed Item (file): {metadata}")
                    #continue indexing into file
                    self.index_directory(item, item_path)
                else:
                    metadata = self.collect_metadata(item, item_path)
                    metadata_list.append(metadata)
                    logging.debug(f"Indexed Item: {metadata}")
        except Exception as e:
            logging.error(f"Failed to process folder: {path}, Error: {e}")
        return metadata_list

    def collect(self, recursive=True):
        api = self.authenticate()
        files = api.drive.root

        if recursive:
            indexed_data = self.index_directory(files)
        else:
            indexed_data = []
            for item_name in files.dir():
                item = files[item_name]
                metadata = self.collect_metadata(item, item_name)
                indexed_data.append(metadata)
                logging.debug(f"Indexed Item (non-recursive): {metadata}")
        return indexed_data

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
        return [f for f in prospects if IndalekoICloudCollector.icloud_platform in f]

class icloud_collector_mixin(IndalekoBaseCLI.default_handler_mixin):
    '''This is the mixin for the iCloud collector'''

    @staticmethod
    def get_pre_parser() -> Union[argparse.Namespace, None]:
        '''Add the parameters for the local storage collector'''
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument('--norecurse',
                            help='Disable recursive directory indexing (for testing).',
                            default=False,
                            action='store_true')
        return parser


@staticmethod
def local_run(keys: dict[str, str]) -> Union[dict,None]:
    '''Run the collector'''
    args = keys['args']
    cli = keys['cli']
    config_data = cli.get_config_data()
    debug = hasattr(args, 'debug') and args.debug
    if debug:
        ic(args)
        ic(config_data)
    kwargs = {
        'timestamp': config_data['Timestamp'],
        'offline': args.offline
    }
    output_file_name=str(Path(args.datadir) / args.outputfile)
    def collect(collector: IndalekoGDriveCollector):
        '''local implementation of collect'''
        data = collector.collect(not args.norecurse)
        output_file = output_file_name
        collector.write_data_to_file(data, output_file)
    def extract_counters(**kwargs):
        '''local implementation of extract_counters'''
        collector = kwargs.get('collector')
        if collector:
            return ic(collector.get_counts())
        else:
            return {}
    output_file_name=str(Path(args.datadir) / args.outputfile)
    def collect(collector: IndalekoICloudCollector) -> None:
        '''local implementation of collect'''
        data = collector.collect(not args.norecurse)
        output_file = output_file_name
        collector.write_data_to_file(data, output_file)
    def extract_counters(**kwargs):
        '''local implementation of extract_counters'''
        ic(kwargs)
        collector = kwargs.get('collector')
        if collector:
            return ic(collector.get_counts())
        else:
            return {}
    collector = IndalekoICloudCollector(**kwargs)
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
        output_file_name=output_file_name,
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


def main() -> None:
    '''iCloud collector main'''
    runner = IndalekoCLIRunner(
        cli_data=IndalekoBaseCliDataModel(
            Platform=None,
            Service=IndalekoICloudCollector.icloud_collector_name,
        ),
        handler_mixin=icloud_collector_mixin,
        features=IndalekoBaseCLI.cli_features(
            machine_config=False,
            input=False,
            platform=False,
        ),
        Run=local_run,
    )
    ic(runner)
    runner.run()

if __name__ == '__main__':
    main()
