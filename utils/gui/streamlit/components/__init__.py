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

from indaleko.utils.gui.streamlit.components.activity import render_activity
from indaleko.utils.gui.streamlit.components.analytics import render_analytics
from indaleko.utils.gui.streamlit.components.common import (
    display_query_plan,
    display_search_results,
    normalize_for_display,
)
from indaleko.utils.gui.streamlit.components.connection import (
    connect_to_db,
    render_connection_status,
)
from indaleko.utils.gui.streamlit.components.dashboard import render_dashboard
from indaleko.utils.gui.streamlit.components.search import render_search
from indaleko.utils.gui.streamlit.components.settings import render_settings
from indaleko.utils.gui.streamlit.components.sidebar import render_sidebar


# Make these available at the component module level
__all__ = [
    "connect_to_db",
    "display_query_plan",
    "display_search_results",
    "normalize_for_display",
    "render_activity",
    "render_analytics",
    "render_connection_status",
    "render_dashboard",
    "render_search",
    "render_settings",
    "render_sidebar",
]
