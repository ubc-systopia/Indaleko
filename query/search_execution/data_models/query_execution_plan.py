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

import os
import sys
import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


class PlanNode(BaseModel):
    """
    A node in the AQL query execution plan.
    """
    id: int = Field(..., description="The node ID")
    type: str = Field(..., description="The type of operation")
    dependencies: List[int] = Field(default_factory=list, description="IDs of dependent nodes")
    estimatedCost: float = Field(0, description="Estimated cost of this operation")
    
    # Optional fields that depend on node type
    collection: Optional[str] = Field(None, description="Collection being accessed (if applicable)")
    indexes: Optional[List[Dict[str, Any]]] = Field(None, description="Indexes being used (if applicable)")
    condition: Optional[Dict[str, Any]] = Field(None, description="Filter condition (if applicable)")
    
    # Additional fields will be stored in the extra dict
    class Config:
        extra = "allow"


class QueryPlan(BaseModel):
    """
    An AQL query execution plan.
    """
    nodes: List[PlanNode] = Field(default_factory=list, description="Operation nodes in the plan")
    rules: List[str] = Field(default_factory=list, description="Optimizer rules applied")
    collections: List[Dict[str, Any]] = Field(default_factory=list, description="Collections used")
    variables: List[Dict[str, Any]] = Field(default_factory=list, description="Variables used")
    estimatedCost: float = Field(0, description="Total estimated cost of the plan")


class QueryAnalysis(BaseModel):
    """
    Analysis of an AQL query execution plan.
    """
    summary: Dict[str, Any] = Field(default_factory=dict, description="Summary metrics")
    warnings: List[str] = Field(default_factory=list, description="Potential issues detected")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for optimization")
    indexes_used: List[str] = Field(default_factory=list, description="Indexes used in the query")


class QueryPerformance(BaseModel):
    """
    Performance metrics for an executed query.
    """
    execution_time_seconds: float = Field(0, description="Total execution time in seconds")
    cpu: Dict[str, float] = Field(default_factory=dict, description="CPU usage metrics")
    memory: Dict[str, int] = Field(default_factory=dict, description="Memory usage metrics")
    io: Dict[str, int] = Field(default_factory=dict, description="I/O metrics")
    threads: int = Field(0, description="Number of threads used")
    query_length: int = Field(0, description="Length of the query string")


class QueryExecutionPlan(BaseModel):
    """
    Comprehensive information about a query's execution plan and performance.
    """
    query_id: str = Field(..., description="Unique identifier for the query")
    query: str = Field(..., description="The AQL query text")
    bind_vars: Dict[str, Any] = Field(default_factory=dict, description="Bind variables used")
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now, description="When the plan was generated")
    
    # The main execution plan
    plan: QueryPlan = Field(..., description="The main execution plan")
    
    # Alternative plans (if allPlans was true)
    alternative_plans: List[QueryPlan] = Field(default_factory=list, description="Alternative execution plans")
    
    # Analysis of the execution plan
    analysis: QueryAnalysis = Field(default_factory=QueryAnalysis, description="Analysis of the plan")
    
    # Performance metrics (if the query was executed)
    performance: Optional[QueryPerformance] = Field(None, description="Performance metrics if executed")
    
    # Query execution statistics
    stats: Dict[str, Any] = Field(default_factory=dict, description="Execution statistics")
    
    # Caching information
    cacheable: bool = Field(False, description="Whether the query is cacheable")
    
    # Raw explain result from ArangoDB
    raw_explain: Dict[str, Any] = Field(default_factory=dict, description="Raw explain result from ArangoDB")
    
    @classmethod
    def from_explain_result(
        cls, 
        query_id: str,
        query: str,
        explain_result: Any,
        bind_vars: Optional[Dict[str, Any]] = None,
        performance: Optional[Dict[str, Any]] = None
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
                    warnings=[f"Unexpected explain result type: {type(explain_result)}"],
                    recommendations=["Check query syntax and database configuration"]
                ),
                performance=None,
                stats={},
                cacheable=False,
                raw_explain={"raw_result": explain_result}
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
            except Exception as e:
                # Skip invalid nodes
                print(f"Warning: Could not parse plan node: {e}")
            
        # Create the main plan
        plan = QueryPlan(
            nodes=nodes,
            rules=plan_data.get("rules", []),
            collections=plan_data.get("collections", []),
            variables=plan_data.get("variables", []),
            estimatedCost=plan_data.get("estimatedCost", 0)
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
                except Exception as e:
                    # Skip invalid nodes
                    print(f"Warning: Could not parse alternative plan node: {e}")
                
            alternative_plans.append(QueryPlan(
                nodes=alt_nodes,
                rules=alt_plan_data.get("rules", []),
                collections=alt_plan_data.get("collections", []),
                variables=alt_plan_data.get("variables", []),
                estimatedCost=alt_plan_data.get("estimatedCost", 0)
            ))
        
        # Extract analysis if available
        analysis_data = explain_result.get("analysis", {})
        analysis = QueryAnalysis(
            summary=analysis_data.get("summary", {}),
            warnings=analysis_data.get("warnings", []),
            recommendations=analysis_data.get("recommendations", []),
            indexes_used=analysis_data.get("summary", {}).get("indexes_used", [])
        )
        
        # Extract performance metrics if available
        performance_model = None
        if performance:
            try:
                performance_model = QueryPerformance(**performance)
            except Exception as e:
                print(f"Warning: Could not parse performance data: {e}")
        
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
            raw_explain=explain_result
        )