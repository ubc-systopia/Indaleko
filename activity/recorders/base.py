"""
This is the abstract base class that activity data recorders use.

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

# pylint: enable=wrong-import-position


class RecorderBase(ABC):
    """
    Abstract base class for activity data providers.

    Note: this class is fairly minimal, and I expect that it will grow as we
    develop the system further.
    """

    @abstractmethod
    def get_recorder_characteristics(self) -> list[ActivityDataCharacteristics]:
        """
        This call returns the characteristics of the data provider.  This is
        intended to be used to help users understand the data provider and to
        help the system understand how to interact with the data provider.

        Returns:
            Dict: A dictionary containing the characteristics of the provider.
        """

    @abstractmethod
    def get_recorder_name(self) -> str:
        """Get the name of the recorder"""

    @abstractmethod
    def get_collector_class_model(self) -> dict[str, type]:
        """Get the class models for the collector(s) used by this recorder."""

    @abstractmethod
    def get_recorder_id(self) -> uuid.UUID:
        """Get the UUID for the recorder"""

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
    def process_data(self, data: Any) -> dict[str, Any]:
        """Process the collected data"""

    @abstractmethod
    def store_data(self, data: dict[str, Any]) -> None:
        """Store the processed data"""

    @abstractmethod
    def update_data(self) -> None:
        """Update the data in the database"""

    @abstractmethod
    def get_latest_db_update(self) -> dict[str, Any]:
        """Get the latest data update from the database"""


def main():
    """This is a test interface for the recorder base."""
    ic("RecorderBase test interface")


if __name__ == "__main__":
    main()
