'''
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
# import logging
import os
# import configparser
# import secrets
# import string
# import datetime
# import time
# import argparse
import sys
# from arango import ArangoClient
# import requests

from icecream import ic
from typing import Any

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db import IndalekoDBConfig
# from constants import IndalekoConstants
from utils import IndalekoSingleton  # IndalekoDocker, IndalekoLogging
# from utils.data_validation import validate_ip_address, validate_hostname
# from utils.misc.directory_management import indaleko_default_log_dir, indaleko_default_config_dir
# import utils.misc.file_name_management
# pylint: enable=wrong-import-position


class IndalekoDBInfo(IndalekoSingleton):
    '''
    Class used to obtain information about the database
    '''

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        '''
        Constructor
        '''
        if self._initialized:
            return
        db_config_file = kwargs.get('db_config_file', IndalekoDBConfig.default_db_config_file)
        no_new_config = kwargs.get('no_new_config', True)
        start = kwargs.get('start', True)
        ic(db_config_file, no_new_config, start)
        self.db_config = IndalekoDBConfig(
            config_file=db_config_file,
            no_new_config=no_new_config,
            start=start
        )
        self._initialized = True

    def get_collections(self) -> list[str]:
        '''
        Get the collections from the database
        '''
        collections = self.db_config.db.collections()
        return [
            collection['name']
            for collection in collections if not collection['name'].startswith('_')
        ]

    def get_collection_info(self, collection_name: str) -> dict[str, Any]:
        '''
        Get information about a collection
        '''
        return self.db_config.db.collection(collection_name).properties()


def main():
    '''Main entry point for grabbing the database information.'''
    db_info = IndalekoDBInfo()
    ic(db_info.db_config)
    ic(db_info.db_config.db)
    ic(type(db_info.db_config.db))
    collections = db_info.get_collections()
    #  ic(db_info.get_collection_info(collections[0]))
    collection_data = None
    for collection in collections:
        collection_data = db_info.db_config.db.collection(collection)
        stats = collection_data.statistics()
        count = collection_data.count()
        properties = collection_data.properties()
        checksum = collection_data.checksum()
        revision = collection_data.revision()
        ic(collection, stats, count, properties, checksum, revision)
    ic(dir(collection_data))


if __name__ == '__main__':
    main()
