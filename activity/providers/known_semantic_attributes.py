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

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
import activity.providers.collaboration.semantic_attributes as collaboration
import activity.providers.location.semantic_attributes as location
import activity.providers.network.semantic_attributes as network
import activity.providers.storage.semantic_attributes as storage
# pylint: enable=wrong-import-position

class KnownSemanticAttributes:
    '''
    This class dynamically constructs definitions of the known semantic
    attributes from each of the provider types.  In this way, we can distribute
    the definition process, yet end up with a unified list.
    '''

    def __init__(self):
        '''Dynamically construct the list of known activity data provider
        semantic attributes'''
        self.attributes_by_provider_type = {}
        for provider in [collaboration, location, network, storage]:
            provider_name = provider.__name__.rsplit('.', maxsplit=1)[-1]
            self.attributes_by_provider_type[provider_name] = {}
            for label, value in provider.__dict__.items():
                if label.startswith('ADP_'):
                    full_label = 'ACTIVITY_DATA_PROVIDER' + label[3:]
                    assert not hasattr(self, full_label), f"Duplicate definition of {full_label}"
                    setattr(self, full_label, value)
                    self.attributes_by_provider_type[provider_name][full_label] = value

def main():
    '''Main function for the module'''
    known_semantic_attributes = KnownSemanticAttributes()
    print(known_semantic_attributes.__dict__)

if __name__ == '__main__':
    main()
