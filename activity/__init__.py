'''initializtion logic for the activity context system'''

import os
import importlib
import sys

from icecream import ic

from .provider_base import ProviderBase
from .provider_characteristics import ProviderCharacteristics

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

__all__ = ['ProviderBase', 'discover']

