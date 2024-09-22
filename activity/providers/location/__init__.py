'''
Init functionality for the location activity data providers.

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
import importlib
import os
import sys

from typing import Dict, Type

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

from activity.providers.location.location_base import LocationProvider

def discover_provider_names():
    '''Discover names of potential provider modules.'''
    current_dir = os.path.dirname(__file__)
    provider_names = []
    for filename in os.listdir(current_dir):
        if filename.endswith('.py') and not filename.endswith('_base.py') \
            and filename != '__init__.py' \
            and filename != '__main__.py':
            provider_names.append(filename[:-3])
    return provider_names

class LazyProviderLoader:
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.provider = None
        self.spec = importlib.util.find_spec(f'.{provider_name}', package=__name__)
        self.module = None
        self.provider_class = None

    def __getattr__(self, name):
        if self.provider is None:
            self._load_provider()
        return getattr(self.provider, name)

    def _load_provider(self):
        if self.module is None:
            self.module = importlib.util.module_from_spec(self.spec)
            self.spec.loader.exec_module(self.module)
            for attr_name in dir(self.module):
                attr = getattr(self.module, attr_name)
                if isinstance(attr, type) and issubclass(attr, LocationProvider) and attr != LocationProvider:
                    self.provider_class = attr
                    break
        if self.provider_class is not None:
            self.provider = self.provider_class()

    def get_class_name(self):
        if self.provider_class is None:
            self._load_provider()
        return self.provider_class.__name__

# Discover providers
provider_names = discover_provider_names()

providers = {name: LazyProviderLoader(name) for name in provider_names}

# Create a dictionary to map class names to their respective LazyProviderLoader
# instances

class_name_to_loader = {}
for name, loader in providers.items():
    loader._load_provider()
    if loader.provider_class is not None:
        class_name_to_loader[name] = loader.get_class_name()

# class_name_to_loader = {loader.get_class_name(): loader for loader in providers.values() if loader.provider_class is not None}

# Define a custom __getattr__ function for the module
def __getattr__(name):
    if name in class_name_to_loader:
        return class_name_to_loader[name].provider_class
    raise AttributeError(f"module {__name__} has no attribute {name}")

# Define what should be available when importing from this package
__all__ = ['LocationProvider']
for key, value in class_name_to_loader.items():
    assert value not in __all__, \
        f"Duplicate class name {value} found in provider {key}"
    __all__.append(value)

# Optionally, provide a function to get all providers
def get_providers():
    '''Return all providers, trigger import as needed'''
    return {
        loader.get_class_name(): loader.provider_class for loader in providers.values()
    }
