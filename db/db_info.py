"""
This module collects and returns information about the database.

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

# import logging
import json
import os

# import configparser
# import secrets
# import string
# import datetime
# import time
# import argparse
import sys
import threading
from typing import Any

# from arango import ArangoClient
# import requests
from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from constants import IndalekoConstants
from data_models.db_statistics import IndalekoDBStatisticsDataModel
from db import IndalekoDBConfig
from utils.misc.data_management import encode_binary_data

# pylint: enable=wrong-import-position


class IndalekoDBInfo:
    """
    Class used to obtain information about the database
    """

    __db_info_semantic_attributes = {
        "DATABASE_TYPE": "f73abb61-858a-4949-9868-f1b82181f08d",
        "DATABASE_NAME": "717efa63-f509-4961-9336-b6fa79c1a009",
        "DATABASE_COLLECTION_NAME": "7ee6a696-0a82-4ddb-8db8-d5a7196027c9",
        "DATABASE_COLLECTION_STATISTICS": "ce008afa-356a-4f2d-ba35-ca3330abfea6",
        "DATABASE_COLLECTION_OBJECT_COUNT": "f4fb9859-e132-471c-a34c-d48020e27bd5",
        "DATABASE_COLLECTION_PROPERTIES": "31b2b7ea-a934-4e34-bb66-1f199db79fdc",
        "DATABASE_COLLECTION_REVISION": "f4fb9859-e132-471c-a34c-d48020e27bd5",
    }

    __init_lock = threading.Lock()
    __uuid_to_name = {}

    source_identifier = "0d9f67d2-26d0-4a67-923b-21a334376046"
    source_version = "1.0"
    source_description = "Database Information Gathering Agent"

    @classmethod
    def get_name_from_uuid(cls: "IndalekoDBInfo", uuid: str) -> str:
        """
        Get the name corresponding to a UUID
        """
        if not cls.__uuid_to_name:
            cls.__init_semantic_labels()
        return cls.__uuid_to_name.get(uuid, None)

    @classmethod
    def __init_semantic_labels(cls: "IndalekoDBInfo") -> None:
        """
        Initialize the semantic labels
        """
        with cls.__init_lock:
            if not cls.__uuid_to_name:
                for key, value in cls.__db_info_semantic_attributes.items():
                    setattr(cls, key, value)
                    cls.__uuid_to_name[value] = key

    def __init__(self, **kwargs: dict[str, Any]) -> None:
        """
        Constructor
        """
        self.__init_semantic_labels()
        db_config_file = kwargs.get(
            "db_config_file",
            IndalekoDBConfig.default_db_config_file,
        )
        no_new_config = kwargs.get("no_new_config", True)
        start = kwargs.get("start", True)
        ic(db_config_file, no_new_config, start)
        self.db_config = IndalekoDBConfig(
            config_file=db_config_file,
            no_new_config=no_new_config,
            start=start,
        )

    def get_collections(self) -> list[str]:
        """
        Get the collections from the database
        """
        collections = self.db_config._arangodb.collections()
        return [collection["name"] for collection in collections if not collection["name"].startswith("_")]

    def get_collection_info(self, collection: str) -> list[dict[str, Any]]:
        """Retrieve and return the statistics for the collection."""
        collection_data = self.db_config._arangodb.collection(collection)
        return [
            {
                "Identifier": {
                    "Identifier": IndalekoDBInfo.DATABASE_TYPE,
                    "Version": "1.0",
                },
                "Data": "ArangoDB",
            },
            {
                "Identifier": {
                    "Identifier": IndalekoDBInfo.DATABASE_NAME,
                    "Version": "1.0",
                },
                "Data": IndalekoConstants.project_name,
            },
            {
                "Identifier": {
                    "Identifier": IndalekoDBInfo.DATABASE_COLLECTION_NAME,
                    "Version": "1.0",
                },
                "Data": collection,
            },
            {
                "Identifier": {
                    "Identifier": IndalekoDBInfo.DATABASE_COLLECTION_STATISTICS,
                    "Version": "1.0",
                },
                "Data": collection_data.statistics(),
            },
            {
                "Identifier": {
                    "Identifier": IndalekoDBInfo.DATABASE_COLLECTION_OBJECT_COUNT,
                    "Version": "1.0",
                },
                "Data": collection_data.count(),
            },
            {
                "Identifier": {
                    "Identifier": IndalekoDBInfo.DATABASE_COLLECTION_PROPERTIES,
                    "Version": "1.0",
                },
                "Data": collection_data.properties(),
            },
            {
                "Identifier": {
                    "Identifier": IndalekoDBInfo.DATABASE_COLLECTION_REVISION,
                    "Version": "1.0",
                },
                "Data": collection_data.revision(),
            },
        ]

    def get_db_info_data(self) -> IndalekoDBStatisticsDataModel:
        """Return an initialized data object for the database statistics."""
        collection_names = self.get_collections()
        collection_data = [
            {
                "CollectionName": collection_name,
                "Attributes": self.get_collection_info(collection_name),
            }
            for collection_name in collection_names
        ]
        return IndalekoDBStatisticsDataModel(
            Record={
                "SourceIdentifier": {
                    "Identifier": self.source_identifier,
                    "Version": self.source_version,
                    "Description": self.source_description,
                },
                "Data": encode_binary_data(
                    bytes(json.dumps(collection_data).encode("utf-8")),
                ),
            },
            DataAttributes=[
                {
                    "Identifier": {
                        "Identifier": IndalekoDBInfo.DATABASE_TYPE,
                        "Version": "1.0",
                        "Description": "Database Type and/or Name (MSSQL, ArangoDB, etc.)",
                    },
                    "Data": "ArangoDB",
                },
                {
                    "Identifier": {
                        "Identifier": IndalekoDBInfo.DATABASE_NAME,
                        "Version": "1.0",
                        "Description": "Database Name",
                    },
                    "Data": IndalekoConstants.project_name,
                },
            ],
            CollectionAttributes=[
                {
                    "CollectionName": collection,
                    "Attributes": self.get_collection_info(collection),
                }
                for collection in collection_names
            ],
        )


def main():
    """Main entry point for grabbing the database information."""
    db_info = IndalekoDBInfo()
    db_data = db_info.get_db_info_data()
    ic(len(db_data.CollectionAttributes))
    ic(db_data.serialize())


if __name__ == "__main__":
    main()
