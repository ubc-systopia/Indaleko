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

from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.source_identifer import IndalekoSourceIdentifierDataModel
from data_models.timestamp import IndalekoTimestampDataModel
from data_models.i_uuid import IndalekoUUIDDataModel

__version__ = '0.1.0'

__all__ = [
    IndalekoSemanticAttributeDataModel,
    IndalekoSourceIdentifierDataModel,
    IndalekoTimestampDataModel,
    IndalekoUUIDDataModel
]

