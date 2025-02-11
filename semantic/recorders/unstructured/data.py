'''
This module defines known semantic attributes for collaboration activity data
providers.

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
'''initializtion logic for the activity context system'''

import os
import sys

from icecream import ic

init_path = os.path.dirname(os.path.abspath(__file__))

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from semantic.characteristics import SemanticDataCharacteristics
import semantic.collectors.semantic_attributes as semantic_attributes
# pylint: enable=wrong-import-position

class IndalekoUnstructuredData:
    '''
    This is a class object for managing unstructured data in the Indaleko system.
    '''

    def __init__(self, **kwargs):
        '''Initialize a new instance of the IndalekoUnstructuredData class object.'''
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.semantic_characteristics = SemanticDataCharacteristics()
        # TODO: add semantic values?
        ic('IndalekoUnstructuredData initialized.')

    def get_semantic_characteristics(self):
        '''Get the semantic characteristics for the unstructured data.'''
        return self.semantic_characteristics
    

def main():
    attributes = [attr for attr, value in semantic_attributes.__dict__.items() if not attr.startswith('__')]
    ic(attributes)

if __name__ == '__main__':
    main()
