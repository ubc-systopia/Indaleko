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

from data_models.indaleko_semantic_attribute_data_model import IndalekoSemanticAttributeDataModel
from data_models.indaleko_source_identifier_data_model import IndalekoSourceIdentifierDataModel
from data_models.indaleko_timestamp_data_model import IndalekoTimestampDataModel
from data_models.indaleko_uuid_data_model import IndalekoUUIDDataModel

__version__ = '0.1.0'

__all__ = [
    IndalekoSemanticAttributeDataModel,
    IndalekoSourceIdentifierDataModel,
    IndalekoTimestampDataModel,
    IndalekoUUIDDataModel
]

