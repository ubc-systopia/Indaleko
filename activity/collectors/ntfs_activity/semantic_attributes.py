"""
Semantic attributes for the NTFS activity collector.

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
from typing import Dict, List, Optional, Any, Tuple

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.semantic_attributes import ActivityAttributes
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
# pylint: enable=wrong-import-position


class NtfsActivityAttributes(str, Enum):
    """Semantic attributes for NTFS activity."""
    # Core attributes
    NTFS_ACTIVITY = "0384a92a-21ec-4c8f-940b-eae2eaa84b6c"
    FILE_ACTIVITY = "fa4d3e5f-86e8-4f2a-89eb-bcf71d87c7c8"
    
    # Activity types
    ACTIVITY_TYPE_CREATE = "ab35da6f-9d41-4cc3-8b3a-68e4a55e9c6e"
    ACTIVITY_TYPE_MODIFY = "c56c86a1-cd83-4fa7-833f-b7dc48b75ce3"
    ACTIVITY_TYPE_DELETE = "7dfc3e98-f754-4fd9-8f72-cd5f3ab51c1b"
    ACTIVITY_TYPE_RENAME = "f4ba2854-e31d-4e03-a35a-ec3456d4cb72"
    ACTIVITY_TYPE_SECURITY_CHANGE = "e4bec39c-ac76-4ae8-baea-7c8ccd5bd0a4"
    ACTIVITY_TYPE_ATTRIBUTE_CHANGE = "1eeeb46a-db1a-4ca9-a64a-2f5e54b2add8"
    ACTIVITY_TYPE_CLOSE = "b5fd771e-9b06-44c1-b75b-45f8f4b9d5fa"
    
    # Process-related attributes
    PROCESS_INITIATED = "e7e5f7a2-1b45-4f0d-8b78-a51c7a05f5b2"
    KNOWN_APPLICATION = "96a2c1b3-c77d-48bf-8314-9c3c5d2e1f2a"
    
    # Special attributes
    EMAIL_ATTACHMENT = "3bcfdf51-6db0-41a1-9c6a-6f77afd21d97"
    HIGH_CONFIDENCE_EMAIL_ATTACHMENT = "d04e5483-6fa9-42bb-be39-a2e2bdd8fbf1"
    MEDIUM_CONFIDENCE_EMAIL_ATTACHMENT = "9b8cea42-a6b1-447f-bce2-5c0a34fedb0d"
    LOW_CONFIDENCE_EMAIL_ATTACHMENT = "f1a2ae4c-d0b3-4ead-a9b5-6c2d73f08f8a"
    OUTLOOK_SOURCE = "0e86d4a5-9b31-4fcb-b7ae-2a5e7a3a8654"
    
    # File type attributes
    DIRECTORY_CHANGE = "b7a1e9b6-d1a9-45c3-8d5c-731cf9b6e5fd"
    FILE_CHANGE = "5ac9e7d8-6bc1-4e1f-9768-2fb3e9d24c5a"


def get_ntfs_activity_semantic_attributes() -> Dict[str, IndalekoSemanticAttributeDataModel]:
    """
    Get the dictionary of semantic attribute models for NTFS activity.
    
    Returns:
        A dictionary of semantic attribute models.
    """
    attributes = {}
    
    # Core attributes
    attributes[NtfsActivityAttributes.NTFS_ACTIVITY] = IndalekoSemanticAttributeDataModel(
        AttributeId=uuid.UUID(NtfsActivityAttributes.NTFS_ACTIVITY),
        Value=True,
        Name="NTFS Activity",
        Description="Activity from the NTFS USN Journal"
    )
    
    attributes[NtfsActivityAttributes.FILE_ACTIVITY] = IndalekoSemanticAttributeDataModel(
        AttributeId=uuid.UUID(NtfsActivityAttributes.FILE_ACTIVITY),
        Value=True,
        Name="File Activity",
        Description="File-related activity"
    )
    
    # Activity types
    attributes[NtfsActivityAttributes.ACTIVITY_TYPE_CREATE] = IndalekoSemanticAttributeDataModel(
        AttributeId=uuid.UUID(NtfsActivityAttributes.ACTIVITY_TYPE_CREATE),
        Value=True,
        Name="File Created",
        Description="File creation activity"
    )
    
    attributes[NtfsActivityAttributes.ACTIVITY_TYPE_MODIFY] = IndalekoSemanticAttributeDataModel(
        AttributeId=uuid.UUID(NtfsActivityAttributes.ACTIVITY_TYPE_MODIFY),
        Value=True,
        Name="File Modified",
        Description="File modification activity"
    )
    
    attributes[NtfsActivityAttributes.ACTIVITY_TYPE_DELETE] = IndalekoSemanticAttributeDataModel(
        AttributeId=uuid.UUID(NtfsActivityAttributes.ACTIVITY_TYPE_DELETE),
        Value=True,
        Name="File Deleted",
        Description="File deletion activity"
    )
    
    attributes[NtfsActivityAttributes.ACTIVITY_TYPE_RENAME] = IndalekoSemanticAttributeDataModel(
        AttributeId=uuid.UUID(NtfsActivityAttributes.ACTIVITY_TYPE_RENAME),
        Value=True,
        Name="File Renamed",
        Description="File rename activity"
    )
    
    attributes[NtfsActivityAttributes.ACTIVITY_TYPE_SECURITY_CHANGE] = IndalekoSemanticAttributeDataModel(
        AttributeId=uuid.UUID(NtfsActivityAttributes.ACTIVITY_TYPE_SECURITY_CHANGE),
        Value=True,
        Name="Security Changed",
        Description="File security attribute changes"
    )
    
    attributes[NtfsActivityAttributes.ACTIVITY_TYPE_ATTRIBUTE_CHANGE] = IndalekoSemanticAttributeDataModel(
        AttributeId=uuid.UUID(NtfsActivityAttributes.ACTIVITY_TYPE_ATTRIBUTE_CHANGE),
        Value=True,
        Name="Attribute Changed",
        Description="File attribute changes"
    )
    
    attributes[NtfsActivityAttributes.ACTIVITY_TYPE_CLOSE] = IndalekoSemanticAttributeDataModel(
        AttributeId=uuid.UUID(NtfsActivityAttributes.ACTIVITY_TYPE_CLOSE),
        Value=True,
        Name="File Closed",
        Description="File close operation"
    )
    
    # Process-related attributes
    attributes[NtfsActivityAttributes.PROCESS_INITIATED] = IndalekoSemanticAttributeDataModel(
        AttributeId=uuid.UUID(NtfsActivityAttributes.PROCESS_INITIATED),
        Value=True,
        Name="Process Initiated",
        Description="Activity initiated by a process with known PID"
    )
    
    attributes[NtfsActivityAttributes.KNOWN_APPLICATION] = IndalekoSemanticAttributeDataModel(
        AttributeId=uuid.UUID(NtfsActivityAttributes.KNOWN_APPLICATION),
        Value=True,
        Name="Known Application",
        Description="Activity initiated by a known application"
    )
    
    # Special attributes
    attributes[NtfsActivityAttributes.EMAIL_ATTACHMENT] = IndalekoSemanticAttributeDataModel(
        AttributeId=uuid.UUID(NtfsActivityAttributes.EMAIL_ATTACHMENT),
        Value=True,
        Name="Email Attachment",
        Description="Activity related to an email attachment"
    )
    
    attributes[NtfsActivityAttributes.HIGH_CONFIDENCE_EMAIL_ATTACHMENT] = IndalekoSemanticAttributeDataModel(
        AttributeId=uuid.UUID(NtfsActivityAttributes.HIGH_CONFIDENCE_EMAIL_ATTACHMENT),
        Value=True,
        Name="High Confidence Email Attachment",
        Description="High confidence (>0.8) that this is an email attachment"
    )
    
    attributes[NtfsActivityAttributes.MEDIUM_CONFIDENCE_EMAIL_ATTACHMENT] = IndalekoSemanticAttributeDataModel(
        AttributeId=uuid.UUID(NtfsActivityAttributes.MEDIUM_CONFIDENCE_EMAIL_ATTACHMENT),
        Value=True,
        Name="Medium Confidence Email Attachment",
        Description="Medium confidence (0.5-0.8) that this is an email attachment"
    )
    
    attributes[NtfsActivityAttributes.LOW_CONFIDENCE_EMAIL_ATTACHMENT] = IndalekoSemanticAttributeDataModel(
        AttributeId=uuid.UUID(NtfsActivityAttributes.LOW_CONFIDENCE_EMAIL_ATTACHMENT),
        Value=True,
        Name="Low Confidence Email Attachment",
        Description="Low confidence (0.1-0.5) that this is an email attachment"
    )
    
    attributes[NtfsActivityAttributes.OUTLOOK_SOURCE] = IndalekoSemanticAttributeDataModel(
        AttributeId=uuid.UUID(NtfsActivityAttributes.OUTLOOK_SOURCE),
        Value=True,
        Name="Outlook Source",
        Description="Activity related to Microsoft Outlook"
    )
    
    # File type attributes
    attributes[NtfsActivityAttributes.DIRECTORY_CHANGE] = IndalekoSemanticAttributeDataModel(
        AttributeId=uuid.UUID(NtfsActivityAttributes.DIRECTORY_CHANGE),
        Value=True,
        Name="Directory Change",
        Description="Activity related to a directory"
    )
    
    attributes[NtfsActivityAttributes.FILE_CHANGE] = IndalekoSemanticAttributeDataModel(
        AttributeId=uuid.UUID(NtfsActivityAttributes.FILE_CHANGE),
        Value=True,
        Name="File Change",
        Description="Activity related to a file (not a directory)"
    )
    
    return attributes


def get_activity_type_semantic_attribute(activity_type: str) -> Optional[Tuple[str, IndalekoSemanticAttributeDataModel]]:
    """
    Get the semantic attribute for a specific activity type.
    
    Args:
        activity_type: The activity type string
        
    Returns:
        The semantic attribute key and model, or None if not found
    """
    attributes = get_ntfs_activity_semantic_attributes()
    
    activity_type_map = {
        "create": NtfsActivityAttributes.ACTIVITY_TYPE_CREATE,
        "modify": NtfsActivityAttributes.ACTIVITY_TYPE_MODIFY,
        "delete": NtfsActivityAttributes.ACTIVITY_TYPE_DELETE,
        "rename": NtfsActivityAttributes.ACTIVITY_TYPE_RENAME,
        "security_change": NtfsActivityAttributes.ACTIVITY_TYPE_SECURITY_CHANGE,
        "attribute_change": NtfsActivityAttributes.ACTIVITY_TYPE_ATTRIBUTE_CHANGE,
        "close": NtfsActivityAttributes.ACTIVITY_TYPE_CLOSE,
    }
    
    if activity_type in activity_type_map:
        key = activity_type_map[activity_type]
        return (key, attributes[key])
    
    return None


def get_semantic_attributes_for_activity(activity_data: Dict[str, Any]) -> List[IndalekoSemanticAttributeDataModel]:
    """
    Generate the appropriate semantic attributes for a given activity.
    
    Args:
        activity_data: The activity data dictionary
        
    Returns:
        List of semantic attributes for the activity
    """
    attributes = get_ntfs_activity_semantic_attributes()
    activity_attributes = []
    
    # Add core attributes
    activity_attributes.append(attributes[NtfsActivityAttributes.NTFS_ACTIVITY])
    activity_attributes.append(attributes[NtfsActivityAttributes.FILE_ACTIVITY])
    
    # Add activity type attribute
    activity_type = activity_data.get("activity_type", "").lower()
    activity_type_attr = get_activity_type_semantic_attribute(activity_type)
    if activity_type_attr:
        activity_attributes.append(activity_type_attr[1])
    
    # Add directory/file attribute
    if activity_data.get("is_directory", False):
        activity_attributes.append(attributes[NtfsActivityAttributes.DIRECTORY_CHANGE])
    else:
        activity_attributes.append(attributes[NtfsActivityAttributes.FILE_CHANGE])
    
    # Add process-related attributes
    if activity_data.get("process_id"):
        activity_attributes.append(attributes[NtfsActivityAttributes.PROCESS_INITIATED])
        
        # If it's Outlook, add the outlook source attribute
        if activity_data.get("process_name", "").lower().startswith("outlook"):
            activity_attributes.append(attributes[NtfsActivityAttributes.OUTLOOK_SOURCE])
    
    # Add email attachment attributes if applicable
    if activity_data.get("email_source") or activity_data.get("confidence_score", 0) > 0:
        activity_attributes.append(attributes[NtfsActivityAttributes.EMAIL_ATTACHMENT])
        
        # Add confidence level attribute
        confidence = activity_data.get("confidence_score", 0)
        if confidence > 0.8:
            activity_attributes.append(attributes[NtfsActivityAttributes.HIGH_CONFIDENCE_EMAIL_ATTACHMENT])
        elif confidence > 0.5:
            activity_attributes.append(attributes[NtfsActivityAttributes.MEDIUM_CONFIDENCE_EMAIL_ATTACHMENT])
        elif confidence > 0.1:
            activity_attributes.append(attributes[NtfsActivityAttributes.LOW_CONFIDENCE_EMAIL_ATTACHMENT])
    
    return activity_attributes