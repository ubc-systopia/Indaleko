"""
Data model for entity resolution requests.

This module defines the data structure for entity resolution queue entries.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional, Union

from data_models.base import IndalekoBaseModel
from pydantic import Field, validator


class ResolutionStatus(str, Enum):
    """Status of an entity resolution request."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class EntityType(str, Enum):
    """Type of entity being resolved."""
    FILE = "file"
    DIRECTORY = "directory"
    UNKNOWN = "unknown"


class EntityInfo(IndalekoBaseModel):
    """Information about an entity that needs resolution."""
    volume_guid: str = Field(description="Volume identifier (e.g., 'C:')")
    frn: str = Field(description="File Reference Number or equivalent identifier")
    file_path: Optional[str] = Field(
        default=None, 
        description="File path if available"
    )


class ResolutionRequest(IndalekoBaseModel):
    """
    Entity resolution request for the queue.
    
    This model represents a request to resolve an entity that was
    detected in an activity stream but doesn't exist in the database.
    """
    status: ResolutionStatus = Field(
        default=ResolutionStatus.PENDING,
        description="Current status of the resolution request"
    )
    machine_id: str = Field(
        description="Identifier for the machine this entity belongs to"
    )
    entity_info: EntityInfo = Field(
        description="Information about the entity to resolve"
    )
    entity_type: EntityType = Field(
        default=EntityType.UNKNOWN,
        description="Type of entity (file, directory, etc.)"
    )
    path_depth: int = Field(
        default=0,
        description="Depth of the path (for ordering - directories before files)" 
    )
    priority: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Priority (1-5, where 1 is highest)"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this request was created"
    )
    attempts: int = Field(
        default=0,
        description="Number of resolution attempts"
    )
    last_error: Optional[str] = Field(
        default=None, 
        description="Last error message if failed"
    )
    last_attempt_time: Optional[datetime] = Field(
        default=None,
        description="When the last resolution attempt occurred"
    )

    @validator('path_depth', pre=True)
    def calculate_path_depth(cls, v, values):
        """Calculate path depth from file_path if not provided."""
        if v == 0 and 'entity_info' in values:
            entity_info = values['entity_info']
            if hasattr(entity_info, 'file_path') and entity_info.file_path:
                # Count path segments, normalizing for Windows vs Unix
                normalized_path = entity_info.file_path.replace('\\', '/')
                # Remove leading/trailing slashes before counting
                cleaned_path = normalized_path.strip('/')
                if cleaned_path:
                    return len(cleaned_path.split('/'))
        return v

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "status": "pending",
                "machine_id": "windows-laptop-1",
                "entity_info": {
                    "volume_guid": "C:",
                    "frn": "40532396646425331",
                    "file_path": "/Users/documents/file.txt"
                },
                "entity_type": "file",
                "path_depth": 3,
                "priority": 2,
                "timestamp": "2025-04-23T11:07:21Z",
                "attempts": 0,
                "last_error": None,
                "last_attempt_time": None
            }
        }