"""
This module defines a utility for acquiring ecobee data.

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

# import json
# import math
import os
import sys
from typing import Any, Dict

# from datetime import datetime

from icecream import ic
from pyecobee import EcobeeService

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.ambient.smart_thermostat.smart_thermostat import (
    SmartThermostatCollector,
)
from activity.collectors.ambient.smart_thermostat.ecobee_data_model import (
    EcobeeAmbientDataModel,
)

# pylint: enable=wrong-import-position


class EcobeeSmartThermostatCollector(SmartThermostatCollector):
    """
    This class provides a utility for acquiring ecobee data.
    """

    def __init__(self, api_key: str, **kwargs):
        """Initialize the object."""
        super().__init__(**kwargs)
        self.data = EcobeeAmbientDataModel()
        self.ecobee = EcobeeService(api_key=api_key)
        self.authenticate()

    def authenticate(self) -> None:
        """Authenticate with the Ecobee API."""
        ic("Authenticating with Ecobee API")
        if not self.ecobee.authorization_token:
            self.ecobee.request_pin()
            print(f"Please authorize the application with PIN: {self.ecobee.pin}")
            input("Press Enter after authorization...")
            self.ecobee.request_tokens()
        else:
            self.ecobee.refresh_tokens()

    def collect_data(self) -> None:
        """
        Collect ecobee data.
        """
        ic("Collecting ecobee data")
        thermostat_summary = self.ecobee.get_thermostats_summary()
        thermostat_data = self.ecobee.get_thermostats(thermostat_summary.thermostat_ids)
        for thermostat in thermostat_data.thermostat_list:
            raw_data = {
                "device_id": thermostat.identifier,
                "device_name": thermostat.name,
                "aux_heat_active": thermostat.runtime.aux_heat1,
                "dehumidifier_mode": thermostat.settings.dehumidifier_mode,
                "ventilator_mode": thermostat.settings.ventilator_mode,
                "current_climate": thermostat.program.current_climate_ref,
                "heat_stage": thermostat.runtime.actual_heat,
                "cool_stage": thermostat.runtime.actual_cool,
                "connected_sensors": len(thermostat.remote_sensors),
                "average_temperature": thermostat.runtime.actual_temperature / 10.0,
            }
            self.data.process_ecobee_data(raw_data)

    def process_data(self, data: Any) -> Dict[str, Any]:
        """
        Process the collected data.
        """
        ic("Processing ecobee data")
        # Example: Convert processed data to a dictionary
        return self.data.dict()

    def store_data(self, data: Dict[str, Any]) -> None:
        """
        Store the processed data.
        """
        ic("Storing ecobee data")
        # Example: Print data to simulate storing
        print("Storing data:", data)

    def get_latest_db_update(self) -> Dict[str, Any]:
        """
        Get the latest data update from the database.
        """
        ic("Getting latest ecobee data update from the database")
        # Example: Simulate fetching the latest data
        return {
            "device_id": "123ABC456DEF",
            "device_name": "Main Floor",
            "aux_heat_active": False,
            "dehumidifier_mode": "auto",
            "ventilator_mode": "auto",
            "current_climate": "home",
            "heat_stage": 1,
            "cool_stage": 0,
            "connected_sensors": 3,
            "average_temperature": 22.5,
        }

    def update_data(self) -> None:
        """
        Update the data in the database.
        """
        ic("Updating ecobee data in the database")
        # Example: Simulate updating data
        latest_data = self.get_latest_db_update()
        self.store_data(latest_data)


def main():
    """Main entry point for the Ecobee Smart Thermostat Collector."""
    ic("Starting Ecobee Smart Thermostat Collector")
    api_key = "YOUR_ECOBEE_API_KEY"
    collector = EcobeeSmartThermostatCollector(api_key=api_key)
    collector.collect_data()
    latest = collector.get_latest_db_update()
    ic(latest)
    ic(collector.get_description())
    ic("Finished Ecobee Smart Thermostat Collector")


if __name__ == "__main__":
    main()
