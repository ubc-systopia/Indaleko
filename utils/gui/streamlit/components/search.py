"""
Search component for Indaleko Streamlit GUI.

This module provides the search interface for natural language queries.

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

import uuid

from datetime import UTC, datetime

import streamlit as st

from utils.gui.streamlit.components.common import display_search_results
from utils.gui.streamlit.components.connection import connect_to_db
from utils.gui.streamlit.mock_modules import FacetGenerator, MockQueryProcessor
from utils.gui.streamlit.services.query import execute_query


def render_search() -> None:
    """
    Render the search interface with natural language query capabilities.

    Provides:
    - Query input with explain and debug options
    - Advanced search options (facets, deduplication)
    - Results display with detailed view
    """
    st.markdown("<div class='main-header'>Search</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='sub-header'>Find what you need using natural language queries</div>",
        unsafe_allow_html=True,
    )

    # Auto-connect in demo mode if not connected
    if not st.session_state.db_connected:
        db_service, db_info = connect_to_db("mock_config")
        st.session_state.db_connected = True
        st.session_state.db_service = db_service
        st.session_state.db_info = db_info

    # Search form
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input(
            "Enter your query",
            placeholder="Find documents about Indaleko",
        )
    with col2:
        explain = st.checkbox("Explain query")
        debug_mode = st.checkbox("Debug mode")
        advanced = st.checkbox("Advanced options")

    if advanced:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.checkbox("Enhanced NL", value=True)
            st.checkbox("Context Aware", value=True)
        with col2:
            st.checkbox("Deduplicate Results", value=True)
            st.slider("Similarity Threshold", 0.0, 1.0, 0.85)
        with col3:
            dynamic_facets = st.checkbox("Dynamic Facets", value=True)
            st.number_input("Max Results", value=100, min_value=1)

    # Search with form for cancel capability
    search_col1, search_col2 = st.columns([3, 1])
    with search_col1:
        search_clicked = st.button("Search", key="search_button")
    with search_col2:
        if "search_running" in st.session_state and st.session_state.search_running:
            cancel_clicked = st.button("Cancel Search", key="cancel_button")
        else:
            cancel_clicked = False

    # Set search state
    if search_clicked:
        st.session_state.search_running = True
    if cancel_clicked:
        st.session_state.search_running = False
        st.warning("Search cancelled.")

    # Process the search if clicked and not cancelled
    if search_clicked and query:
        if not st.session_state.get("search_cancelled", False):
            with st.spinner("Searching..."):
                try:
                    # First run query execution regardless of explain mode
                    search_results = execute_query(
                        query,
                        st.session_state.db_service,
                        debug=debug_mode,
                    )

                    # If we didn't get any results, or got an error, fall back to mock data
                    if not search_results or (isinstance(search_results, dict) and "error" in search_results):
                        if debug_mode:
                            st.warning(
                                "No results found or error encountered. Using mock data.",
                            )
                        # Use mock processor as fallback
                        processor = MockQueryProcessor()
                        search_results = processor.execute(query, explain=False)

                    # If explain mode is enabled, also show the query explanation
                    if explain:
                        st.subheader("Query Explanation")

                        # Get explanation results
                        explain_results = execute_query(
                            query,
                            st.session_state.db_service,
                            explain=True,
                            debug=debug_mode,
                        )

                        if explain_results:
                            # Check if we have a valid query plan
                            if isinstance(explain_results, dict) and (
                                "nodes" in explain_results
                                or "plan" in explain_results
                                or "_is_explain_result" in explain_results
                            ):
                                # Use our dedicated display function for query plans
                                display_search_results(explain_results)
                            else:
                                # Regular JSON display for other result types
                                st.json(explain_results)

                    # Check if search results are actually explain results (error case)
                    if isinstance(search_results, dict) and "_is_explain_result" in search_results:
                        if not explain:  # Only show this if we're not already in explain mode
                            st.subheader("Query Explanation (Error)")
                            st.warning(
                                "Your search returned an explanation instead of results. This may indicate a problem.",
                            )
                            display_search_results(search_results)

                        # Generate mock results for display
                        processor = MockQueryProcessor()
                        search_results = processor.execute(query, explain=False)

                    # Process and display the actual search results
                    st.session_state.query_results = search_results
                    st.session_state.search_running = False

                    # Display the results immediately
                    result_count = len(search_results) if isinstance(search_results, (list, tuple)) else 1
                    st.success(f"Found {result_count} results")

                    # Debug info in debug mode
                    if debug_mode:
                        result_type = type(search_results).__name__
                        st.info(f"Result type: {result_type}")
                        if isinstance(search_results, (list, tuple)) and len(search_results) > 0:
                            sample_item = search_results[0]
                            st.info(f"First result type: {type(sample_item).__name__}")
                            if isinstance(sample_item, dict):
                                st.info(f"Sample keys: {list(sample_item.keys())[:5]}")

                    # Display results based on advanced options
                    if advanced and dynamic_facets:
                        # Generate facets
                        facet_generator = FacetGenerator()
                        facets = facet_generator.generate(search_results)

                        if facets:
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                st.subheader("Refine Results")
                                for facet_name, facet_values in facets.items():
                                    st.write(f"**{facet_name}**")
                                    for value, count in facet_values.items():
                                        st.checkbox(
                                            f"{value} ({count})",
                                            key=f"{facet_name}_{value}",
                                        )

                            with col2:
                                # Display results with facets
                                st.subheader("Results")
                                display_search_results(search_results)
                        else:
                            # No facets available
                            st.subheader("Results")
                            display_search_results(search_results)
                    else:
                        # Display results without facets
                        st.subheader("Results")
                        display_search_results(search_results)
                except Exception as e:
                    st.error(f"Search error: {e}")
                    st.session_state.search_running = False

    # Show previous results if available
    elif st.session_state.query_results:
        previous_results = st.session_state.query_results
        st.subheader("Previous Results")

        # Check if previous_results is a list or dict before getting length
        if isinstance(previous_results, (list, tuple)):
            st.success(f"Found {len(previous_results)} results")
        elif isinstance(previous_results, dict):
            st.success("Found 1 result")
        else:
            st.success("Found results")

        # Use our helper function to display the results
        display_search_results(previous_results)

    # Always show the direct results display section at the bottom if we have no other results
    if not st.session_state.get("query_results") and not (search_clicked and query):
        st.subheader("Sample Data")
        st.info("Run a search to see results, or explore this sample data:")

        # Create some sample results to showcase the interface
        sample_results = [
            {
                "_id": f"Objects/{uuid.uuid4()}",
                "_key": str(uuid.uuid4()),
                "Label": "sample_document.pdf",
                "type": "file",
                "size": 1024 * 5,
                "timestamp": datetime.now(UTC).isoformat(),
                "description": "Sample PDF document for UI demonstration",
            },
            {
                "_id": f"Objects/{uuid.uuid4()}",
                "_key": str(uuid.uuid4()),
                "Label": "project_report.docx",
                "type": "file",
                "size": 2048 * 3,
                "timestamp": datetime.now(UTC).isoformat(),
                "description": "Word document with project details",
            },
            {
                "_id": f"Objects/{uuid.uuid4()}",
                "_key": str(uuid.uuid4()),
                "Label": "presentation.pptx",
                "type": "file",
                "size": 4096,
                "timestamp": datetime.now(UTC).isoformat(),
                "description": "Presentation slides for upcoming meeting",
            },
        ]

        # Display the sample results
        display_search_results(sample_results)
