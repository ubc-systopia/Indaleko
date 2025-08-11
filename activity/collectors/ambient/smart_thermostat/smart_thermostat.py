"""
This module defines a common base for smart thermostat data collectors.

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

import os
import sys

from typing import Any


# from datetime import datetime

# from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.ambient.base import AmbientCollector
from activity.collectors.ambient.data_models.smart_thermostat import (
    ThermostatSensorData,
)


# pylint: enable=wrong-import-position


class SmartThermostatCollector(AmbientCollector):
    """This class provides a common base for smart thermostat data collectors."""

    def __init__(self, **kwargs) -> None:
        """Initialize the object."""
        self.config = kwargs.get("config", {})
        self.data = ThermostatSensorData()

    def collect_data(self) -> None:
        """Collect smart thermostat data."""
        raise NotImplementedError("Subclasses must implement this method")

    def process_data(self, data: Any) -> dict[str, Any]:
        """Process the collected data."""
        raise NotImplementedError("Subclasses must implement this method")

    def store_data(self, data: dict[str, Any]) -> None:
        """Store the processed data."""
        raise NotImplementedError("Subclasses must implement this method")

    def update_data(self) -> None:
        """Update the data in the database."""
        raise NotImplementedError("Subclasses must implement this method")

    def get_description(self) -> str:
        """Get a description of the smart thermostat data collector."""
        return "Base class for smart thermostat data collectors"

    def get_latest_db_update(self) -> dict[str, Any]:
        """Get the latest data update from the database."""
        raise NotImplementedError("Subclasses must implement this method")
