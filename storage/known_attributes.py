"""
This module defines the data model for the WiFi based location
activity data provider.

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

import os
import sys


from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.storage_semantic_attributes import StorageSemanticAttributes

# pylint: enable=wrong-import-position


class KnownStorageAttributes:
    """
    This class defines known semantic attributes for the storage providers.
    """

    _initialized = False
    _attributes_by_provider_type = {}
    _attributes_by_uuid = {}
    _short_prefix = "SP_"
    full_prefix = "STORAGE_ATTRIBUTES"

    _modules_to_load = {
        # empty thus far
    }

    STORAGE_ATTRIBUTES_DEVICE = '3fa47f24-b198-434d-b440-119ec5af4f7d'  # st_dev
    STORAGE_ATTRIBUTES_GID = '64ec8b5a-78ba-4787-ba8d-cb033ec24116'  # st_gid
    STORAGE_ATTRIBUTES_MODE = '1bb62d33-0392-4ffe-af1d-5ebfc32afbb9'  # st_mode
    STORAGE_ATTRIBUTES_NLINK = '06677615-2957-4966-aab9-dde29660c334'  # st_nlink
    STORAGE_ATTRIBUTES_REPARSE_TAG = '7ebf1a92-94f9-40b0-8887-349c24f0e354'  # windows specific - move?
    STORAGE_ATTRIBUTES_UID = '1bd30cfc-9320-427d-bdde-60d9e8aa4400'  # st_uid
    STORAGE_ATTRIBUTES_INODE = '882d75c6-a424-4d8b-a938-c264a281204c'  # st_ino

    STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX = 'f425ae89-fff2-4b93-a90e-0e2fd9220411' #  suffix based MIME type
    STORAGE_ATTRIBUTES_MIME_TYPE = 'bce15d05-d4fd-4d37-933f-ff6b4e5dde9d'  # MIME type from file analysis
    STORAGE_ATTRIBUTES_FILE_SUFFIX = 'd4282ceb-ec50-4bbf-8718-680c67a4d257'  # File suffix
    STORAGE_ATTRIBUTES_LOWERCASE_FILE_NAME = 'c6724410-a717-44a7-b9d3-6b276e250c1d'  # Lowercase file name


    @classmethod
    def _initialize(cls: "KnownStorageAttributes") -> None:
        """
        Dynamically construct the list of known storage provider
        semantic attributes.
        """
        if cls._initialized:
            return
        cls._initialized = True
        cls._attributes_by_provider_type["base"] = {}

        # add the attributes in the class
        #
        for label, value in StorageSemanticAttributes.__members__.items():
            setattr(cls, label, value.value)
            cls._attributes_by_uuid[value.value] = label
            cls._attributes_by_provider_type["base"][label] = value.value

    def __init__(self):
        if not self._initialized:
            self._initialize()

    @staticmethod
    def get_attribute_by_uuid(uuid_value):
        """Get the attribute by the UUID"""
        return KnownStorageAttributes._attributes_by_uuid.get(uuid_value)


KnownStorageAttributes._initialize()


def main():
    """Main function for the module"""
    ic("Starting")
    ic(dir(KnownStorageAttributes))


if __name__ == "__main__":
    main()
