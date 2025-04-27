"""
This module is a location activity data provider for Indaleko.

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

from typing import Any

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# This logic is part of what allows me to execute it locally or as part of the
# overall package/project.  It's a bit of a hack, but it works.
# pylint: disable=wrong-import-position
from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.base import CollectorBase


# pylint: enable=wrong-import-position


class CollaborationCollector(CollectorBase):
    """This is a collaboration activity data provider for Indaleko."""

    def get_collector_characteristics(self) -> list[ActivityDataCharacteristics]:
        return []

    def get_collector_name(self) -> str:
        return "CollaborationCollector"

    def get_provider_id(self) -> uuid.UUID:
        return uuid.uuid4()

    def retrieve_data(self, data_id: uuid.UUID) -> dict:
        return {}

    def get_cursor(self, activity_context: uuid.UUID) -> uuid.UUID:
        return uuid.uuid4()

    def cache_duration(self) -> datetime.timedelta:
        return datetime.timedelta(hours=1)

    def get_description(self) -> str:
        return "Collaboration data provider for Indaleko."

    def get_json_schema(self) -> dict:
        return {}

    def collect_data(self) -> None:
        pass

    def process_data(self, data: Any) -> dict[str, Any]:
        return {}

    def store_data(self, data: dict[str, Any]) -> None:
        pass

    def update_data(self) -> None:
        pass

    def get_latest_db_update(self) -> dict[str, Any]:
        return {}


def main():
    """This is a test interface for the location provider."""
    ic("Test the collaboration collector class.")
    ic("Not implemented yet.")


if __name__ == "__main__":
    main()
