"""
This module defines data models for relationship-based queries in Indaleko.

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
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Union, Any

from pydantic import BaseModel, Field

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from data_models.base import IndalekoBaseModel
from data_models.named_entity import IndalekoNamedEntityDataModel
from query.query_processing.data_models.query_language_enhancer import EntityResolution


class RelationshipType(str, Enum):
    """Types of relationships that can exist between entities in Indaleko."""
    
    # User-File relationships
    CREATED = "created"               # User created a file
    MODIFIED = "modified"             # User modified a file
    VIEWED = "viewed"                 # User viewed a file
    OWNS = "owns"                     # User owns a file
    
    # File-File relationships
    DERIVED_FROM = "derived_from"     # File was derived from another file
    CONTAINS = "contains"             # File contains another file (e.g., archive)
    CONTAINED_BY = "contained_by"     # File is contained by another file
    RELATED_TO = "related_to"         # Files are semantically related
    SAME_FOLDER = "same_folder"       # Files are in the same folder
    VERSION_OF = "version_of"         # File is a version of another file
    
    # User-User relationships
    SHARED_WITH = "shared_with"       # User shared with another user
    COLLABORATED_WITH = "collaborated_with"  # Users collaborated on files
    RECOMMENDED_TO = "recommended_to"  # User recommended to another user
    
    # Other
    UNKNOWN = "unknown"               # Unknown relationship type


class RelationshipDirection(str, Enum):
    """Direction of a relationship between entities."""
    
    OUTBOUND = "outbound"     # From source to target (e.g., User created File)
    INBOUND = "inbound"       # From target to source (e.g., File created by User)
    ANY = "any"               # Direction doesn't matter


class EntityType(str, Enum):
    """Types of entities that can participate in relationships."""
    
    USER = "user"             # User entity
    FILE = "file"             # File entity
    FOLDER = "folder"         # Folder entity
    ACTIVITY = "activity"     # Activity entity
    SERVICE = "service"       # Service entity
    LOCATION = "location"     # Location entity
    TIME = "time"             # Time entity
    DEVICE = "device"         # Device entity
    APPLICATION = "application"  # Application entity
    UNKNOWN = "unknown"       # Unknown entity type


class RelationshipEntity(BaseModel):
    """Entity participating in a relationship."""
    
    entity_type: EntityType = Field(..., description="Type of entity")
    identifier: Optional[str] = Field(None, description="Identifier for the entity")
    resolution: Optional[EntityResolution] = Field(None, description="Resolution information for the entity")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Additional attributes for the entity")
    
    class Config:
        json_schema_extra = {
            "example": {
                "entity_type": "user",
                "identifier": "alice@example.com",
                "resolution": {
                    "original_text": "Alice",
                    "normalized_value": "alice@example.com",
                    "entity_type": "user",
                    "confidence": 0.95
                },
                "attributes": {
                    "display_name": "Alice Smith",
                    "user_id": "12345"
                }
            }
        }


class RelationshipQuery(IndalekoBaseModel):
    """Model for a relationship-based query."""
    
    relationship_type: RelationshipType = Field(..., description="Type of relationship being queried")
    direction: RelationshipDirection = Field(default=RelationshipDirection.ANY, description="Direction of relationship")
    source_entity: RelationshipEntity = Field(..., description="Source entity in the relationship")
    target_entity: Optional[RelationshipEntity] = Field(None, description="Target entity in the relationship")
    
    time_constraint: Optional[Dict[str, Any]] = Field(None, description="Time constraints on the relationship")
    additional_filters: Dict[str, Any] = Field(default_factory=dict, description="Additional filters for the query")
    
    max_depth: int = Field(default=1, description="Maximum depth for traversing relationships")
    limit: Optional[int] = Field(None, description="Maximum number of results to return")
    
    natural_language_query: Optional[str] = Field(None, description="Original natural language query")
    confidence: float = Field(default=1.0, description="Confidence in the relationship query interpretation")
    
    class Config:
        json_schema_extra = {
            "example": {
                "relationship_type": "shared_with",
                "direction": "outbound",
                "source_entity": {
                    "entity_type": "user",
                    "identifier": "current_user",
                    "attributes": {"is_self": True}
                },
                "target_entity": {
                    "entity_type": "user",
                    "identifier": "bob@example.com",
                    "resolution": {
                        "original_text": "Bob",
                        "normalized_value": "bob@example.com",
                        "entity_type": "user",
                        "confidence": 0.9
                    }
                },
                "time_constraint": {
                    "start_time": "2023-01-01T00:00:00Z",
                    "end_time": "2023-01-31T23:59:59Z"
                },
                "additional_filters": {
                    "file_type": "document"
                },
                "max_depth": 1,
                "limit": 10,
                "natural_language_query": "Show me documents I shared with Bob in January",
                "confidence": 0.85
            }
        }


class RelationshipQueryResult(IndalekoBaseModel):
    """Result of a relationship query execution."""
    
    query: RelationshipQuery = Field(..., description="The original relationship query")
    result_count: int = Field(..., description="Number of results found")
    results: List[Dict[str, Any]] = Field(..., description="Results of the query")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Time the query was executed")
    path_visualizations: Optional[Dict[str, Any]] = Field(None, description="Visualizations of relationship paths")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": {
                    "relationship_type": "shared_with",
                    "direction": "outbound",
                    "source_entity": {
                        "entity_type": "user",
                        "identifier": "current_user"
                    },
                    "target_entity": {
                        "entity_type": "user",
                        "identifier": "bob@example.com"
                    },
                    "natural_language_query": "Show me documents I shared with Bob in January"
                },
                "result_count": 3,
                "results": [
                    {
                        "file_name": "Proposal.docx",
                        "shared_on": "2023-01-15T14:30:00Z",
                        "path": "/Documents/Work/Proposal.docx"
                    },
                    {
                        "file_name": "Budget.xlsx",
                        "shared_on": "2023-01-20T09:15:00Z",
                        "path": "/Documents/Finance/Budget.xlsx"
                    },
                    {
                        "file_name": "Meeting_Notes.pdf",
                        "shared_on": "2023-01-25T16:45:00Z",
                        "path": "/Documents/Meetings/Meeting_Notes.pdf"
                    }
                ],
                "execution_time_ms": 237.5,
                "timestamp": "2023-02-10T15:30:00Z"
            }
        }