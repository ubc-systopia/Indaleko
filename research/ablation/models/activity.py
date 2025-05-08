"""Base activity data models for ablation testing."""

from datetime import UTC, datetime
from enum import Enum, auto
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from data_models.base import IndalekoBaseModel


class ActivityType(Enum):
    """Enumeration of activity types for the ablation framework."""

    MUSIC = auto()
    LOCATION = auto()
    TASK = auto()
    COLLABORATION = auto()
    STORAGE = auto()
    MEDIA = auto()


class ActivityData(IndalekoBaseModel):
    """Base model for all activity data."""

    id: UUID = Field(default_factory=uuid4)
    activity_type: ActivityType
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    modified_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str
    semantic_attributes: dict[str, dict] = Field(default_factory=dict)

    class Config:
        frozen = False
        arbitrary_types_allowed = True


class TruthData(BaseModel):
    """Model for tracking ground truth data for ablation testing."""

    query_id: UUID
    query_text: str
    matching_entities: list[UUID]
    activity_types: list[ActivityType]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        frozen = False
        arbitrary_types_allowed = True
