"""This implements the IP Location Service."""

import datetime
import ipaddress
import os
import sys
import uuid

from typing import Any

import requests

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
# now we can import modules from the project root
from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.location import LocationCollector
from activity.collectors.location.data_models.base_location_data_model import (
    BaseLocationDataModel,
)
from activity.collectors.location.data_models.ip_location_data_model import (
    IPLocationDataModel,
)


# pylint: enable=wrong-import-position


class IPLocation(LocationCollector):
    """This is the IP Location Service."""

    def __init__(self) -> None:
        self.timeout = 10
        self._name = "IP Location Service"
        self._location = ""
        self._provider_id = uuid.UUID("82ae879d-7280-4b5a-a98a-5ebc1bf61bbc")
        self.ip_address = self.capture_public_ip_address()
        self.ip_location_data = self.get_ip_location_data()
        self.location_data = self.map_ip_location_data_to_data_model(
            self.ip_location_data,
        )

    @staticmethod
    def capture_public_ip_address(timeout: int = 10) -> str:
        """Capture the public IP address."""
        response = requests.get("https://api.ipify.org?format=json", timeout=timeout)
        data = response.json()
        return data.get("ip")

    def map_ip_location_data_to_data_model(
        self,
        location_data: dict,
    ) -> IPLocationDataModel:
        """Map the IP location data to the data model."""
        # start with the required fields
        if "ip_address" in location_data:
            ip_address = location_data.get("ip_address")
        else:
            try:
                ip_address = ipaddress.IPv4Address(location_data.get("query"))
            except ipaddress.AddressValueError:
                ip_address = ipaddress.IPv6Address(location_data.get("query"))
        # Build nested Location data
        location_dict: dict[str, Any] = {
            "latitude": location_data.get("lat"),
            "longitude": location_data.get("lon"),
            # Use UTC timezone for timestamp
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "source": "IP",
        }
        # Add optional location attributes
        if "altitude" in location_data:
            location_dict["altitude"] = location_data.get("altitude")
        if "accuracy" in location_data:
            location_dict["accuracy"] = location_data.get("accuracy")
        if "heading" in location_data:
            location_dict["heading"] = location_data.get("heading")
        if "speed" in location_data:
            location_dict["speed"] = location_data.get("speed")
        # Build full example to populate required activity metadata fields
        example = BaseLocationDataModel.Config.json_schema_extra["example"].copy()
        example["Location"] = location_dict
        example["ip_address"] = ip_address
        # Add optional IP-related fields
        for field in [
            "city",
            "country",
            "country_code",
            "region",
            "region_name",
            "postal_code",
            "isp",
            "org",
            "as_name",
            "timezone",
        ]:
            if field in location_data:
                example[field] = location_data.get(field)
        return IPLocationDataModel(**example)

    def get_ip_location_data(self) -> dict:
        """Get the coordinates for the location."""
        if self.ip_address is None:
            return None
        url = f"http://ip-api.com/json/{self.ip_address}"
        response = requests.get(url, timeout=self.timeout)
        data = response.json()
        if data.get("status") == "success":
            return data
        return None

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
        # Return the latest stored data for this provider
        if data_id == self.get_provider_id() and hasattr(self, "data") and self.data:
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
        # Determine time window
        start = reference_time - prior_time_window
        end = reference_time + subsequent_time_window
        history = self.get_location_history(start, end)
        # Limit entries if requested
        if max_entries and len(history) > max_entries:
            return history[:max_entries]
        return history

    def get_cursor(self, activity_context: uuid.UUID) -> uuid.UUID:
        """Retrieve the current cursor for this data provider
        Input:
             activity_context: the activity context into which this cursor is
             being used
         Output:
             The cursor for this data provider, which can be used to retrieve
             data from this provider (via the retrieve_data call).
        """
        # Use provider ID as cursor for simplicity
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
        This is a geolocation service that provides location data for
        the device.
        """

    def get_json_schema(self) -> dict:
        """Get the JSON schema for the provider."""
        return IPLocationDataModel.schema_json()

    def collect_data(self) -> None:
        """Collect and store the latest IP location data."""
        # Fetch the public IP and corresponding geolocation
        self.ip_address = self.capture_public_ip_address(self.timeout)
        self.ip_location_data = self.get_ip_location_data()
        self.location_data = None
        if self.ip_location_data:
            self.location_data = self.map_ip_location_data_to_data_model(
                self.ip_location_data,
            )
            processed = self.process_data(self.location_data)
            self.store_data(processed)

    def process_data(self, data: Any) -> dict[str, Any]:
        """Process collected data into a serializable dict."""
        if isinstance(data, IPLocationDataModel):
            return data.dict()
        if isinstance(data, dict):
            model = self.map_ip_location_data_to_data_model(data)
            return model.dict()
        raise TypeError(f"Unsupported data type: {type(data)}")

    def store_data(self, data: dict[str, Any]) -> None:
        """Store processed data in memory."""
        if not hasattr(self, "data"):
            self.data = []
        self.data.append(data)

    def get_location_name(self) -> str:
        """Get the location."""
        location = self._location
        if location is None:
            location = ""
        return location

    def get_coordinates(self) -> dict[str, float]:
        """Get the coordinates for the location."""
        # Return the most recent stored coordinates
        if hasattr(self, "data") and self.data:
            loc = self.data[-1].get("Location", {}) or {}
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
        for record in getattr(self, "data", []):
            # extract timestamp from nested Location
            loc = record.get("Location", {}) or {}
            ts_val = loc.get("timestamp")
            # Handle both datetime and isoformat string
            if isinstance(ts_val, datetime.datetime):
                ts = ts_val
            else:
                try:
                    ts = datetime.datetime.fromisoformat(ts_val)
                except Exception:
                    continue
            if start_time <= ts <= end_time:
                events.append(record)
        return events

    def get_distance(
        self,
        location1: dict[str, float],
        location2: dict[str, float],
    ) -> float:
        """Get the distance between two locations."""
        raise NotImplementedError("This method is not implemented yet.")


def main() -> None:
    """This is the interface for testing the foo.py module."""
    location = IPLocation()
    ic(location.get_collectorr_name())
    ic(location.get_provider_id())
    ic(location.get_collector_characteristics())
    ic(location.get_description())
    ic(location.get_json_schema())
    ic(location.get_location_name())
    ic(location.get_coordinates())
    ic(location.get_location_history(datetime.datetime.now(), datetime.datetime.now()))
    ic(location.ip_address)
    ic(location.ip_location_data)
    ic(location.location_data.json())


if __name__ == "__main__":
    main()
