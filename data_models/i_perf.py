"""
This module defines the performance data model for Indaleko.

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
import uuid

from datetime import UTC, datetime
from typing import Any, TypeVar

from pydantic import AwareDatetime, Field, field_validator


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

T = TypeVar("T", bound="IndalekoPerformanceDataModel")

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel  # noqa: E402
from data_models.record import IndalekoRecordDataModel  # noqa: E402


# pylint: enable=wrong-import-position


class IndalekoPerformanceDataModel(IndalekoBaseModel):
    """
    This class defines the data model for the Indaleko performance data.
    """

    Record: IndalekoRecordDataModel = Field(
        None,
        title="Record",
        description="The record associated with the performance data.",
    )

    MachineConfigurationId: uuid.UUID | None = Field(
        None,
        title="MachineConfigurationId",
        description="The UUID for the machine configuration (e.g. a reference "
        "to the relevant record in the MachineConfig collection).",
    )

    StartTimestamp: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        title="StartTimestamp",
        description="The timestamp of when collection of this performance data was started.",
    )

    EndTimestamp: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        title="EndTimestamp",
        description="The timestamp of when collection of this performance data was ended.",
    )

    ElapsedTime: float | None = Field(
        None,
        title="ElapsedTime",
        description="The elapsed time in seconds.",
    )

    UserCPUTime: float = Field(
        ...,
        title="UserCPUTime",
        description="The user CPU time in seconds.",
    )

    SystemCPUTime: float = Field(
        ...,
        title="SystemCPUTime",
        description="The system CPU time in seconds.",
    )

    InputSize: int | None = Field(
        None,
        title="InputSize",
        description="The size of the input data in bytes.",
    )

    OutputSize: int | None = Field(
        None,
        title="OutputSize",
        description="The size of the output data in bytes.",
    )

    PeakMemoryUsage: int | None = Field(
        None,
        title="PeakMemoryUsage",
        description="The peak memory usage in bytes.",
    )

    IOReadBytes: int | None = Field(
        None,
        title="IOReadBytes",
        description="The number of bytes read during execution.",
    )

    IOWriteBytes: int | None = Field(
        None,
        title="IOWriteBytes",
        description="The number of bytes written during execution.",
    )

    ThreadCount: int | None = Field(
        None,
        title="ThreadCount",
        description="The number of threads used.",
    )

    ErrorCount: int | None = Field(
        None,
        title="ErrorCount",
        description="The number of errors encountered.",
    )

    AdditionalData: dict[str, Any] | None = Field(
        default_factory=dict,
        title="AdditionalData",
        description="Additional performance data.",
    )

    @staticmethod
    def validate_timestamp(ts: str | datetime) -> datetime:
        """Ensure that the timestamp is in UTC"""
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        return ts

    @field_validator("StartTimestamp", mode="before")
    @classmethod
    def ensure_starttime(cls, value: datetime):
        return cls.validate_timestamp(value)

    @field_validator("EndTimestamp", mode="before")
    @classmethod
    def ensure_endtime(cls, value: datetime):
        return cls.validate_timestamp(value)

    @field_validator("ElapsedTime", mode="before")
    @classmethod
    def calculate_elapsed_time(
        cls: type[T],
        value: float | None = None,
        values: dict[str, Any] | None = None,
    ) -> float:
        """Calculate the elapsed time if it is not provided."""
        if value is None:
            start = values.get("StartTimestamp", datetime.now(UTC))
            end = values.get("EndTimestamp", datetime.now(UTC))
            value = (end - start).total_seconds()
        return value

    class Config:
        """Sample configuration data for the data model."""

        json_schema_extra = {
            "example": {
                "Record": {
                    "SourceIdentifier": {
                        "Identifier": "429f1f3c-7a21-463f-b7aa-cd731bb202b1",
                        "Version": "1.0",
                    },
                    "Timestamp": "2024-07-30T23:38:48.319654+00:00",
                    "Attributes": {"Key": "Value"},
                    "Data": "Base64EncodedData",
                },
                "MachineConfigurationId": "a8343055-7d85-4424-b83e-9fa413a7ebf7",
                "StartTimestamp": "2024-07-30T23:38:48.319654+00:00",
                "EndTimestamp": "2024-07-30T23:38:48.319654+00:00",
                "ElapsedTime": 0.0,
                "UserCPUTime": 0.0,
                "SystemCPUTime": 0.0,
                "InputSize": 0,
                "OutputSize": 0,
                "PeakMemoryUsage": 0,
                "IOReadBytes": 0,
                "IOWriteBytes": 0,
                "ThreadCount": 0,
                "ErrorCount": 0,
                "AdditionalData": {
                    "Files": 14279384,
                    "Directories": 62172,
                },
            },
        }


def main():
    """This allows testing the data model."""
    IndalekoPerformanceDataModel.test_model_main()


if __name__ == "__main__":
    main()
