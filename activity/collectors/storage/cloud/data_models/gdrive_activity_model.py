"""
Google Drive Activity Data Model for Indaleko.

This module defines the data model for Google Drive activity data collection,
maintaining a standardized representation of file activities that can be stored
in the Indaleko database.

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
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Union, Any

# Import path setup
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.data_model.activity_classification import IndalekoActivityClassification
from activity.data_model.activity import IndalekoStorageActivityData
from data_models.base import IndalekoBaseModel
from pydantic import Field, field_validator

# pylint: enable=wrong-import-position


class GDriveActivityType(str, Enum):
    """Type of Google Drive activity."""
    CREATE = "create"
    EDIT = "edit"
    DELETE = "delete"
    MOVE = "move"
    RENAME = "rename"
    COMMENT = "comment"
    SHARE = "share"
    DOWNLOAD = "download"
    VIEW = "view"
    TRASH = "trash"
    RESTORE = "restore"
    COPY = "copy"
    UNKNOWN = "unknown"


class GDriveFileType(str, Enum):
    """Type of Google Drive file."""
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    FORM = "form"
    DRAWING = "drawing"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    PDF = "pdf"
    FOLDER = "folder"
    SHORTCUT = "shortcut"
    SHARED_DRIVE = "shared_drive"
    OTHER = "other"
    UNKNOWN = "unknown"


class GDriveUserInfo(IndalekoBaseModel):
    """Information about a Google Drive user."""
    user_id: str = Field(..., description="Google Drive user ID")
    email: Optional[str] = Field(None, description="User email address")
    display_name: Optional[str] = Field(None, description="User display name")
    photo_url: Optional[str] = Field(None, description="User profile photo URL")
    
    class Config:
        """Sample configuration for the data model."""
        json_schema_extra = {
            "example": {
                "user_id": "12345678901234567890",
                "email": "user@example.com",
                "display_name": "Example User",
                "photo_url": "https://lh3.googleusercontent.com/a/example"
            }
        }


class GDriveFileInfo(IndalekoBaseModel):
    """Information about a Google Drive file."""
    file_id: str = Field(..., description="Google Drive file ID")
    name: str = Field(..., description="File name")
    mime_type: str = Field(..., description="File MIME type")
    file_type: GDriveFileType = Field(..., description="File type category")
    description: Optional[str] = Field(None, description="File description")
    size: Optional[int] = Field(None, description="File size in bytes")
    md5_checksum: Optional[str] = Field(None, description="MD5 checksum of file content")
    version: Optional[str] = Field(None, description="File version")
    starred: Optional[bool] = Field(None, description="Whether the file is starred")
    trashed: Optional[bool] = Field(None, description="Whether the file is trashed")
    created_time: Optional[datetime] = Field(None, description="File creation time")
    modified_time: Optional[datetime] = Field(None, description="File last modification time")
    viewed_time: Optional[datetime] = Field(None, description="File last viewed time")
    shared: Optional[bool] = Field(None, description="Whether the file is shared")
    web_view_link: Optional[str] = Field(None, description="Link to view the file in browser")
    parent_folder_id: Optional[str] = Field(None, description="ID of parent folder")
    parent_folder_name: Optional[str] = Field(None, description="Name of parent folder")
    
    @field_validator('created_time', 'modified_time', 'viewed_time', mode='before')
    @classmethod
    def ensure_timezone(cls, v):
        """Ensure that datetime values have timezone information."""
        if v is None:
            return v
        if isinstance(v, str):
            try:
                # Try to parse ISO format string
                v = datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                try:
                    # Try RFC 3339 format
                    v = datetime.strptime(v, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
                except ValueError:
                    # Return original value if parsing fails
                    return v
        
        # Ensure datetime has timezone
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
    
    class Config:
        """Sample configuration for the data model."""
        json_schema_extra = {
            "example": {
                "file_id": "1ABCdefGHIjklMNOpqrsTUVwxyz12345",
                "name": "Project Proposal.docx",
                "mime_type": "application/vnd.google-apps.document",
                "file_type": "document",
                "description": "Proposal for new project",
                "size": 12345,
                "md5_checksum": "1a2b3c4d5e6f7g8h9i0j",
                "version": "15",
                "starred": False,
                "trashed": False,
                "created_time": "2023-04-01T14:30:00.000Z",
                "modified_time": "2023-04-15T09:45:00.000Z",
                "viewed_time": "2023-04-20T16:20:00.000Z",
                "shared": True,
                "web_view_link": "https://docs.google.com/document/d/1abc...",
                "parent_folder_id": "0ABCdefGHIjklMNOpqrsTUVwxyz12345",
                "parent_folder_name": "Projects"
            }
        }


class GDriveActivityData(IndalekoBaseModel):
    """Google Drive activity data model."""
    # Core activity fields
    activity_id: str = Field(..., description="Unique identifier for this activity")
    activity_type: GDriveActivityType = Field(..., description="Type of activity")
    timestamp: datetime = Field(..., description="When the activity occurred")
    
    # User information
    user: GDriveUserInfo = Field(..., description="User who performed the activity")
    
    # File information
    file: GDriveFileInfo = Field(..., description="File involved in the activity")
    
    # Additional metadata
    destination_folder_id: Optional[str] = Field(None, description="For move/copy: destination folder ID")
    destination_folder_name: Optional[str] = Field(None, description="For move/copy: destination folder name")
    previous_file_name: Optional[str] = Field(None, description="For rename: previous file name")
    comment_id: Optional[str] = Field(None, description="For comment: comment ID")
    comment_content: Optional[str] = Field(None, description="For comment: comment content")
    shared_with: Optional[List[GDriveUserInfo]] = Field(None, description="For share: users the file was shared with")
    permission_changes: Optional[Dict[str, str]] = Field(None, description="For share: permission changes")
    
    # Original API response for reference
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Original API response")
    
    # Classification for activity context system
    activity_classification: Optional[IndalekoActivityClassification] = Field(
        None, description="Multi-dimensional classification of this activity"
    )
    
    @field_validator('timestamp', mode='before')
    @classmethod
    def ensure_timezone(cls, v):
        """Ensure that datetime values have timezone information."""
        if isinstance(v, str):
            try:
                # Try to parse ISO format string
                v = datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                try:
                    # Try RFC 3339 format
                    v = datetime.strptime(v, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
                except ValueError:
                    # Return original value if parsing fails
                    return v
        
        # Ensure datetime has timezone
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
    
    def to_storage_activity(self) -> IndalekoStorageActivityData:
        """Convert to a standardized Indaleko storage activity."""
        activity_data = IndalekoStorageActivityData(
            # Core fields
            ObjectIdentifier=uuid.uuid4(),
            Origin=str(uuid.UUID("3e7d8f29-7c73-41c5-b3d4-1a9b42567890")),  # Google Drive Collector UUID
            Timestamp=self.timestamp,
            
            # Activity type mapping
            Access={
                GDriveActivityType.VIEW: True,
                GDriveActivityType.DOWNLOAD: True,
            }.get(self.activity_type, False),
            
            Create={
                GDriveActivityType.CREATE: True,
                GDriveActivityType.COPY: True,
            }.get(self.activity_type, False),
            
            Delete={
                GDriveActivityType.DELETE: True,
                GDriveActivityType.TRASH: True,
            }.get(self.activity_type, False),
            
            Modify={
                GDriveActivityType.EDIT: True,
                GDriveActivityType.RENAME: True,
                GDriveActivityType.COMMENT: True,
            }.get(self.activity_type, False),
            
            Move=self.activity_type == GDriveActivityType.MOVE,
            Restore=self.activity_type == GDriveActivityType.RESTORE,
            
            # File info
            URI=f"gdrive://{self.file.file_id}",
            Name=self.file.name,
            
            # Additional fields mapped to attributes
            Attributes={
                "gdrive_activity_id": self.activity_id,
                "gdrive_activity_type": self.activity_type,
                "gdrive_file_id": self.file.file_id,
                "gdrive_file_type": self.file.file_type,
                "gdrive_mime_type": self.file.mime_type,
                "gdrive_user_id": self.user.user_id,
                "gdrive_user_email": self.user.email,
                "gdrive_web_view_link": self.file.web_view_link,
                "gdrive_parent_folder_id": self.file.parent_folder_id,
                "gdrive_parent_folder_name": self.file.parent_folder_name,
            }
        )
        
        # Add rename info if available
        if self.previous_file_name:
            activity_data.Attributes["previous_name"] = self.previous_file_name
        
        # Add move info if available
        if self.destination_folder_id:
            activity_data.Attributes["destination_folder_id"] = self.destination_folder_id
            if self.destination_folder_name:
                activity_data.Attributes["destination_folder_name"] = self.destination_folder_name
        
        # Add comment info if available
        if self.comment_id:
            activity_data.Attributes["comment_id"] = self.comment_id
            if self.comment_content:
                activity_data.Attributes["comment_content"] = self.comment_content
        
        # Add sharing info if available
        if self.shared_with:
            activity_data.Attributes["shared_with"] = [user.email for user in self.shared_with if user.email]
            
        # Add classification if available
        if self.activity_classification:
            activity_data.Classification = self.activity_classification
        
        return activity_data
    
    class Config:
        """Sample configuration for the data model."""
        json_schema_extra = {
            "example": {
                "activity_id": "1234567890abcdef",
                "activity_type": "edit",
                "timestamp": "2023-04-15T09:45:00.000Z",
                "user": {
                    "user_id": "12345678901234567890",
                    "email": "user@example.com",
                    "display_name": "Example User",
                    "photo_url": "https://lh3.googleusercontent.com/a/example"
                },
                "file": {
                    "file_id": "1ABCdefGHIjklMNOpqrsTUVwxyz12345",
                    "name": "Project Proposal.docx",
                    "mime_type": "application/vnd.google-apps.document",
                    "file_type": "document",
                    "size": 12345,
                    "created_time": "2023-04-01T14:30:00.000Z",
                    "modified_time": "2023-04-15T09:45:00.000Z",
                    "shared": True,
                    "web_view_link": "https://docs.google.com/document/d/1abc...",
                    "parent_folder_id": "0ABCdefGHIjklMNOpqrsTUVwxyz12345",
                    "parent_folder_name": "Projects"
                }
            }
        }