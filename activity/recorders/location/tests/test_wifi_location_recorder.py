from datetime import UTC

import pytest

from db.db_config import IndalekoDBConfig


def test_registration_and_collection_created(wifi_recorder):
    cfg = IndalekoDBConfig()
    # Extract collection names from ArangoDB
    names = [col["name"] for col in cfg._arangodb.collections()]
    assert wifi_recorder.collection.name in names


def test_update_and_persistence(monkeypatch, wifi_recorder):
    # Stub provider.collect_data to inject deterministic data
    # Build a full example dict for WiFiLocationDataModel and override Location
    from datetime import datetime

    from activity.collectors.location.data_models.wifi_location_data_model import (
        WiFiLocationDataModel,
    )

    # Start from the model's full example
    example = WiFiLocationDataModel.get_json_example()
    # Override the Location section
    timestamp = datetime.now(UTC).isoformat()
    example["Location"] = {
        "latitude": 11.0,
        "longitude": 22.0,
        "accuracy": 4.0,
        "timestamp": timestamp,
        "source": "WiFi",
    }
    fake_data = example

    def fake_collect():
        wifi_recorder.provider.data = [fake_data]

    monkeypatch.setattr(wifi_recorder.provider, "collect_data", fake_collect)
    # Perform update and verify
    model = wifi_recorder.update_data()
    assert model is not None
    assert model.Location.latitude == pytest.approx(11.0)
    latest = wifi_recorder.get_latest_db_update()
    assert latest == model


def test_idempotent_no_duplicate(monkeypatch, wifi_recorder):
    # Use full example data for idempotent check
    from datetime import datetime

    from activity.collectors.location.data_models.wifi_location_data_model import (
        WiFiLocationDataModel,
    )

    example = WiFiLocationDataModel.get_json_example()
    ts = datetime.now(UTC).isoformat()
    example["Location"] = {
        "latitude": 11.0,
        "longitude": 22.0,
        "accuracy": 4.0,
        "timestamp": ts,
        "source": "WiFi",
    }
    fake_data = example
    monkeypatch.setattr(
        wifi_recorder.provider,
        "collect_data",
        lambda: setattr(wifi_recorder.provider, "data", [fake_data]),
    )
    wifi_recorder.update_data()
    count1 = wifi_recorder.collection.collection.count()
    wifi_recorder.update_data()
    count2 = wifi_recorder.collection.collection.count()
    assert count2 == count1


def test_change_triggers_new_insert(monkeypatch, wifi_recorder):
    from datetime import datetime

    from activity.collectors.location.data_models.wifi_location_data_model import (
        WiFiLocationDataModel,
    )

    # Build two example payloads
    example_base = WiFiLocationDataModel.get_json_example()
    ts = datetime.now(UTC).isoformat()
    fake1 = example_base.copy()
    fake1["Location"] = {
        "latitude": 11.0,
        "longitude": 22.0,
        "accuracy": 4.0,
        "timestamp": ts,
        "source": "WiFi",
    }
    fake2 = example_base.copy()
    fake2["Location"] = {
        "latitude": 12.0,
        "longitude": 22.0,
        "accuracy": 5.0,
        "timestamp": ts,
        "source": "WiFi",
    }
    # Alternate between two data points
    calls = {"cnt": 0}

    def fake_collect():
        wifi_recorder.provider.data = [fake1] if calls["cnt"] == 0 else [fake2]
        calls["cnt"] += 1

    monkeypatch.setattr(wifi_recorder.provider, "collect_data", fake_collect)
    first = wifi_recorder.update_data()
    count1 = wifi_recorder.collection.collection.count()
    second = wifi_recorder.update_data()
    count2 = wifi_recorder.collection.collection.count()
    assert count2 == count1 + 1
    assert second.Location.latitude == pytest.approx(12.0)
