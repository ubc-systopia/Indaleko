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
from datetime import UTC, datetime
from enum import Enum
from typing import Any

# Import path setup
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from pydantic import Field, field_validator

from activity.collectors.storage.data_models.storage_activity_data_model import (
    GoogleDriveStorageActivityData,
    StorageActivityType,
    StorageItemType,
    StorageProviderType,
)
from activity.data_model.activity_classification import IndalekoActivityClassification
from data_models.base import IndalekoBaseModel

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
    email: str | None = Field(None, description="User email address")
    display_name: str | None = Field(None, description="User display name")
    photo_url: str | None = Field(None, description="User profile photo URL")

    class Config:
        """Sample configuration for the data model."""

        json_schema_extra = {
            "example": {
                "user_id": "12345678901234567890",
                "email": "user@example.com",
                "display_name": "Example User",
                "photo_url": "https://lh3.googleusercontent.com/a/example",
            },
        }


class GDriveFileInfo(IndalekoBaseModel):
    """Information about a Google Drive file."""

    file_id: str = Field(..., description="Google Drive file ID")
    name: str = Field(..., description="File name")
    mime_type: str = Field(..., description="File MIME type")
    file_type: GDriveFileType = Field(..., description="File type category")
    description: str | None = Field(None, description="File description")
    size: int | None = Field(None, description="File size in bytes")
    md5_checksum: str | None = Field(
        None,
        description="MD5 checksum of file content",
    )
    version: str | None = Field(None, description="File version")
    starred: bool | None = Field(None, description="Whether the file is starred")
    trashed: bool | None = Field(None, description="Whether the file is trashed")
    created_time: datetime | None = Field(None, description="File creation time")
    modified_time: datetime | None = Field(
        None,
        description="File last modification time",
    )
    viewed_time: datetime | None = Field(None, description="File last viewed time")
    shared: bool | None = Field(None, description="Whether the file is shared")
    web_view_link: str | None = Field(
        None,
        description="Link to view the file in browser",
    )
    parent_folder_id: str | None = Field(None, description="ID of parent folder")
    parent_folder_name: str | None = Field(None, description="Name of parent folder")

    @field_validator("created_time", "modified_time", "viewed_time", mode="before")
    @classmethod
    def ensure_timezone(cls, v):
        """Ensure that datetime values have timezone information."""
        if v is None:
            return v
        if isinstance(v, str):
            try:
                # Try to parse ISO format string
                v = datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                try:
                    # Try RFC 3339 format
                    v = datetime.strptime(v, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                        tzinfo=UTC,
                    )
                except ValueError:
                    # Return original value if parsing fails
                    return v

        # Ensure datetime has timezone
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=UTC)
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
                "parent_folder_name": "Projects",
            },
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
    destination_folder_id: str | None = Field(
        None,
        description="For move/copy: destination folder ID",
    )
    destination_folder_name: str | None = Field(
        None,
        description="For move/copy: destination folder name",
    )
    previous_file_name: str | None = Field(
        None,
        description="For rename: previous file name",
    )
    comment_id: str | None = Field(None, description="For comment: comment ID")
    comment_content: str | None = Field(
        None,
        description="For comment: comment content",
    )
    shared_with: list[GDriveUserInfo] | None = Field(
        None,
        description="For share: users the file was shared with",
    )
    permission_changes: dict[str, str] | None = Field(
        None,
        description="For share: permission changes",
    )

    # Original API response for reference
    raw_data: dict[str, Any] | None = Field(
        None,
        description="Original API response",
    )

    # Classification for activity context system
    activity_classification: IndalekoActivityClassification | None = Field(
        None,
        description="Multi-dimensional classification of this activity",
    )

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_timezone(cls, v):
        """Ensure that datetime values have timezone information."""
        if isinstance(v, str):
            try:
                # Try to parse ISO format string
                v = datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                try:
                    # Try RFC 3339 format
                    v = datetime.strptime(v, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                        tzinfo=UTC,
                    )
                except ValueError:
                    # Return original value if parsing fails
                    return v

        # Ensure datetime has timezone
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v

    def to_storage_activity(self) -> GoogleDriveStorageActivityData:
        """Convert to a standardized Google Drive storage activity."""
        # Map activity type
        storage_activity_type = StorageActivityType.OTHER
        if self.activity_type == GDriveActivityType.CREATE:
            storage_activity_type = StorageActivityType.CREATE
        elif self.activity_type == GDriveActivityType.EDIT:
            storage_activity_type = StorageActivityType.MODIFY
        elif self.activity_type == GDriveActivityType.DELETE:
            storage_activity_type = StorageActivityType.DELETE
        elif self.activity_type == GDriveActivityType.MOVE:
            storage_activity_type = StorageActivityType.MOVE
        elif self.activity_type == GDriveActivityType.RENAME:
            storage_activity_type = StorageActivityType.RENAME
        elif self.activity_type == GDriveActivityType.SHARE:
            storage_activity_type = StorageActivityType.SHARE
        elif self.activity_type == GDriveActivityType.DOWNLOAD:
            storage_activity_type = StorageActivityType.DOWNLOAD
        elif self.activity_type == GDriveActivityType.VIEW:
            storage_activity_type = StorageActivityType.READ
        elif self.activity_type == GDriveActivityType.TRASH:
            storage_activity_type = StorageActivityType.TRASH
        elif self.activity_type == GDriveActivityType.RESTORE:
            storage_activity_type = StorageActivityType.RESTORE
        elif self.activity_type == GDriveActivityType.COPY:
            storage_activity_type = StorageActivityType.COPY

        # Map item type
        item_type = StorageItemType.FILE
        if self.file.file_type == GDriveFileType.FOLDER:
            item_type = StorageItemType.DIRECTORY

        # Create storage activity
        return GoogleDriveStorageActivityData(
            # Core fields from BaseStorageActivityData
            activity_id=uuid.uuid4(),
            timestamp=self.timestamp,
            activity_type=storage_activity_type,
            item_type=item_type,
            file_name=self.file.name,
            file_path=f"gdrive://{self.file.file_id}",
            file_id=self.file.file_id,
            provider_type=StorageProviderType.GOOGLE_DRIVE,
            provider_id=uuid.UUID(
                "3e7d8f29-7c73-41c5-b3d4-1a9b42567890",
            ),  # Google Drive Collector UUID
            user_id=self.user.user_id,
            user_name=self.user.display_name or self.user.email,
            previous_file_name=self.previous_file_name,
            # Additional attributes
            attributes={
                "gdrive_activity_id": self.activity_id,
                "gdrive_activity_type": self.activity_type,
                "gdrive_file_type": self.file.file_type,
                "gdrive_mime_type": self.file.mime_type,
                "gdrive_user_email": self.user.email,
                "gdrive_parent_folder_id": self.file.parent_folder_id,
                "gdrive_parent_folder_name": self.file.parent_folder_name,
            },
            # CloudStorageActivityData fields
            cloud_item_id=self.file.file_id,
            cloud_parent_id=self.file.parent_folder_id,
            shared=self.file.shared,
            web_url=self.file.web_view_link,
            mime_type=self.file.mime_type,
            size=self.file.size,
            is_directory=self.file.file_type == GDriveFileType.FOLDER,
            created_time=self.file.created_time,
            modified_time=self.file.modified_time,
            # GoogleDriveStorageActivityData fields
            parents=([self.file.parent_folder_id] if self.file.parent_folder_id else None),
            version=self.file.version,
        )

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
                    "photo_url": "https://lh3.googleusercontent.com/a/example",
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
                    "parent_folder_name": "Projects",
                },
            },
        }
