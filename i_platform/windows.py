"""
This class defines constants and functions that are specific to Windows.

Indaleko Windows
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
"""

import argparse

class IndalekoWindows:
    '''This contains Windows specific definitions used in Indaleko'''

    FILE_ATTRIBUTES = {
        'FILE_ATTRIBUTE_READONLY' : 0x00000001,
        'FILE_ATTRIBUTE_HIDDEN' : 0x00000002,
        'FILE_ATTRIBUTE_SYSTEM' : 0x00000004,
        'FILE_ATTRIBUTE_DIRECTORY' : 0x00000010,
        'FILE_ATTRIBUTE_ARCHIVE' : 0x00000020,
        'FILE_ATTRIBUTE_DEVICE' : 0x00000040,
        'FILE_ATTRIBUTE_NORMAL' : 0x00000080,
        'FILE_ATTRIBUTE_TEMPORARY' : 0x00000100,
        'FILE_ATTRIBUTE_SPARSE_FILE' : 0x00000200,
        'FILE_ATTRIBUTE_REPARSE_POINT' : 0x00000400,
        'FILE_ATTRIBUTE_COMPRESSED' : 0x00000800,
        'FILE_ATTRIBUTE_OFFLINE' : 0x00001000,
        'FILE_ATTRIBUTE_NOT_CONTENT_INDEXED' : 0x00002000,
        'FILE_ATTRIBUTE_ENCRYPTED' : 0x00004000,
        'FILE_ATTRIBUTE_INTEGRITY_STREAM' : 0x00008000,
        'FILE_ATTRIBUTE_VIRTUAL' : 0x00010000,
        'FILE_ATTRIBUTE_NO_SCRUB_DATA' : 0x00020000,
        'FILE_ATTRIBUTE_EA' : 0x00040000,
        'FILE_ATTRIBUTE_PINNED' : 0x00080000,
        'FILE_ATTRIBUTE_UNPINNED' : 0x00100000,
        'FILE_ATTRIBUTE_RECALL_ON_OPEN' : 0x00040000,
        'FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS' : 0x00400000,
        'FILE_ATTRIBUTE_STRICTLY_SEQUENTIAL' : 0x20000000,
        'FILE_ATTRIBUTE_OPEN_REPARSE_POINT' : 0x00200000,
        'FILE_ATTRIBUTE_OPEN_NO_RECALL' : 0x00100000,
        'FILE_ATTRIBUTE_FIRST_PIPE_INSTANCE' : 0x00080000,
    }

    @staticmethod
    def map_file_attributes(attributes : int):
        '''
        Given an integer representing file attributes on Windows,
        return a string representation of the attributes.
        '''
        file_attributes = []
        if 0 == attributes:
            file_attributes = ['FILE_ATTRIBUTE_NORMAL']
        for attr, value in IndalekoWindows.FILE_ATTRIBUTES.items():
            if attributes & value == value:
                file_attributes.append(attr)
        return ' | '.join(file_attributes)

def main():
    '''This is the test code for the IndalekoWindows class.'''
    parser = argparse.ArgumentParser(description='Indaleko Windows test logic')
    parser.add_argument('--attr',
                        '-a',
                        default = 0xFFFFFFFF,
                        type = int,
                        help = 'file attribute bits to test')
    args = parser.parse_args()
    if args.attr == 0xFFFFFFFF:
        print('Testing all attributes')
        for attr, value in IndalekoWindows.FILE_ATTRIBUTES.items():
            print(f'{attr} = {value}')
            print(f'{attr} = {value}')
    else:
        print(f'{args.attr} = {IndalekoWindows.map_file_attributes(args.attr)}')

if __name__ == '__main__':
    main()
