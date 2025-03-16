"""This implements the Windows GPS Location Service"""

import asyncio
import datetime
import os
import sys
import uuid
import winsdk.windows.devices.geolocation as wdg

from typing import List, Dict, Any

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.location.data_models.windows_gps_location_data_model import (
    WindowsGPSLocationDataModel,
)
from activity.collectors.location.location_base import LocationCollector

# pylint: enable=wrong-import-position


class WindowsGPSLocation(LocationCollector):
    """This is the Windows GPS Location Service"""

    def __init__(self):
        self._name = "GPS Location Service"
        self._location = "GPS Location"
        self._collector_id = uuid.UUID("750fd846-b6cd-4c81-b774-53ba25905e29")
        self.coords = self.get_coords()

    @staticmethod
    async def get_coords_async() -> wdg.Geoposition:
        """Get the coordinates for the location"""
        geolocator = wdg.Geolocator()
        return await geolocator.get_geoposition_async()

    def get_coords(self) -> WindowsGPSLocationDataModel:
        """Get the coordinates for the location"""
        coords = asyncio.run(self.get_coords_async())
        data = coords.coordinate
        if isinstance(data.timestamp, str):
            data.timestamp = datetime.fromisoformat(data.timestamp)
        kwargs = {
            "latitude": data.latitude,
            "longitude": data.longitude,
            "timestamp": data.timestamp,
            "source": "GPS",
            "altitude": getattr(data, "altitude", None),
            "accuracy": getattr(data, "accuracy", None),
            "altitude_accuracy": getattr(data, "altitude_accuracy", None),
            "is_remote_source": False,
            "point": f"POINT({data.latitude} {data.longitude})",
            "position_source": "GPS",
            "position_source_timestamp": data.timestamp,
            "civic_address": getattr(coords, "civic_address", None),
            "venue_data": getattr(coords, "venue_data", None),
        }
        if hasattr(data, "satellite_data"):
            kwargs["satellite_data"] = {}
            for attr in dir(data.satellite_data):
                if not attr.startswith("_"):
                    kwargs["satellite_data"][attr] = getattr(data.satellite_data, attr)
        ic(kwargs)
        return WindowsGPSLocationDataModel(**kwargs)

    def get_collector_characteristics(self) -> List[ActivityDataCharacteristics]:
        """Get the provider characteristics"""
        return [
            ActivityDataCharacteristics.ACTIVITY_DATA_SPATIAL,
            ActivityDataCharacteristics.ACTIVITY_DATA_DEVICE_STATE,
        ]

    def get_collector_name(self) -> str:
        """Get the provider name"""
        return self._name

    def get_provider_id(self) -> uuid.UUID:
        """Get the provider ID"""
        return self._collector_id

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
        return """WindowsGPSLocation is a geolocation service."""

    def get_json_schema(self) -> dict:
        """Get the JSON schema for the provider"""
        return WindowsGPSLocationDataModel(
            **WindowsGPSLocationDataModel.Config.json_schema_extra["example"]
        ).model_json_schema()

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
        raise NotImplementedError("This method is not implemented yet.")
        return []

    def get_distance(
        self, location1: Dict[str, float], location2: Dict[str, float]
    ) -> float:
        """Get the distance between two locations"""
        raise NotImplementedError("This method is not implemented yet.")


def main():
    """This is the interface for testing the module."""


if __name__ == "__main__":
    main()
