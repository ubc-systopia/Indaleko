"""Ablation results models for the ablation testing framework."""

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import Field

from data_models.base import IndalekoBaseModel


class MetricType(str, Enum):
    """Types of metrics used in ablation testing."""

    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    LATENCY = "latency"
    RELEVANCE = "relevance"
    COMPLETENESS = "completeness"
    CUSTOM = "custom"


class AblationResult(IndalekoBaseModel):
    """Model for storing results of an ablation test.

    This model stores performance metrics for a specific query with
    a specific collection ablated from the database.
    """

    id: UUID = Field(default_factory=uuid4)
    test_id: UUID
    query_id: UUID
    query_text: str
    ablated_collection: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Performance metrics before ablation
    baseline_metrics: dict[str, float]

    # Performance metrics after ablation
    ablated_metrics: dict[str, float]

    # Impact of ablation (difference between baseline and ablated)
    impact_metrics: dict[str, float]

    # Number of results returned
    baseline_result_count: int
    ablated_result_count: int

    # Execution details
    execution_time_ms: float

    # Additional metadata
    metadata: dict[str, object] = Field(default_factory=dict)

    class Config:
        frozen = False
        arbitrary_types_allowed = True

    @classmethod
    def get_arangodb_schema(cls) -> dict:
        """Get the ArangoDB schema for this model."""
        return {
            "properties": {
                "id": {"type": "string"},
                "test_id": {"type": "string"},
                "query_id": {"type": "string"},
                "query_text": {"type": "string"},
                "ablated_collection": {"type": "string"},
                "timestamp": {"type": "string", "format": "date-time"},
                "baseline_metrics": {"type": "object"},
                "ablated_metrics": {"type": "object"},
                "impact_metrics": {"type": "object"},
                "baseline_result_count": {"type": "integer"},
                "ablated_result_count": {"type": "integer"},
                "execution_time_ms": {"type": "number"},
                "metadata": {"type": "object"},
            },
            "required": [
                "id",
                "test_id",
                "query_id",
                "query_text",
                "ablated_collection",
                "timestamp",
                "baseline_metrics",
                "ablated_metrics",
                "impact_metrics",
                "baseline_result_count",
                "ablated_result_count",
                "execution_time_ms",
            ],
            "additionalProperties": False,
        }


class AblationTestMetadata(IndalekoBaseModel):
    """Model for storing metadata about an ablation test run.

    This model contains information about the test environment, configuration,
    and summary results across all queries in the test.
    """

    id: UUID = Field(default_factory=uuid4)
    test_id: UUID
    test_name: str
    description: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Test configuration
    ablation_collections: list[str]
    query_count: int

    # Test environment
    environment: dict[str, str] = Field(default_factory=dict)

    # Summary metrics across all queries
    summary_metrics: dict[str, dict[str, float]] = Field(default_factory=dict)

    # Overall impact ranking of collections (most to least impactful)
    impact_ranking: list[dict[str, str | float]] = Field(default_factory=list)

    # Runtime statistics
    total_execution_time_ms: float
    average_query_time_ms: float

    # Additional metadata
    metadata: dict[str, object] = Field(default_factory=dict)

    class Config:
        frozen = False
        arbitrary_types_allowed = True

    @classmethod
    def get_arangodb_schema(cls) -> dict:
        """Get the ArangoDB schema for this model."""
        return {
            "properties": {
                "id": {"type": "string"},
                "test_id": {"type": "string"},
                "test_name": {"type": "string"},
                "description": {"type": "string"},
                "timestamp": {"type": "string", "format": "date-time"},
                "ablation_collections": {"type": "array", "items": {"type": "string"}},
                "query_count": {"type": "integer"},
                "environment": {"type": "object"},
                "summary_metrics": {"type": "object"},
                "impact_ranking": {"type": "array", "items": {"type": "object"}},
                "total_execution_time_ms": {"type": "number"},
                "average_query_time_ms": {"type": "number"},
                "metadata": {"type": "object"},
            },
            "required": [
                "id",
                "test_id",
                "test_name",
                "timestamp",
                "ablation_collections",
                "query_count",
                "total_execution_time_ms",
                "average_query_time_ms",
            ],
            "additionalProperties": False,
        }


class AblationQueryTruth(IndalekoBaseModel):
    """Model for storing ground truth data for ablation queries.

    This model links queries to their expected results and the activity types
    that they are targeting, allowing for accurate measurement of precision and recall.
    """

    id: UUID = Field(default_factory=uuid4)
    query_id: UUID
    query_text: str
    matching_ids: list[str]
    activity_types: list[str]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Indicates whether this is a synthetic query or based on real user data
    synthetic: bool = True

    # Difficulty level of the query (used for analysis)
    difficulty: str = "medium"  # easy, medium, hard

    # Additional metadata
    metadata: dict[str, object] = Field(default_factory=dict)

    class Config:
        frozen = False
        arbitrary_types_allowed = True

    @classmethod
    def get_arangodb_schema(cls) -> dict:
        """Get the ArangoDB schema for this model."""
        return {
            "properties": {
                "id": {"type": "string"},
                "query_id": {"type": "string"},
                "query_text": {"type": "string"},
                "matching_ids": {"type": "array", "items": {"type": "string"}},
                "activity_types": {"type": "array", "items": {"type": "string"}},
                "created_at": {"type": "string", "format": "date-time"},
                "synthetic": {"type": "boolean"},
                "difficulty": {"type": "string"},
                "metadata": {"type": "object"},
            },
            "required": ["id", "query_id", "query_text", "matching_ids", "activity_types", "created_at"],
            "additionalProperties": False,
        }
