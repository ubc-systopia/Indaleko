'''
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
'''

import importlib
import os
import sys

from typing import Union, Any, Dict

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


class KnownStorageAttributes:
    '''
    This class defines known semantic attributes for the storage providers.
    '''
    _initialized = False
    _attributes_by_provider_type = {}
    _attributes_by_uuid = {}
    _short_prefix = 'SP_'
    full_prefix = 'STORAGE_ATTRIBUTES'

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

    @classmethod
    def _initialize(cls: 'KnownStorageAttributes') -> None:
        '''
        Dynamically construct the list of known storage provider
        semantic attributes.
        '''
        if cls._initialized:
            return
        cls._initialized = True
        cls._attributes_by_provider_type['base'] = {}

        # add the attributes in the base class
        for label, value in cls.__dict__.items():
            if not label.startswith(KnownStorageAttributes.full_prefix):
                continue  # skip anything that doesn't start with the long prefix
            cls._attributes_by_uuid[value] = label
            cls._attributes_by_provider_type['base'][label] = value

        def add_types(obj: object, table: dict):
            for label, value in table.items():
                full_label = label
                if label.startswith(KnownStorageAttributes._short_prefix):
                    full_label = KnownStorageAttributes.full_prefix + label[3:]
                elif not label.startswith(KnownStorageAttributes.full_prefix):
                    continue  # skip anything that doesn't start with the long prefix
                assert not hasattr(obj, full_label), f"Duplicate definition of {full_label}"
                setattr(obj, full_label, value)
                provider_type = label.rsplit('_', maxsplit=2)[-2]
                if provider_type not in cls._attributes_by_provider_type:
                    cls._attributes_by_provider_type[provider_type] = {}
                cls._attributes_by_provider_type[provider_type][full_label] = value
                cls._attributes_by_uuid[value] = full_label

        # load the modules and add the attributes
        for name in cls._modules_to_load.values():
            module = KnownStorageAttributes.safe_import(name)
            add_types(cls, module.__dict__)

    @staticmethod
    def safe_import(name: str) -> Union[Dict[str, Any], None]:
        '''Given a module name, load it and then extract the important data from it'''
        module = None
        try:
            module = importlib.import_module(name)
        except ImportError as e:
            ic(f'Import module {name} failed {e}')
        return module

    def __init__(self):
        if not self._initialized:
            self._initialize()
        ic(dir(self))

    @staticmethod
    def get_attribute_by_uuid(uuid_value):
        '''Get the attribute by the UUID'''
        return KnownStorageAttributes._attributes_by_uuid.get(uuid_value)


KnownStorageAttributes._initialize()


def main():
    '''Main function for the module'''
    ic('Starting')
    ic(dir(KnownStorageAttributes))


if __name__ == '__main__':
    main()
