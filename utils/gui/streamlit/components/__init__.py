"""Component module for Indaleko Streamlit GUI.

Contains UI components that make up the modular interface.

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

from .dashboard import render_dashboard
from .search import render_search
from .analytics import render_analytics
from .activity import render_activity
from .settings import render_settings
from .sidebar import render_sidebar
from .connection import render_connection_status, connect_to_db
from .common import normalize_for_display, display_search_results, display_query_plan

# Make these available at the component module level
__all__ = [
    'render_dashboard',
    'render_search',
    'render_analytics',
    'render_activity',
    'render_settings',
    'render_sidebar',
    'render_connection_status',
    'connect_to_db',
    'normalize_for_display',
    'display_search_results',
    'display_query_plan',
]