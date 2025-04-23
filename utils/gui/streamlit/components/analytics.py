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


import networkx as nx
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.gui.streamlit.components.connection import connect_to_db
from utils.gui.streamlit.services.database import (
    get_activity_timeline,
    get_cross_source_patterns,
    get_file_type_distribution,
    get_storage_summary,
)


def render_analytics():
    """
    Render the analytics page with charts and visualizations

    Includes:
    - Storage analysis
    - Activity analysis
    - Relationship analysis
    - Pattern analysis
    - Insights
    """
    st.markdown("<div class='main-header'>Analytics</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='sub-header'>Visualize and analyze your data</div>",
        unsafe_allow_html=True,
    )

    # Auto-connect in demo mode if not connected
    if not st.session_state.db_connected:
        db_service, db_info = connect_to_db("mock_config")
        st.session_state.db_connected = True
        st.session_state.db_service = db_service
        st.session_state.db_info = db_info

    # Analytics tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Storage", "Activities", "Relationships", "Patterns", "Insights"],
    )

    with tab1:
        st.subheader("Storage Analysis")

        # Storage distribution by type
        storage_data = get_storage_summary(st.session_state.db_service)
        if storage_data:
            fig = px.bar(
                storage_data, x="storage", y="count", title="Files by Storage Volume",
            )
            st.plotly_chart(fig, use_container_width=True)

        # File type distribution
        file_types = get_file_type_distribution(st.session_state.db_service)
        if file_types:
            fig = px.pie(
                file_types,
                values="count",
                names="extension",
                title="Top File Extensions",
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Activity Analysis")

        # Activity timeline
        activity_data = get_activity_timeline(st.session_state.db_service)
        if activity_data:
            fig = px.line(
                activity_data, x="date", y="count", title="Activity Over Time",
            )
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
        st.subheader("Cross-Source Patterns")

        # Get pattern data
        pattern_data = get_cross_source_patterns(st.session_state.db_service)

        if pattern_data:
            # Display summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Patterns", f"{len(pattern_data['patterns'])}")
            with col2:
                st.metric(
                    "Recent Correlations", f"{len(pattern_data['recent_correlations'])}",
                )
            with col3:
                st.metric(
                    "Active Suggestions", f"{len(pattern_data['active_suggestions'])}",
                )

            # Pattern visualization (network graph)
            st.subheader("Pattern Network")
            if len(pattern_data["patterns"]) > 0:
                fig = create_pattern_network_graph(pattern_data["patterns"])
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info(
                    "No patterns detected yet. Patterns will appear as you use different data sources.",
                )

            # Correlation timeline
            st.subheader("Cross-Source Correlations")
            if len(pattern_data["correlations"]) > 0:
                fig = create_correlation_timeline(pattern_data["correlations"])
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No correlations detected yet.")

            # Suggestions
            st.subheader("Proactive Suggestions")
            display_suggestions(pattern_data["suggestions"])
        else:
            st.info(
                "Cross-source pattern detection not available or no patterns detected yet.",
            )

    with tab5:
        st.subheader("Insights")

        # Placeholder for insights
        st.info("Automated insights will be added in future updates.")

        # Mock insights
        st.markdown(
            """
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
        """,
        )


def create_pattern_network_graph(patterns):
    """Create a network graph visualization of patterns between data sources"""
    # Create nodes for source types
    source_type_map = {
        "ntfs": {"id": "ntfs", "label": "File Activity", "group": 1},
        "collaboration": {"id": "collaboration", "label": "Collaboration", "group": 2},
        "location": {"id": "location", "label": "Location", "group": 3},
        "ambient": {"id": "ambient", "label": "Ambient", "group": 4},
        "task": {"id": "task", "label": "Tasks", "group": 5},
        "semantic": {"id": "semantic", "label": "Semantic", "group": 6},
        "query": {"id": "query", "label": "Search", "group": 7},
    }

    # Create edges from patterns
    edges = []
    for pattern in patterns:
        if len(pattern["source_types"]) > 1:
            for i in range(len(pattern["source_types"]) - 1):
                source = pattern["source_types"][i]
                target = pattern["source_types"][i + 1]
                weight = (
                    pattern["confidence"] * 5
                )  # Scale confidence for line thickness

                edges.append(
                    {
                        "from": source,
                        "to": target,
                        "width": weight,
                        "label": f"{pattern['confidence']:.2f}",
                        "title": pattern["description"],
                    },
                )

    # Create the network graph using networkx and plotly
    G = nx.Graph()

    # Add nodes
    for node_id, node_data in source_type_map.items():
        G.add_node(node_id, **node_data)

    # Add edges
    for edge in edges:
        G.add_edge(edge["from"], edge["to"], weight=edge["width"], title=edge["title"])

    # Compute layout
    pos = nx.spring_layout(G)

    # Create Plotly figure
    edge_x = []
    edge_y = []
    edge_widths = []
    edge_hover = []

    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_widths.append(edge[2].get("weight", 1))
        edge_hover.append(edge[2].get("title", ""))

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=1.5, color="#888"),
        hoverinfo="text",
        text=edge_hover,
        mode="lines",
    )

    node_x = []
    node_y = []
    node_colors = []
    node_hover = []

    for node in G.nodes(data=True):
        x, y = pos[node[0]]
        node_x.append(x)
        node_y.append(y)
        node_colors.append(node[1].get("group", 0))
        node_hover.append(node[1].get("label", node[0]))

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers",
        hoverinfo="text",
        text=node_hover,
        marker=dict(
            showscale=True,
            colorscale="YlGnBu",
            size=15,
            color=node_colors,
            line_width=2,
        ),
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title="Cross-Source Pattern Network",
            titlefont_size=16,
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        ),
    )

    return fig


def create_correlation_timeline(correlations):
    """Create a timeline visualization of correlations"""
    # Process correlations for timeline
    timeline_data = []

    for correlation in correlations:
        source_names = [s.capitalize() for s in correlation["source_types"]]
        timeline_data.append(
            {
                "date": correlation["timestamp"],
                "correlation": " + ".join(source_names),
                "confidence": correlation["confidence"],
                "description": correlation["description"],
            },
        )

    # Sort by timestamp
    timeline_data.sort(key=lambda x: x["date"])

    # Create timeline using plotly
    fig = px.scatter(
        timeline_data,
        x="date",
        y="correlation",
        size="confidence",
        hover_data=["description"],
        color="confidence",
        color_continuous_scale="Viridis",
        title="Cross-Source Correlations Timeline",
    )

    return fig


def display_suggestions(suggestions):
    """Display proactive suggestions in an interactive format"""
    # Sort suggestions by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_suggestions = sorted(
        suggestions, key=lambda x: priority_order.get(x["priority"], 4),
    )

    # Display each suggestion
    for i, suggestion in enumerate(sorted_suggestions):
        # Skip expired or dismissed suggestions
        if suggestion.get("is_expired", False) or suggestion.get("dismissed", False):
            continue

        # Create expandable card
        expander = st.expander(
            f"{suggestion['title']} ({suggestion['suggestion_type'].capitalize()})",
            expanded=suggestion["priority"] in ["critical", "high"],
        )

        with expander:
            st.write(suggestion["content"])

            # Add metadata
            st.caption(
                f"Confidence: {suggestion['confidence']:.2f} • Priority: {suggestion['priority'].capitalize()}",
            )

            # Add actions
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Apply 👍", key=f"apply_{i}"):
                    # Here you would implement the logic to apply the suggestion
                    st.success("Suggestion applied!")
            with col2:
                if st.button("Dismiss 👎", key=f"dismiss_{i}"):
                    # Here you would implement the logic to dismiss the suggestion
                    st.info("Suggestion dismissed.")
