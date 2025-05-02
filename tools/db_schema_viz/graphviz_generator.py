"""
GraphViz generator module for the Indaleko database schema visualization.

This module provides functions to generate GraphViz DOT files from
collection and relationship information, and to convert them to
various output formats.

Project Indaleko
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

import logging
import os
from pathlib import Path
import tempfile
from typing import Dict, List, Any, Optional

import graphviz


def generate_dot(
    collections: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
    groups: Dict[str, List[str]],
    show_indexes: bool = True
) -> str:
    """
    Generate a GraphViz DOT representation of the database schema.

    Args:
        collections: List of collection information
        relationships: List of relationships between collections
        groups: Dictionary mapping group names to lists of collection names
        show_indexes: Whether to show key indexes

    Returns:
        A string containing the GraphViz DOT representation
    """
    logging.info("Generating GraphViz DOT representation...")

    # Create a new directed graph
    dot = graphviz.Digraph(
        name="IndalekoDB",
        comment="Indaleko Database Schema",
        format="pdf"
    )

    # Set graph attributes
    dot.attr(
        rankdir="TB",  # Top to bottom layout
        ranksep="0.75",
        nodesep="0.5",
        compound="true",
        fontname="Arial",
        fontsize="14",
        bgcolor="white"
    )

    # Define node and edge attributes
    dot.attr("node",
        shape="box",
        style="filled,rounded",
        fontname="Arial",
        fontsize="12",
        margin="0.2,0.1",
        height="0.6",
        width="2.5"
    )

    dot.attr("edge",
        fontname="Arial",
        fontsize="10",
        fontcolor="#333333",
        arrowsize="0.8"
    )

    # Create subgraphs for groups
    for group_name, collection_names in groups.items():
        with dot.subgraph(name=f"cluster_{group_name.replace(' ', '_')}") as subgraph:
            subgraph.attr(
                label=group_name,
                style="rounded,dashed",
                color="gray",
                fontname="Arial",
                fontsize="14",
                labeljust="l"
            )

            # Add nodes for each collection in this group
            for collection_name in collection_names:
                collection = next((c for c in collections if c["name"] == collection_name), None)
                if collection:
                    _add_collection_node(subgraph, collection)

                    # Add index nodes if requested
                    if show_indexes and collection.get("key_indexes"):
                        _add_index_nodes(subgraph, collection)

    # Add relationships as edges
    for relationship in relationships:
        from_collection = relationship["from"]
        to_collection = relationship["to"]

        # Check if both collections exist
        if from_collection in [c["name"] for c in collections] and to_collection in [c["name"] for c in collections]:
            edge_style = "dashed" if relationship.get("type") in ["enriches", "contextualizes", "references"] else "solid"
            dot.edge(
                from_collection,
                to_collection,
                label=relationship.get("type", ""),
                style=edge_style,
                color="#AA0000",
                tooltip=relationship.get("description", "")
            )

    # Add a legend
    _add_legend(dot)

    return dot.source


def _add_collection_node(graph, collection: Dict[str, Any]) -> None:
    """
    Add a node for a collection to the graph.

    Args:
        graph: The GraphViz graph to add the node to
        collection: The collection information
    """
    # Set node attributes based on collection type
    if collection["type"] == "document":
        fillcolor = "#e6eeff"  # Light blue
        color = "#003380"      # Dark blue
    else:  # Edge collection
        fillcolor = "#ffe6e6"  # Light red
        color = "#800000"      # Dark red

    # Create the node label with collection name and description
    label = f"{collection['name']}\\n{collection['description']}"

    graph.node(
        collection["name"],
        label=label,
        fillcolor=fillcolor,
        color=color,
        style="filled,rounded",
        tooltip=f"{collection['type'].capitalize()} collection with {collection['count']} documents"
    )


def _add_index_nodes(graph, collection: Dict[str, Any]) -> None:
    """
    Add nodes for collection indexes to the graph.

    Args:
        graph: The GraphViz graph to add the nodes to
        collection: The collection information
    """
    key_indexes = collection.get("key_indexes", [])
    for i, index in enumerate(key_indexes):
        index_name = f"{collection['name']}_idx{i+1}"

        # Create a label for the index
        fields_str = ", ".join(index.get("fields", []))
        index_type = index.get("type", "unknown")
        unique = "unique " if index.get("unique", False) else ""

        label = f"{unique}{index_type}\\n({fields_str})"

        # Add the index node
        graph.node(
            index_name,
            label=label,
            shape="box",
            style="filled,rounded",
            fillcolor="#e6ffe6",  # Light green
            color="#006600",      # Dark green
            fontsize="10",
            width="1.5",
            height="0.4",
            tooltip=f"{index_type.capitalize()} index on {fields_str}"
        )

        # Connect the index to its collection
        graph.edge(
            index_name,
            collection["name"],
            style="dotted",
            arrowhead="none",
            color="#006600"
        )


def _add_legend(graph) -> None:
    """
    Add a legend to the graph.

    Args:
        graph: The GraphViz graph to add the legend to
    """
    with graph.subgraph(name="cluster_legend") as legend:
        legend.attr(
            label="Legend",
            style="rounded",
            color="black",
            fontname="Arial",
            fontsize="12",
            bgcolor="#f5f5f5"
        )

        # Add legend nodes
        legend.node(
            "document_collection",
            label="Document Collection",
            shape="box",
            style="filled,rounded",
            fillcolor="#e6eeff",
            color="#003380",
            fontsize="10"
        )

        legend.node(
            "edge_collection",
            label="Edge Collection",
            shape="box",
            style="filled,rounded",
            fillcolor="#ffe6e6",
            color="#800000",
            fontsize="10"
        )

        legend.node(
            "index",
            label="Index",
            shape="box",
            style="filled,rounded",
            fillcolor="#e6ffe6",
            color="#006600",
            fontsize="10"
        )

        # Add legend edges
        legend.edge(
            "document_collection",
            "edge_collection",
            label="contains",
            style="solid",
            color="#AA0000",
            fontsize="10"
        )

        legend.edge(
            "edge_collection",
            "index",
            label="references",
            style="dashed",
            color="#AA0000",
            fontsize="10"
        )

        # Set legend layout
        legend.attr(rank="sink")


def generate_output(
    dot: str,
    output_path: str,
    format: str = "pdf",
    orientation: str = "landscape"
) -> None:
    """
    Generate output in the specified format from a DOT representation.

    Args:
        dot: The GraphViz DOT representation
        output_path: The path to save the output to
        format: The output format (pdf, png, svg)
        orientation: The diagram orientation (portrait or landscape)
    """
    logging.info(f"Generating DOT file to {output_path}...")

    # If the output path has a format extension, replace it with .dot
    dot_output_path = os.path.splitext(output_path)[0] + ".dot"

    # Write the DOT file
    try:
        # Create directory if it doesn't exist
        output_dir = os.path.dirname(dot_output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Write the DOT source to a file
        with open(dot_output_path, 'w') as f:
            f.write(dot)

        logging.info(f"DOT file written to {dot_output_path}")
        logging.info(f"To generate output, run: dot -T{format} -o {output_path} {dot_output_path}")

        # Also try to use the graphviz library if it works
        try:
            source = graphviz.Source(dot, format=format)
            source.render(os.path.splitext(os.path.basename(dot_output_path))[0],
                         directory=os.path.dirname(dot_output_path),
                         cleanup=False)
            logging.info(f"Graphviz rendering attempted. Check for output files in {os.path.dirname(dot_output_path)}")
        except Exception as render_e:
            logging.warning(f"Could not render with graphviz library: {render_e}")

    except Exception as e:
        logging.error(f"Error generating output: {e}")
