'''
IndalecoSingleton.py - This module is used to create singletones in Indaleko.


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
"""

'''

class IndalekoSingleton:
    '''This class is used to manage Indaleko singletons.'''
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        '''Create an instance of the IndalekoSingleton class.'''
        if cls._instance is None:
            try:
                cls._instance = super(IndalekoSingleton, cls).__new__(cls, *args, **kwargs)
            except TypeError: # in case base class doesn't take any arguments
                cls._instance = super(IndalekoSingleton, cls).__new__(cls)
        return cls._instance

def main():
    '''Test the IndalekoSingleton class.'''
    instance1 = IndalekoSingleton()
    instance2 = IndalekoSingleton()
    assert instance1 == instance2, 'IndalekoSingleton is not a singleton.'
    print('IndalekoSingleton is a singleton.')

if __name__ == '__main__':
    main()
