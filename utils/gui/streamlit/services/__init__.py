"""Services module for Indaleko Streamlit GUI.

Contains data access and business logic services used by UI components.

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

from indaleko.utils.gui.streamlit.services.config import get_config_files
from indaleko.utils.gui.streamlit.services.database import (
    get_activity_timeline,
    get_db_stats,
    get_file_type_distribution,
    get_storage_summary,
)
from indaleko.utils.gui.streamlit.services.query import execute_query


__all__ = [
    "execute_query",
    "get_activity_timeline",
    "get_config_files",
    "get_db_stats",
    "get_file_type_distribution",
    "get_storage_summary",
]
