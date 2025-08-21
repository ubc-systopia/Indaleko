"""
This module defines a Nest-specific implementation of the thermostat
ambient data collection model.

Project Indaleko
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
from activity.collectors.ambient.data_models.smart_thermostat import (
    ThermostatSensorData,
)


# pylint: enable=wrong-import-position


class NestAmbientDataModel(ThermostatSensorData):
    """
    Nest-specific implementation of the thermostat sensor ambient data model.
    Extends ThermostatSensorData to maintain the common structure while adding
    Nest-specific attributes and capabilities.
    """

    # Nest identification - useful for tracking specific devices
    device_id: str = Field(
        ...,
        description="Nest device identifier",
        pattern="^[a-zA-Z0-9]+$",
    )

    device_name: str = Field(
        ...,
        description="Name assigned to the thermostat",
        min_length=1,
    )

    # Additional Nest-specific sensor data
    eco_mode: bool | None = Field(None, description="Whether eco mode is active")

    leaf: bool | None = Field(
        None,
        description="Whether the Nest leaf icon is displayed",
    )

    # Equipment stages (common in Nest systems)
    heat_stage: int | None = Field(
        None,
        description="Current heating stage (0 = off, 1 = stage 1, 2 = stage 2)",
        ge=0,
        le=2,
    )

    cool_stage: int | None = Field(
        None,
        description="Current cooling stage (0 = off, 1 = stage 1, 2 = stage 2)",
        ge=0,
        le=2,
    )

    # Remote sensor summary
    connected_sensors: int = Field(
        0,
        description="Number of connected remote sensors",
        ge=0,
    )

    average_temperature: float | None = Field(
        None,
        description="Average temperature across all sensors in Celsius",
    )

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, value: str) -> str:
        """Validate Nest device identifier format."""
        if not value.isalnum():
            raise ValueError("Nest device identifier must be alphanumeric")
        return value

    @field_validator("average_temperature")
    @classmethod
    def validate_avg_temperature(cls, value: float | None) -> float | None:
        """Validate average temperature is within reasonable bounds."""
        if value is not None and not -50.0 <= value <= 100.0:
            raise ValueError("Average temperature must be between -50°C and 100°C")
        return value

    class Config:
        """Configuration and example data for the Nest ambient data model."""

        json_schema_extra = {
            "example": {
                # Include all base ThermostatSensorData fields
                **ThermostatSensorData.Config.json_schema_extra["example"],
                # Add Nest-specific fields
                "device_id": "ABC123DEF456",
                "device_name": "Living Room",
                "eco_mode": True,
                "leaf": True,
                "heat_stage": 1,
                "cool_stage": 0,
                "connected_sensors": 2,
                "average_temperature": 21.0,
                # Override source to specify Nest
                "source": "nest",
            },
        }


def main() -> None:
    """This allows testing the data model."""
    NestAmbientDataModel.test_model_main()


if __name__ == "__main__":
    main()
