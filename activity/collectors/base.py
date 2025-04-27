"""
This is the abstract base class that activity data providers use.

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
from abc import ABC, abstractmethod
from typing import Any

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.data_model import IndalekoActivityCollectorDataModel
from utils.misc.directory_management import (
    indaleko_default_config_dir,
    indaleko_default_data_dir,
    indaleko_default_log_dir,
)
from utils.misc.file_name_management import indaleko_file_name_prefix

# pylint: enable=wrong-import-position


class CollectorBase(ABC):
    """
    Abstract base class for activity data providers.

    Note: this class is fairly minimal, and I expect that it will grow as we
    develop the system further.
    """

    @abstractmethod
    def get_collector_characteristics(self) -> list[ActivityDataCharacteristics]:
        """
        This call returns the characteristics of the data provider.  This is
        intended to be used to help users understand the data provider and to
        help the system understand how to interact with the data provider.

        Returns:
            Dict: A dictionary containing the characteristics of the provider.
        """

    @abstractmethod
    def get_collector_name(self) -> str:
        """Get the name of the provider"""

    @abstractmethod
    def get_provider_id(self) -> uuid.UUID:
        """Get the UUID for the provider"""

    @abstractmethod
    def retrieve_data(self, data_id: uuid.UUID) -> dict:
        """
        This call retrieves the data associated with the provided data_id.

        Args:
            data_id (uuid.UUID): The UUID that represents the data to be
            retrieved.

        Returns:
            Dict: The data associated with the data_id.
        """

    @abstractmethod
    def get_cursor(self, activity_context: uuid.UUID) -> uuid.UUID:
        """Retrieve the current cursor for this data provider
        Input:
             activity_context: the activity context into which this cursor is
             being used
         Output:
             The cursor for this data provider, which can be used to retrieve
             data from this provider (via the retrieve_data call).
        """

    @abstractmethod
    def cache_duration(self) -> datetime.timedelta:
        """
        Retrieve the maximum duration that data from this provider may be
        cached
        """

    @abstractmethod
    def get_description(self) -> str:
        """
        Retrieve a description of the data provider. Note: this is used for
        prompt construction, so please be concise and specific in your
        description.
        """

    @abstractmethod
    def get_json_schema(self) -> dict:
        """
        Retrieve the JSON data schema to use for the database.
        """

    @abstractmethod
    def collect_data(self) -> None:
        """Collect data from the provider"""

    @abstractmethod
    def process_data(self, data: Any) -> dict[str, Any]:
        """Process the collected data"""

    @abstractmethod
    def store_data(self, data: dict[str, Any]) -> None:
        """Store the processed data"""


class BaseActivityCollector:
    """
    This is the base class for Indaleko storage collectors.  It provides
    fundamental mechanisms for managing the data and configuration files
    that are used by the collectors.
    """

    collector_data = IndalekoActivityCollectorDataModel(
        PlatformName=None,
        ServiceRegistrationName="Indaleko Generic Activity Collector",
        ServiceFileName="activity_collector",
        ServiceUUID=uuid.UUID("6a1b20e8-2a75-4f6b-a1b2-05bd0bb84fb5"),
        ServiceVersion="1.0",
        ServiceDescription="Base Indaleko activity collector. Do not use.",
    )

    # default values, override in the child class
    cli_handler_mixin = None
    requires_machine_config = False
    file_prefix = indaleko_file_name_prefix
    file_suffix = ".jsonl"

    def __init__(self, **kwargs):
        if self.requires_machine_config:
            assert "machine_config" in kwargs, "machine_config must be specified"
            self.machine_config = kwargs["machine_config"]
            if "machine_id" not in kwargs:
                kwargs["machine_id"] = self.machine_config.machine_id
        self.debug = kwargs.get("debug", False)
        self.offline = False
        if "offline" in kwargs:
            self.offline = kwargs["offline"]
            del kwargs["offline"]
        if self.debug:
            ic(self.offline)
        if "collector_data" in kwargs:
            self.collector_data = kwargs["collector_data"]
        assert hasattr(self, "collector_data"), "collector_data must either be passed in or created in derived class"
        self.platform = kwargs.get("platform", self.collector_data.PlatformName)
        self.file_prefix = kwargs.get(
            "file_prefix",
            BaseActivityCollector.file_prefix,
        ).replace("-", "_")
        self.file_suffix = kwargs.get(
            "file_suffix",
            BaseActivityCollector.file_suffix,
        ).replace("-", "_")
        self.data_dir = kwargs.get("data_dir", indaleko_default_data_dir)
        assert os.path.isdir(
            self.data_dir,
        ), f"{self.data_dir} must be an existing directory"
        self.config_dir = kwargs.get("config_dir", indaleko_default_config_dir)
        assert os.path.isdir(
            self.data_dir,
        ), f"{self.data_dir} must be an existing directory"
        self.log_dir = kwargs.get("log_dir", indaleko_default_log_dir)
        assert os.path.isdir(
            self.data_dir,
        ), f"{self.data_dir} must be an existing directory"
        self.timestamp = kwargs.get(
            "timestamp",
            datetime.datetime.now(datetime.UTC).isoformat(),
        )
        assert isinstance(self.timestamp, str), "timestamp must be a string"
        assert hasattr(self, "collector_data"), "Must be created by derived class"
        self.machine_id = None
        self.storage_description = None
        if self.requires_machine_config:
            if "machine_id" in kwargs:
                self.machine_id = kwargs["machine_id"]
            else:
                assert "machine_config" in kwargs, "machine_config must be specified"
                self.machine_config = kwargs["machine_config"]
                self.machine_id = self.machine_config.machine_id
            assert hasattr(self, "machine_id")
            if "storage_description" in kwargs:
                assert isinstance(kwargs["storage_description"], str), (
                    "storage_description must be a string, " f'not {type(kwargs["storage_description"])}'
                )
                self.storage_description = kwargs["storage_description"]
        self.path = kwargs.get("path", None)
        self.collector_service = None
        if not self.offline:
            ic("might want to add registration here")


def main():
    """This is a test interface for the provider base."""
    ic("ProviderBase test interface")


if __name__ == "__main__":
    main()
