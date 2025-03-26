"""
This is a utility class that can be used for picking files from the ArangoDB database
for further processing.

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
import os
import sys

from typing import Callable

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
# from data_models.i_object import IndalekoObjectDataModel
from db.db_config import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections
from db.i_collections import IndalekoCollections
from storage.i_object import IndalekoObject
from storage.known_attributes import StorageSemanticAttributes
import random

# pylint: enable=wrong-import-position


class IndalekoFilePicker:

    def __init__(self, db_config: IndalekoDBConfig = IndalekoDBConfig()):
        self.db_config = db_config
        self.object_collection = IndalekoCollections.get_collection(
                IndalekoDBCollections.Indaleko_Object_Collection
        )

    def pick_random_files(
        self,
        process_func: Callable[['IndalekoObject'], None] = None,
        count: int = 1
    ) -> None:
        """
        This method will pick random files from the ArangoDB (using the Objects collection)
        and then process them using the provided function.
        """
        # Get the total number of documents in the collection
        total_docs = self.object_collection.collection.count()

        # Generate random offsets
        random_offsets = random.sample(range(total_docs), count)

        # Retrieve documents at the random offsets
        files = [IndalekoObject(**self.object_collection.collection.random()) for _ in random_offsets]
        for file in files:
            if process_func is not None:
                process_func(file)

    def pick_all_files(
            self,
            process_func: Callable[['IndalekoObject'], None],
    ) -> None:
        """
        This method will pick all files from the ArangoDB (using the Objects collection)
        and then process them using the provided function.
        """
        raise NotImplementedError("Not yet implemented")


def check_mime_type(file: IndalekoObject) -> None:
    """Check the mime type of the file"""
    doc = file.serialize()
    semantic_attributes = doc.get('SemanticAttributes')
    ic(type(semantic_attributes))
    for attribute in semantic_attributes:
        identifier = attribute.get('Identifier')
        value = attribute.get('Value')
        match(identifier):
            case StorageSemanticAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX:
                ic('MIMETYPE from SUFFIX: ', value)
            case StorageSemanticAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_STORAGE_PROVIDER:
                ic('MIMETYPE from PROVIDER: ', value)
            case StorageSemanticAttributes.STORAGE_ATTRIBUTES_MIMETYPE_FROM_CONTENT:
                ic('MIMETYPE from CONTENT: ', value)
            case _:
                pass


def main():
    """Test code for IndalekoStorageRecorder.py"""
    parser = argparse.ArgumentParser(description="Test code for IndalekoStorageRecorder.py")
    args = parser.parse_args()
    ic(args)
    IndalekoFilePicker().pick_random_files(process_func=check_mime_type, count=1)


if __name__ == "__main__":
    main()
