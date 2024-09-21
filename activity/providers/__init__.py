'''
Init functionality for the activity data providers.

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
import sys

from icecream import ic

init_path = os.path.dirname(os.path.abspath(__file__))

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

__version__ = '0.1.0'

def discover_providers():
    '''Discover providers'''
    categories = []
    file_parent = os.path.dirname(__file__)
    for x in os.listdir(file_parent):
        if x == '__pycache__':
            continue
        if os.path.isdir(os.path.join(file_parent, x)):
            categories.append(x)
    ic(categories)

def discover_plugins():
    plugins = {}
    plugin_dir = os.path.dirname(__file__)
    ic(plugin_dir)

    for filename in os.listdir(plugin_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = filename[:-3]  # Remove .py extension
            try:
                module = importlib.import_module(f'.{module_name}', package=__name__)
                if hasattr(module, 'register_plugin'):
                    plugins[module_name] = module.register_plugin()
            except ImportError as e:
                print(f"Error importing {module_name}: {e}")

    return plugins

# Discover and load all plugins
#discovered_plugins = discover_plugins()
#ic(discovered_plugins)

# Make discovered plugins available when importing the package
# globals().update(discovered_plugins)

__all__ = [] # list(discovered_plugins.keys())

# You could also provide a function to get all discovered plugins
#def get_all_plugins():
#    return discovered_plugins

print(discover_providers())
