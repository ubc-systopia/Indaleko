"""
This implements the WiFi map based Location Service

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
import sys
import uuid

from typing import List, Dict, Any

# from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.location import LocationCollector
from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.location.data_models.wifi_location_data_model import (
    WiFiLocationDataModel,
)

# pylint: enable=wrong-import-position


class WiFiLocation(LocationCollector):
    """This is the IP Location Service"""

    def __init__(self):
        self.timeout = 10
        self._name = "WiFi Location Service"
        self._location = "WiFi Location"
        self._provider_id = uuid.UUID("a6647dfc-de28-4f89-82ca-d61b775a4c15")
        self.wifi_data = WiFiLocationDataModel()

    def get_collector_characteristics(self) -> List[ActivityDataCharacteristics]:
        """Get the provider characteristics"""
        raise NotImplementedError("This method is not fully implemented yet.")
        return [
            ActivityDataCharacteristics.ACTIVITY_DATA_SPATIAL,
            ActivityDataCharacteristics.ACTIVITY_DATA_NETWORK,
            ActivityDataCharacteristics.PROVIDER_DEVICE_STATE_DATA,
        ]

    def get_collectorr_name(self) -> str:
        """Get the provider name"""
        return self._name

    def get_provider_id(self) -> uuid.UUID:
        """Get the provider ID"""
        return self._provider_id

    def retrieve_data(self, data_type: str) -> str:
        """Retrieve data from the provider"""
        raise NotImplementedError("This method is not implemented yet.")

    def retrieve_temporal_data(
        self,
        reference_time: datetime.datetime,
        prior_time_window: datetime.timedelta,
        subsequent_time_window: datetime.timedelta,
        max_entries: int = 0,
    ) -> List[Dict]:
        """Retrieve temporal data from the provider"""
        raise NotImplementedError("This method is not implemented yet.")

    def get_cursor(self, activity_context: uuid.UUID) -> uuid.UUID:
        """Retrieve the current cursor for this data provider
        Input:
             activity_context: the activity context into which this cursor is
             being used
         Output:
             The cursor for this data provider, which can be used to retrieve
             data from this provider (via the retrieve_data call).
        """

    def cache_duration(self) -> datetime.timedelta:
        """
        Retrieve the maximum duration that data from this provider may be
        cached
        """
        return datetime.timedelta(minutes=10)

    def get_description(self) -> str:
        """
        Retrieve a description of the data provider. Note: this is used for
        prompt construction, so please be concise and specific in your
        description.
        """
        return """
        This is a geolocation service that provides location data for
        the device.
        """

    def get_json_schema(self) -> dict:
        """Get the JSON schema for the provider"""
        return {}

    def get_location_name(self) -> str:
        """Get the location"""
        location = self._location
        if location is None:
            location = ""
        return location

    def get_coordinates(self) -> Dict[str, float]:
        """Get the coordinates for the location"""
        return {"latitude": 0.0, "longitude": 0.0}

    def get_location_history(
        self, start_time: datetime.datetime, end_time: datetime.datetime
    ) -> List[Dict[str, Any]]:
        """Get the location history for the location"""
        return []

    def get_distance(
        self, location1: Dict[str, float], location2: Dict[str, float]
    ) -> float:
        """Get the distance between two locations"""
        raise NotImplementedError("This method is not implemented yet.")


def main():
    """This is the interface for testing the foo.py module."""


if __name__ == "__main__":
    main()
