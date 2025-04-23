"""
Dashboard component for Indaleko Streamlit GUI

This module provides the dashboard view with metrics and charts.

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

import plotly.express as px
import streamlit as st

from utils.gui.streamlit.components.connection import connect_to_db
from utils.gui.streamlit.services.database import (
    get_activity_timeline,
    get_db_stats,
    get_file_type_distribution,
    get_storage_summary,
)
from utils.gui.streamlit.services.query import execute_query


def render_dashboard():
    """
    Render the main dashboard with overview metrics and charts

    Shows database stats, storage distribution, file types, and activity timeline.
    Also includes a quick search function.
    """
    st.markdown("<div class='main-header'>Dashboard</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='sub-header'>Overview of your Unified Personal Index</div>",
        unsafe_allow_html=True,
    )

    # Auto-connect in demo mode if not connected
    if not st.session_state.db_connected:
        db_service, db_info = connect_to_db("mock_config")
        st.session_state.db_connected = True
        st.session_state.db_service = db_service
        st.session_state.db_info = db_info

    # Get database stats
    stats = get_db_stats(st.session_state.db_info)

    if stats:
        # Stats cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(
                f"""
            <div class="card">
                <div class="metric-value">{stats["collections"]}</div>
                <div class="metric-label">Collections</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown(
                f"""
            <div class="card">
                <div class="metric-value">{stats["documents"]}</div>
                <div class="metric-label">Documents</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col3:
            st.markdown(
                f"""
            <div class="card">
                <div class="metric-value">{stats["indexes"]}</div>
                <div class="metric-label">Indexes</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col4:
            st.markdown(
                f"""
            <div class="card">
                <div class="metric-value">{stats["size"]}</div>
                <div class="metric-label">Database Size</div>
            </div>
            """,
                unsafe_allow_html=True,
            )

    # Storage summary
    storage_data = get_storage_summary(st.session_state.db_service)
    if storage_data:
        st.subheader("Storage Summary")
        fig = px.pie(
            storage_data,
            values="count",
            names="storage",
            title="Files by Storage Volume",
        )
        st.plotly_chart(fig, use_container_width=True)

    # File type distribution
    file_types = get_file_type_distribution(st.session_state.db_service)
    if file_types:
        st.subheader("File Type Distribution")
        fig = px.bar(file_types, x="extension", y="count", title="Top File Extensions")
        st.plotly_chart(fig, use_container_width=True)

    # Recent activity
    activity_data = get_activity_timeline(st.session_state.db_service)
    if activity_data:
        st.subheader("Activity Timeline")
        fig = px.line(activity_data, x="date", y="count", title="Activity Over Time")
        st.plotly_chart(fig, use_container_width=True)

    # Quick search
    st.subheader("Quick Search")
    col1, col2 = st.columns([4, 1])
    with col1:
        quick_query = st.text_input("Search your personal index")
    with col2:
        quick_debug = st.checkbox(
            "Debug", help="Show detailed diagnostic information during search",
        )

    if quick_query:
        with st.spinner("Searching..."):
            results = execute_query(
                quick_query, st.session_state.db_service, debug=quick_debug,
            )
            if results:
                st.subheader("Results")

                # Check if results is a list or dict before trying to slice
                if isinstance(results, (list, tuple)):
                    # Display up to 5 items
                    items_to_show = results[:5] if len(results) > 5 else results
                    st.json(items_to_show)
                    if len(results) > 5:
                        st.info(
                            f"Showing 5 of {len(results)} results. Go to Search for more.",
                        )
                elif isinstance(results, dict):
                    # Display the dictionary
                    st.json(results)
                else:
                    # For any other type, convert to string
                    st.code(str(results))

                if st.button("Go to Search"):
                    st.session_state.current_page = "search"
                    st.session_state.query_results = results
                    st.experimental_rerun()
