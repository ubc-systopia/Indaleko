"""initializtion logic for the activity context system."""

import os
import sys


# from icecream import ic

init_path = os.path.dirname(os.path.abspath(__file__))

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.activity_data_registration import (  # noqa: E402
    IndalekoActivityDataRegistrationDataModel,
)
from data_models.collection_metadata_data_model import (  # noqa: E402
    IndalekoCollectionMetadataDataModel,
)
from data_models.i_object import IndalekoObjectDataModel  # noqa: E402
from data_models.i_perf import IndalekoPerformanceDataModel  # noqa: E402
from data_models.i_uuid import IndalekoUUIDDataModel  # noqa: E402
from data_models.identity_domain import IndalekoIdentityDomainDataModel  # noqa: E402
from data_models.machine_config import IndalekoMachineConfigDataModel  # noqa: E402
from data_models.query_history import IndalekoQueryHistoryDataModel  # noqa: E402
from data_models.record import IndalekoRecordDataModel  # noqa: E402
from data_models.relationship import IndalekoRelationshipDataModel  # noqa: E402
from data_models.semantic_attribute import (  # noqa: E402
    IndalekoSemanticAttributeDataModel,
)
from data_models.service import IndalekoServiceDataModel  # noqa: E402
from data_models.source_identifier import (  # noqa: E402
    IndalekoSourceIdentifierDataModel,
)
from data_models.timestamp import IndalekoTimestampDataModel  # noqa: E402
from data_models.user_identity import IndalekoUserDataModel  # noqa: E402


# pylint: enable=wrong-import-position

__version__ = "0.1.0"

__all__ = [
    "IndalekoActivityDataRegistrationDataModel",
    "IndalekoCollectionMetadataDataModel",
    "IndalekoIdentityDomainDataModel",
    "IndalekoMachineConfigDataModel",
    "IndalekoObjectDataModel",
    "IndalekoPerformanceDataModel",
    "IndalekoQueryHistoryDataModel",
    "IndalekoRecordDataModel",
    "IndalekoRelationshipDataModel",
    "IndalekoSemanticAttributeDataModel",
    "IndalekoServiceDataModel",
    "IndalekoSourceIdentifierDataModel",
    "IndalekoTimestampDataModel",
    "IndalekoUUIDDataModel",
    "IndalekoUserDataModel",
]
