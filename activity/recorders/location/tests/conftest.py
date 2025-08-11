import os
import sys

import pytest


# Ensure the project root (indaleko directory) is on sys.path for imports
root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if root not in sys.path:
    sys.path.insert(0, root)
    # os.environ["PYTHONPATH"] = root  # not needed, sys.path update suffices

from activity.recorders.location.ip_location_recorder import IPLocationRecorder
from activity.recorders.location.wifi_location_recorder import WiFiLocationRecorder
from activity.recorders.registration_service import (
    IndalekoActivityDataRegistrationService,
)


@pytest.fixture
def ip_recorder():
    # Ensure clean state by deleting any existing collection/registration
    IndalekoActivityDataRegistrationService.delete_activity_provider_collection(
        str(IPLocationRecorder.identifier),
        delete_data_collection=True,
    )
    rec = IPLocationRecorder()
    yield rec
    # Clean up after test
    IndalekoActivityDataRegistrationService.delete_activity_provider_collection(
        str(rec.get_recorder_id()),
        delete_data_collection=True,
    )


@pytest.fixture
def wifi_recorder():
    IndalekoActivityDataRegistrationService.delete_activity_provider_collection(
        str(WiFiLocationRecorder.identifier),
        delete_data_collection=True,
    )
    rec = WiFiLocationRecorder()
    yield rec
    IndalekoActivityDataRegistrationService.delete_activity_provider_collection(
        str(rec.get_recorder_id()),
        delete_data_collection=True,
    )
