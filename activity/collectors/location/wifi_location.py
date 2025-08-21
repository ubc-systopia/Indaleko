"""
This implements the WiFi map based Location Service.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import datetime
import os
import subprocess
import sys
import uuid

from typing import Any

import requests


# from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
# pylint: enable=wrong-import-position


from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.location import LocationCollector
from activity.collectors.location.data_models.wifi_location_data_model import (
    WiFiLocationDataModel,
)


class WiFiLocation(LocationCollector):
    """This is the WiFi-based Location Service."""

    def __init__(self) -> None:
        self.timeout = 10
        self._name = "WiFi Location Service"
        self._location = "WiFi Location"
        self._provider_id = uuid.UUID("a6647dfc-de28-4f89-82ca-d61b775a4c15")
        # Initialize in-memory storage for collected data
        self.data: list[dict] = []

    def get_collector_characteristics(self) -> list[ActivityDataCharacteristics]:
        """Get the provider characteristics."""
        return [
            ActivityDataCharacteristics.ACTIVITY_DATA_SPATIAL,
            ActivityDataCharacteristics.ACTIVITY_DATA_NETWORK,
            ActivityDataCharacteristics.PROVIDER_DEVICE_STATE_DATA,
        ]

    def get_collector_name(self) -> str:
        """Get the provider name."""
        return self._name

    # alias for backwards compatibility
    get_collectorr_name = get_collector_name

    def get_provider_id(self) -> uuid.UUID:
        """Get the provider ID."""
        return self._provider_id

    def retrieve_data(self, data_id: uuid.UUID) -> dict[str, Any]:
        """Retrieve the data associated with the given data_id."""
        if data_id == self.get_provider_id() and self.data:
            return self.data[-1]
        return {}

    def retrieve_temporal_data(
        self,
        reference_time: datetime.datetime,
        prior_time_window: datetime.timedelta,
        subsequent_time_window: datetime.timedelta,
        max_entries: int = 0,
    ) -> list[dict[str, Any]]:
        """Retrieve temporal data from the provider."""
        # Return historical records within the time window
        start = reference_time - prior_time_window
        end = reference_time + subsequent_time_window
        history = self.get_location_history(start, end)
        if max_entries and len(history) > max_entries:
            return history[:max_entries]
        return history

    def get_cursor(self, activity_context: uuid.UUID) -> uuid.UUID:
        """Retrieve the current cursor for this data provider."""
        # Use provider ID as a simple cursor
        return self.get_provider_id()

    def cache_duration(self) -> datetime.timedelta:
        """
        Retrieve the maximum duration that data from this provider may be
        cached.
        """
        return datetime.timedelta(minutes=10)

    def get_description(self) -> str:
        """
        Retrieve a description of the data provider. Note: this is used for
        prompt construction, so please be concise and specific in your
        description.
        """
        return """
        This is a geolocation service that estimates device location
        by scanning nearby WiFi access points and using a geolocation API.
        """

    def get_json_schema(self) -> dict:
        """Get the JSON schema for the provider."""
        return WiFiLocationDataModel.schema_json()

    def get_location_name(self) -> str:
        """Get the location."""
        location = self._location
        if location is None:
            location = ""
        return location

    def get_coordinates(self) -> dict[str, float]:
        """Get the coordinates for the most recent location."""
        if self.data:
            loc = self.data[-1].get("Location", {})
            return {
                "latitude": loc.get("latitude", 0.0),
                "longitude": loc.get("longitude", 0.0),
            }
        return {"latitude": 0.0, "longitude": 0.0}

    def get_location_history(
        self,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
    ) -> list[dict[str, Any]]:
        """Get the location history for the location."""
        events: list[dict[str, Any]] = []
        for record in self.data:
            loc = record.get("Location", {})
            ts_str = loc.get("timestamp")
            try:
                ts = datetime.datetime.fromisoformat(ts_str)
            except Exception:
                continue
            if start_time <= ts <= end_time:
                events.append(record)
        return events

    def collect_data(self) -> None:
        """Collect and store the latest WiFi-based location data."""
        # Scan nearby WiFi access points
        aps = []
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "BSSID,SIGNAL", "device", "wifi", "list"],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in result.stdout.splitlines():
                if not line:
                    continue
                parts = line.split(":")
                if len(parts) >= 2:
                    mac, signal = parts[0], parts[1]
                    try:
                        strength = int(signal)
                    except ValueError:
                        strength = None
                    aps.append({"macAddress": mac, "signalStrength": strength})
        except Exception:
            aps = []
        # Geolocate via Mozilla Location Service
        location = None
        if aps:
            body = {"wifiAccessPoints": aps}
            try:
                resp = requests.post(
                    "https://location.services.mozilla.com/v1/geolocate?key=test",  # replace with valid API key
                    json=body,
                    timeout=self.timeout,
                )
                data = resp.json()
                if "location" in data:
                    location = data
            except Exception:
                location = None
        # Store result if available
        if location:
            loc = location["location"]
            timestamp = datetime.datetime.now(datetime.UTC).isoformat()
            record = {
                "Location": {
                    "latitude": loc.get("lat"),
                    "longitude": loc.get("lng"),
                    "accuracy": location.get("accuracy"),
                    "timestamp": timestamp,
                    "source": "WiFi",
                },
            }
            # Directly store the record dict without model validation
            self.store_data(record)

    def process_data(self, data: Any) -> dict[str, Any]:
        """Process collected data into a serializable dict."""
        if isinstance(data, WiFiLocationDataModel):
            return data.model_dump()
        if isinstance(data, dict):
            model = WiFiLocationDataModel(**data)
            return model.model_dump()
        raise TypeError(f"Unsupported data type: {type(data)}")

    def store_data(self, data: dict[str, Any]) -> None:
        """Store processed data in memory."""
        self.data.append(data)

    def get_distance(
        self,
        location1: dict[str, float],
        location2: dict[str, float],
    ) -> float:
        """Get the distance between two locations in meters using Haversine formula."""
        # Earth radius in meters
        from math import atan2, cos, radians, sin, sqrt

        lat1, lon1 = location1.get("latitude"), location1.get("longitude")
        lat2, lon2 = location2.get("latitude"), location2.get("longitude")
        # convert to radians
        rlat1, rlon1, rlat2, rlon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = rlat2 - rlat1
        dlon = rlon2 - rlon1
        a = sin(dlat / 2) ** 2 + cos(rlat1) * cos(rlat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return 6371000 * c


def main() -> None:
    """This is the interface for testing the foo.py module."""


if __name__ == "__main__":
    main()
