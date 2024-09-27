'''
This module defines the data model for the WiFi based location
activity data provider.

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

import os
import sys

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


class KnownSemanticAttributes:
    '''
    This class dynamically constructs definitions of the known semantic
    attributes from each of the provider types.  In this way, we can distribute
    the definition process, yet end up with a unified list.
    '''
    _initialized = False
    _attributes_by_provider_type = {}
    _attributes_by_uuid = {}

    @classmethod
    def _initialize(cls):
        '''Dynamically construct the list of known activity data provider
        semantic attributes'''
        if cls._initialized:
            return
        cls._initialized = True
        import activity.providers.collaboration.semantic_attributes as collaboration
        import activity.providers.location.semantic_attributes as location
        import activity.providers.network.semantic_attributes as network
        import activity.providers.storage.semantic_attributes as storage
        for provider in [collaboration, location, network, storage]:
            for label, value in provider.__dict__.items():
                if label.startswith('ADP_'):
                    full_label = 'ACTIVITY_DATA_PROVIDER' + label[3:]
                    assert not hasattr(cls, full_label), f"Duplicate definition of {full_label}"
                    setattr(cls, full_label, value)
                    provider_type = label.rsplit('_', maxsplit=2)[-2]
                    if provider_type not in cls._attributes_by_provider_type:
                        cls._attributes_by_provider_type[provider_type] = {}
                    cls._attributes_by_provider_type[provider_type][full_label] = value
                    cls._attributes_by_uuid[value] = full_label

    @staticmethod
    def get_attribute_by_uuid(uuid_value):
        '''Get the attribute by the UUID'''
        return KnownSemanticAttributes._attributes_by_uuid.get(uuid_value)

KnownSemanticAttributes._initialize()

def main():
    '''Main function for the module'''
    known_semantic_attributes = KnownSemanticAttributes()
    for attr in dir(known_semantic_attributes):
        if attr.startswith('ACTIVITY_DATA_PROVIDER'):
            ic(attr)

if __name__ == '__main__':
    main()
