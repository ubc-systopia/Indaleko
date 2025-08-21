"""
Query execution plan visualization for Indaleko.

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

import os
import re
import sys
import textwrap

from enum import Enum
from typing import Any


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from pydantic import Field, validator

from data_models.base import IndalekoBaseModel


class NodeType(str, Enum):
    """Types of nodes in the query execution plan."""

    ENUMERATE_COLLECTION = "EnumerateCollectionNode"
    INDEX = "IndexNode"
    FILTER = "FilterNode"
    SORT = "SortNode"
    LIMIT = "LimitNode"
    RETURN = "ReturnNode"
    CALCULATION = "CalculationNode"
    SUBQUERY = "SubqueryNode"
    JOIN = "JoinNode"
    TRAVERSAL = "TraversalNode"
    SCATTER = "ScatterNode"
    GATHER = "GatherNode"
    DISTRIBUTE = "DistributeNode"
    REMOTE = "RemoteNode"
    NORESULTS = "NoResultsNode"
    SINGLETON = "SingletonNode"
    INSERT = "InsertNode"
    UPDATE = "UpdateNode"
    REPLACE = "ReplaceNode"
    REMOVE = "RemoveNode"
    UPSERT = "UpsertNode"
    UNKNOWN = "UnknownNode"


class OperationType(str, Enum):
    """Types of operations in the query execution plan."""

    SCAN = "scan"  # Full collection scan
    INDEX_SCAN = "index_scan"  # Using an index
    FILTER = "filter"  # Filtering results
    SORT = "sort"  # Sorting results
    LIMIT = "limit"  # Limiting results
    RETURN = "return"  # Returning results
    CALCULATION = "calculation"  # Calculating values
    JOIN = "join"  # Joining collections
    TRAVERSAL = "traversal"  # Graph traversal
    MODIFICATION = "modification"  # Insert/update/delete/replace
    UNKNOWN = "unknown"  # Unknown operation


class PerformanceImpact(str, Enum):
    """Performance impact level of an operation."""

    HIGH = "high"  # High impact on performance (bad)
    MEDIUM = "medium"  # Medium impact on performance
    LOW = "low"  # Low impact on performance (good)
    UNKNOWN = "unknown"  # Unknown impact


class ExecutionNode(IndalekoBaseModel):
    """Represents a node in the query execution plan."""

    node_id: int = Field(..., description="The node ID")
    node_type: NodeType = Field(..., description="The type of the node")
    operation_type: OperationType = Field(
        default=OperationType.UNKNOWN,
        description="The type of operation performed",
    )
    collection: str | None = Field(
        default=None,
        description="The collection accessed (if applicable)",
    )
    index: str | None = Field(
        default=None,
        description="The index used (if applicable)",
    )
    index_type: str | None = Field(
        default=None,
        description="The type of index used (if applicable)",
    )
    estimated_cost: float = Field(
        default=0.0,
        description="The estimated cost of this operation",
    )
    expressions: list[str] = Field(
        default_factory=list,
        description="Expressions or conditions used in this node",
    )
    performance_impact: PerformanceImpact = Field(
        default=PerformanceImpact.UNKNOWN,
        description="The performance impact of this operation",
    )
    parent_id: int | None = Field(
        default=None,
        description="The parent node ID (if any)",
    )
    children_ids: list[int] = Field(
        default_factory=list,
        description="The child node IDs",
    )
    depth: int = Field(
        default=0,
        description="The depth of this node in the execution tree",
    )
    raw_data: dict[str, Any] = Field(
        default_factory=dict,
        description="The raw node data from ArangoDB",
    )

    @validator("operation_type", pre=True, always=True)
    def set_operation_type(self, v, values):
        """Set the operation type based on the node type."""
        if v != OperationType.UNKNOWN:
            return v

        node_type = values.get("node_type")
        if node_type == NodeType.ENUMERATE_COLLECTION:
            return OperationType.SCAN
        if node_type == NodeType.INDEX:
            return OperationType.INDEX_SCAN
        if node_type == NodeType.FILTER:
            return OperationType.FILTER
        if node_type == NodeType.SORT:
            return OperationType.SORT
        if node_type == NodeType.LIMIT:
            return OperationType.LIMIT
        if node_type == NodeType.RETURN:
            return OperationType.RETURN
        if node_type == NodeType.CALCULATION:
            return OperationType.CALCULATION
        if node_type in [NodeType.JOIN, NodeType.SCATTER, NodeType.GATHER]:
            return OperationType.JOIN
        if node_type == NodeType.TRAVERSAL:
            return OperationType.TRAVERSAL
        if node_type in [
            NodeType.INSERT,
            NodeType.UPDATE,
            NodeType.REPLACE,
            NodeType.REMOVE,
            NodeType.UPSERT,
        ]:
            return OperationType.MODIFICATION
        return OperationType.UNKNOWN


class ExecutionPlan(IndalekoBaseModel):
    """Represents a query execution plan."""

    nodes: list[ExecutionNode] = Field(
        default_factory=list,
        description="The nodes in the execution plan",
    )
    total_cost: float = Field(
        default=0.0,
        description="The total estimated cost of the plan",
    )
    collections_used: list[str] = Field(
        default_factory=list,
        description="The collections used in the plan",
    )
    indexes_used: list[dict[str, Any]] = Field(
        default_factory=list,
        description="The indexes used in the plan",
    )
    query: str = Field(default="", description="The original query")
    cacheable: bool = Field(default=False, description="Whether the query is cacheable")
    warnings: list[str] = Field(
        default_factory=list,
        description="Warnings about the query",
    )
    optimizations: list[str] = Field(
        default_factory=list,
        description="Optimizations applied to the query",
    )
    bottlenecks: list[str] = Field(
        default_factory=list,
        description="Identified bottlenecks in the query",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recommendations for improving the query",
    )


class PlanVisualizer:
    """Visualizes query execution plans."""

    def __init__(self, colorize: bool = True, max_depth: int = 10) -> None:
        """
        Initialize the plan visualizer.

        Args:
            colorize: Whether to use colors in the visualization
            max_depth: Maximum depth to visualize in the plan tree
        """
        self.colorize = colorize
        self.max_depth = max_depth

        # Define ANSI color codes
        self.colors = {
            "reset": "\033[0m",
            "bold": "\033[1m",
            "red": "\033[31m",
            "green": "\033[32m",
            "yellow": "\033[33m",
            "blue": "\033[34m",
            "magenta": "\033[35m",
            "cyan": "\033[36m",
            "white": "\033[37m",
            "gray": "\033[90m",
            "red_bg": "\033[41m",
            "green_bg": "\033[42m",
            "yellow_bg": "\033[43m",
            "blue_bg": "\033[44m",
        }

        # Color mappings for different node types and performance impacts
        self.node_colors = {
            NodeType.ENUMERATE_COLLECTION: "red",
            NodeType.INDEX: "green",
            NodeType.FILTER: "yellow",
            NodeType.SORT: "yellow",
            NodeType.LIMIT: "cyan",
            NodeType.RETURN: "green",
            NodeType.CALCULATION: "blue",
            NodeType.SUBQUERY: "magenta",
            NodeType.JOIN: "red",
            NodeType.TRAVERSAL: "yellow",
            NodeType.SCATTER: "yellow",
            NodeType.GATHER: "yellow",
            NodeType.DISTRIBUTE: "yellow",
            NodeType.REMOTE: "magenta",
            NodeType.SINGLETON: "cyan",
            NodeType.INSERT: "magenta",
            NodeType.UPDATE: "magenta",
            NodeType.REPLACE: "magenta",
            NodeType.REMOVE: "magenta",
            NodeType.UPSERT: "magenta",
            NodeType.UNKNOWN: "gray",
        }

        self.impact_colors = {
            PerformanceImpact.HIGH: "red",
            PerformanceImpact.MEDIUM: "yellow",
            PerformanceImpact.LOW: "green",
            PerformanceImpact.UNKNOWN: "gray",
        }

    def parse_plan(self, explain_result: dict[str, Any]) -> ExecutionPlan:
        """
        Parse the ArangoDB explain result into an ExecutionPlan.

        Args:
            explain_result: The raw explain result from ArangoDB

        Returns:
            An ExecutionPlan object
        """
        # Extract the plan data
        plan_data = explain_result.get("plan", {})
        if not plan_data:
            # Try getting it from raw_result if wrapped
            if "raw_result" in explain_result and isinstance(
                explain_result["raw_result"],
                dict,
            ):
                plan_data = explain_result["raw_result"].get("plan", {})
                if not plan_data:
                    return ExecutionPlan()

        # Extract query if available
        query = explain_result.get("query", "")
        if not query and "raw_result" in explain_result:
            query = explain_result.get("raw_result", {}).get("query", "")

        # Initialize the execution plan
        plan = ExecutionPlan(
            total_cost=plan_data.get("estimatedCost", 0.0),
            collections_used=plan_data.get("collections", []),
            query=query,
            cacheable=explain_result.get("cacheable", False),
        )

        # Extract warnings
        warnings = explain_result.get("warnings", [])
        if isinstance(warnings, list):
            for warning in warnings:
                if isinstance(warning, dict) and "message" in warning:
                    plan.warnings.append(warning["message"])
                else:
                    plan.warnings.append(str(warning))

        # Extract nodes
        nodes_data = plan_data.get("nodes", [])

        # Build the execution node tree
        nodes_by_id = {}
        parent_map = {}

        for node_data in nodes_data:
            node_id = node_data.get("id", 0)
            node_type_str = node_data.get("type", "UnknownNode")

            # Map the node type string to our enum
            try:
                node_type = NodeType(node_type_str)
            except ValueError:
                node_type = NodeType.UNKNOWN

            # Create the execution node
            node = ExecutionNode(
                node_id=node_id,
                node_type=node_type,
                collection=node_data.get("collection"),
                estimated_cost=node_data.get("estimatedCost", 0.0),
                raw_data=node_data,
            )

            # Extract expressions
            if "expression" in node_data:
                node.expressions.append(str(node_data["expression"]))

            # Extract index information
            if node_data.get("indexes"):
                index_data = node_data["indexes"][0]  # Take the first index
                node.index = index_data.get("name")
                node.index_type = index_data.get("type")

                # Add to plan's indexes used
                plan.indexes_used.append(
                    {
                        "name": node.index,
                        "type": node.index_type,
                        "collection": node.collection,
                    },
                )

            # Set performance impact based on node type and cost
            node.performance_impact = self._assess_performance_impact(node)

            # Map parent-child relationships
            if "dependencies" in node_data:
                for dep_id in node_data["dependencies"]:
                    if dep_id not in parent_map:
                        parent_map[dep_id] = []
                    parent_map[dep_id].append(node_id)
                    node.parent_id = dep_id

            # Store the node
            nodes_by_id[node_id] = node

        # Set child IDs
        for node_id, node in nodes_by_id.items():
            if node_id in parent_map:
                for child_id in parent_map[node_id]:
                    node.children_ids.append(child_id)

        # Calculate node depths
        self._calculate_node_depths(nodes_by_id)

        # Add nodes to the plan
        plan.nodes = list(nodes_by_id.values())

        # Generate optimizations, bottlenecks, and recommendations
        plan.optimizations = self._identify_optimizations(plan)
        plan.bottlenecks = self._identify_bottlenecks(plan)
        plan.recommendations = self._generate_recommendations(plan)

        return plan

    def _calculate_node_depths(self, nodes_by_id: dict[int, ExecutionNode]) -> None:
        """
        Calculate the depth of each node in the execution tree.

        Args:
            nodes_by_id: Dictionary mapping node IDs to ExecutionNode objects
        """
        # Find root nodes (no parent)
        root_nodes = [node for node in nodes_by_id.values() if node.parent_id is None]

        # Use recursive depth-first traversal to set depths
        def set_depth(node, depth) -> None:
            node.depth = depth
            for child_id in node.children_ids:
                if child_id in nodes_by_id:
                    set_depth(nodes_by_id[child_id], depth + 1)

        # Set depths starting from each root node
        for root in root_nodes:
            set_depth(root, 0)

    def _assess_performance_impact(self, node: ExecutionNode) -> PerformanceImpact:
        """
        Assess the performance impact of a node.

        Args:
            node: The ExecutionNode to assess

        Returns:
            PerformanceImpact enum value
        """
        # Full collection scans are high impact
        if node.node_type == NodeType.ENUMERATE_COLLECTION:
            return PerformanceImpact.HIGH

        # Index scans are generally low impact
        if node.node_type == NodeType.INDEX:
            return PerformanceImpact.LOW

        # Sort operations can be medium to high impact
        if node.node_type == NodeType.SORT:
            if node.estimated_cost > 1000:
                return PerformanceImpact.HIGH
            return PerformanceImpact.MEDIUM

        # Join operations can be high impact
        if node.node_type == NodeType.JOIN:
            return PerformanceImpact.HIGH

        # Base impact on estimated cost for other operations
        if node.estimated_cost > 5000:
            return PerformanceImpact.HIGH
        if node.estimated_cost > 1000:
            return PerformanceImpact.MEDIUM
        if node.estimated_cost > 0:
            return PerformanceImpact.LOW

        return PerformanceImpact.UNKNOWN

    def _identify_optimizations(self, plan: ExecutionPlan) -> list[str]:
        """
        Identify optimizations applied to the query.

        Args:
            plan: The ExecutionPlan

        Returns:
            List of optimization descriptions
        """
        optimizations = []

        # Check if indexes are being used
        index_nodes = [node for node in plan.nodes if node.node_type == NodeType.INDEX]
        if index_nodes:
            index_info = []
            for node in index_nodes:
                if node.collection and node.index:
                    index_info.append(
                        f"{node.collection}.{node.index} ({node.index_type})",
                    )
                elif node.index:
                    index_info.append(f"{node.index} ({node.index_type})")

            if index_info:
                optimizations.append(f"Using indexes: {', '.join(index_info)}")

        # Check if filters are pushed down to index scans
        if any(node.node_type == NodeType.INDEX and node.expressions for node in plan.nodes):
            optimizations.append("Filter conditions pushed down to index scan")

        # Check if limits are applied early
        limit_nodes = [node for node in plan.nodes if node.node_type == NodeType.LIMIT]
        if limit_nodes and any(node.depth < len(plan.nodes) // 2 for node in limit_nodes):
            optimizations.append("Limit applied early in the execution plan")

        return optimizations

    def _identify_bottlenecks(self, plan: ExecutionPlan) -> list[str]:
        """
        Identify potential bottlenecks in the query.

        Args:
            plan: The ExecutionPlan

        Returns:
            List of bottleneck descriptions
        """
        bottlenecks = []

        # Check for full collection scans
        scan_nodes = [node for node in plan.nodes if node.node_type == NodeType.ENUMERATE_COLLECTION]
        if scan_nodes:
            collections = [node.collection for node in scan_nodes if node.collection]
            if collections:
                bottlenecks.append(
                    f"Full collection scan(s) on: {', '.join(collections)}",
                )

        # Check for expensive sorts
        sort_nodes = [node for node in plan.nodes if node.node_type == NodeType.SORT and node.estimated_cost > 1000]
        if sort_nodes:
            bottlenecks.append("Expensive sort operation(s)")

        # Check for expensive join operations
        join_nodes = [node for node in plan.nodes if node.node_type == NodeType.JOIN]
        if join_nodes:
            bottlenecks.append("Join operation(s) may be expensive")

        # Check overall cost
        if plan.total_cost > 10000:
            bottlenecks.append(f"High overall query cost: {plan.total_cost:.2f}")

        return bottlenecks

    def _generate_recommendations(self, plan: ExecutionPlan) -> list[str]:
        """
        Generate recommendations for improving the query.

        Args:
            plan: The ExecutionPlan

        Returns:
            List of recommendation descriptions
        """
        recommendations = []

        # Recommend indexes for full collection scans
        scan_nodes = [node for node in plan.nodes if node.node_type == NodeType.ENUMERATE_COLLECTION]
        if scan_nodes:
            collections = [node.collection for node in scan_nodes if node.collection]
            for collection in collections:
                # Look for filter expressions related to this collection
                filter_nodes = [node for node in plan.nodes if node.node_type == NodeType.FILTER and node.expressions]

                if filter_nodes:
                    filters = []
                    for node in filter_nodes:
                        for expr in node.expressions:
                            if collection in expr:
                                # Extract field name from filter expression
                                matches = re.findall(rf"{collection}\.(\w+)", expr)
                                if matches:
                                    filters.extend(matches)

                    if filters:
                        recommendations.append(
                            f"Consider adding an index on {collection} for field(s): {', '.join(set(filters))}",
                        )
                    else:
                        recommendations.append(
                            f"Consider adding appropriate indexes on {collection}",
                        )

        # Recommend using LIMIT if high cost
        if plan.total_cost > 5000 and not any(node.node_type == NodeType.LIMIT for node in plan.nodes):
            recommendations.append(
                "Consider adding a LIMIT clause to reduce result set size",
            )

        # Recommend filter pushdown
        if any(node.node_type == NodeType.FILTER and node.depth > 1 for node in plan.nodes):
            recommendations.append(
                "Consider restructuring filters to allow pushdown optimization",
            )

        return recommendations

    def visualize_text(
        self,
        plan: ExecutionPlan | dict[str, Any],
        verbose: bool = False,
    ) -> str:
        """
        Visualize the execution plan as formatted text.

        Args:
            plan: Either an ExecutionPlan object or the raw explain result
            verbose: Whether to include all details

        Returns:
            Formatted text visualization
        """
        # Parse the plan if it's a raw explain result
        if isinstance(plan, dict):
            plan = self.parse_plan(plan)

        # Ensure we have a valid plan
        if not isinstance(plan, ExecutionPlan):
            return "Invalid execution plan"

        # Start building the visualization
        lines = []

        # Add query and overall stats
        if plan.query:
            query_display = self._colorize("Query:", "bold")
            lines.append(f"{query_display} {plan.query}")
            lines.append("")

        # Add summary section
        summary = self._colorize("Summary:", "bold")
        lines.append(summary)
        lines.append(f"  Total Cost: {self._format_cost(plan.total_cost)}")
        lines.append(f"  Collections: {', '.join(plan.collections_used)}")

        if plan.indexes_used:
            indexes = []
            for idx in plan.indexes_used:
                if "name" in idx and "collection" in idx and "type" in idx:
                    indexes.append(f"{idx['collection']}.{idx['name']} ({idx['type']})")
                elif "name" in idx and "type" in idx:
                    indexes.append(f"{idx['name']} ({idx['type']})")
                elif "name" in idx:
                    indexes.append(idx["name"])
            if indexes:
                lines.append(f"  Indexes Used: {', '.join(indexes)}")

        lines.append(f"  Cacheable: {plan.cacheable}")
        lines.append("")

        # Add execution plan visualization
        exec_plan = self._colorize("Execution Plan:", "bold")
        lines.append(exec_plan)

        # Find root nodes (no parent)
        root_nodes = [node for node in plan.nodes if node.parent_id is None]

        # Visualize each tree starting from the root nodes
        for root in root_nodes:
            tree_lines = self._visualize_node_tree(root, plan.nodes, "", verbose)
            lines.extend(tree_lines)

        lines.append("")

        # Add optimizations
        if plan.optimizations:
            optimizations = self._colorize("Optimizations:", "bold")
            lines.append(optimizations)
            for opt in plan.optimizations:
                lines.append(f"  ✓ {self._colorize(opt, 'green')}")
            lines.append("")

        # Add bottlenecks
        if plan.bottlenecks:
            bottlenecks = self._colorize("Bottlenecks:", "bold")
            lines.append(bottlenecks)
            for bottleneck in plan.bottlenecks:
                lines.append(f"  ⚠ {self._colorize(bottleneck, 'red')}")
            lines.append("")

        # Add recommendations
        if plan.recommendations:
            recommendations = self._colorize("Recommendations:", "bold")
            lines.append(recommendations)
            for rec in plan.recommendations:
                lines.append(f"  → {self._colorize(rec, 'yellow')}")
            lines.append("")

        # Add warnings
        if plan.warnings:
            warnings = self._colorize("Warnings:", "bold")
            lines.append(warnings)
            for warning in plan.warnings:
                lines.append(f"  ⚠ {self._colorize(warning, 'red')}")
            lines.append("")

        return "\n".join(lines)

    def _visualize_node_tree(
        self,
        node: ExecutionNode,
        all_nodes: list[ExecutionNode],
        prefix: str = "",
        verbose: bool = False,
    ) -> list[str]:
        """
        Recursively visualize a node and its children.

        Args:
            node: The current node to visualize
            all_nodes: All nodes in the plan
            prefix: The line prefix for indentation
            verbose: Whether to include all details

        Returns:
            List of formatted lines
        """
        # Skip if depth exceeds maximum
        if node.depth > self.max_depth:
            return []

        lines = []

        # Get node children
        children = [n for n in all_nodes if n.node_id in node.children_ids]

        # Determine if this is the last node at this level
        is_last = True  # Since we're processing from roots in a custom order

        # Create the node line
        if is_last:
            node_prefix = prefix + "└─ "
            child_prefix = prefix + "   "
        else:
            node_prefix = prefix + "├─ "
            child_prefix = prefix + "│  "

        # Format the node description
        node_desc = self._format_node(node, verbose)
        lines.append(f"{node_prefix}{node_desc}")

        # Recursively add children
        for child in children:
            child_lines = self._visualize_node_tree(
                child,
                all_nodes,
                child_prefix,
                verbose,
            )
            lines.extend(child_lines)

        return lines

    def _format_node(self, node: ExecutionNode, verbose: bool = False) -> str:
        """
        Format a node for display.

        Args:
            node: The node to format
            verbose: Whether to include all details

        Returns:
            Formatted node string
        """
        # Base description with node type
        node_type_color = self.node_colors.get(node.node_type, "white")
        node_type_str = self._colorize(node.node_type.value, node_type_color)

        desc = node_type_str

        # Add collection name if available
        if node.collection:
            desc += f" on {self._colorize(node.collection, 'cyan')}"

        # Add index if available
        if node.index:
            index_str = f"using index {node.index}"
            if node.index_type:
                index_str += f" ({node.index_type})"
            desc += f" {self._colorize(index_str, 'green')}"

        # Add cost
        cost_str = self._format_cost(node.estimated_cost)
        desc += f" {self._colorize(f'[Cost: {cost_str}]', 'gray')}"

        # Add expressions for verbose mode
        if verbose and node.expressions:
            expr_str = " ".join(textwrap.shorten(expr, width=50) for expr in node.expressions)
            # Use a space for indentation since child_prefix isn't defined here
            desc += f"\n    {self._colorize(f'Expression: {expr_str}', 'gray')}"

        return desc

    def _format_cost(self, cost: float) -> str:
        """
        Format a cost value with appropriate units and coloring.

        Args:
            cost: The cost value to format

        Returns:
            Formatted cost string
        """
        if cost > 5000:
            return self._colorize(f"{cost:.2f}", "red")
        if cost > 1000:
            return self._colorize(f"{cost:.2f}", "yellow")
        return self._colorize(f"{cost:.2f}", "green")

    def _colorize(self, text: str, color: str) -> str:
        """
        Apply ANSI color to text if colorization is enabled.

        Args:
            text: The text to colorize
            color: The color to apply

        Returns:
            Colorized text
        """
        if not self.colorize:
            return text

        color_code = self.colors.get(color, "")
        if not color_code:
            return text

        return f"{color_code}{text}{self.colors['reset']}"
