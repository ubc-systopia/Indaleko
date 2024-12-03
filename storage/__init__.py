'''
Init functionality for the storage data providers.

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
import importlib
import platform
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
from storage.collectors.base import IndalekoIndexer

'''
match platform.system():
    case 'Linux':
        raise NotImplementedError('Linux is not supported yet')
    case 'Darwin':
        raise NotImplementedError('Linux is not supported yet')
    case 'Windows':
        raise NotImplementedError('Windows is not supported yet')
    case _:
        raise NotImplementedError('Unsupported platform')
'''
# pylint: enable=wrong-import-position

__version__ = '0.1.0'

# Discover and load all plugins
#discovered_plugins = discover_plugins()
#ic(discovered_plugins)

# Make discovered plugins available when importing the package
# globals().update(discovered_plugins)

__all__ = [
    'IndalekoIndexer',
]


# You could also provide a function to get all discovered plugins
#def get_all_plugins():
#    return discovered_plugins

#print(discover_providers())
