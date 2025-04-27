#!/usr/bin/env python3
"""
Tests for IP and WiFi Location Collectors.
"""

import datetime
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Setup project root path
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from activity.collectors.location.data_models.ip_location_data_model import (
    IPLocationDataModel,
)
from activity.collectors.location.ip_location import IPLocation
from activity.collectors.location.wifi_location import WiFiLocation


class TestIPLocation(unittest.TestCase):
    """Test cases for the IPLocation collector."""

    def setUp(self):
        # Mock requests.get for IPify and IP API calls
        self.mock_ipify_response = {"ip": "123.123.123.123"}
        self.mock_ip_api_response = {
            "status": "success",
            "lat": 10.0,
            "lon": 20.0,
            "accuracy": 50.0,
            "query": "123.123.123.123",
        }
        patcher_get = patch("activity.collectors.location.ip_location.requests.get")
        self.mock_get = patcher_get.start()
        self.addCleanup(patcher_get.stop)

        def get_side_effect(url, *args, **kwargs):
            class MockResponse:
                def __init__(self, json_data):
                    self._json = json_data

                def json(self):
                    return self._json

            if "api.ipify.org" in url:
                return MockResponse(self.mock_ipify_response)
            elif "ip-api.com" in url:
                return MockResponse(self.mock_ip_api_response)
            raise ValueError(f"Unexpected URL: {url}")

        self.mock_get.side_effect = get_side_effect

    def test_initialization(self):
        loc = IPLocation()
        self.assertEqual(loc.ip_address, "123.123.123.123")
        self.assertIsInstance(loc.location_data, IPLocationDataModel)
        # Coordinates should be nested under Location attribute
        self.assertEqual(loc.location_data.Location.latitude, 10.0)
        self.assertEqual(loc.location_data.Location.longitude, 20.0)

    def test_collect_data(self):
        loc = IPLocation()
        # Clear any existing data
        if hasattr(loc, "data"):
            loc.data.clear()
        loc.collect_data()
        self.assertTrue(hasattr(loc, "data"))
        self.assertGreater(len(loc.data), 0)
        record = loc.data[-1]
        self.assertIsInstance(record, dict)
        # Check nested Location in the record
        loc_data = record.get("Location", {})
        self.assertEqual(loc_data.get("latitude"), 10.0)
        self.assertEqual(loc_data.get("longitude"), 20.0)
        self.assertEqual(loc_data.get("source"), "IP")

    def test_retrieve_data_and_history(self):
        loc = IPLocation()
        loc.collect_data()
        latest = loc.data[-1]
        data = loc.retrieve_data(loc.get_provider_id())
        self.assertEqual(data, latest)
        now = datetime.datetime.now(datetime.UTC)
        history = loc.retrieve_temporal_data(
            now,
            datetime.timedelta(minutes=1),
            datetime.timedelta(minutes=1),
        )
        self.assertIsInstance(history, list)
        self.assertIn(latest, history)


class TestWiFiLocation(unittest.TestCase):
    """Test cases for the WiFiLocation collector."""

    def setUp(self):
        # Mock subprocess.run to simulate WiFi scan
        patcher_run = patch("activity.collectors.location.wifi_location.subprocess.run")
        self.mock_run = patcher_run.start()
        self.addCleanup(patcher_run.stop)
        mock_proc = MagicMock()
        mock_proc.stdout = "AP1:60\nAP2:40\n"
        self.mock_run.return_value = mock_proc

        # Mock requests.post to simulate geolocation API
        self.mock_location = {"location": {"lat": 30.0, "lng": 40.0}, "accuracy": 30.0}
        patcher_post = patch("activity.collectors.location.wifi_location.requests.post")
        self.mock_post = patcher_post.start()
        self.addCleanup(patcher_post.stop)

        def post_side_effect(url, json, timeout):
            class MockResponse:
                def __init__(self, json_data):
                    self._json = json_data

                def json(self):
                    return self._json

            return MockResponse(self.mock_location)

        self.mock_post.side_effect = post_side_effect

    def test_collect_data(self):
        loc = WiFiLocation()
        # Clear any existing data
        loc.data.clear()
        loc.collect_data()
        self.assertTrue(hasattr(loc, "data"))
        self.assertGreater(len(loc.data), 0)
        record = loc.data[-1]
        self.assertIsInstance(record, dict)
        self.assertIn("Location", record)
        loc_data = record["Location"]
        self.assertEqual(loc_data.get("latitude"), 30.0)
        self.assertEqual(loc_data.get("longitude"), 40.0)
        self.assertEqual(loc_data.get("accuracy"), 30.0)
        self.assertEqual(loc_data.get("source"), "WiFi")

    def test_get_coordinates(self):
        loc = WiFiLocation()
        loc.data.clear()
        loc.collect_data()
        coords = loc.get_coordinates()
        self.assertEqual(coords.get("latitude"), 30.0)
        self.assertEqual(coords.get("longitude"), 40.0)

    def test_retrieve_data_and_history(self):
        loc = WiFiLocation()
        loc.data.clear()
        loc.collect_data()
        latest = loc.data[-1]
        data = loc.retrieve_data(loc.get_provider_id())
        self.assertEqual(data, latest)
        now = datetime.datetime.now(datetime.UTC)
        history = loc.retrieve_temporal_data(
            now,
            datetime.timedelta(minutes=1),
            datetime.timedelta(minutes=1),
        )
        self.assertIsInstance(history, list)
        self.assertIn(latest, history)


if __name__ == "__main__":
    unittest.main()
