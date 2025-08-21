"""
Data model for AQL query execution plans.

This module defines the data models for storing and analyzing AQL query execution plans.

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

import contextlib
import datetime
import os
import sys

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


class PlanNode(BaseModel):
    """A node in the AQL query execution plan."""

    id: int = Field(..., description="The node ID")
    type: str = Field(..., description="The type of operation")
    dependencies: list[int] = Field(
        default_factory=list,
        description="IDs of dependent nodes",
    )
    estimatedCost: float = Field(0, description="Estimated cost of this operation")

    # Optional fields that depend on node type
    collection: str | None = Field(
        None,
        description="Collection being accessed (if applicable)",
    )
    indexes: list[dict[str, Any]] | None = Field(
        None,
        description="Indexes being used (if applicable)",
    )
    condition: dict[str, Any] | None = Field(
        None,
        description="Filter condition (if applicable)",
    )

    # Additional fields will be stored in the extra dict
    class Config:
        extra = "allow"


class QueryPlan(BaseModel):
    """An AQL query execution plan."""

    nodes: list[PlanNode] = Field(
        default_factory=list,
        description="Operation nodes in the plan",
    )
    rules: list[str] = Field(
        default_factory=list,
        description="Optimizer rules applied",
    )
    collections: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Collections used",
    )
    variables: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Variables used",
    )
    estimatedCost: float = Field(0, description="Total estimated cost of the plan")


class QueryAnalysis(BaseModel):
    """Analysis of an AQL query execution plan."""

    summary: dict[str, Any] = Field(default_factory=dict, description="Summary metrics")
    warnings: list[str] = Field(
        default_factory=list,
        description="Potential issues detected",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recommendations for optimization",
    )
    indexes_used: list[str] = Field(
        default_factory=list,
        description="Indexes used in the query",
    )


class QueryPerformance(BaseModel):
    """Performance metrics for an executed query."""

    execution_time_seconds: float = Field(
        0,
        description="Total execution time in seconds",
    )
    cpu: dict[str, float] = Field(default_factory=dict, description="CPU usage metrics")
    memory: dict[str, int] = Field(
        default_factory=dict,
        description="Memory usage metrics",
    )
    io: dict[str, int] = Field(default_factory=dict, description="I/O metrics")
    threads: int = Field(0, description="Number of threads used")
    query_length: int = Field(0, description="Length of the query string")


class QueryHintSeverity(str, Enum):
    """Severity levels for query performance hints."""

    INFO = "info"  # Informational hint
    WARNING = "warning"  # Warning about potential issues
    ERROR = "error"  # Error condition
    CRITICAL = "critical"  # Critical issue


class QueryPerformanceImpact(str, Enum):
    """Performance impact levels for query hints."""

    POSITIVE = "positive"  # Positive impact on performance
    NEUTRAL = "neutral"  # No significant impact
    NEGATIVE = "negative"  # Negative impact on performance
    CRITICAL = "critical"  # Critical performance issue


class QueryPerformanceHint(BaseModel):
    """Performance hint for query optimization."""

    hint_type: str = Field(..., description="Type of performance hint")
    description: str = Field(..., description="Description of the performance hint")
    severity: QueryHintSeverity = Field(..., description="Severity of the hint")
    affected_component: str = Field(..., description="Component affected by the hint")
    performance_impact: QueryPerformanceImpact = Field(
        ...,
        description="Impact on query performance",
    )
    recommendation: str | None = Field(
        None,
        description="Recommendation for improvement",
    )


class QueryExecutionPlan(BaseModel):
    """Comprehensive information about a query's execution plan and performance."""

    query_id: str = Field(..., description="Unique identifier for the query")
    query: str = Field(..., description="The AQL query text")
    bind_vars: dict[str, Any] = Field(
        default_factory=dict,
        description="Bind variables used",
    )
    timestamp: datetime.datetime = Field(
        default_factory=datetime.datetime.now,
        description="When the plan was generated",
    )

    # The main execution plan
    plan: QueryPlan = Field(..., description="The main execution plan")

    # Alternative plans (if allPlans was true)
    alternative_plans: list[QueryPlan] = Field(
        default_factory=list,
        description="Alternative execution plans",
    )

    # Analysis of the execution plan
    analysis: QueryAnalysis = Field(
        default_factory=QueryAnalysis,
        description="Analysis of the plan",
    )

    # Performance metrics (if the query was executed)
    performance: QueryPerformance | None = Field(
        None,
        description="Performance metrics if executed",
    )

    # Query execution statistics
    stats: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution statistics",
    )

    # Caching information
    cacheable: bool = Field(False, description="Whether the query is cacheable")

    # Raw explain result from ArangoDB
    raw_explain: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw explain result from ArangoDB",
    )

    @classmethod
    def from_explain_result(
        cls,
        query_id: str,
        query: str,
        explain_result: Any,
        bind_vars: dict[str, Any] | None = None,
        performance: dict[str, Any] | None = None,
    ) -> "QueryExecutionPlan":
        """
        Create a QueryExecutionPlan from an ArangoDB explain result.

        Args:
            query_id (str): A unique identifier for the query
            query (str): The AQL query string
            explain_result (Any): The explain result from ArangoDB
            bind_vars (Optional[Dict[str, Any]]): The bind variables used in the query
            performance (Optional[Dict[str, Any]]): Performance metrics if the query was executed

        Returns:
            QueryExecutionPlan: A structured representation of the query plan
        """
        if bind_vars is None:
            bind_vars = {}

        # Ensure explain_result is a dictionary
        if not isinstance(explain_result, dict):
            # Create a default plan if we don't have a dictionary result
            return cls(
                query_id=query_id,
                query=query,
                bind_vars=bind_vars,
                plan=QueryPlan(),
                analysis=QueryAnalysis(
                    warnings=[
                        f"Unexpected explain result type: {type(explain_result)}",
                    ],
                    recommendations=["Check query syntax and database configuration"],
                ),
                performance=None,
                stats={},
                cacheable=False,
                raw_explain={"raw_result": explain_result},
            )

        # Extract the main plan
        plan_data = explain_result.get("plan", {})
        if not plan_data:
            # Use raw_result if available
            plan_data = explain_result.get("raw_result", {})
            if isinstance(plan_data, dict) and "plan" in plan_data:
                plan_data = plan_data["plan"]
            else:
                plan_data = {}

        # Parse plan nodes
        nodes = []
        for node_data in plan_data.get("nodes", []):
            try:
                nodes.append(PlanNode(**node_data))
            except Exception:
                # Skip invalid nodes
                pass

        # Create the main plan
        plan = QueryPlan(
            nodes=nodes,
            rules=plan_data.get("rules", []),
            collections=plan_data.get("collections", []),
            variables=plan_data.get("variables", []),
            estimatedCost=plan_data.get("estimatedCost", 0),
        )

        # Parse alternative plans if available
        alternative_plans = []
        for alt_plan_data in explain_result.get("plans", []):
            if not isinstance(alt_plan_data, dict):
                continue

            alt_nodes = []
            for node_data in alt_plan_data.get("nodes", []):
                try:
                    alt_nodes.append(PlanNode(**node_data))
                except Exception:
                    # Skip invalid nodes
                    pass

            alternative_plans.append(
                QueryPlan(
                    nodes=alt_nodes,
                    rules=alt_plan_data.get("rules", []),
                    collections=alt_plan_data.get("collections", []),
                    variables=alt_plan_data.get("variables", []),
                    estimatedCost=alt_plan_data.get("estimatedCost", 0),
                ),
            )

        # Extract analysis if available
        analysis_data = explain_result.get("analysis", {})
        analysis = QueryAnalysis(
            summary=analysis_data.get("summary", {}),
            warnings=analysis_data.get("warnings", []),
            recommendations=analysis_data.get("recommendations", []),
            indexes_used=analysis_data.get("summary", {}).get("indexes_used", []),
        )

        # Extract performance metrics if available
        performance_model = None
        if performance:
            with contextlib.suppress(Exception):
                performance_model = QueryPerformance(**performance)

        # Create the full execution plan model
        return cls(
            query_id=query_id,
            query=query,
            bind_vars=bind_vars,
            plan=plan,
            alternative_plans=alternative_plans,
            analysis=analysis,
            performance=performance_model,
            stats=explain_result.get("stats", {}),
            cacheable=explain_result.get("cacheable", False),
            raw_explain=explain_result,
        )
