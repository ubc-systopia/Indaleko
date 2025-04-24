"""
Activity component for Indaleko Streamlit GUI

This module provides the activity context visualization.

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

import plotly.graph_objects as go
import streamlit as st

from utils.gui.streamlit.components.common import normalize_for_display
from utils.gui.streamlit.components.connection import connect_to_db


def render_activity():
    """
    Render the activity timeline and context visualization

    Shows activity over time, with location and context information
    """
    st.markdown("<div class='main-header'>Activity</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='sub-header'>View and understand your activity context</div>",
        unsafe_allow_html=True,
    )

    # Auto-connect in demo mode if not connected
    if not st.session_state.db_connected:
        db_service, db_info = connect_to_db("mock_config")
        st.session_state.db_connected = True
        st.session_state.db_service = db_service
        st.session_state.db_info = db_info

    # Activity visualization
    st.info(
        "This page visualizes your activity context data, showing how your files relate to your activities.",
    )

    # Timeline selector
    timeline_options = [
        "Today",
        "Last 7 Days",
        "Last 30 Days",
        "Last 90 Days",
        "Custom Range",
    ]
    selected_timeline = st.selectbox("Select Time Range", timeline_options)

    if selected_timeline == "Custom Range":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date")
        with col2:
            end_date = st.date_input("End Date")

    # Activity type selector
    activity_types = [
        "All Activities",
        "File Operations",
        "Communication",
        "Meetings",
        "Location",
        "Ambient Conditions",
    ]
    selected_activity_types = st.multiselect(
        "Activity Types",
        activity_types,
        default=["All Activities"],
    )

    # Activity context visualization (mock data)
    st.subheader("Activity Timeline")

    # Mock data for timeline visualization
    dates = [
        "2025-04-01",
        "2025-04-02",
        "2025-04-03",
        "2025-04-04",
        "2025-04-05",
        "2025-04-06",
        "2025-04-07",
    ]
    file_activities = [5, 12, 8, 15, 10, 3, 7]
    communication = [3, 5, 7, 2, 8, 4, 6]
    meetings = [1, 0, 2, 3, 1, 0, 0]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=dates, y=file_activities, name="File Activities"))
    fig.add_trace(go.Bar(x=dates, y=communication, name="Communication"))
    fig.add_trace(go.Bar(x=dates, y=meetings, name="Meetings"))

    fig.update_layout(
        title="Activity by Day",
        xaxis_title="Date",
        yaxis_title="Activity Count",
        barmode="stack",
    )

    st.plotly_chart(fig, use_container_width=True)

    # Activity details
    st.subheader("Activity Details")

    # Mock data for detailed activity
    activities = [
        {
            "timestamp": "2025-04-07 14:32:00",
            "type": "file_created",
            "description": "Created presentation.pptx",
            "location": "Home Office",
        },
        {
            "timestamp": "2025-04-07 13:15:00",
            "type": "meeting",
            "description": "Team Standup",
            "location": "Home Office",
        },
        {
            "timestamp": "2025-04-07 11:45:00",
            "type": "email",
            "description": "Sent document to Bob",
            "location": "Coffee Shop",
        },
        {
            "timestamp": "2025-04-07 10:30:00",
            "type": "file_modified",
            "description": "Updated budget.xlsx",
            "location": "Coffee Shop",
        },
        {
            "timestamp": "2025-04-06 16:20:00",
            "type": "file_viewed",
            "description": "Viewed project_proposal.pdf",
            "location": "Office",
        },
    ]

    try:
        # Normalize activities for display
        normalized_activities = [normalize_for_display(activity) for activity in activities]
        st.dataframe(normalized_activities, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not display activities as table: {e}")
        for activity in activities:
            st.json(activity)

    # Activity map
    st.subheader("Activity Locations")
    st.info("Location map visualization will be added in a future update.")
