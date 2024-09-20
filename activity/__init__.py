'''initializtion logic for the activity context system'''

import os
import importlib
import sys

from icecream import ic

from .provider_base import ProviderBase

project_root = os.environ.get('INDALEKO_ROOT')

if project_root is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


def initialize_module():
    '''initialize the module'''

__version__ = '0.1.0'

def discover_plugins():
    plugins = {}
    plugin_dir = os.path.dirname(__file__)

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
discovered_plugins = discover_plugins()

# Make discovered plugins available when importing the package
globals().update(discovered_plugins)

__all__ = list(discovered_plugins.keys())

# You could also provide a function to get all discovered plugins
def get_all_plugins():
    return discovered_plugins
