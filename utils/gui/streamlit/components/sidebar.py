"""
Sidebar component for Indaleko Streamlit GUI.

This module provides the navigation sidebar for the application.

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

import streamlit as st

from utils.gui.streamlit.components.connection import (
    connect_to_db,
    render_connection_status,
)
from utils.gui.streamlit.services.config import get_config_files


def render_sidebar() -> None:
    """
    Render the navigation sidebar for the application.

    Includes:
    - Logo/title
    - Database connection management
    - Navigation buttons for different sections
    - Version/copyright information
    """
    with st.sidebar:
        # Try to show logo, fall back to text if not found
        try:
            image_path = os.path.join(
                os.environ.get("INDALEKO_ROOT"),
                "figures",
                "indaleko-arch.png",
            )
            if os.path.exists(image_path):
                st.image(image_path, use_container_width=True)
            else:
                st.title("Indaleko")
        except Exception:
            st.title("Indaleko")

        # Database connection section
        st.subheader("Database Connection")

        # Show connection status
        render_connection_status()

        # Create two columns: config selection and options
        col1, col2 = st.columns([3, 1])

        with col1:
            config_files = get_config_files()

            if not config_files:
                st.warning("No database configuration files found.")
                if st.button("Setup Database"):
                    st.session_state.current_page = "setup"
            else:
                selected_config = st.selectbox("Select Config", config_files)

        with col2:
            # Add a debug toggle
            st.session_state.connect_debug = st.checkbox(
                "Debug",
                value=st.session_state.connect_debug,
            )

        # Connection button - full width
        if config_files and st.button("Connect", use_container_width=True):
            db_service, db_info = connect_to_db(selected_config)
            if db_service:
                st.session_state.db_connected = True
                st.session_state.db_service = db_service
                st.session_state.db_info = db_info
                if st.session_state.using_real_db:
                    st.success("Connected to real database!")
                else:
                    st.warning("Connected to mock database.")
                st.experimental_rerun()
            else:
                st.error("Failed to connect to database.")

        # Navigation section
        st.subheader("Navigation")

        if st.button("Dashboard", key="nav_dashboard"):
            st.session_state.current_page = "dashboard"

        if st.button("Search", key="nav_search"):
            st.session_state.current_page = "search"

        if st.button("Analytics", key="nav_analytics"):
            st.session_state.current_page = "analytics"

        if st.button("Activity", key="nav_activity"):
            st.session_state.current_page = "activity"

        if st.button("Settings", key="nav_settings"):
            st.session_state.current_page = "settings"

        # Demo mode notice
        st.markdown("---")
        if not st.session_state.using_real_db:
            st.caption("⚠️ Running in demo mode with mock data")
        else:
            st.caption("Connected to real database")

        # Footer
        st.markdown("---")
        st.caption("© 2024-2025 Indaleko Project")
