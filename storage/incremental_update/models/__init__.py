"""
Data models for the incremental update service.

This package contains the data models used by the incremental update
service for entity resolution.
"""

from storage.incremental_update.models.resolution_request import (
    EntityInfo,
    EntityType,
    ResolutionRequest,
    ResolutionStatus,
)

__all__ = ["EntityInfo", "EntityType", "ResolutionRequest", "ResolutionStatus"]
