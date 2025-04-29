"""
This module defines a utility for acquiring Nest data.

Project Indaleko
"""

import os
import sys
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
from activity.collectors.ambient.smart_thermostat.nest_data_model import (
    NestAmbientDataModel,
)
from activity.collectors.ambient.smart_thermostat.smart_thermostat import (
    SmartThermostatCollector,
)

# pylint: enable=wrong-import-position


class NestSmartThermostatCollector(SmartThermostatCollector):
    """
    This class provides a utility for acquiring Nest data.
    """

    def __init__(self, access_token: str, **kwargs):
        """Initialize the object."""
        super().__init__(**kwargs)
        self.data = NestAmbientDataModel()
        self.access_token = access_token

    def collect_data(self) -> None:
        """
        Collect Nest data.
        """
        ic("Collecting Nest data")
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        response = requests.get(
            "https://smartdevicemanagement.googleapis.com/v1/enterprises/YOUR_PROJECT_ID/devices",
            headers=headers,
        )
        if response.status_code == 200:
            devices = response.json().get("devices", [])
            for device in devices:
                if device["type"] == "sdm.devices.types.THERMOSTAT":
                    raw_data = {
                        "device_id": device["name"],
                        "device_name": device["traits"]["sdm.devices.traits.Info"]["customName"],
                        "eco_mode": device["traits"]["sdm.devices.traits.ThermostatEco"]["mode"] == "MANUAL_ECO",
                        "leaf": device["traits"]["sdm.devices.traits.ThermostatEco"]["leaf"],
                        "heat_stage": device["traits"]["sdm.devices.traits.ThermostatHvac"]["status"] == "HEATING",
                        "cool_stage": device["traits"]["sdm.devices.traits.ThermostatHvac"]["status"] == "COOLING",
                        "connected_sensors": len(
                            device["traits"]["sdm.devices.traits.Temperature"]["ambientTemperatureCelsius"],
                        ),
                        "average_temperature": device["traits"]["sdm.devices.traits.Temperature"][
                            "ambientTemperatureCelsius"
                        ],
                    }
                    self.data = NestAmbientDataModel(**raw_data)

    def process_data(self, data: Any) -> dict[str, Any]:
        """
        Process the collected data.
        """
        ic("Processing Nest data")
        # Example: Convert processed data to a dictionary
        return self.data.dict()

    def store_data(self, data: dict[str, Any]) -> None:
        """
        Store the processed data.
        """
        ic("Storing Nest data")
        # Example: Print data to simulate storing
        print("Storing data:", data)

    def get_latest_db_update(self) -> dict[str, Any]:
        """
        Get the latest data update from the database.
        """
        ic("Getting latest Nest data update from the database")
        # Example: Simulate fetching the latest data
        return {
            "device_id": "ABC123DEF456",
            "device_name": "Living Room",
            "eco_mode": True,
            "leaf": True,
            "heat_stage": 1,
            "cool_stage": 0,
            "connected_sensors": 2,
            "average_temperature": 21.0,
        }

    def update_data(self) -> None:
        """
        Update the data in the database.
        """
        ic("Updating Nest data in the database")
        # Example: Simulate updating data
        latest_data = self.get_latest_db_update()
        self.store_data(latest_data)


def main():
    """Main entry point for the Nest Smart Thermostat Collector."""
    ic("Starting Nest Smart Thermostat Collector")
    access_token = "YOUR_NEST_ACCESS_TOKEN"
    collector = NestSmartThermostatCollector(access_token=access_token)
    collector.collect_data()
    latest = collector.get_latest_db_update()
    ic(latest)
    ic(collector.get_description())
    ic("Finished Nest Smart Thermostat Collector")


if __name__ == "__main__":
    main()
