"""
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
"""

import argparse
from datetime import datetime, timezone
import keyring
import logging
import os
import sys
import uuid

from getpass import getpass
from icecream import ic
from typing import Union
from pyicloud import PyiCloudService

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db import IndalekoServiceManager
from utils.misc.file_name_management import generate_file_name
from storage.collectors.base import BaseStorageCollector
from storage.collectors.cloud.cloud_base import BaseCloudStorageCollector
from storage.collectors.data_model import IndalekoStorageCollectorDataModel

# pylint: enable=wrong-import-position


class IndalekoICloudStorageCollector(BaseCloudStorageCollector):

    icloud_platform = "iCloud"
    icloud_collector_name = "collector"

    indaleko_icloud_collector_uuid = "cf8694ff-6cfe-4801-9842-4315fc7a02e6"
    indaleko_icloud_collector_service_name = "iCloud Collector"
    indaleko_icloud_collector_service_description = (
        "This service indexes the iCloud folder of the user."
    )
    indaleko_icloud_collector_service_version = "1.0"
    indaleko_icloud_collector_service_type_identifier = (
        IndalekoServiceManager.service_type_storage_collector
    )

    icloud_root_folder = {
        "ObjectIdentifier": "d0dac621-4de3-44df-a2c9-49841b86b508",
        "name": "icloud_root_dir",
        "path_display": "root",
        "size": 0,
        "modified": datetime.now(timezone.utc),
        "date_changed": datetime.now(timezone.utc),
        "created": datetime.now(timezone.utc),
        "last_opened": datetime.now(timezone.utc),
    }

    indaleko_icloud_local_collector_service = {
        "service_name": indaleko_icloud_collector_service_name,
        "service_description": indaleko_icloud_collector_service_description,
        "service_version": indaleko_icloud_collector_service_version,
        "service_type": indaleko_icloud_collector_service_type_identifier,
        "service_identifier": indaleko_icloud_collector_uuid,
    }

    collector_data = IndalekoStorageCollectorDataModel(
        PlatformName=icloud_platform,
        ServiceFileName=icloud_collector_name,
        ServiceUUID=uuid.UUID(indaleko_icloud_collector_uuid),
        ServiceVersion=indaleko_icloud_collector_service_version,
        ServiceDescription=indaleko_icloud_collector_service_description,
    )

    def __init__(self, **kwargs):
        # self.auth_logger = self.setup_logging()
        self.service = None
        self.icloud_credentials = None
        # invocations without this are probing for basic info
        # and don't need to authenticate yet.
        if "platform" not in kwargs:
            kwargs["platform"] = IndalekoICloudStorageCollector.icloud_platform
        if "collector_data" not in kwargs:
            kwargs["collector_data"] = IndalekoICloudStorageCollector.collector_data
        super().__init__(
            **kwargs,
            collector_name=IndalekoICloudStorageCollector.icloud_collector_name,
            **IndalekoICloudStorageCollector.indaleko_icloud_local_collector_service,
        )
        """
        self.icloud_credentials = IndalekoICloudStorageCollector.load_icloud_credentials()
        if self.icloud_credentials is None:
            logging.debug('No iCloud credentials found, reconstructing.')
            # self.query_user_for_credentials()
        if self.icloud_credentials is not None:
            logging.info(f"Using iCloud credentials: {self.icloud_credentials}")
            try:
                self.service = PyiCloudService(
                    self.icloud_credentials['username'],
                    self.icloud_credentials['password']
                )
            except Exception as e:
                logging.error(f"Error initializing iCloud service: {e}")
        """

    @staticmethod
    def get_user_id(config_data: dict[str, str]) -> str:
        """This method returns the user id."""
        ic(config_data)
        usernames = IndalekoICloudStorageCollector.get_stored_usernames()
        if usernames:
            ic(usernames)
            print("Stored usernames:")
            for stored_username in usernames:
                print(f"- {stored_username}")
        user_id = input(
            "Enter your iCloud username (or press Enter to select from the list above): "
        ).strip()
        if not user_id and usernames:
            if len(usernames) == 1:
                user_id = usernames[0]
            else:
                user_id = input(
                    "Please select a username from the list above: "
                ).strip()
        return user_id

    @staticmethod
    def load_icloud_credentials() -> None:
        logging.info("Loading iCloud credentials.")
        username = keyring.get_password("iCloud", "username")
        password = keyring.get_password("iCloud", "password")
        icloud_credentials = None
        if username and password:
            icloud_credentials = {"username": username, "password": password}
            logging.info(f"Loaded credentials for username: {username}")
        return icloud_credentials

    @staticmethod
    def store_icloud_credentials() -> "IndalekoICloudStorageCollector":
        """This method stores the credentials."""
        user_id = IndalekoICloudStorageCollector.get_user_id()
        password = getpass("Enter your iCloud password: ")
        IndalekoICloudStorageCollector._store_credentials(user_id, password)
        IndalekoICloudStorageCollector.update_stored_usernames(user_id)
        return

    @staticmethod
    def set_icloud_credentials(credentials: dict) -> "IndalekoICloudStorageCollector":
        """This method sets the credentials."""
        user_id = credentials.get("username")
        password = credentials.get("password")
        IndalekoICloudStorageCollector._store_credentials(user_id, password)
        IndalekoICloudStorageCollector.update_stored_usernames(user_id)
        return

    @staticmethod
    def query_user_for_credentials() -> "IndalekoICloudStorageCollector":
        """This method queries the user for credentials."""
        user_id = IndalekoICloudStorageCollector.get_user_id({})
        password = keyring.get_password("iCloud", user_id)
        if not password:
            password = getpass("Enter your iCloud password: ")
            IndalekoICloudStorageCollector._store_credentials(user_id, password)
            IndalekoICloudStorageCollector.update_stored_usernames(user_id)
        return user_id, password

    @staticmethod
    def get_icloud_credentials(refresh: bool = False):
        """This method retrieves the iCloud credentials."""
        return IndalekoICloudStorageCollector.query_user_for_credentials()

    @staticmethod
    def _store_credentials(username, password):
        keyring.set_password("iCloud", username, password)
        # self.auth_logger.debug(f"Stored credentials for {username}")

    @staticmethod
    def get_stored_usernames():
        usernames = keyring.get_password("iCloud", "usernames")
        if usernames:
            return [x for x in usernames.split(",") if len(x) > 3]
        return []

    @staticmethod
    def update_stored_usernames(username):
        usernames = IndalekoICloudStorageCollector.get_stored_usernames()
        if username not in usernames:
            usernames.append(username)
            keyring.set_password("iCloud", "usernames", ",".join(usernames))
        return usernames

    def list_all_entries(self, service_name):
        """This method lists all the entries."""
        # self.auth_logger.debug(f"Listing all entries for service '{service_name}':")
        # stored_usernames = self.get_stored_usernames()
        # for stored_username in stored_usernames:
        #     self.auth_logger.debug(f"Username: {stored_username}")

    @staticmethod
    def authenticate(
        user_id: str, password: str, prompt: bool = False
    ) -> Union[PyiCloudService, None]:
        """
        This method authenticates the user.

        Inputs:
            user_id: the user id to authenticate
            password: the password to use
            prompt: whether to prompt the user for 2FA code

        Returns:
            PyiCloudService: the authenticated service object
            None: if authentication fails
        """
        api = PyiCloudService(user_id, password)
        if not api:
            logging.error("Failed to authenticate with iCloud")
            return None
        if api.is_trusted_session:
            logging.info("Trusted session established")
            return api
        if api.requires_2fa:
            if not prompt:
                logging.error("Two-factor authentication is required for this account.")
                ic("2FA required in a non-interactive session, failed")
                return None
            code = input(
                "Enter the code you received on one of your approved devices: "
            )
            result = api.validate_2fa_code(code)
            if not result:
                logging.error("Failed to verify security code")
                ic("The security code was not accepted.")
                return None
            if not api.is_trusted_session:
                api.trust_session()
        return api

    @staticmethod
    def generate_icloud_collector_file_name(**kwargs):
        """This method generates the name of the file that wiil contain the metadata
        of the files in the iCloud folder."""
        assert "user_id" in kwargs, "No user_id found in kwargs"
        return generate_file_name(**kwargs)

    @staticmethod
    def convert_to_serializable(data):
        """Converts the data into serializable form"""
        if isinstance(data, (int, float, str, bool, type(None))):
            return data
        elif isinstance(data, list):
            return [
                IndalekoICloudStorageCollector.convert_to_serializable(item)
                for item in data
            ]
        elif isinstance(data, dict):
            return {
                key: IndalekoICloudStorageCollector.convert_to_serializable(value)
                for key, value in data.items()
            }
        else:
            if hasattr(data, "__dict__"):
                return IndalekoICloudStorageCollector.convert_to_serializable(
                    data.__dict__
                )
            return None

    def collect_metadata(self, item, item_path):
        def to_utc_iso(dt):
            # Convert to UTC and format with 'Z' suffix
            if dt is not None:
                return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            else:
                # Return the default UTC time with 'Z' suffix
                return (
                    datetime(1970, 1, 1, 0, 0, tzinfo=timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z")
                )

        metadata = {
            "name": item.name,
            "path_display": IndalekoICloudStorageCollector.icloud_root_folder[
                "path_display"
            ]
            + "/"
            + item_path,
            "size": getattr(item, "size", 0) or 0,  # Default to 0 if size is None or 0
            "date_created": to_utc_iso(getattr(item, "date_created", None)),
            "date_modified": to_utc_iso(getattr(item, "date_modified", None)),
            "last_opened": to_utc_iso(getattr(item, "date_last_opened", None)),
            "date_changed": to_utc_iso(getattr(item, "date_changed", None)),
            "ObjectIdentifier": str(
                uuid.uuid4()
            ),  # Generate and add a UUID for each file
            "drivewsid": getattr(item, "drivewsid", "Unknown"),
            "docwsid": getattr(item, "docwsid", "Unknown"),
            "zone": getattr(item, "zone", "Unknown"),
            "extension": getattr(item, "extension", "Unknown"),
            "parentId": getattr(item, "parentId", "Unknown"),
            "item_id": getattr(item, "item_id", "Unknown"),
            "etag": getattr(item, "etag", "Unknown"),
            "type": getattr(item, "type", "Unknown"),
        }
        return metadata

    def index_directory(self, folder, path=""):
        """Recursively get the contents of a folder and write metadata to a JSON Lines file."""
        metadata_list = []
        try:
            logging.info(f"Entering folder: {path or '/'}")
            for item_name in folder.dir():
                item = folder[item_name]
                item_path = f"{path}/{item_name}"

                if item.type == "folder":
                    # Recursively get the contents of this folder
                    metadata = self.collect_metadata(item, item_path)
                    metadata_list.append(metadata)
                    logging.debug(f"Indexed Item (file): {metadata}")
                    # continue indexing into file
                    self.index_directory(item, item_path)
                else:
                    metadata = self.collect_metadata(item, item_path)
                    metadata_list.append(metadata)
                    logging.debug(f"Indexed Item: {metadata}")
        except Exception as e:
            logging.error(f"Failed to process folder: {path}, Error: {e}")
        return metadata_list

    def collect(self, recursive=True):
        """This method collects the data from the iCloud folder."""
        # need to get the user name, which isn't captured anywhere easy for us
        # to get.
        pre_parser = (
            IndalekoICloudStorageCollector.icloud_collector_mixin.get_pre_parser()
        )
        pre_args, _ = pre_parser.parse_known_args()
        # try to get the cached password.  If this fails, it should return None
        password = keyring.get_password("iCloud", pre_args.userid)
        # this should deal with authentication.  This prompt option may not be ideal.
        api = self.authenticate(pre_args.userid, password, prompt=True)
        files = api.drive.root

        if recursive:
            self.data = self.index_directory(files)
        else:
            self.data = []
            for item_name in files.dir():
                item = files[item_name]
                metadata = self.collect_metadata(item, item_name)
                self.data.append(metadata)
                logging.debug(f"Indexed Item (non-recursive): {metadata}")
        return self.data

    @staticmethod
    def find_collector_files(
        search_dir: str,
        prefix: str = BaseStorageCollector.default_file_prefix,
        suffix: str = BaseStorageCollector.default_file_suffix,
    ) -> list:
        """This function finds the files to ingest:
        search_dir: path to the search directory
        prefix: prefix of the file to ingest
        suffix: suffix of the file to ingest (default is .json)
        """
        prospects = BaseStorageCollector.find_collector_files(
            search_dir, prefix, suffix
        )
        return [
            f for f in prospects if IndalekoICloudStorageCollector.icloud_platform in f
        ]

    class icloud_collector_mixin(BaseCloudStorageCollector.cloud_collector_mixin):
        """This is the mixin for the iCloud collector"""

        @staticmethod
        def get_pre_parser() -> Union[argparse.ArgumentParser, None]:
            """This method returns the pre-parser for the cloud storage collector."""
            parser = BaseCloudStorageCollector.cloud_collector_mixin.get_pre_parser()
            known_users = [
                x
                for x in IndalekoICloudStorageCollector.get_stored_usernames()
                if len(x) > 3
            ]
            default_user = None
            if len(known_users) > 0:
                default_user = known_users[0]
            parser.add_argument(
                "--userid",
                type=str,
                default=default_user,
                help=f'The iCloud username (known users: {",".join(known_users)},'
                f"default: {default_user})",
            )
            return parser

        @staticmethod
        def generate_output_file_name(keys: dict[str, str]) -> str:
            """This method is used to generate an output file name.  Note
            that it assumes the keys are in the desired format. Don't just
            pass in configuration data."""
            if not keys.get("UserId"):
                pre_parser = (
                    IndalekoICloudStorageCollector.icloud_collector_mixin.get_pre_parser()
                )
                pre_args, _ = pre_parser.parse_known_args()
                if pre_args.userid:
                    keys["UserId"] = pre_args.userid
            if not keys.get("UserId"):
                collector = IndalekoICloudStorageCollector(
                    config_dir=keys["ConfigDirectory"]
                )
                keys["UserId"] = collector.get_user_id(keys)
            if not keys.get("UserId"):
                keys["UserId"] = "unknown@unknown.com"
            return BaseCloudStorageCollector.cloud_collector_mixin.generate_output_file_name(
                keys
            )

    cli_handler_mixin = icloud_collector_mixin


def main() -> None:
    """iCloud collector main"""
    BaseCloudStorageCollector.cloud_collector_runner(
        IndalekoICloudStorageCollector,
    )


if __name__ == "__main__":
    main()
