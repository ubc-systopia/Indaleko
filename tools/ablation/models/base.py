"""
Base models for the ablation study framework.

This module provides the base Pydantic models used for data validation
and serialization throughout the ablation framework.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator

# Import Indaleko base model if available
try:
    from data_models.base import IndalekoBaseModel as BaseIndalekoModel
except ImportError:
    # If not available, create a compatible model
    class BaseIndalekoModel(BaseModel):
        """Base model compatible with Indaleko data models."""

        class Config:
            """Pydantic config for the base model."""

            arbitrary_types_allowed = True
            json_encoders = {
                UUID: lambda v: str(v)
            }


class AblationBaseModel(BaseIndalekoModel):
    """Base model for all ablation models.

    This model serves as the foundation for all data models in the ablation
    framework, ensuring consistency with the Indaleko architecture.
    """

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    @validator('created_at', 'updated_at')
    def ensure_timezone(cls, v):
        """Ensure datetimes are timezone-aware."""
        if v is not None and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    class Config:
        """Pydantic config for the ablation base model."""

        arbitrary_types_allowed = True
        json_encoders = {
            UUID: lambda v: str(v),
            datetime: lambda v: v.isoformat()
        }


class SemanticAttribute(BaseIndalekoModel):
    """Model for semantic attributes.

    Semantic attributes are standardized metadata fields used across
    the Indaleko ecosystem. They consist of an identifier and a value.
    """

    Identifier: Dict[str, Any]
    Value: Any

    class Config:
        """Pydantic config for the semantic attribute model."""

        arbitrary_types_allowed = True
        json_encoders = {
            UUID: lambda v: str(v)
        }


class ActivityBaseModel(AblationBaseModel):
    """Base model for all activity data.

    This model serves as the foundation for all activity-related data models
    in the ablation framework, providing common fields across activity types.
    """

    user_id: UUID = Field(default_factory=uuid4)
    device_id: UUID = Field(default_factory=uuid4)
    session_id: UUID = Field(default_factory=uuid4)
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    semantic_attributes: List[SemanticAttribute] = Field(default_factory=list)
    source: str = "ablation_synthetic"

    @validator('start_time', 'end_time')
    def ensure_timezone(cls, v):
        """Ensure datetimes are timezone-aware."""
        if v is not None and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class NamedEntity(AblationBaseModel):
    """Model for named entities.

    Named entities represent real-world objects or concepts with consistent
    identities, such as locations, people, or organizations.
    """

    name: str
    entity_type: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
    references: List[UUID] = Field(default_factory=list)


class QueryTruth(AblationBaseModel):
    """Model for query truth data.

    Query truth data records which records should match a given query,
    enabling precise calculation of precision and recall metrics.
    """

    query_id: UUID
    query_text: str
    activity_type: str
    matching_ids: List[UUID] = Field(default_factory=list)
    components: Dict[str, Any] = Field(default_factory=dict)


class MetricsResult(BaseIndalekoModel):
    """Model for ablation test metrics.

    This model represents the metrics calculated for a query with and without
    ablation, including precision, recall, and F1 score.
    """

    query_id: UUID
    query_text: str
    baseline_precision: float
    baseline_recall: float
    baseline_f1: float
    ablated_precision: float
    ablated_recall: float
    ablated_f1: float
    ablated_collection: str
    impact_score: float  # Percentage decrease in F1 score
