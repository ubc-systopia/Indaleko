"""This module defines the data models for enhanced natural language processing.

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



class QueryIntentType(str, Enum):
    """Defines the different types of query intents supported by the system."""

    SEARCH = "search"  # Basic search for objects
    FILTER = "filter"  # Apply filters to search results
    SORT = "sort"  # Sort results by a specific field
    AGGREGATE = "aggregate"  # Aggregate data (count, sum, etc.)
    COUNT = "count"  # Count matching objects
    ANALYZE = "analyze"  # Analyze patterns in data
    RELATIONSHIP = "relationship"  # Find relationships between objects
    TIMELINE = "timeline"  # Generate a timeline view
    CONTENT = "content"  # Search within object content
    COMPARE = "compare"  # Compare multiple objects
    CONTEXT = "context"  # Find context for objects (activity data)
    UNKNOWN = "unknown"  # Default when intent is unclear


class QueryConstraintType(str, Enum):
    """Defines the different types of constraints that can be applied to queries."""

    EQUALS = "equals"  # Exact equality
    CONTAINS = "contains"  # String contains
    STARTS_WITH = "starts_with"  # String starts with
    ENDS_WITH = "ends_with"  # String ends with
    GREATER_THAN = "greater_than"  # Greater than (numeric/dates)
    LESS_THAN = "less_than"  # Less than (numeric/dates)
    BETWEEN = "between"  # Between two values
    NEAR = "near"  # Geographical proximity
    WITHIN = "within"  # Contained within
    MATCHES = "matches"  # Regex or pattern matching
    NOT = "not"  # Negation of other constraint
    IN = "in"  # Value in a set
    BEFORE = "before"  # Temporal before
    AFTER = "after"  # Temporal after
    SIMILAR_TO = "similar_to"  # Semantic similarity


class EntityResolution(BaseModel):
    """Represents resolved entity information from the query."""

    original_text: str = Field(..., description="Original entity text from the query")
    normalized_value: str = Field(..., description="Normalized value of the entity")
    entity_type: str = Field(
        ..., description="Type of entity (e.g., person, location, date)",
    )
    confidence: float = Field(
        ..., description="Confidence score for the entity resolution",
    )
    resolved_entity: dict[str, Any] | None = Field(
        None, description="Resolved entity from the database if available",
    )


class QueryConstraint(BaseModel):
    """Represents a single constraint in the query."""

    field: str = Field(..., description="Field to apply the constraint to")
    operation: QueryConstraintType = Field(
        ..., description="Type of constraint operation",
    )
    value: Any = Field(..., description="Value to compare against")
    entity_resolution: EntityResolution | None = Field(
        None, description="Resolution info if the value was an entity",
    )
    confidence: float = Field(default=1.0, description="Confidence in this constraint")


class QueryIntent(BaseModel):
    """Detailed representation of a query's intent."""

    primary_intent: QueryIntentType = Field(
        ..., description="Primary intent of the query",
    )
    secondary_intents: list[QueryIntentType] = Field(
        default_factory=list, description="Secondary intents",
    )
    confidence: float = Field(
        ..., description="Confidence in the intent classification",
    )
    description: str = Field(
        ...,
        description="Human-readable description of what the query is trying to accomplish",
    )


class RelationshipInfo(BaseModel):
    """Describes a relationship query between entities."""

    source_entity: EntityResolution = Field(
        ..., description="Source entity in the relationship",
    )
    target_entity: EntityResolution | None = Field(
        None, description="Target entity in the relationship",
    )
    relationship_type: str = Field(..., description="Type of relationship sought")
    direction: str = Field(
        default="any", description="Direction of relationship (any, from, to)",
    )


class TimeConstraint(BaseModel):
    """Represents a time-based constraint for timeline queries."""

    start_time: str | None = Field(None, description="Start time for the constraint")
    end_time: str | None = Field(None, description="End time for the constraint")
    time_field: str = Field(..., description="Field to apply the time constraint to")
    resolution: str = Field(
        default="day",
        description="Time resolution (second, minute, hour, day, month, year)",
    )


class FacetSuggestion(BaseModel):
    """Represents a suggested facet based on query analysis."""

    facet_name: str = Field(..., description="Name of the suggested facet")
    facet_description: str = Field(
        ..., description="Description of what this facet represents",
    )
    relevance: float = Field(..., description="Relevance score for this facet")
    example_values: list[str] = Field(
        default_factory=list, description="Example values for this facet",
    )


class QueryContext(BaseModel):
    """Additional contextual information about the query."""

    collections: list[str] = Field(
        ..., description="Collections relevant to this query",
    )
    temporal_context: TimeConstraint | None = Field(
        None, description="Temporal context for the query",
    )
    spatial_context: dict[str, Any] | None = Field(
        None, description="Spatial context for the query",
    )
    user_context: dict[str, Any] | None = Field(
        None, description="User-specific context",
    )
    activity_context: dict[str, Any] | None = Field(
        None, description="Activity context relevant to the query",
    )


class EnhancedQueryUnderstanding(BaseModel):
    """Enhanced understanding of a natural language query."""

    original_query: str = Field(..., description="Original query text")
    intent: QueryIntent = Field(..., description="Detailed intent information")
    entities: list[EntityResolution] = Field(
        default_factory=list, description="Resolved entities",
    )
    constraints: list[QueryConstraint] = Field(
        default_factory=list, description="Query constraints",
    )
    context: QueryContext = Field(..., description="Query context information")
    relationships: list[RelationshipInfo] | None = Field(
        None, description="Relationship information if relevant",
    )
    suggested_facets: list[FacetSuggestion] = Field(
        default_factory=list, description="Suggested facets for exploration",
    )
    refinement_suggestions: list[str] = Field(
        default_factory=list, description="Suggested query refinements",
    )
    conversational_response: str = Field(
        ..., description="Natural language response explaining the query understanding",
    )
    confidence: float = Field(
        ..., description="Overall confidence in the query understanding",
    )
