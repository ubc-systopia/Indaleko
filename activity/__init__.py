'''initializtion logic for the activity context system'''

import os
import importlib
import sys

# from icecream import ic

init_path = os.path.dirname(os.path.abspath(__file__))

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.provider_base import ProviderBase
from activity.provider_characteristics import ProviderCharacteristics
from Indaleko import Indaleko
# pylint: enable=wrong-import-position

provider_dir = os.path.join(init_path, 'providers')
providers = [
    x for x in os.listdir(provider_dir) \
        if os.path.isdir(os.path.join(provider_dir, x))
        and not x.startswith('_')
]
# ic(providers)

__version__ = '0.1.0'

__all__ = ['ProviderBase', 'ProviderCharacteristics']

