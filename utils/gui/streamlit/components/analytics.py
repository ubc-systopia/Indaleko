"""
Analytics component for Indaleko Streamlit GUI

This module provides data visualization and analytics capabilities.

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

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from utils.gui.streamlit.services.database import (
    get_storage_summary, 
    get_file_type_distribution, 
    get_activity_timeline
)
from utils.gui.streamlit.components.connection import connect_to_db

def render_analytics():
    """
    Render the analytics page with charts and visualizations
    
    Includes:
    - Storage analysis
    - Activity analysis
    - Relationship analysis
    - Insights
    """
    st.markdown("<div class='main-header'>Analytics</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Visualize and analyze your data</div>", unsafe_allow_html=True)

    # Auto-connect in demo mode if not connected
    if not st.session_state.db_connected:
        db_service, db_info = connect_to_db("mock_config")
        st.session_state.db_connected = True
        st.session_state.db_service = db_service
        st.session_state.db_info = db_info

    # Analytics tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Storage", "Activities", "Relationships", "Insights"])

    with tab1:
        st.subheader("Storage Analysis")

        # Storage distribution by type
        storage_data = get_storage_summary(st.session_state.db_service)
        if storage_data:
            fig = px.bar(storage_data, x="storage", y="count", title="Files by Storage Volume")
            st.plotly_chart(fig, use_container_width=True)

        # File type distribution
        file_types = get_file_type_distribution(st.session_state.db_service)
        if file_types:
            fig = px.pie(file_types, values="count", names="extension", title="Top File Extensions")
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Activity Analysis")

        # Activity timeline
        activity_data = get_activity_timeline(st.session_state.db_service)
        if activity_data:
            fig = px.line(activity_data, x="date", y="count", title="Activity Over Time")
            st.plotly_chart(fig, use_container_width=True)

        # Placeholder for more activity charts
        st.info("Additional activity visualizations will be added in future updates.")

    with tab3:
        st.subheader("Relationship Analysis")

        # Placeholder for relationship visualization
        st.info("Relationship visualizations will be added in future updates.")

        # Mockup of a relationship graph
        nodes = [
            {"id": 1, "label": "User", "group": 1},
            {"id": 2, "label": "Document.pdf", "group": 2},
            {"id": 3, "label": "Report.docx", "group": 2},
            {"id": 4, "label": "Colleague", "group": 1},
            {"id": 5, "label": "Meeting.ics", "group": 3},
            {"id": 6, "label": "Project_Plan.xlsx", "group": 2},
        ]

        edges = [
            {"from": 1, "to": 2, "label": "created"},
            {"from": 1, "to": 3, "label": "modified"},
            {"from": 1, "to": 4, "label": "shared_with"},
            {"from": 4, "to": 3, "label": "viewed"},
            {"from": 1, "to": 5, "label": "participated"},
            {"from": 5, "to": 6, "label": "referenced"},
            {"from": 4, "to": 6, "label": "created"},
        ]

        st.json({"nodes": nodes, "edges": edges})

        st.write("Network visualization will be implemented in a future update.")

    with tab4:
        st.subheader("Insights")

        # Placeholder for insights
        st.info("Automated insights will be added in future updates.")

        # Mock insights
        st.markdown("""
        #### Sample Insights:

        1. **Collaboration Patterns**
           - You collaborate most frequently with Bob on PDF documents
           - Wednesday is your most active day for file sharing

        2. **File Usage Patterns**
           - 60% of Excel files are only accessed once after creation
           - You create most text documents between 2-4 PM

        3. **Storage Optimization**
           - 120 MB of duplicate files detected across devices
           - 240 MB of files haven't been accessed in over a year
        """)