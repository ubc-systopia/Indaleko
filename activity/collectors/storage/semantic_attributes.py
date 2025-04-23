"""
Semantic attributes for storage activities.

This module provides semantic attributes for storage activities that are
collected from various storage providers.

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
from enum import Enum
from typing import Any

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.storage.data_models.storage_activity_data_model import (
    StorageActivityType,
    StorageItemType,
    StorageProviderType,
)
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel

# pylint: enable=wrong-import-position

# Legacy attributes (preserved for backward compatibility)
ADP_MACHINE_IDENTITY = "ff5c27ea-a319-46c9-9d7b-161ff9a0e6ca"
ADP_OBJECT_URI = "f45a6642-e5d0-4de0-9736-c9d2d77e2a12"
ADP_STORAGE_IDENTITY = "df17c079-4d6d-4b9b-ad98-04dd37d05907"


class StorageActivityAttributes(Enum):
    """UUIDs for storage activity semantic attributes."""

    # Common storage activity attributes
    STORAGE_ACTIVITY = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4567")
    FILE_CREATE = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4568")
    FILE_MODIFY = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4569")
    FILE_DELETE = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4570")
    FILE_RENAME = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4571")
    FILE_MOVE = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4572")
    FILE_COPY = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4573")
    FILE_SECURITY_CHANGE = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4574")
    FILE_ATTRIBUTE_CHANGE = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4575")
    FILE_SHARE = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4576")
    FILE_UNSHARE = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4577")
    FILE_READ = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4578")
    FILE_CLOSE = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4579")
    FILE_DOWNLOAD = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4580")
    FILE_UPLOAD = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4581")
    FILE_SYNC = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4582")
    FILE_VERSION = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4583")
    FILE_RESTORE = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4584")
    FILE_TRASH = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4585")

    # Storage provider types
    PROVIDER_LOCAL_NTFS = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4590")
    PROVIDER_DROPBOX = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4591")
    PROVIDER_ONEDRIVE = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4592")
    PROVIDER_GOOGLE_DRIVE = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4593")
    PROVIDER_ICLOUD = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4594")
    PROVIDER_NETWORK_SHARE = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4595")
    PROVIDER_S3 = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4596")
    PROVIDER_AZURE_BLOB = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4597")

    # Storage implementation-specific attributes
    STORAGE_NTFS = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4620")
    STORAGE_DROPBOX = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4621")
    STORAGE_ONEDRIVE = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4622")
    STORAGE_GDRIVE = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4623")
    STORAGE_ICLOUD = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4624")
    STORAGE_SHARED = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4625")

    # Storage item types
    ITEM_FILE = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4600")
    ITEM_DIRECTORY = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4601")
    ITEM_SYMLINK = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4602")
    ITEM_SHORTCUT = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4603")
    ITEM_VIRTUAL = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4604")

    # File metadata attributes
    FILE_NAME = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4610")
    FILE_PATH = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4611")
    FILE_SIZE = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4612")
    FILE_CREATION_TIME = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4613")
    FILE_MODIFICATION_TIME = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4614")
    FILE_ACCESS_TIME = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4615")
    FILE_MIME_TYPE = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4616")
    FILE_EXTENSION = uuid.UUID("f1a0c5d0-8e59-4c00-8c80-f80c1a3b4617")


# Maps storage activity types to semantic attributes
ACTIVITY_TYPE_TO_SEMANTIC_ATTRIBUTE = {
    StorageActivityType.CREATE: StorageActivityAttributes.FILE_CREATE,
    StorageActivityType.MODIFY: StorageActivityAttributes.FILE_MODIFY,
    StorageActivityType.DELETE: StorageActivityAttributes.FILE_DELETE,
    StorageActivityType.RENAME: StorageActivityAttributes.FILE_RENAME,
    StorageActivityType.MOVE: StorageActivityAttributes.FILE_MOVE,
    StorageActivityType.COPY: StorageActivityAttributes.FILE_COPY,
    StorageActivityType.SECURITY_CHANGE: StorageActivityAttributes.FILE_SECURITY_CHANGE,
    StorageActivityType.ATTRIBUTE_CHANGE: StorageActivityAttributes.FILE_ATTRIBUTE_CHANGE,
    StorageActivityType.SHARE: StorageActivityAttributes.FILE_SHARE,
    StorageActivityType.UNSHARE: StorageActivityAttributes.FILE_UNSHARE,
    StorageActivityType.READ: StorageActivityAttributes.FILE_READ,
    StorageActivityType.CLOSE: StorageActivityAttributes.FILE_CLOSE,
    StorageActivityType.DOWNLOAD: StorageActivityAttributes.FILE_DOWNLOAD,
    StorageActivityType.UPLOAD: StorageActivityAttributes.FILE_UPLOAD,
    StorageActivityType.SYNC: StorageActivityAttributes.FILE_SYNC,
    StorageActivityType.VERSION: StorageActivityAttributes.FILE_VERSION,
    StorageActivityType.RESTORE: StorageActivityAttributes.FILE_RESTORE,
    StorageActivityType.TRASH: StorageActivityAttributes.FILE_TRASH,
}

# Maps storage provider types to semantic attributes
PROVIDER_TYPE_TO_SEMANTIC_ATTRIBUTE = {
    StorageProviderType.LOCAL_NTFS: StorageActivityAttributes.PROVIDER_LOCAL_NTFS,
    StorageProviderType.DROPBOX: StorageActivityAttributes.PROVIDER_DROPBOX,
    StorageProviderType.ONEDRIVE: StorageActivityAttributes.PROVIDER_ONEDRIVE,
    StorageProviderType.GOOGLE_DRIVE: StorageActivityAttributes.PROVIDER_GOOGLE_DRIVE,
    StorageProviderType.ICLOUD: StorageActivityAttributes.PROVIDER_ICLOUD,
    StorageProviderType.NETWORK_SHARE: StorageActivityAttributes.PROVIDER_NETWORK_SHARE,
    StorageProviderType.AWS_S3: StorageActivityAttributes.PROVIDER_S3,
    StorageProviderType.AZURE_BLOB: StorageActivityAttributes.PROVIDER_AZURE_BLOB,
}

# Maps storage item types to semantic attributes
ITEM_TYPE_TO_SEMANTIC_ATTRIBUTE = {
    StorageItemType.FILE: StorageActivityAttributes.ITEM_FILE,
    StorageItemType.DIRECTORY: StorageActivityAttributes.ITEM_DIRECTORY,
    StorageItemType.SYMLINK: StorageActivityAttributes.ITEM_SYMLINK,
    StorageItemType.SHORTCUT: StorageActivityAttributes.ITEM_SHORTCUT,
    StorageItemType.VIRTUAL: StorageActivityAttributes.ITEM_VIRTUAL,
}


def get_storage_activity_semantic_attributes() -> (
    list[IndalekoSemanticAttributeDataModel]
):
    """
    Get all defined semantic attributes for storage activities.

    Returns:
        List of semantic attribute data models
    """
    attributes = []
    for attr in StorageActivityAttributes:
        # Convert UUID to string for compatibility with IndalekoSemanticAttributeDataModel
        identifier = uuid_to_str(attr.value)

        attribute = IndalekoSemanticAttributeDataModel(
            Identifier=identifier,
            Label=attr.name,
            Description=f"Storage activity: {attr.name}",
        )
        attributes.append(attribute)
    return attributes


def uuid_to_str(value):
    """
    Convert UUID objects to strings for compatibility with IndalekoSemanticAttributeDataModel.

    Args:
        value: Value to convert if it's a UUID

    Returns:
        String representation of UUID or the original value
    """
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def get_semantic_attributes_for_activity(
    activity_data: dict[str, Any],
) -> list[IndalekoSemanticAttributeDataModel]:
    """
    Get semantic attributes for a storage activity.

    Args:
        activity_data: Dictionary containing activity data

    Returns:
        List of semantic attribute data models
    """
    attributes = []

    # Add common storage activity attribute
    attributes.append(
        IndalekoSemanticAttributeDataModel(
            Identifier=uuid_to_str(StorageActivityAttributes.STORAGE_ACTIVITY.value),
        ),
    )

    # Add activity type attribute
    activity_type = activity_data.get("activity_type")
    if activity_type and activity_type in ACTIVITY_TYPE_TO_SEMANTIC_ATTRIBUTE:
        attributes.append(
            IndalekoSemanticAttributeDataModel(
                Identifier=uuid_to_str(
                    ACTIVITY_TYPE_TO_SEMANTIC_ATTRIBUTE[activity_type].value,
                ),
            ),
        )

    # Add provider type attribute
    provider_type = activity_data.get("provider_type")
    if provider_type and provider_type in PROVIDER_TYPE_TO_SEMANTIC_ATTRIBUTE:
        attributes.append(
            IndalekoSemanticAttributeDataModel(
                Identifier=uuid_to_str(
                    PROVIDER_TYPE_TO_SEMANTIC_ATTRIBUTE[provider_type].value,
                ),
            ),
        )

    # Add item type attribute
    item_type = activity_data.get("item_type")
    if item_type and item_type in ITEM_TYPE_TO_SEMANTIC_ATTRIBUTE:
        attributes.append(
            IndalekoSemanticAttributeDataModel(
                Identifier=uuid_to_str(ITEM_TYPE_TO_SEMANTIC_ATTRIBUTE[item_type].value),
            ),
        )

    # Add file name attribute if present
    if activity_data.get("file_name"):
        attributes.append(
            IndalekoSemanticAttributeDataModel(
                Identifier=uuid_to_str(StorageActivityAttributes.FILE_NAME.value),
                Value=activity_data["file_name"],
            ),
        )

    # Add file path attribute if present
    if activity_data.get("file_path"):
        attributes.append(
            IndalekoSemanticAttributeDataModel(
                Identifier=uuid_to_str(StorageActivityAttributes.FILE_PATH.value),
                Value=activity_data["file_path"],
            ),
        )

    # Add file size attribute if present
    if "size" in activity_data and activity_data["size"] is not None:
        attributes.append(
            IndalekoSemanticAttributeDataModel(
                Identifier=uuid_to_str(StorageActivityAttributes.FILE_SIZE.value),
                Value=activity_data["size"],
            ),
        )

    # Add file mime type attribute if present
    if activity_data.get("mime_type"):
        attributes.append(
            IndalekoSemanticAttributeDataModel(
                Identifier=uuid_to_str(StorageActivityAttributes.FILE_MIME_TYPE.value),
                Value=activity_data["mime_type"],
            ),
        )

    # Add file extension attribute if present
    if (
        "file_name" in activity_data
        and activity_data["file_name"]
        and "." in activity_data["file_name"]
    ):
        extension = activity_data["file_name"].split(".")[-1].lower()
        attributes.append(
            IndalekoSemanticAttributeDataModel(
                Identifier=uuid_to_str(StorageActivityAttributes.FILE_EXTENSION.value),
                Value=extension,
            ),
        )

    return attributes
