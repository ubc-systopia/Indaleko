import os
import sys

import pytest

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db.db_config import IndalekoDBConfig

# pylint: enable=wrong-import-position


def test_registration_and_collection_created(ip_recorder):
    cfg = IndalekoDBConfig()
    # The collection should exist in ArangoDB
    # Extract collection names from ArangoDB
    names = [col["name"] for col in cfg._arangodb.collections()]
    assert ip_recorder.collection.name in names


def test_update_and_persistence(ip_recorder):
    # Perform an update (real API call) and verify model persistence
    model = ip_recorder.update_data()
    assert model is not None
    latest = ip_recorder.get_latest_db_update()
    assert latest == model


def test_idempotent_no_duplicate(ip_recorder):
    # First update may insert a record
    ip_recorder.update_data()
    # Count documents in the underlying Arango collection
    count1 = ip_recorder.collection.collection.count()
    # Second update should not insert when data unchanged
    ip_recorder.update_data()
    count2 = ip_recorder.collection.collection.count()
    assert count2 == count1


def test_change_triggers_new_insert(monkeypatch, ip_recorder):
    # Initial update to populate DB
    orig = ip_recorder.update_data()
    count1 = ip_recorder.collection.collection.count()
    # Monkey-patch provider to return a new, shifted location
    fake_ip = "9.9.9.9"

    def fake_capture(timeout=None):
        return fake_ip

    def fake_get_data():
        return {
            "lat": orig.Location.latitude + 1.0,
            "lon": orig.Location.longitude,
            "query": fake_ip,
        }

    monkeypatch.setattr(ip_recorder.provider, "capture_public_ip_address", fake_capture)
    monkeypatch.setattr(ip_recorder.provider, "get_ip_location_data", fake_get_data)
    # Trigger update again
    new_model = ip_recorder.update_data()
    count2 = ip_recorder.collection.collection.count()
    assert count2 == count1 + 1
    assert new_model.Location.latitude == pytest.approx(orig.Location.latitude + 1.0)
