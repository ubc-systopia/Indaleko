'''initializtion logic for the db management models in Indaleko'''

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
from db.collection import IndalekoCollection
from db.collection_index import IndalekoCollectionIndex
from db.i_collections import IndalekoCollections
from db.db_config import IndalekoDBConfig
# pylint: enable=wrong-import-position

__version__ = '0.1.0'

__all__ = [
    'IndalekoCollection',
    'IndalekoCollectionIndex',
    'IndalekoCollections',
    'IndalekoDBConfig'
]