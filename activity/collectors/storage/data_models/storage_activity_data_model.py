"""
Storage activity data models for Indaleko.

This module provides standardized data models for capturing storage activity
across different storage providers (local NTFS, cloud services, etc.).

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

from pydantic import AwareDatetime, Field, model_validator


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from data_models.provenance_data import BaseProvenanceDataModel
from data_models.timestamp import IndalekoTimestampDataModel


# pylint: enable=wrong-import-position


class StorageActivityType(str, Enum):
    """Types of storage activities that are tracked across providers."""

    CREATE = "create"  # File or folder creation
    MODIFY = "modify"  # Content modification
    DELETE = "delete"  # File or folder deletion
    RENAME = "rename"  # Rename operation
    MOVE = "move"  # Move from one location to another
    COPY = "copy"  # Copy operation
    SECURITY_CHANGE = "security"  # Security/permission changes
    ATTRIBUTE_CHANGE = "attribute"  # Changes to file attributes
    SHARE = "share"  # File sharing operation
    UNSHARE = "unshare"  # Removing sharing permissions
    READ = "read"  # File read operation
    CLOSE = "close"  # File close operation
    DOWNLOAD = "download"  # File download (primarily cloud)
    UPLOAD = "upload"  # File upload (primarily cloud)
    SYNC = "sync"  # Synchronization operation
    VERSION = "version"  # New version created
    RESTORE = "restore"  # Restore from previous version/trash
    TRASH = "trash"  # Moved to trash/recycle bin
    OTHER = "other"  # Other storage activity


class StorageProviderType(str, Enum):
    """Types of storage providers."""

    LOCAL_NTFS = "ntfs"  # Local NTFS filesystem
    DROPBOX = "dropbox"  # Dropbox cloud storage
    ONEDRIVE = "onedrive"  # Microsoft OneDrive
    GOOGLE_DRIVE = "gdrive"  # Google Drive
    ICLOUD = "icloud"  # Apple iCloud
    NETWORK_SHARE = "network"  # Network file share
    AWS_S3 = "s3"  # Amazon S3
    AZURE_BLOB = "azure_blob"  # Azure Blob Storage
    OTHER = "other"  # Other storage provider


class StorageItemType(str, Enum):
    """Types of storage items."""

    FILE = "file"  # Regular file
    DIRECTORY = "directory"  # Directory/folder
    SYMLINK = "symlink"  # Symbolic link
    SHORTCUT = "shortcut"  # Windows shortcut or similar
    VIRTUAL = "virtual"  # Virtual file (doesn't exist physically)
    OTHER = "other"  # Other storage item type


class BaseStorageActivityData(IndalekoBaseModel):
    """
    Base data model for all storage activity records.

    This model captures the common attributes across all storage providers
    and serves as the foundation for provider-specific models.
    """

    activity_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    timestamp: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))
    activity_type: StorageActivityType = Field(
        ...,
        description="Type of storage activity",
    )

    @model_validator(mode="after")
    def ensure_timezone(self) -> "BaseStorageActivityData":
        """Ensure that timestamp has a timezone."""
        if not hasattr(self, "timestamp"):
            self.timestamp = datetime.now(UTC)
        elif self.timestamp:
            # First check if it's a string (which can happen during deserialization)
            if isinstance(self.timestamp, str):
                try:
                    # Try to parse as ISO format with timezone
                    self.timestamp = datetime.fromisoformat(self.timestamp)
                    # If no timezone info, add UTC
                    if not self.timestamp.tzinfo:
                        self.timestamp = self.timestamp.replace(tzinfo=UTC)
                except ValueError:
                    # If parsing fails, use current time
                    self.timestamp = datetime.now(UTC)
            # Then check if it's a datetime without timezone
            elif isinstance(self.timestamp, datetime) and not self.timestamp.tzinfo:
                self.timestamp = self.timestamp.replace(tzinfo=UTC)
        return self

    # Item information
    item_type: StorageItemType = Field(
        ...,
        description="Type of storage item (file, directory, etc.)",
    )
    file_name: str = Field(..., description="Name of the file or directory")
    file_path: str | None = Field(
        None,
        description="Full path to the file if available",
    )
    file_id: str | None = Field(
        None,
        description="Provider-specific ID for the file",
    )

    # Provider information
    provider_type: StorageProviderType = Field(
        ...,
        description="Type of storage provider",
    )
    provider_id: uuid.UUID = Field(..., description="UUID of the activity provider")

    # User and process information
    user_id: str | None = Field(
        None,
        description="User ID associated with the activity",
    )
    user_name: str | None = Field(
        None,
        description="User name associated with the activity",
    )
    process_id: int | None = Field(
        None,
        description="Process ID that performed the activity",
    )
    process_name: str | None = Field(
        None,
        description="Name of the process that performed the activity",
    )

    # Additional data
    attributes: dict[str, Any] | None = Field(
        None,
        description="Additional storage-specific attributes",
    )

    # For operations with source and target (move, rename, etc.)
    previous_file_name: str | None = Field(
        None,
        description="Previous file name for rename/move operations",
    )
    previous_file_path: str | None = Field(
        None,
        description="Previous file path for move operations",
    )

    # Provenance
    provenance: BaseProvenanceDataModel | None = Field(
        None,
        description="Provenance information",
    )


class NtfsStorageActivityData(BaseStorageActivityData):
    """NTFS-specific storage activity data model."""

    file_reference_number: str = Field(
        ...,
        description="NTFS file reference number (file ID)",
    )
    parent_file_reference_number: str | None = Field(
        None,
        description="Parent directory file reference number",
    )
    reason_flags: int | None = Field(None, description="USN Journal reason flags")
    volume_name: str = Field(..., description="Volume name (e.g., C:)")
    is_directory: bool = Field(
        default=False,
        description="Whether the item is a directory",
    )
    security_id: int | None = Field(None, description="Security ID for the file")
    usn: int | None = Field(None, description="USN Journal sequence number")

    @model_validator(mode="after")
    def set_item_type(self) -> "NtfsStorageActivityData":
        """Set item_type based on is_directory."""
        if not hasattr(self, "item_type") or self.item_type is None:
            self.item_type = StorageItemType.DIRECTORY if self.is_directory else StorageItemType.FILE
        return self

    @model_validator(mode="after")
    def validate_rename_fields(self) -> "NtfsStorageActivityData":
        """Ensure that rename operations have previous file name."""
        if self.activity_type == StorageActivityType.RENAME and not self.previous_file_name:
            raise ValueError("Rename operations must include previous_file_name")
        return self


class CloudStorageActivityData(BaseStorageActivityData):
    """Base model for cloud storage activity data."""

    cloud_item_id: str = Field(..., description="Cloud-specific item ID")
    cloud_parent_id: str | None = Field(
        None,
        description="Parent directory/folder ID",
    )
    shared: bool | None = Field(None, description="Whether the item is shared")
    web_url: str | None = Field(
        None,
        description="URL to access the item in web browser",
    )
    mime_type: str | None = Field(None, description="MIME type of the file")
    size: int | None = Field(None, description="Size of the file in bytes")
    is_directory: bool = Field(
        default=False,
        description="Whether the item is a directory/folder",
    )
    created_time: AwareDatetime | None = Field(
        None,
        description="Time when the item was created",
    )
    modified_time: AwareDatetime | None = Field(
        None,
        description="Time when the item was last modified",
    )

    @model_validator(mode="after")
    def set_item_type(self) -> "CloudStorageActivityData":
        """Set item_type based on is_directory."""
        if not hasattr(self, "item_type") or self.item_type is None:
            self.item_type = StorageItemType.DIRECTORY if self.is_directory else StorageItemType.FILE
        return self

    @model_validator(mode="after")
    def ensure_cloud_datetimes_have_timezone(self) -> "CloudStorageActivityData":
        """Ensure that created_time and modified_time have timezones."""
        # Handle created_time
        if hasattr(self, "created_time") and self.created_time:
            if isinstance(self.created_time, str):
                try:
                    self.created_time = datetime.fromisoformat(self.created_time)
                    if not self.created_time.tzinfo:
                        self.created_time = self.created_time.replace(
                            tzinfo=UTC,
                        )
                except ValueError:
                    self.created_time = datetime.now(UTC)
            elif isinstance(self.created_time, datetime) and not self.created_time.tzinfo:
                self.created_time = self.created_time.replace(tzinfo=UTC)

        # Handle modified_time
        if hasattr(self, "modified_time") and self.modified_time:
            if isinstance(self.modified_time, str):
                try:
                    self.modified_time = datetime.fromisoformat(self.modified_time)
                    if not self.modified_time.tzinfo:
                        self.modified_time = self.modified_time.replace(
                            tzinfo=UTC,
                        )
                except ValueError:
                    self.modified_time = datetime.now(UTC)
            elif isinstance(self.modified_time, datetime) and not self.modified_time.tzinfo:
                self.modified_time = self.modified_time.replace(tzinfo=UTC)

        return self


class DropboxStorageActivityData(CloudStorageActivityData):
    """Dropbox-specific storage activity data."""

    dropbox_file_id: str = Field(..., description="Dropbox file ID")
    revision: str | None = Field(None, description="Dropbox file revision ID")
    shared_folder_id: str | None = Field(
        None,
        description="ID of the shared folder if applicable",
    )


class OneDriveStorageActivityData(CloudStorageActivityData):
    """OneDrive-specific storage activity data."""

    drive_id: str = Field(..., description="OneDrive drive ID")
    item_id: str = Field(..., description="OneDrive item ID")
    c_tag: str | None = Field(None, description="Change tag for detecting changes")
    e_tag: str | None = Field(None, description="ETag for the item")


class GoogleDriveStorageActivityData(CloudStorageActivityData):
    """Google Drive-specific storage activity data."""

    file_id: str = Field(..., description="Google Drive file ID")
    drive_id: str | None = Field(
        None,
        description="Google Drive ID if not the default",
    )
    parents: list[str] | None = Field(None, description="IDs of parent folders")
    spaces: list[str] | None = Field(
        None,
        description="Spaces containing the file (drive, photos, etc.)",
    )
    version: str | None = Field(None, description="Version number of the file")


class StorageActivityMetadata(IndalekoBaseModel):
    """Metadata for storage activity collection."""

    collection_start_time: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )
    provider_type: StorageProviderType = Field(
        ...,
        description="Type of storage provider",
    )
    provider_name: str = Field(..., description="Name of the activity provider")
    source_machine: str | None = Field(
        None,
        description="Source machine name if applicable",
    )
    activity_count: int = Field(default=0, description="Number of activities collected")
    storage_location: str | None = Field(
        None,
        description="Storage location (volume, URL, etc.)",
    )
    provenance: Any | None = Field(
        None,
        description="Provenance information (optional)",
    )

    @model_validator(mode="after")
    def ensure_timezone(self) -> "StorageActivityMetadata":
        """Ensure that collection_start_time has a timezone."""
        if not hasattr(self, "collection_start_time"):
            self.collection_start_time = datetime.now(UTC)
        elif self.collection_start_time:
            # First check if it's a string (which can happen during deserialization)
            if isinstance(self.collection_start_time, str):
                try:
                    # Try to parse as ISO format with timezone
                    self.collection_start_time = datetime.fromisoformat(
                        self.collection_start_time,
                    )
                    # If no timezone info, add UTC
                    if not self.collection_start_time.tzinfo:
                        self.collection_start_time = self.collection_start_time.replace(
                            tzinfo=UTC,
                        )
                except ValueError:
                    # If parsing fails, use current time
                    self.collection_start_time = datetime.now(UTC)
            # Then check if it's a datetime without timezone
            elif isinstance(self.collection_start_time, datetime) and not self.collection_start_time.tzinfo:
                self.collection_start_time = self.collection_start_time.replace(
                    tzinfo=UTC,
                )
        return self


class StorageActivityData(IndalekoBaseModel):
    """Container for a collection of storage activities."""

    activity_data_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    metadata: StorageActivityMetadata
    activities: list[BaseStorageActivityData] = Field(default_factory=list)
    Timestamp: IndalekoTimestampDataModel = Field(
        default_factory=IndalekoTimestampDataModel,
    )
