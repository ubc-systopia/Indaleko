'''
This module defines the SemanticCharacteristics class.  This class is used to
describe the characteristics of a data provider.  This is intended to be used to
help the system understand how to interact with the data provider.

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

import os
import sys
import uuid

from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

class SemanticDataCharacteristics:
    '''
    Define the semantic data characteristics for our semantic metadata extractors.
    '''
    SEMANTIC_DATA_CONTENTS = '31764240-1397-4cd2-9c74-b332a0ff1b72'
    SEMANTIC_DATA_CHECKSUMS = '8f4654e9-1a36-45ef-95bb-4e4600f2f46a'

    _characteristic_prefix = 'SEMANTIC_DATA_'

    def __init__(self):
        '''Initialize the semantic extractor characteristics.'''
        self.uuid_to_label = {}
        for label, value in SemanticDataCharacteristics.__dict__.items():
            if label.startswith(SemanticDataCharacteristics._characteristic_prefix):
                setattr(self, label+'_UUID', uuid.UUID(value))
                self.uuid_to_label[value] = label

    @staticmethod
    def get_semantic_chracteristics() -> dict:
        '''Get the semantic characteristics for the system.'''
        return {label: value for label, value in SemanticDataCharacteristics.__dict__.items() if label.startswith(SemanticDataCharacteristics._characteristic_prefix)}

    @staticmethod
    def get_semantic_characteristic_label(uuid_value: uuid.UUID) -> str:
        '''Get the label for a semantic characteristic.'''
        return SemanticDataCharacteristics().uuid_to_label.get(uuid_value, None)
    
def main():
    '''Main entry point for this module.'''
    ic('SemanticDataCharacteristics module test.')
    for label, value in SemanticDataCharacteristics.get_semantic_chracteristics().items():
        ic(label, value)
        ic(SemanticDataCharacteristics.get_semantic_characteristic_label(value))

if __name__ == '__main__':
    main()
