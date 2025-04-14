"""
Database connection components

These components handle database connection and status display.

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
import sys

def render_connection_status():
    """
    Display the current database connection status.
    
    This component shows if the database is connected, what type of connection
    it is (real or mock), and any relevant database details.
    """
    # Show connection status indicator
    if st.session_state.db_connected:
        if st.session_state.using_real_db:
            st.success("✅ Connected to REAL ArangoDB Database")

            # Show database details if available
            if hasattr(st.session_state, 'db_info') and st.session_state.db_info:
                db_info = st.session_state.db_info
                if hasattr(db_info, 'db_config') and hasattr(db_info.db_config, 'database'):
                    st.info(f"Database: {db_info.db_config.database}")
        else:
            st.warning("⚠️ Using MOCK Database Connection")
    else:
        st.error("❌ Not Connected")

def connect_to_db(config_file):
    """
    Connect to the database using the specified configuration file.
    
    Args:
        config_file (str): The database configuration file
        
    Returns:
        tuple: (db_service, db_info) connection objects, or (None, None) if connection fails
    """
    # Create a container for connection status that we can update
    status_container = st.empty()
    status_container.info(
        f"Connecting to database using config file: {config_file}..."
    )

    # Debug log container that's only shown in debug mode
    if 'connect_debug' in st.session_state and st.session_state.connect_debug:
        debug_container = st.expander("Connection Debug Info", expanded=True)
        debug_log = debug_container.empty()
    else:
        debug_container = None
        debug_log = None

    # Log function that writes to debug container if available
    def log_debug(message, level="info"):
        if debug_log:
            if level == "info":
                debug_log.info(message)
            elif level == "success":
                debug_log.success(message)
            elif level == "warning":
                debug_log.warning(message)
            elif level == "error":
                debug_log.error(message)

    try:
        # First try to connect to the real database
        real_db_connection = False

        try:
            # Only import these modules when trying to connect
            log_debug("Trying to import real database modules...", "info")

            try:
                from db.db_config import IndalekoDBConfig as RealDBConfig
                log_debug("✅ Imported db_config", "success")
            except ImportError as e:
                log_debug(f"❌ Failed to import db_config: {e}", "error")
                raise

            try:
                from db.service_manager import IndalekoServiceManager \
                    as RealServiceManager
                log_debug("✅ Imported service_manager", "success")
            except ImportError as e:
                log_debug(f"❌ Failed to import service_manager: {e}", "error")
                raise

            try:
                from db.db_info import IndalekoDBInfo as RealDBInfo
                log_debug("✅ Imported db_info", "success")
            except ImportError as e:
                log_debug(f"❌ Failed to import db_info: {e}", "error")
                raise

            config_path = os.path.join(
                os.environ.get("INDALEKO_ROOT"),
                "config", config_file
            )
            log_debug(f"Looking for config file at: {config_path}", "info")

            if os.path.exists(config_path):
                log_debug(f"✅ Found config file: {config_path}", "success")
                try:
                    RealDBConfig(config_file=config_path)
                    log_debug("✅ Created DB config", "success")

                    db_service = RealServiceManager()
                    log_debug("✅ Created service manager", "success")

                    # IndalekoDBInfo takes keyword arguments,
                    # not a positional db_config
                    db_info = RealDBInfo(db_config_file=config_path)
                    log_debug("✅ Created DB info", "success")

                    # Test connection
                    log_debug("Testing database connection...", "info")
                    status_container.info("Testing database connection...")

                    # The IndalekoServiceManager doesn't have
                    # is_connected() method
                    # Let's check connection by verifying the
                    # db_config instead
                    try:
                        # Check if we can access collections - this
                        # will fail if not connected
                        collection_names = \
                            db_service.db_config.db.collections()
                        if collection_names:
                            log_debug("✅ Connected to real ArangoDB database "
                                      f"with {len(collection_names)} "
                                      "collections!",
                                      "success"
                                      )
                            status_container.success(
                                "✅ Connected to real ArangoDB database "
                            )
                            real_db_connection = True
                            # Set flag to indicate we're using a real database
                            st.session_state.using_real_db = True
                            return db_service, db_info
                        else:
                            log_debug("⚠️ Connected but no collections"
                                      " found", "warning")
                            status_container.warning(
                                "⚠️ Connected but no collections found"
                            )
                    except Exception as e:
                        log_debug(
                            f"❌ Failed to verify connection: {e}",
                            "error"
                        )
                        status_container.error(f"❌ Failed to verify connection: {e}")
                except Exception as e:
                    log_debug(f"❌ Error creating database connection: {e}", "error")
                    status_container.error(f"❌ Error creating database connection: {e}")
            else:
                log_debug(f"⚠️ Config file not found: {config_path}", "warning")
                status_container.warning(f"⚠️ Config file not found: {config_path}")
        except Exception as e:
            log_debug(f"⚠️ Could not use real database modules: {e}", "warning")
            status_container.warning(f"⚠️ Could not use real database modules: {e}")

        # Fall back to mock if real connection fails
        if not real_db_connection:
            log_debug("Falling back to mock database connection", "info")
            status_container.info("Falling back to mock database connection")
            # Import mock classes inside this function to avoid circular imports
            from utils.gui.streamlit.mock_modules import MockServiceManager, MockDBInfo
            db_service = MockServiceManager()
            db_info = MockDBInfo()
            st.session_state.using_real_db = False
            return db_service, db_info
    except Exception as e:
        log_debug(f"❌ Error connecting to database: {e}", "error")
        status_container.error(f"❌ Error connecting to database: {e}")
        return None, None