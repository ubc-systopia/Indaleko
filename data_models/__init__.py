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

from data_models.activity_data_registration import IndalekoActivityDataRegistrationDataModel
from data_models.i_object import IndalekoObjectDataModel
from data_models.identity_domain import IndalekoIdentityDomainDataModel
from data_models.machine_config import IndalekoMachineConfigDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.relationship import IndalekoRelationshipDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.service import IndalekoServiceDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from data_models.timestamp import IndalekoTimestampDataModel
from data_models.user_identity import IndalekoUserDataModel
from data_models.i_uuid import IndalekoUUIDDataModel
from data_models.i_perf import IndalekoPerformanceDataModel

__version__ = '0.1.0'

__all__ = [
    'IndalekoActivityDataRegistrationDataModel',
    'IndalekoIdentityDomainDataModel',
    'IndalekoObjectDataModel',
    'IndalekoMachineConfigDataModel',
    'IndalekoPerformanceDataModel',
    'IndalekoRecordDataModel',
    'IndalekoRelationshipDataModel',
    'IndalekoSemanticAttributeDataModel',
    'IndalekoServiceDataModel',
    'IndalekoSourceIdentifierDataModel',
    'IndalekoTimestampDataModel',
    'IndalekoUserDataModel',
    'IndalekoUUIDDataModel'
]
