"""
Query Path Visualization for Indaleko.

This module provides the QueryPathVisualizer class, which visualizes
query paths and relationships to help users understand their exploration.

Project Indaleko
Copyright (C) 2025 Tony Mason

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
import sys
import tempfile
import uuid
from typing import Any

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.context.navigation import QueryNavigator
from query.context.relationship import QueryRelationshipDetector, RelationshipType

# pylint: enable=wrong-import-position


class QueryPathVisualizer:
    """
    Visualizes query paths and relationships.

    This class generates visual representations of query exploration paths
    to help users understand their search process and relationships between
    different queries.
    """

    # Color mapping for relationship types
    RELATIONSHIP_COLORS = {
        RelationshipType.REFINEMENT: "blue",
        RelationshipType.BROADENING: "green",
        RelationshipType.PIVOT: "orange",
        RelationshipType.BACKTRACK: "gray",
        RelationshipType.UNRELATED: "red",
    }

    def __init__(self, db_config=None, debug=False):
        """
        Initialize the QueryPathVisualizer.

        Args:
            db_config: Optional database configuration
            debug: Whether to enable debug logging
        """
        # Set up logging
        self._logger = logging.getLogger("QueryPathVisualizer")
        if debug:
            self._logger.setLevel(logging.DEBUG)

        # Initialize dependencies
        self._navigator = QueryNavigator(db_config=db_config, debug=debug)
        self._detector = QueryRelationshipDetector(db_config=db_config, debug=debug)
        self._db_config = db_config

        # Initialize graph state
        self.graph = None
        self.pos = None

    def generate_path_graph(
        self,
        query_id: uuid.UUID | None = None,
        context_handle: uuid.UUID | None = None,
        max_depth: int = 10,
        include_branches: bool = True,
    ) -> Any:
        """
        Generate a visual graph of related queries.

        Args:
            query_id: Optional query ID to visualize the path for
            context_handle: Optional context handle to visualize queries for
            max_depth: Maximum path depth to visualize
            include_branches: Whether to include exploration branches

        Returns:
            NetworkX graph object
        """
        try:
            # Import networkx here to avoid dependency issues
            import networkx as nx

            # Create a new directed graph
            self.graph = nx.DiGraph()

            if query_id:
                # Get the query path
                path = self._navigator.get_query_path(query_id, max_depth=max_depth)

                if not path:
                    self._logger.warning(f"No path found for query {query_id}")
                    return self.graph

                # Add nodes and edges for the path
                self._add_path_to_graph(path)

                # Add branches if requested
                if include_branches:
                    self._add_branches_to_graph(query_id, max_depth=max_depth)

            elif context_handle:
                # Get queries for this context
                queries = self._navigator.get_related_queries(
                    context_handle=context_handle,
                )

                if not queries:
                    self._logger.warning(
                        f"No queries found for context {context_handle}",
                    )
                    return self.graph

                # Add nodes for all queries
                for query in queries:
                    query_id = uuid.UUID(query["query_id"])
                    self.graph.add_node(
                        query_id,
                        label=self._truncate_text(query["query_text"]),
                        tooltip=query["query_text"],
                        result_count=query.get("result_count", 0),
                        timestamp=query.get("timestamp"),
                    )

                # Add edges based on previous_query_id relations
                for query in queries:
                    if query.get("previous_query_id"):
                        try:
                            from_id = uuid.UUID(query["previous_query_id"])
                            to_id = uuid.UUID(query["query_id"])

                            # Only add edge if both nodes exist
                            if from_id in self.graph.nodes and to_id in self.graph.nodes:
                                relationship = query.get("relationship_type", "unknown")
                                self.graph.add_edge(
                                    from_id,
                                    to_id,
                                    relationship=relationship,
                                    color=self.RELATIONSHIP_COLORS.get(
                                        relationship,
                                        "gray",
                                    ),
                                )
                        except ValueError:
                            continue

            # Calculate layout if needed
            self._calculate_layout()

            return self.graph

        except ImportError:
            self._logger.error("NetworkX not installed. Cannot generate graph.")
            return None
        except Exception as e:
            self._logger.error(f"Error generating path graph: {e}")
            return None

    def _add_path_to_graph(self, path: list[dict[str, Any]]) -> None:
        """
        Add a query path to the graph.

        Args:
            path: List of query dictionaries
        """
        # Add nodes for all queries in the path
        for query in path:
            query_id = uuid.UUID(query["query_id"])
            self.graph.add_node(
                query_id,
                label=self._truncate_text(query["query_text"]),
                tooltip=query["query_text"],
                result_count=query.get("result_count", 0),
                timestamp=query.get("timestamp"),
                is_path=True,
            )

        # Add edges based on path order
        for i in range(len(path) - 1):
            from_id = uuid.UUID(path[i]["query_id"])
            to_id = uuid.UUID(path[i + 1]["query_id"])

            # Detect relationship if not already specified
            relationship = path[i + 1].get("relationship_type")
            if not relationship:
                rel_type, _ = self._detector.detect_relationship(path[i], path[i + 1])
                relationship = rel_type.value

            self.graph.add_edge(
                from_id,
                to_id,
                relationship=relationship,
                color=self.RELATIONSHIP_COLORS.get(relationship, "gray"),
                is_path=True,
            )

    def _add_branches_to_graph(self, query_id: uuid.UUID, max_depth: int = 3) -> None:
        """
        Add exploration branches to the graph.

        Args:
            query_id: Query ID to find branches from
            max_depth: Maximum depth of branches
        """
        # Get exploration branches
        branches = self._navigator.get_exploration_branches(
            query_id,
            max_branches=5,
            max_queries_per_branch=max_depth,
        )

        for branch_id, branch_path in branches.items():
            # Add nodes and edges for this branch
            for query in branch_path:
                query_id = uuid.UUID(query["query_id"])

                # Add node if it doesn't exist
                if query_id not in self.graph.nodes:
                    self.graph.add_node(
                        query_id,
                        label=self._truncate_text(query["query_text"]),
                        tooltip=query["query_text"],
                        result_count=query.get("result_count", 0),
                        timestamp=query.get("timestamp"),
                        is_branch=True,
                    )

            # Add edges
            for i in range(len(branch_path) - 1):
                from_id = uuid.UUID(branch_path[i]["query_id"])
                to_id = uuid.UUID(branch_path[i + 1]["query_id"])

                relationship = branch_path[i + 1].get("relationship_type")
                if not relationship:
                    rel_type, _ = self._detector.detect_relationship(
                        branch_path[i],
                        branch_path[i + 1],
                    )
                    relationship = rel_type.value

                self.graph.add_edge(
                    from_id,
                    to_id,
                    relationship=relationship,
                    color=self.RELATIONSHIP_COLORS.get(relationship, "gray"),
                    is_branch=True,
                    width=1,
                )

    def _calculate_layout(self) -> None:
        """Calculate the layout for the graph."""
        try:
            import networkx as nx

            if not self.graph:
                return

            # Choose a layout algorithm
            try:
                # First try dot layout for hierarchical visualization
                self.pos = nx.nx_agraph.graphviz_layout(self.graph, prog="dot")
            except (ImportError, AttributeError):
                # Fall back to spring layout if graphviz not available
                self.pos = nx.spring_layout(self.graph, seed=42)

        except ImportError:
            self._logger.error("NetworkX not installed. Cannot calculate layout.")
        except Exception as e:
            self._logger.error(f"Error calculating layout: {e}")

    def _truncate_text(self, text: str, max_length: int = 30) -> str:
        """
        Truncate text to a maximum length.

        Args:
            text: Text to truncate
            max_length: Maximum length

        Returns:
            Truncated text
        """
        if not text:
            return ""

        if len(text) <= max_length:
            return text

        return text[:max_length] + "..."

    def export_graph(
        self,
        file_path: str | None = None,
        format: str = "png",
        show: bool = False,
    ) -> str | None:
        """
        Export the graph visualization to a file.

        Args:
            file_path: Output file path (optional)
            format: Output format (png, pdf, svg)
            show: Whether to display the graph

        Returns:
            Path to the exported file or None on error
        """
        try:
            # Import matplotlib here to avoid dependency issues
            import matplotlib.pyplot as plt
            import networkx as nx

            if not self.graph:
                self._logger.error("No graph has been generated")
                return None

            # Create figure
            plt.figure(figsize=(12, 8))

            # Calculate layout if needed
            if not self.pos:
                self._calculate_layout()

            # Prepare node colors and sizes
            node_colors = []
            node_sizes = []

            for node in self.graph.nodes():
                # Main path nodes are larger and blue
                if self.graph.nodes[node].get("is_path", False):
                    node_colors.append("skyblue")
                    node_sizes.append(1500)
                # Branch nodes are smaller and gray
                else:
                    node_colors.append("lightgray")
                    node_sizes.append(1000)

            # Prepare edge colors and widths
            edge_colors = []
            edge_widths = []

            for u, v, data in self.graph.edges(data=True):
                edge_colors.append(data.get("color", "gray"))

                # Main path edges are thicker
                if data.get("is_path", False):
                    edge_widths.append(2.0)
                else:
                    edge_widths.append(1.0)

            # Draw the graph
            nx.draw(
                self.graph,
                pos=self.pos,
                with_labels=True,
                labels={n: self.graph.nodes[n]["label"] for n in self.graph.nodes()},
                node_color=node_colors,
                node_size=node_sizes,
                edge_color=edge_colors,
                width=edge_widths,
                font_size=8,
                font_weight="bold",
                arrows=True,
            )

            # Add title
            plt.title("Query Exploration Path")

            # Generate temp file if no path provided
            if not file_path:
                fd, file_path = tempfile.mkstemp(suffix=f".{format}")
                os.close(fd)

            # Save the graph
            plt.savefig(file_path, format=format, bbox_inches="tight")

            # Show the graph if requested
            if show:
                plt.show()
            else:
                plt.close()

            return file_path

        except ImportError:
            self._logger.error("Required libraries not installed. Cannot export graph.")
            return None
        except Exception as e:
            self._logger.error(f"Error exporting graph: {e}")
            return None

    def generate_report(self, query_id: uuid.UUID) -> dict[str, Any]:
        """
        Generate a report about the query exploration.

        Args:
            query_id: Query ID to generate the report for

        Returns:
            Dictionary with report data
        """
        try:
            # Get the query path
            path = self._navigator.get_query_path(query_id)

            if not path:
                return {
                    "path_length": 0,
                    "query_text": "Unknown",
                    "exploration_summary": "No exploration path found",
                }

            # Get the query text
            query_text = path[-1]["query_text"] if path else "Unknown"

            # Analyze the sequence
            analysis = self._detector.analyze_query_sequence(query_id)

            # Generate text summary
            exploration_pattern = analysis["exploration_pattern"]
            pattern_descriptions = {
                "systematic-narrowing": "systematically refining your search by adding constraints",
                "systematic-broadening": "gradually broadening your search by removing constraints",
                "exploratory": "exploring different aspects of the topic",
                "depth-first-search": "focusing on specific areas before backtracking",
                "mixed": "using a mixed exploration strategy",
            }

            summary = f"You have been {pattern_descriptions.get(exploration_pattern, 'searching')} "
            summary += f"through {len(path)} queries. "

            if analysis["focus_shifts"] > 0:
                summary += f"You've shifted focus {analysis['focus_shifts']} times. "

            # Add relationship details
            if path and len(path) > 1:
                last_rel = analysis["relationships"][-1]["relationship"]
                if last_rel == RelationshipType.REFINEMENT:
                    summary += "Your most recent search refined your previous query."
                elif last_rel == RelationshipType.BROADENING:
                    summary += "Your most recent search broadened your previous query."
                elif last_rel == RelationshipType.PIVOT:
                    summary += "Your most recent search explored a different aspect."
                elif last_rel == RelationshipType.BACKTRACK:
                    summary += "Your most recent search returned to a previous approach."

            # Generate visualization
            viz_path = self.export_graph()

            return {
                "path_length": len(path),
                "query_text": query_text,
                "exploration_pattern": exploration_pattern,
                "focus_shifts": analysis["focus_shifts"],
                "exploration_summary": summary,
                "visualization_path": viz_path,
            }

        except Exception as e:
            self._logger.error(f"Error generating report: {e}")
            return {
                "path_length": 0,
                "query_text": "Error",
                "exploration_summary": f"Error generating report: {e}",
            }


def main():
    """Test functionality of QueryPathVisualizer."""
    logging.basicConfig(level=logging.DEBUG)

    # Create visualizer
    visualizer = QueryPathVisualizer(debug=True)

    # Test with navigator to get query data
    navigator = QueryNavigator(debug=True)

    # Get query history
    history = navigator.get_query_history(limit=5)

    if not history:
        print("No query history found. Please run some test queries first.")
        return

    # Use the most recent query for testing
    test_query_id = uuid.UUID(history[0]["query_id"])
    print(f"Generating visualization for query: {history[0]['query_text']}")

    # Generate the graph
    graph = visualizer.generate_path_graph(test_query_id, include_branches=True)

    if not graph:
        print("Failed to generate graph.")
        return

    # Display node and edge information
    print(f"\nGraph has {len(graph.nodes)} nodes and {len(graph.edges)} edges")

    print("\nNodes:")
    for i, (node, attrs) in enumerate(graph.nodes(data=True)):
        print(f"  {i+1}. {node}: {attrs.get('label', 'Unlabeled')}")

    print("\nEdges:")
    for i, (u, v, attrs) in enumerate(graph.edges(data=True)):
        print(f"  {i+1}. {u} → {v}: {attrs.get('relationship', 'Unknown')}")

    # Export the graph
    output_path = visualizer.export_graph(show=False)

    if output_path:
        print(f"\nGraph exported to: {output_path}")

    # Generate report
    report = visualizer.generate_report(test_query_id)

    print("\nQuery Exploration Report:")
    print(f"  Path Length: {report['path_length']}")
    print(f"  Query: {report['query_text']}")
    print(f"  Exploration Pattern: {report['exploration_pattern']}")
    print(f"  Summary: {report['exploration_summary']}")
    if "visualization_path" in report:
        print(f"  Visualization: {report['visualization_path']}")


if __name__ == "__main__":
    main()
