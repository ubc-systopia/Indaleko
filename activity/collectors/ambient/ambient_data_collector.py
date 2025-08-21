"""
This module defines a common base for ambient data collectors.

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


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
# from activity.data_model.activity import IndalekoActivityDataModel
# pylint: enable=wrong-import-position


class BaseAmbientDataCollector:
    """
    This class provides a common base for ambient data collectors. Typically an
    ambient data _collector_ will be associated with an ambient data _provider_.
    The latter is responsible for actually collecting the data, and the former is
    responsible for interpreting the data and storing it in the database.
    """

    def __init__(self, **kwargs) -> None:
        self.config = kwargs.get("config", {})
        self.data = []

    def collect_data(self) -> None:
        """Collect ambient data. This method should be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement this method")

    def process_data(self, data: Any) -> dict[str, Any]:
        """Process the collected data. This method should be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement this method")

    def store_data(self, data: dict[str, Any]) -> None:
        """Store the processed data. This method should be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement this method")

    def get_description(self) -> str:
        """Get a description of the ambient data collector. This method can be overridden by subclasses."""
        return "Base class for ambient data collectors"

    def get_latest_db_update(self) -> dict[str, Any]:
        """Get the latest data update from the database. This method should be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement this method")

    def update_data(self) -> None:
        """Update the data in the database. This method should be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement this method")
