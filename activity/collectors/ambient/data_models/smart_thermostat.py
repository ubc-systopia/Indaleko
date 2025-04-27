"""
This module defines the data model for smart thermostat ambient data collection.

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

from pydantic import Field, field_validator


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.ambient.data_models.ambient_data_model import (
    BaseAmbientConditionDataModel,
)


# pylint: enable=wrong-import-position


class ThermostatSensorData(BaseAmbientConditionDataModel):
    """
    Data model for smart thermostat sensor data, specifically designed with
    ecobee-like capabilities in mind but generalizable to other smart thermostats.
    """

    # Core temperature readings
    temperature: float = Field(
        ...,
        description="Current temperature in Celsius",
        ge=-50.0,  # reasonable minimum temperature
        le=100.0,  # reasonable maximum temperature
    )

    humidity: float | None = Field(
        None,
        description="Relative humidity percentage",
        ge=0.0,
        le=100.0,
    )

    # System state information
    hvac_mode: str = Field(
        ...,
        description="Current HVAC system mode",
        pattern="^(heat|cool|auto|off)$",
    )

    hvac_state: str = Field(
        ...,
        description="Current HVAC running state",
        pattern="^(heating|cooling|fan|idle)$",
    )

    fan_mode: str = Field(
        ...,
        description="Fan operation mode",
        pattern="^(auto|on|scheduled)$",
    )

    # Target/Set points
    target_temperature: float = Field(
        ...,
        description="Target temperature in Celsius",
        ge=-50.0,
        le=100.0,
    )

    # Optional enhanced sensor data
    occupancy_detected: bool | None = Field(
        None,
        description="Whether occupancy is detected in the sensor's area",
    )

    air_quality: int | None = Field(
        None,
        description="Air quality index (if available)",
        ge=0,
        le=500,
    )

    @field_validator("temperature", "target_temperature")
    @classmethod
    def validate_temperature(cls, value: float) -> float:
        """Validate temperature is within reasonable bounds"""
        if not -50.0 <= value <= 100.0:
            raise ValueError("Temperature must be between -50°C and 100°C")
        return round(value, 2)  # Round to 2 decimal places for consistency

    class Config:
        """Configuration and example data for the thermostat sensor model"""

        json_schema_extra = {
            "example": {
                **BaseAmbientConditionDataModel.Config.json_schema_extra["example"],
                "temperature": 21.5,
                "humidity": 45.5,
                "hvac_mode": "auto",
                "hvac_state": "idle",
                "fan_mode": "auto",
                "target_temperature": 22.0,
                "occupancy_detected": True,
                "air_quality": 95,
                "source": "ecobee",
            },
        }


def main():
    """This allows testing the data model"""
    ThermostatSensorData.test_model_main()


if __name__ == "__main__":
    main()
