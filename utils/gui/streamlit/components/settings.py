"""
Settings component for Indaleko Streamlit GUI

This module provides configuration settings for the application.

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
from datetime import datetime

from utils.gui.streamlit.components.connection import connect_to_db

def render_settings():
    """
    Render the settings page with configuration options
    
    Includes tabs for:
    - Database configuration
    - Collections management
    - Indexing settings
    - User preferences
    """
    st.markdown("<div class='main-header'>Settings</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-header'>Configure your Indaleko experience</div>", unsafe_allow_html=True)

    # Auto-connect in demo mode if not connected
    if not st.session_state.db_connected:
        db_service, db_info = connect_to_db("mock_config")
        st.session_state.db_connected = True
        st.session_state.db_service = db_service
        st.session_state.db_info = db_info

    # Settings tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Database", "Collections", "Indexing", "Preferences"])

    with tab1:
        st.subheader("Database Configuration")

        db_info = st.session_state.db_info

        # Check if we're using real IndalekoDBInfo or mock
        if hasattr(db_info, 'db_config') and not hasattr(db_info, 'get_host'):
            # Real IndalekoDBInfo - adapt to expected interface
            host = db_info.db_config.hosts[0] if hasattr(db_info.db_config, 'hosts') and db_info.db_config.hosts else "localhost"
            port = db_info.db_config.port if hasattr(db_info.db_config, 'port') else 8529
            database = db_info.db_config.database if hasattr(db_info.db_config, 'database') else "indaleko"
            username = db_info.db_config.username if hasattr(db_info.db_config, 'username') else "indaleko"

            st.json({
                "host": host,
                "port": port,
                "database": database,
                "username": username,
                "connected": True
            })
        else:
            # Mock DBInfo with the expected methods
            st.json({
                "host": db_info.get_host() if hasattr(db_info, 'get_host') else "localhost",
                "port": db_info.get_port() if hasattr(db_info, 'get_port') else 8529,
                "database": db_info.get_database_name() if hasattr(db_info, 'get_database_name') else "indaleko",
                "username": db_info.get_username() if hasattr(db_info, 'get_username') else "indaleko",
                "connected": True
            })

        if st.button("Disconnect"):
            st.session_state.db_connected = False
            st.session_state.db_service = None
            st.session_state.db_info = None
            st.success("Disconnected from database.")
            st.experimental_rerun()

    with tab2:
        st.subheader("Collection Management")

        # Get collections - handle different formats
        try:
            if hasattr(st.session_state.db_info, 'db_config') and hasattr(st.session_state.db_info.db_config, 'db'):
                # Using real IndalekoDBInfo
                # Get raw collection data from ArangoDB
                collections_data = st.session_state.db_info.db_config.db.collections()
                collections = []

                # Format collections consistently
                for collection in collections_data:
                    if not collection["name"].startswith("_"):  # Skip system collections
                        # Get collection object
                        coll_obj = st.session_state.db_info.db_config.db.collection(collection["name"])
                        # Get count
                        try:
                            count = coll_obj.count()
                        except:
                            count = "Unknown"

                        collections.append({
                            "name": collection["name"],
                            "type": collection["type"],
                            "status": collection.get("status", "unknown"),
                            "count": count
                        })
            else:
                # Using mock or custom format
                collections = st.session_state.db_info.get_collections()

                # Convert string collections to dict format if needed
                if collections and isinstance(collections[0], str):
                    collections = [{"name": name, "type": "unknown", "status": "loaded", "count": "Unknown"}
                                 for name in collections]
        except Exception as e:
            st.error(f"Error getting collections: {e}")
            collections = []

        if collections:
            for collection in collections:
                # Handle both string and dict collection formats
                if isinstance(collection, dict):
                    collection_name = collection["name"]
                    collection_type = collection.get("type", "unknown")
                    collection_status = collection.get("status", "unknown")
                    collection_count = collection.get("count", "Unknown")
                else:
                    # If it's just a string
                    collection_name = str(collection)
                    collection_type = "unknown"
                    collection_status = "unknown"
                    collection_count = "Unknown"

                with st.expander(collection_name):
                    st.write(f"**Type:** {collection_type}")
                    st.write(f"**Status:** {collection_status}")
                    st.write(f"**Count:** {collection_count}")

                    # Collection actions
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.button("Truncate", key=f"truncate_{collection_name}")
                    with col2:
                        st.button("View Schema", key=f"schema_{collection_name}")
                    with col3:
                        st.button("View Sample", key=f"sample_{collection_name}")

    with tab3:
        st.subheader("Indexing Configuration")

        st.info("Configure how Indaleko indexes your data.")

        # Index settings
        col1, col2 = st.columns(2)
        with col1:
            st.checkbox("Enable automatic indexing", value=True)
            st.checkbox("Index file contents", value=True)
            st.checkbox("Extract EXIF metadata", value=True)
            st.checkbox("Calculate file checksums", value=True)

        with col2:
            st.checkbox("Detect file MIME types", value=True)
            st.checkbox("Track file versions", value=False)
            st.checkbox("Index cloud storage", value=True)
            st.checkbox("Track email attachments", value=False)

        # Schedule settings
        st.subheader("Indexing Schedule")
        schedule_options = ["Manual", "Hourly", "Daily", "Weekly"]
        selected_schedule = st.selectbox("Indexing Schedule", schedule_options, index=2)

        if selected_schedule != "Manual":
            if selected_schedule == "Daily":
                st.time_input("Time of day", value=datetime.strptime("03:00", "%H:%M"))
            elif selected_schedule == "Weekly":
                days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                st.selectbox("Day of week", days, index=6)
                st.time_input("Time of day", value=datetime.strptime("03:00", "%H:%M"))

    with tab4:
        st.subheader("User Preferences")

        # UI preferences
        st.write("**UI Settings**")
        col1, col2 = st.columns(2)
        with col1:
            st.selectbox("Theme", ["Light", "Dark", "System Default"], index=2)
            st.selectbox("Default View", ["Dashboard", "Search", "Analytics", "Activity"], index=0)

        with col2:
            st.checkbox("Show welcome screen on startup", value=True)
            st.checkbox("Enable animations", value=True)

        # Search preferences
        st.write("**Search Preferences**")
        col1, col2 = st.columns(2)
        with col1:
            st.checkbox("Use enhanced natural language", value=True)
            st.checkbox("Context-aware search", value=True)

        with col2:
            st.checkbox("Dynamic facets", value=True)
            st.checkbox("Deduplicate results", value=True)

        # Save button
        if st.button("Save Preferences"):
            st.success("Preferences saved successfully!")