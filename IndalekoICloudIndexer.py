import argparse
import keyring
import logging
import os
import uuid

from datetime import datetime, timezone
from getpass import getpass
from icecream import ic
from Indaleko import Indaleko
from IndalekoIndexer import IndalekoIndexer
import IndalekoLogging as IndalekoLogging
from pyicloud import PyiCloudService

class IndalekoICloudIndexer(IndalekoIndexer):

    icloud_platform = 'iCloud'
    icloud_indexer_name = 'icloud_indexer'

    indaleko_icloud_indexer_uuid = 'cf8694ff-6cfe-4801-9842-4315fc7a02e6'
    indaleko_icloud_indexer_service_name = 'iCloud Indexer'
    indaleko_icloud_indexer_service_description = 'This service indexes the iCloud folder of the user.'
    indaleko_icloud_indexer_service_version = '1.0'
    indaleko_icloud_indexer_service_type = 'Indexer'

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

    indaleko_icloud_local_indexer_service = {
        'service_name': indaleko_icloud_indexer_service_name,
        'service_description': indaleko_icloud_indexer_service_description,
        'service_version': indaleko_icloud_indexer_service_version,
        'service_type': indaleko_icloud_indexer_service_type,
        'service_identifier': indaleko_icloud_indexer_uuid,
    }

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
            kwargs['platform'] = IndalekoICloudIndexer.icloud_platform
        super().__init__(
            **kwargs,
            indexer_name=IndalekoICloudIndexer.icloud_indexer_name,
            **IndalekoICloudIndexer.indaleko_icloud_local_indexer_service
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

    def store_icloud_credentials(self) -> 'IndalekoICloudIndexer':
        '''This method stores the credentials.'''
        user_id = self.get_user_id()
        password = getpass("Enter your iCloud password: ")
        self._store_credentials(user_id, password)
        self.update_stored_usernames(user_id)
        return self

    def set_icloud_credentials(self, credentials: dict) -> 'IndalekoICloudIndexer':
        '''This method sets the credentials.'''
        user_id = credentials.get("username")
        password = credentials.get("password")
        self._store_credentials(user_id, password)
        self.update_stored_usernames(user_id)
        return self

    def query_user_for_credentials(self) -> 'IndalekoICloudIndexer':
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
        self.auth_logger.debug(f"Stored credentials for {username}")

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
        self.auth_logger.debug(f"Listing all entries for service '{service_name}':")
        stored_usernames = self.get_stored_usernames()
        for stored_username in stored_usernames:
            self.auth_logger.debug(f"Username: {stored_username}")

    def authenticate(self):
        user_id, password = self.get_icloud_credentials()
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
    def generate_windows_indexer_file_name(**kwargs):
        '''This method generates the name of the file that wiil contain the metadata
        of the files in the iCloud folder.'''
        assert 'user_id' in kwargs, 'No user_id found in kwargs'
        return Indaleko.generate_file_name(**kwargs)

    @staticmethod
    def convert_to_serializable(data):
        '''Converts the data into serializable form'''
        if isinstance(data, (int, float, str, bool, type(None))):
            return data
        elif isinstance(data, list):
            return [IndalekoICloudIndexer.convert_to_serializable(item) for item in data]
        elif isinstance(data, dict):
            return {key: IndalekoICloudIndexer.convert_to_serializable(value) for key, value in data.items()}
        else:
            if hasattr(data, '__dict__'):
                return IndalekoICloudIndexer.convert_to_serializable(data.__dict__)
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
            'path_display': IndalekoICloudIndexer.icloud_root_folder['path_display'] + '/' + item_path,
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

    def index(self, recursive=True):
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
        return [f for f in prospects if IndalekoICloudIndexer.icloud_platform in f]

def main():
    logging_levels = Indaleko.get_logging_levels()
    timestamp = datetime.now(timezone.utc).isoformat()
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument('--logdir', '-l',
                            help='Path to the log directory',
                            default=Indaleko.default_log_dir)
    pre_parser.add_argument('--loglevel',
                            type=int,
                            default=logging.DEBUG,
                            choices=logging_levels,
                            help='Logging level to use (lower number = more logging)')
    pre_args, _ = pre_parser.parse_known_args()
    indaleko_logging = IndalekoLogging.IndalekoLogging(platform=IndalekoICloudIndexer.icloud_platform,
                                                       service_name='indexer',
                                                       log_dir=pre_args.logdir,
                                                       log_level=pre_args.loglevel,
                                                       timestamp=timestamp,
                                                       suffix='log')
    log_file_name = indaleko_logging.get_log_file_name()
    ic(log_file_name)
    indexer = IndalekoICloudIndexer(timestamp=timestamp)

    output_file_name = IndalekoICloudIndexer.generate_windows_indexer_file_name(
        platform=IndalekoICloudIndexer.icloud_platform,
        user_id = indexer.get_user_id(),
        service = 'indexer',
        timestamp=timestamp,
        suffix='jsonl'
    )
    parser = argparse.ArgumentParser(parents=[pre_parser])
    parser.add_argument('--output',
                        type=str,
                        default=output_file_name,
                        help='Name and location of where to save the fetched metadata')
    parser.add_argument('--datadir', '-d',
                        help='Path to dhe data directory',
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
    logging.info('Indaleko iCloud Indexer started.')
    logging.info('Output file: %s', output_file)
    logging.info('Indexing: %s', args.path)
    logging.info(args)
    data = indexer.index(recursive= (not args.norecurse))
    indexer.write_data_to_file(data, output_file)
    for count_type, count_value in indexer.get_counts().items():
        logging.info('Count %s: %s', count_type, count_value)
    logging.info('Indaleko iCloud Indexer finished.')

if __name__ == '__main__':
    main()
