"""
Indaleko Streamlit GUI Application - Modular Version

This module provides a Streamlit-based GUI for Indaleko using a component-based architecture.

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

import streamlit as st

# Set up path to include Indaleko modules
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# THIS MUST BE THE FIRST STREAMLIT COMMAND
# Page configuration
st.set_page_config(
    page_title="Indaleko Unified Personal Index",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom styling (after page config)
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E88E5;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #757575;
        margin-bottom: 2rem;
    }
    .card {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #f8f9fa;
        box-shadow: 0 0.125rem 0.25rem rgba(0,0,0,0.075);
        margin-bottom: 1.5rem;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1E88E5;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #757575;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Import components
from utils.gui.streamlit.components import (
    connect_to_db,
    render_activity,
    render_analytics,
    render_dashboard,
    render_search,
    render_settings,
    render_sidebar,
)

# Initialize session state
if "using_real_db" not in st.session_state:
    st.session_state.using_real_db = False
if "connect_debug" not in st.session_state:
    st.session_state.connect_debug = False
if "db_connected" not in st.session_state:
    st.session_state.db_connected = False
if "db_service" not in st.session_state:
    st.session_state.db_service = None
if "db_info" not in st.session_state:
    st.session_state.db_info = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "dashboard"
if "query_results" not in st.session_state:
    st.session_state.query_results = None

# Show demo mode notice (after page config & styling)
# - only if not using real DB
if not st.session_state.using_real_db:
    st.warning(
        "⚠️ **DEMO MODE** - Running with simulated data. Database connections are mocked.",
    )
    st.info(
        """
    This is a prototype of the Indaleko GUI showing the interface design
    and navigation. The displayed data is simulated and does not reflect
    actual database content.
    """,
    )

# Render sidebar (always present)
render_sidebar()

# Render main content based on current page
if not st.session_state.db_connected and st.session_state.current_page != "setup":
    # Welcome screen (shown when not connected)
    st.markdown(
        "<div class='main-header'>Welcome to Indaleko</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='sub-header'>Unified Personal Index</div>",
        unsafe_allow_html=True,
    )

    st.warning("Please connect to a database to continue.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            """
        <div class="card">
            <h3>Unified Storage View</h3>
            <p>View all your storage across devices and cloud services in one place.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            """
        <div class="card">
            <h3>Natural Language Search</h3>
            <p>Find your data using natural language queries powered by AI.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            """
        <div class="card">
            <h3>Activity Context</h3>
            <p>Understand your data in the context of your activities and collaborations.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    try:
        image_path = os.path.join(
            os.environ.get("INDALEKO_ROOT"),
            "figures",
            "arch-diagram-solid.png",
        )
        if os.path.exists(image_path):
            st.image(image_path, use_container_width=True)
    except Exception:
        pass

elif st.session_state.current_page == "setup":
    st.markdown("<div class='main-header'>Database Setup</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='sub-header'>Configure your Indaleko database</div>",
        unsafe_allow_html=True,
    )

    st.info("This wizard will help you set up an ArangoDB database for Indaleko.")

    with st.form("setup_form"):
        st.subheader("Database Configuration")

        col1, col2 = st.columns(2)
        with col1:
            host = st.text_input("Host", "localhost")
            port = st.number_input("Port", value=8529, min_value=1, max_value=65535)
            database = st.text_input("Database Name", "indaleko")

        with col2:
            username = st.text_input("Username", "indaleko")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")

        st.subheader("Docker Configuration")
        use_docker = st.checkbox("Use Docker for ArangoDB", value=True)

        if use_docker:
            docker_image = st.text_input("Docker Image", "arangodb:latest")
            docker_volume = st.text_input("Docker Volume", "indaleko_data")

        submitted = st.form_submit_button("Set Up Database")

        if submitted:
            if password != confirm_password:
                st.error("Passwords do not match.")
            else:
                try:
                    # Here we'd call the actual setup code
                    # For demo purposes, we'll just show success
                    st.success(
                        "Database setup successfully! Redirecting to dashboard...",
                    )
                    st.session_state.current_page = "dashboard"
                    db_service, db_info = connect_to_db("mock_config")
                    if db_service:
                        st.session_state.db_connected = True
                        st.session_state.db_service = db_service
                        st.session_state.db_info = db_info
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error setting up database: {e}")

elif st.session_state.current_page == "dashboard":
    render_dashboard()

elif st.session_state.current_page == "search":
    render_search()

elif st.session_state.current_page == "analytics":
    render_analytics()

elif st.session_state.current_page == "activity":
    render_activity()

elif st.session_state.current_page == "settings":
    render_settings()

# Auto-connect to database on startup
if not st.session_state.get("tried_auto_connect", False):
    st.session_state.tried_auto_connect = True
    st.info("🔄 Trying automatic database connection on startup...")
    from utils.gui.streamlit.services.config import get_config_files

    config_files = get_config_files()
    if config_files:
        db_service, db_info = connect_to_db(config_files[0])
        if db_service:
            st.session_state.db_connected = True
            st.session_state.db_service = db_service
            st.session_state.db_info = db_info
            st.success("✅ Auto-connected to database!")
        else:
            st.warning("⚠️ Could not auto-connect to database. Please connect manually.")
    else:
        st.warning("⚠️ No database configuration files found.")

# Footer
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**Indaleko Project**")
with col2:
    st.markdown("Built with Streamlit")
with col3:
    st.markdown("v0.2.0")


def main():
    # Main function - app entry point
    pass


if __name__ == "__main__":
    main()
