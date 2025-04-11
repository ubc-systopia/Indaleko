"""
This module contains data models for NTFS activity data collection.

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

from pydantic import Field, model_validator

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from data_models.provenance_data import IndalekoProvenanceData
from data_models.timestamp import IndalekoTimestamp
# pylint: enable=wrong-import-position


class UsnJournalReasonFlags(Enum):
    """USN Journal reason flags as defined by Windows."""
    USN_REASON_DATA_OVERWRITE = 0x00000001
    USN_REASON_DATA_EXTEND = 0x00000002
    USN_REASON_DATA_TRUNCATION = 0x00000004
    USN_REASON_NAMED_DATA_OVERWRITE = 0x00000010
    USN_REASON_NAMED_DATA_EXTEND = 0x00000020
    USN_REASON_NAMED_DATA_TRUNCATION = 0x00000040
    USN_REASON_FILE_CREATE = 0x00000100
    USN_REASON_FILE_DELETE = 0x00000200
    USN_REASON_EA_CHANGE = 0x00000400
    USN_REASON_SECURITY_CHANGE = 0x00000800
    USN_REASON_RENAME_OLD_NAME = 0x00001000
    USN_REASON_RENAME_NEW_NAME = 0x00002000
    USN_REASON_INDEXABLE_CHANGE = 0x00004000
    USN_REASON_BASIC_INFO_CHANGE = 0x00008000
    USN_REASON_HARD_LINK_CHANGE = 0x00010000
    USN_REASON_COMPRESSION_CHANGE = 0x00020000
    USN_REASON_ENCRYPTION_CHANGE = 0x00040000
    USN_REASON_OBJECT_ID_CHANGE = 0x00080000
    USN_REASON_REPARSE_POINT_CHANGE = 0x00100000
    USN_REASON_STREAM_CHANGE = 0x00200000
    USN_REASON_TRANSACTED_CHANGE = 0x00400000
    USN_REASON_INTEGRITY_CHANGE = 0x00800000
    USN_REASON_DESIRED_STORAGE_CLASS_CHANGE = 0x01000000
    USN_REASON_CLOSE = 0x80000000


class FileActivityType(str, Enum):
    """Types of file activities that are tracked."""
    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    RENAME = "rename"
    SECURITY_CHANGE = "security_change"
    ATTRIBUTE_CHANGE = "attribute_change"
    CLOSE = "close"
    OTHER = "other"


class NtfsFileActivityData(IndalekoBaseModel):
    """Data model for a file activity record from the NTFS USN Journal."""
    activity_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    usn: int = Field(..., description="The Update Sequence Number for this activity")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    file_reference_number: str = Field(..., description="NTFS file reference number (file ID)")
    parent_file_reference_number: Optional[str] = Field(None, description="Parent directory file reference number")
    activity_type: FileActivityType = Field(..., description="Type of file activity")
    reason_flags: int = Field(..., description="Reason flags from the USN record")
    file_name: str = Field(..., description="Name of the file")
    file_path: Optional[str] = Field(None, description="Full path to the file if available")
    volume_name: str = Field(..., description="Volume name (e.g., C:)")
    process_id: Optional[int] = Field(None, description="Process ID that performed the activity")
    process_name: Optional[str] = Field(None, description="Name of the process that performed the activity")
    provenance: Optional[IndalekoProvenanceData] = Field(None, description="Provenance data if available")
    previous_file_name: Optional[str] = Field(None, description="Previous file name for rename operations")
    previous_parent_file_reference_number: Optional[str] = Field(
        None, description="Previous parent directory for move operations"
    )
    is_directory: bool = Field(False, description="Whether the file is a directory")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Additional file attributes")
    
    @model_validator(mode='after')
    def validate_rename_fields(self) -> 'NtfsFileActivityData':
        """Ensure that rename operations have previous file name."""
        if self.activity_type == FileActivityType.RENAME and not self.previous_file_name:
            raise ValueError("Rename operations must include previous_file_name")
        return self


class EmailAttachmentActivityData(NtfsFileActivityData):
    """Extended data model for tracking files that are likely email attachments."""
    email_source: Optional[str] = Field(None, description="Source email address if known")
    email_subject: Optional[str] = Field(None, description="Email subject if known")
    email_timestamp: Optional[datetime] = Field(None, description="Email received timestamp if known")
    attachment_original_name: Optional[str] = Field(None, description="Original attachment filename if known")
    confidence_score: float = Field(0.0, description="Confidence score that this is an email attachment (0.0-1.0)")
    matching_signals: List[str] = Field(default_factory=list, description="Signals that matched to identify as attachment")
    email_id: Optional[str] = Field(None, description="Email ID if known")


class NtfsActivityMetadata(IndalekoBaseModel):
    """Metadata for NTFS activity collection."""
    monitor_start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    monitor_volumes: List[str] = Field(default_factory=list)
    journal_id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4)
    first_usn: Optional[int] = Field(None)
    last_usn: Optional[int] = Field(None)
    activity_count: int = Field(0)
    source_machine: str = Field(..., description="Source machine name")
    provenance: IndalekoProvenanceData = Field(default_factory=IndalekoProvenanceData)


class NtfsActivityData(IndalekoBaseModel):
    """Container for a collection of NTFS file activities."""
    activity_data_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    metadata: NtfsActivityMetadata
    activities: List[NtfsFileActivityData] = Field(default_factory=list)
    Timestamp: IndalekoTimestamp = Field(default_factory=IndalekoTimestamp)