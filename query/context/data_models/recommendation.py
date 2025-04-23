"""
Data models for the Contextual Query Recommendation Engine.

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

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import Field

from data_models.base import IndalekoBaseModel


class RecommendationSource(str, Enum):
    """Types of recommendation sources."""

    QUERY_HISTORY = "query_history"
    ACTIVITY_CONTEXT = "activity_context"
    ENTITY_RELATIONSHIP = "entity_relationship"
    TEMPORAL_PATTERN = "temporal_pattern"
    MANUAL = "manual"
    SYSTEM = "system"


class FeedbackType(str, Enum):
    """Types of user feedback on recommendations."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEUTRAL = "neutral"
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    IRRELEVANT = "irrelevant"


class QuerySuggestion(IndalekoBaseModel):
    """Model representing a suggested query."""

    suggestion_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    query_text: str = Field(..., description="The suggested query text")
    rationale: str = Field(
        ..., description="Explanation of why this query is suggested",
    )
    confidence: float = Field(..., description="Confidence score (0.0-1.0)")
    source: RecommendationSource = Field(
        ..., description="Source of this recommendation",
    )
    source_context: dict[str, Any] = Field(
        default_factory=dict, description="Context information from the source",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this suggestion was created",
    )
    relevance_factors: dict[str, float] = Field(
        default_factory=dict, description="Factors contributing to relevance score",
    )
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")

    class Config:
        """Configuration for the model."""

        json_schema_extra = {
            "example": {
                "suggestion_id": "12345678-1234-5678-1234-567812345678",
                "query_text": "Find PDF documents created last week related to Indaleko",
                "rationale": "Based on your recent searches and file creation activity",
                "confidence": 0.85,
                "source": "activity_context",
                "source_context": {
                    "recent_file_types": ["pdf", "docx"],
                    "recent_topics": ["Indaleko", "documentation"],
                },
                "created_at": "2025-04-20T10:15:30+00:00",
                "relevance_factors": {
                    "recency": 0.9,
                    "activity_match": 0.8,
                    "query_similarity": 0.7,
                },
                "tags": ["document_search", "recent_activity", "file_type"],
            },
        }


class RecommendationFeedback(IndalekoBaseModel):
    """Model for recording feedback on recommendations."""

    feedback_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    suggestion_id: uuid.UUID = Field(
        ..., description="ID of the suggestion receiving feedback",
    )
    feedback_type: FeedbackType = Field(..., description="Type of feedback provided")
    result_count: int | None = Field(
        None, description="Number of results from the suggested query",
    )
    user_comments: str | None = Field(None, description="Optional user comments")
    context: dict[str, Any] = Field(
        default_factory=dict, description="Context when feedback was given",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When feedback was provided",
    )

    class Config:
        """Configuration for the model."""

        json_schema_extra = {
            "example": {
                "feedback_id": "87654321-8765-4321-8765-432187654321",
                "suggestion_id": "12345678-1234-5678-1234-567812345678",
                "feedback_type": "helpful",
                "result_count": 7,
                "user_comments": "Exactly what I needed",
                "context": {
                    "session_id": "abc123",
                    "current_task": "documentation_review",
                },
                "timestamp": "2025-04-20T10:30:45+00:00",
            },
        }


class RecommendationSettings(IndalekoBaseModel):
    """Settings for the recommendation engine."""

    enabled: bool = Field(True, description="Whether recommendations are enabled")
    max_suggestions: int = Field(
        5, description="Maximum number of suggestions to return",
    )
    min_confidence: float = Field(0.5, description="Minimum confidence threshold")
    refresh_interval: int = Field(60, description="Refresh interval in seconds")
    source_weights: dict[RecommendationSource, float] = Field(
        default_factory=lambda: {
            RecommendationSource.QUERY_HISTORY: 1.0,
            RecommendationSource.ACTIVITY_CONTEXT: 1.0,
            RecommendationSource.ENTITY_RELATIONSHIP: 0.8,
            RecommendationSource.TEMPORAL_PATTERN: 0.7,
            RecommendationSource.MANUAL: 1.0,
            RecommendationSource.SYSTEM: 0.9,
        },
        description="Weights for different recommendation sources",
    )
    enable_learning: bool = Field(True, description="Whether to learn from feedback")
    store_history: bool = Field(
        True, description="Whether to store recommendation history",
    )

    class Config:
        """Configuration for the model."""

        json_schema_extra = {
            "example": {
                "enabled": True,
                "max_suggestions": 5,
                "min_confidence": 0.5,
                "refresh_interval": 60,
                "source_weights": {
                    "query_history": 1.0,
                    "activity_context": 1.0,
                    "entity_relationship": 0.8,
                    "temporal_pattern": 0.7,
                    "manual": 1.0,
                    "system": 0.9,
                },
                "enable_learning": True,
                "store_history": True,
            },
        }
