"""
This module defines the data model for the EXIF metadata collector.

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

# standard imports
import os
import sys
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

# third-party imports
from pydantic import Field, field_validator

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Indaleko imports
from semantic.data_models.base_data_model import BaseSemanticDataModel


class ExifGpsData(BaseSemanticDataModel):
    """EXIF GPS data model."""

    latitude: float | None = Field(
        None, description="GPS latitude in decimal degrees",
    )
    longitude: float | None = Field(
        None, description="GPS longitude in decimal degrees",
    )
    altitude: float | None = Field(None, description="GPS altitude in meters")
    timestamp: datetime | None = Field(None, description="GPS timestamp")
    map_datum: str | None = Field(None, description="GPS map datum")


class ExifCameraData(BaseSemanticDataModel):
    """Camera information from EXIF data."""

    make: str | None = Field(None, description="Camera manufacturer")
    model: str | None = Field(None, description="Camera model")
    serial_number: str | None = Field(None, description="Camera serial number")
    lens_make: str | None = Field(None, description="Lens manufacturer")
    lens_model: str | None = Field(None, description="Lens model")
    lens_serial_number: str | None = Field(None, description="Lens serial number")


class ExifCaptureSettings(BaseSemanticDataModel):
    """Capture settings from EXIF data."""

    datetime_original: datetime | None = Field(
        None, description="Date and time when the original image was generated",
    )
    datetime_digitized: datetime | None = Field(
        None, description="Date and time when the image was stored as digital data",
    )
    exposure_time: float | None = Field(None, description="Exposure time in seconds")
    f_number: float | None = Field(None, description="F-number (relative aperture)")
    iso: int | None = Field(None, description="ISO speed rating")
    focal_length: float | None = Field(
        None, description="Focal length in millimeters",
    )
    exposure_bias: float | None = Field(None, description="Exposure bias in EV")
    metering_mode: str | None = Field(None, description="Metering mode")
    flash: str | None = Field(None, description="Flash status")


class ExifImageInfo(BaseSemanticDataModel):
    """Image information from EXIF data."""

    width: int | None = Field(None, description="Image width in pixels")
    height: int | None = Field(None, description="Image height in pixels")
    bits_per_sample: int | None = Field(
        None, description="Number of bits per component",
    )
    compression: str | None = Field(None, description="Compression scheme")
    photometric_interpretation: str | None = Field(
        None, description="Pixel composition",
    )
    orientation: str | None = Field(None, description="Orientation of image")
    samples_per_pixel: int | None = Field(
        None, description="Number of components per pixel",
    )
    planar_configuration: str | None = Field(
        None, description="Image data arrangement",
    )
    software: str | None = Field(None, description="Software used")
    artist: str | None = Field(None, description="Person who created the image")
    copyright: str | None = Field(None, description="Copyright information")
    user_comment: str | None = Field(None, description="User comments")


class ExifDataModel(BaseSemanticDataModel):
    """
    This class defines the data model for EXIF metadata.
    Includes camera information, capture settings, GPS data, and image information.
    """

    exif_data_id: UUID = Field(
        default_factory=uuid4,
        description="The unique identifier for the EXIF metadata record.",
    )

    # Raw EXIF data dictionary for advanced use cases
    raw_exif: dict[str, Any] = Field(
        default_factory=dict, description="Raw EXIF data in key-value format",
    )

    # Structured EXIF data
    camera: ExifCameraData | None = Field(None, description="Camera information")
    capture_settings: ExifCaptureSettings | None = Field(
        None, description="Capture settings",
    )
    gps: ExifGpsData | None = Field(None, description="GPS data")
    image_info: ExifImageInfo | None = Field(None, description="Image information")

    @classmethod
    @field_validator("exif_data_id")
    def validate_exif_data_id(cls, value):
        if not isinstance(value, UUID):
            raise ValueError("EXIF data ID must be a UUID")
        return value

    class Config:
        @staticmethod
        def schema_extra() -> dict:
            base_example = BaseSemanticDataModel.Config.json_schema_extra["example"]
            return {
                "example": {
                    **base_example,
                    "exif_data_id": "123e4567-e89b-12d3-a456-426614174000",
                    "raw_exif": {
                        "Make": "Canon",
                        "Model": "Canon EOS 5D Mark IV",
                        "ExposureTime": "1/125",
                        "FNumber": "4.0",
                        "ISOSpeedRatings": "400",
                    },
                    "camera": {
                        "make": "Canon",
                        "model": "Canon EOS 5D Mark IV",
                        "lens_model": "EF24-70mm f/4L IS USM",
                    },
                    "capture_settings": {
                        "datetime_original": "2023-07-15T14:22:36",
                        "exposure_time": 0.008,
                        "f_number": 4.0,
                        "iso": 400,
                        "focal_length": 50.0,
                    },
                    "gps": {
                        "latitude": 37.773972,
                        "longitude": -122.431297,
                        "altitude": 12.5,
                    },
                    "image_info": {
                        "width": 6720,
                        "height": 4480,
                        "software": "Adobe Photoshop Lightroom Classic 12.0",
                        "artist": "John Doe",
                    },
                },
            }

        json_schema_extra = {
            "example": {
                **BaseSemanticDataModel.Config.json_schema_extra["example"],
                "exif_data_id": "123e4567-e89b-12d3-a456-426614174000",
                "raw_exif": {
                    "Make": "Canon",
                    "Model": "Canon EOS 5D Mark IV",
                    "ExposureTime": "1/125",
                    "FNumber": "4.0",
                    "ISOSpeedRatings": "400",
                },
                "camera": {
                    "make": "Canon",
                    "model": "Canon EOS 5D Mark IV",
                    "lens_model": "EF24-70mm f/4L IS USM",
                },
                "capture_settings": {
                    "datetime_original": "2023-07-15T14:22:36",
                    "exposure_time": 0.008,
                    "f_number": 4.0,
                    "iso": 400,
                    "focal_length": 50.0,
                },
                "gps": {
                    "latitude": 37.773972,
                    "longitude": -122.431297,
                    "altitude": 12.5,
                },
                "image_info": {
                    "width": 6720,
                    "height": 4480,
                    "software": "Adobe Photoshop Lightroom Classic 12.0",
                    "artist": "John Doe",
                },
            },
        }


def main():
    """Test code for the EXIF data model"""
    ExifDataModel.test_model_main()


if __name__ == "__main__":
    main()
