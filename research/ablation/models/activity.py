"""Base activity data models for ablation testing."""

from datetime import datetime, timezone
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ActivityType(Enum):
    """Enumeration of activity types for the ablation framework."""
    
    MUSIC = auto()
    LOCATION = auto()
    TASK = auto()
    COLLABORATION = auto()
    STORAGE = auto()
    MEDIA = auto()


class ActivityData(BaseModel):
    """Base model for all activity data."""
    
    id: UUID = Field(default_factory=uuid4)
    activity_type: ActivityType
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str
    semantic_attributes: Dict[str, Dict] = Field(default_factory=dict)
    
    class Config:
        frozen = False
        arbitrary_types_allowed = True


class TruthData(BaseModel):
    """Model for tracking ground truth data for ablation testing."""
    
    query_id: UUID
    query_text: str
    matching_entities: List[UUID]
    activity_types: List[ActivityType]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        frozen = False
        arbitrary_types_allowed = True
