"""
NTFS activity collector for Indaleko.

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
import json
import time
import queue
import threading
import logging
import ctypes
from ctypes import wintypes
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Set, Tuple, Union, Generator, Callable
import platform
import socket
import win32api
import win32con
import win32file
import win32process
import win32ts
import pywintypes
from pathlib import Path

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.base import CollectorBase
from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.ntfs_activity.data_models.ntfs_activity_data_model import (
    FileActivityType,
    NtfsFileActivityData,
    EmailAttachmentActivityData,
    NtfsActivityData,
    NtfsActivityMetadata,
    UsnJournalReasonFlags
)
from activity.collectors.ntfs_activity.semantic_attributes import (
    get_ntfs_activity_semantic_attributes,
    get_semantic_attributes_for_activity
)
from data_models.provenance_data import IndalekoProvenanceData
from data_models.timestamp import IndalekoTimestamp
# pylint: enable=wrong-import-position


class NtfsActivityCollector(CollectorBase):
    """
    Collects file system activity data from the NTFS USN Journal.
    
    This collector monitors the USN Journal on Windows NTFS volumes and processes
    the events to provide a high-level view of file system activities.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize the NTFS activity collector.
        
        Args:
            volumes: List of volume paths to monitor (e.g., ["C:", "D:"])
            filters: Dictionary of filters to apply to the events
            buffer_size: Size of the buffer to use for reading the USN Journal
            monitor_interval: How often to check for new events (in seconds)
            process_lookup_cache_size: Maximum number of processes to cache info for
            email_attachment_detection: Whether to enable email attachment detection
            outlook_integration: Whether to enable Outlook integration
        """
        # Validate platform
        if platform.system() != "Windows":
            raise RuntimeError("NtfsActivityCollector is only available on Windows")
        
        # Basic configuration
        self._name = kwargs.get("name", "NTFS Activity Collector")
        self._provider_id = kwargs.get(
            "provider_id", uuid.UUID("7d8f5a92-35c7-41e6-b13d-6c4e89e7f2a5")
        )
        self._version = kwargs.get("version", "1.0.0")
        self._description = kwargs.get(
            "description", "Collects file system activities from the NTFS USN Journal"
        )
        
        # Configuration
        self._volumes = kwargs.get("volumes", ["C:"])
        self._buffer_size = kwargs.get("buffer_size", 65536)
        self._monitor_interval = kwargs.get("monitor_interval", 1.0)
        self._process_lookup_cache_size = kwargs.get("process_lookup_cache_size", 1000)
        self._email_attachment_detection = kwargs.get("email_attachment_detection", True)
        self._outlook_integration = kwargs.get("outlook_integration", True)
        self._include_close_events = kwargs.get("include_close_events", False)
        self._max_queue_size = kwargs.get("max_queue_size", 10000)
        self._machine_name = socket.gethostname()
        
        # Filters
        self._filters = kwargs.get("filters", {})
        self._excluded_paths = self._filters.get("excluded_paths", [])
        self._excluded_process_names = self._filters.get("excluded_process_names", [])
        self._excluded_extensions = self._filters.get("excluded_extensions", [])
        
        # Data structures
        self._activities = []
        self._event_queue = queue.Queue(maxsize=self._max_queue_size)
        self._volume_handles = {}
        self._usn_journals = {}
        self._active = False
        self._stop_event = threading.Event()
        self._journal_threads = []
        self._processing_thread = None
        self._process_cache = {}
        self._path_cache = {}
        
        # File reference to path mapping cache
        self._file_ref_to_path = {}
        
        # Email attachment detection
        self._recent_outlook_activities = []
        self._recent_attachment_candidates = []
        
        # Metadata
        self._metadata = NtfsActivityMetadata(
            monitor_volumes=self._volumes,
            source_machine=self._machine_name,
            provenance=IndalekoProvenanceData(
                SourceIdentifier=str(self._provider_id),
                SourceType="NTFS USN Journal",
                SourceVersion=self._version,
                CollectionTime=datetime.now(timezone.utc)
            )
        )
        
        # Setup logging
        self._logger = logging.getLogger("NtfsActivityCollector")
        
        # Start threads if auto_start is True
        if kwargs.get("auto_start", False):
            self.start_monitoring()
    
    def start_monitoring(self):
        """Start monitoring the USN Journal on all configured volumes."""
        if self._active:
            return
            
        self._active = True
        self._stop_event.clear()
        
        # Start the processing thread
        self._processing_thread = threading.Thread(
            target=self._event_processing_thread, 
            daemon=True
        )
        self._processing_thread.start()
        
        # Start a monitoring thread for each volume
        for volume in self._volumes:
            try:
                self._start_volume_monitoring(volume)
            except Exception as e:
                self._logger.error(f"Failed to start monitoring volume {volume}: {e}")
    
    def stop_monitoring(self):
        """Stop monitoring the USN Journal on all volumes."""
        if not self._active:
            return
            
        # Signal all threads to stop
        self._stop_event.set()
        self._active = False
        
        # Wait for journal threads to stop
        for thread in self._journal_threads:
            thread.join(timeout=5.0)
        
        # Wait for processing thread to stop
        if self._processing_thread:
            self._processing_thread.join(timeout=5.0)
        
        # Close all volume handles
        for volume, handle in self._volume_handles.items():
            try:
                win32file.CloseHandle(handle)
            except Exception as e:
                self._logger.error(f"Error closing handle for volume {volume}: {e}")
        
        self._volume_handles.clear()
        self._usn_journals.clear()
        self._journal_threads.clear()
        self._processing_thread = None
    
    def _start_volume_monitoring(self, volume: str):
        """
        Start monitoring a specific volume.
        
        Args:
            volume: The volume to monitor (e.g., "C:")
        """
        # Open the volume
        volume_path = f"\\\\?\\{volume}\\"
        handle = win32file.CreateFile(
            volume_path,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
            None,
            win32file.OPEN_EXISTING,
            win32file.FILE_ATTRIBUTE_NORMAL,
            None
        )
        
        # Initialize the USN Journal if needed
        try:
            # Try to get USN Journal info - this will fail if the journal doesn't exist
            usn_journal_info = win32file.DeviceIoControl(
                handle,
                win32file.FSCTL_QUERY_USN_JOURNAL,
                None,
                1024
            )
        except pywintypes.error:
            # Create the USN Journal
            win32file.DeviceIoControl(
                handle,
                win32file.FSCTL_CREATE_USN_JOURNAL,
                None,
                0
            )
            usn_journal_info = win32file.DeviceIoControl(
                handle,
                win32file.FSCTL_QUERY_USN_JOURNAL,
                None,
                1024
            )
        
        # Store volume handle and journal info
        self._volume_handles[volume] = handle
        self._usn_journals[volume] = usn_journal_info
        
        # Start a thread to monitor this volume
        journal_thread = threading.Thread(
            target=self._monitor_usn_journal,
            args=(volume,),
            daemon=True
        )
        self._journal_threads.append(journal_thread)
        journal_thread.start()
    
    def _monitor_usn_journal(self, volume: str):
        """
        Monitor the USN Journal for a specific volume.
        
        Args:
            volume: The volume to monitor (e.g., "C:")
        """
        # Get the handle and journal info
        handle = self._volume_handles.get(volume)
        journal_info = self._usn_journals.get(volume)
        
        if not handle or not journal_info:
            self._logger.error(f"Missing handle or journal info for volume {volume}")
            return
        
        journal_id = journal_info["UsnJournalID"]
        first_usn = journal_info["FirstUsn"]
        next_usn = first_usn
        
        # Setup read data structure
        read_data = win32file.AllocateReadBuffer(self._buffer_size)
        
        while not self._stop_event.is_set():
            try:
                # Setup the read journal data structure
                read_journal_data = struct.pack("QQ", next_usn, 0xFFFFFFFFFFFFFFFF)
                
                # Read from the USN Journal
                data = win32file.DeviceIoControl(
                    handle,
                    win32file.FSCTL_READ_USN_JOURNAL,
                    read_journal_data,
                    self._buffer_size,
                    None
                )
                
                # Update next USN to read
                next_usn = struct.unpack_from("Q", data)[0]
                
                # Process the records
                offset = 8
                while offset < len(data):
                    record_length = struct.unpack_from("I", data, offset)[0]
                    if record_length == 0:
                        break
                    
                    record_data = data[offset:offset + record_length]
                    self._process_usn_record(volume, record_data)
                    
                    offset += record_length
                
                # Sleep a bit to avoid high CPU usage
                time.sleep(self._monitor_interval)
                
            except Exception as e:
                self._logger.error(f"Error reading USN journal on volume {volume}: {e}")
                time.sleep(5)  # Wait a bit before retrying
    
    def _process_usn_record(self, volume: str, record_data: bytes):
        """
        Process a USN journal record.
        
        Args:
            volume: The volume the record is from
            record_data: The raw record data
        """
        # Parse the USN record
        # USN_RECORD_V2 structure: https://docs.microsoft.com/en-us/windows/win32/api/winioctl/ns-winioctl-usn_record_v2
        record = {}
        
        # Extract the basic record information
        record["RecordLength"] = struct.unpack_from("I", record_data, 0)[0]
        record["MajorVersion"] = struct.unpack_from("H", record_data, 4)[0]
        record["MinorVersion"] = struct.unpack_from("H", record_data, 6)[0]
        
        # Check the version - we only support V2 and V3
        if record["MajorVersion"] not in (2, 3):
            return
        
        record["FileReferenceNumber"] = struct.unpack_from("Q", record_data, 8)[0]
        record["ParentFileReferenceNumber"] = struct.unpack_from("Q", record_data, 16)[0]
        record["Usn"] = struct.unpack_from("Q", record_data, 24)[0]
        record["TimeStamp"] = struct.unpack_from("Q", record_data, 32)[0]
        record["Reason"] = struct.unpack_from("I", record_data, 40)[0]
        record["SourceInfo"] = struct.unpack_from("I", record_data, 44)[0]
        record["SecurityId"] = struct.unpack_from("I", record_data, 48)[0]
        record["FileAttributes"] = struct.unpack_from("I", record_data, 52)[0]
        record["FileNameLength"] = struct.unpack_from("H", record_data, 56)[0]
        record["FileNameOffset"] = struct.unpack_from("H", record_data, 58)[0]
        
        # Extract the filename (UTF-16 encoded)
        filename_offset = record["FileNameOffset"]
        filename_length = record["FileNameLength"]
        filename_bytes = record_data[filename_offset:filename_offset+filename_length]
        record["FileName"] = filename_bytes.decode("utf-16")
        
        # Convert Windows timestamp to datetime
        # Windows timestamp is in 100-nanosecond intervals since January 1, 1601
        timestamp = record["TimeStamp"]
        if timestamp:
            dt = datetime(1601, 1, 1) + timedelta(microseconds=timestamp / 10)
            record["DateTime"] = dt.replace(tzinfo=timezone.utc)
        else:
            record["DateTime"] = datetime.now(timezone.utc)
        
        # Convert file attributes
        is_directory = bool(record["FileAttributes"] & win32file.FILE_ATTRIBUTE_DIRECTORY)
        
        # Add to event queue for processing
        self._event_queue.put({
            "volume": volume,
            "record": record,
            "is_directory": is_directory
        })
    
    def _event_processing_thread(self):
        """Process events from the queue."""
        while not self._stop_event.is_set() or not self._event_queue.empty():
            try:
                # Get an event from the queue with timeout
                try:
                    event = self._event_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Process the event
                self._process_event(event)
                
                # Mark the task as done
                self._event_queue.task_done()
                
            except Exception as e:
                self._logger.error(f"Error processing event: {e}")
    
    def _process_event(self, event: Dict[str, Any]):
        """
        Process a USN journal event.
        
        Args:
            event: The event to process
        """
        record = event["record"]
        volume = event["volume"]
        is_directory = event["is_directory"]
        
        # Skip if the file is in an excluded path
        file_name = record["FileName"]
        if any(file_name.startswith(exc) for exc in self._excluded_paths):
            return
        
        # Skip if the file has an excluded extension
        if not is_directory and "." in file_name:
            ext = file_name.split(".")[-1].lower()
            if ext in self._excluded_extensions:
                return
        
        # Determine the activity type
        activity_type = self._determine_activity_type(record["Reason"])
        
        # Skip close events if configured to do so
        if activity_type == FileActivityType.CLOSE and not self._include_close_events:
            return
        
        # Try to get the process ID and name that made this change
        process_id, process_name = self._get_associated_process()
        
        # Skip if the process is in the excluded list
        if process_name and any(process_name.startswith(exc) for exc in self._excluded_process_names):
            return
        
        # Get the full file path if possible
        file_path = None
        try:
            file_path = self._get_file_path(
                volume, 
                record["FileReferenceNumber"],
                record["ParentFileReferenceNumber"],
                record["FileName"]
            )
        except Exception as e:
            self._logger.warning(f"Failed to get file path: {e}")
        
        # Create the activity data
        activity_data = NtfsFileActivityData(
            usn=record["Usn"],
            timestamp=record["DateTime"],
            file_reference_number=str(record["FileReferenceNumber"]),
            parent_file_reference_number=str(record["ParentFileReferenceNumber"]),
            activity_type=activity_type,
            reason_flags=record["Reason"],
            file_name=record["FileName"],
            file_path=file_path,
            volume_name=volume,
            process_id=process_id,
            process_name=process_name,
            is_directory=is_directory,
            attributes={
                "file_attributes": record["FileAttributes"],
                "security_id": record["SecurityId"],
                "source_info": record["SourceInfo"]
            }
        )
        
        # Handle rename operations by looking for the previous name
        if activity_type == FileActivityType.RENAME:
            # Look for the matching old name in recent activities
            for recent_activity in reversed(self._activities):
                if (recent_activity.activity_type == FileActivityType.RENAME and 
                    recent_activity.file_reference_number == activity_data.file_reference_number and
                    recent_activity.file_name != activity_data.file_name and
                    not hasattr(recent_activity, "matched_rename")):
                    # Found the matching old name activity
                    activity_data.previous_file_name = recent_activity.file_name
                    # Mark this activity as matched so we don't match it again
                    setattr(recent_activity, "matched_rename", True)
                    break
        
        # Check if this might be an email attachment save
        if self._email_attachment_detection and activity_type == FileActivityType.CREATE:
            # If the process is Outlook, this is likely an email attachment
            if process_name and "outlook" in process_name.lower():
                # Convert to EmailAttachmentActivityData
                email_activity = self._create_email_attachment_activity(activity_data)
                # Add to recent activities
                self._activities.append(email_activity)
                # Add to recent outlook activities
                self._recent_outlook_activities.append(email_activity)
                # Trim the list if it gets too long
                if len(self._recent_outlook_activities) > 100:
                    self._recent_outlook_activities.pop(0)
                
                return
            
            # Otherwise, check if it might be an attachment based on heuristics
            email_confidence = self._check_email_attachment_confidence(activity_data)
            if email_confidence > 0.1:
                # Convert to EmailAttachmentActivityData with confidence score
                email_activity = self._create_email_attachment_activity(
                    activity_data, 
                    confidence_score=email_confidence
                )
                # Add to recent activities
                self._activities.append(email_activity)
                # Add to recent attachment candidates
                self._recent_attachment_candidates.append(email_activity)
                # Trim the list if it gets too long
                if len(self._recent_attachment_candidates) > 100:
                    self._recent_attachment_candidates.pop(0)
                
                return
        
        # Add to activities list
        self._activities.append(activity_data)
        
        # Update metadata
        self._metadata.activity_count += 1
        if self._metadata.first_usn is None or record["Usn"] < self._metadata.first_usn:
            self._metadata.first_usn = record["Usn"]
        if self._metadata.last_usn is None or record["Usn"] > self._metadata.last_usn:
            self._metadata.last_usn = record["Usn"]
    
    def _determine_activity_type(self, reason_flags: int) -> FileActivityType:
        """
        Determine the activity type from the reason flags.
        
        Args:
            reason_flags: The reason flags from the USN record
            
        Returns:
            The determined activity type
        """
        if reason_flags & win32file.USN_REASON_FILE_CREATE:
            return FileActivityType.CREATE
        elif reason_flags & win32file.USN_REASON_FILE_DELETE:
            return FileActivityType.DELETE
        elif (reason_flags & win32file.USN_REASON_RENAME_OLD_NAME or 
              reason_flags & win32file.USN_REASON_RENAME_NEW_NAME):
            return FileActivityType.RENAME
        elif reason_flags & win32file.USN_REASON_SECURITY_CHANGE:
            return FileActivityType.SECURITY_CHANGE
        elif (reason_flags & win32file.USN_REASON_EA_CHANGE or 
              reason_flags & win32file.USN_REASON_BASIC_INFO_CHANGE or
              reason_flags & win32file.USN_REASON_COMPRESSION_CHANGE or
              reason_flags & win32file.USN_REASON_ENCRYPTION_CHANGE):
            return FileActivityType.ATTRIBUTE_CHANGE
        elif reason_flags & win32file.USN_REASON_CLOSE:
            return FileActivityType.CLOSE
        elif (reason_flags & win32file.USN_REASON_DATA_OVERWRITE or
              reason_flags & win32file.USN_REASON_DATA_EXTEND or
              reason_flags & win32file.USN_REASON_DATA_TRUNCATION):
            return FileActivityType.MODIFY
        else:
            return FileActivityType.OTHER
    
    def _get_associated_process(self) -> Tuple[Optional[int], Optional[str]]:
        """
        Try to determine the process that caused this file activity.
        
        Returns:
            Tuple of (process_id, process_name) or (None, None) if unknown
        """
        # This is a complex topic. In a real implementation, this would
        # require ETW (Event Tracing for Windows) or similar mechanisms.
        # For this prototype, we'll just return None values.
        return None, None
    
    def _get_file_path(
        self, 
        volume: str, 
        file_ref: int, 
        parent_ref: int, 
        file_name: str
    ) -> Optional[str]:
        """
        Get the full path for a file based on its reference numbers.
        
        Args:
            volume: The volume the file is on
            file_ref: The file reference number
            parent_ref: The parent directory reference number
            file_name: The file name
            
        Returns:
            The full path to the file, or None if it can't be determined
        """
        # Check cache first
        if file_ref in self._file_ref_to_path:
            return self._file_ref_to_path[file_ref]
        
        # Get the path components by walking up the tree
        path_components = [file_name]
        current_parent = parent_ref
        
        # Prevent infinite loops
        visited = {file_ref, parent_ref}
        max_depth = 100
        depth = 0
        
        while current_parent != 0 and depth < max_depth:
            depth += 1
            
            # If we've seen this parent before, we have a loop
            if current_parent in visited and current_parent != 5:  # 5 is root on NTFS
                break
                
            # Check if we have the parent in our cache
            if current_parent in self._file_ref_to_path:
                parent_path = self._file_ref_to_path[current_parent]
                full_path = os.path.join(parent_path, *reversed(path_components))
                self._file_ref_to_path[file_ref] = full_path
                return full_path
            
            # Otherwise, try to get the parent from the filesystem
            try:
                # Open the file by reference number
                handle = self._open_by_id(volume, current_parent)
                if not handle:
                    break
                    
                # Get the file name information
                name_info = win32file.GetFileInformationByHandleEx(
                    handle, 
                    win32file.FileNameInfo
                )
                parent_name = os.path.basename(name_info).strip('\\')
                
                # Add to path components
                if parent_name:
                    path_components.append(parent_name)
                
                # Get the parent's parent
                info = win32file.GetFileInformationByHandleEx(
                    handle, 
                    win32file.FileIdInfo
                )
                current_parent = info["ParentIdLowPart"] | (info["ParentIdHighPart"] << 32)
                
                # Close the handle
                win32file.CloseHandle(handle)
                
            except Exception as e:
                self._logger.debug(f"Error getting file path: {e}")
                break
        
        # If we reached the root, construct the full path
        if depth == max_depth or current_parent == 5:  # 5 is root on NTFS
            full_path = f"{volume}\\" + "\\".join(reversed(path_components))
            self._file_ref_to_path[file_ref] = full_path
            return full_path
        
        # If we couldn't resolve the full path, construct a partial path
        return f"{volume}\\...\\{file_name}"
    
    def _open_by_id(self, volume: str, file_id: int) -> Optional[int]:
        """
        Open a file by its file ID.
        
        Args:
            volume: The volume the file is on
            file_id: The file ID to open
            
        Returns:
            File handle if successful, None otherwise
        """
        try:
            # Create the file ID structure
            file_id_descriptor = struct.pack("QQ", file_id, 0)
            
            # Open the file by ID
            handle = win32file.OpenFileById(
                self._volume_handles[volume],
                file_id_descriptor,
                win32file.FILE_READ_ATTRIBUTES | win32file.FILE_READ_EA,
                win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE | win32file.FILE_SHARE_DELETE,
                None,
                0
            )
            
            return handle
        except Exception as e:
            self._logger.debug(f"Error opening file by ID {file_id}: {e}")
            return None
    
    def _check_email_attachment_confidence(self, activity_data: NtfsFileActivityData) -> float:
        """
        Check if a file activity might be related to an email attachment.
        
        Args:
            activity_data: The file activity data
            
        Returns:
            Confidence score from 0.0 to 1.0
        """
        # This is a simplified implementation. In a real-world scenario,
        # this would use multiple heuristics and signals to determine the confidence.
        
        signals = []
        confidence = 0.0
        
        # Signal 1: File created in a download or temp directory
        if activity_data.file_path:
            download_paths = ["\\Downloads\\", "\\Temp\\", "\\Temporary Internet Files\\"]
            if any(path in activity_data.file_path for path in download_paths):
                signals.append("download_directory")
                confidence += 0.3
        
        # Signal 2: Created shortly after Outlook activity
        if self._recent_outlook_activities:
            recent_time = self._recent_outlook_activities[-1].timestamp
            time_diff = (activity_data.timestamp - recent_time).total_seconds()
            if 0 <= time_diff <= 30:  # Within 30 seconds
                signals.append("recent_outlook_activity")
                confidence += 0.5
            elif 30 < time_diff <= 300:  # Within 5 minutes
                signals.append("recent_outlook_activity")
                confidence += 0.2
        
        # Signal 3: File name contains common attachment patterns
        filename = activity_data.file_name.lower()
        attachment_patterns = ["att", "attach", "email", "fw_", "fwd_", "re_"]
        if any(pattern in filename for pattern in attachment_patterns):
            signals.append("attachment_filename_pattern")
            confidence += 0.3
        
        # Cap confidence at 1.0
        confidence = min(confidence, 1.0)
        
        return confidence
    
    def _create_email_attachment_activity(
        self, 
        activity_data: NtfsFileActivityData,
        confidence_score: float = 0.9,
        email_source: Optional[str] = None,
        email_subject: Optional[str] = None,
        email_timestamp: Optional[datetime] = None,
        attachment_original_name: Optional[str] = None,
        email_id: Optional[str] = None,
        matching_signals: Optional[List[str]] = None
    ) -> EmailAttachmentActivityData:
        """
        Create an email attachment activity from a file activity.
        
        Args:
            activity_data: The base file activity data
            confidence_score: Confidence score that this is an email attachment
            email_source: Email source address if known
            email_subject: Email subject if known
            email_timestamp: Email timestamp if known
            attachment_original_name: Original attachment name if known
            email_id: Email ID if known
            matching_signals: List of signals that matched
            
        Returns:
            EmailAttachmentActivityData object
        """
        # Create a copy of the activity data dict
        activity_dict = activity_data.model_dump()
        
        # Add email attachment specific fields
        activity_dict["email_source"] = email_source
        activity_dict["email_subject"] = email_subject
        activity_dict["email_timestamp"] = email_timestamp
        activity_dict["attachment_original_name"] = attachment_original_name
        activity_dict["confidence_score"] = confidence_score
        activity_dict["email_id"] = email_id
        activity_dict["matching_signals"] = matching_signals or []
        
        # Create and return the email attachment activity
        return EmailAttachmentActivityData(**activity_dict)
    
    def get_activities(self, filters: Optional[Dict] = None) -> List[NtfsFileActivityData]:
        """
        Get collected activities, optionally filtered.
        
        Args:
            filters: Dictionary of filters to apply
            
        Returns:
            List of file activities
        """
        if not filters:
            return self._activities
        
        results = []
        for activity in self._activities:
            match = True
            for key, value in filters.items():
                if hasattr(activity, key) and getattr(activity, key) != value:
                    match = False
                    break
            if match:
                results.append(activity)
                
        return results
    
    def get_activity_by_id(self, activity_id: uuid.UUID) -> Optional[NtfsFileActivityData]:
        """
        Get an activity by its ID.
        
        Args:
            activity_id: The activity ID to look for
            
        Returns:
            The activity if found, None otherwise
        """
        for activity in self._activities:
            if activity.activity_id == activity_id:
                return activity
        return None
    
    def get_activities_by_file_path(self, file_path: str) -> List[NtfsFileActivityData]:
        """
        Get activities for a specific file path.
        
        Args:
            file_path: The file path to look for
            
        Returns:
            List of activities for the file
        """
        results = []
        for activity in self._activities:
            if activity.file_path == file_path or (
                activity.file_path and file_path.endswith(activity.file_name)
            ):
                results.append(activity)
        return results
    
    def get_activities_by_time_range(
        self, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[NtfsFileActivityData]:
        """
        Get activities within a time range.
        
        Args:
            start_time: Start of the time range
            end_time: End of the time range
            
        Returns:
            List of activities within the time range
        """
        results = []
        for activity in self._activities:
            if start_time <= activity.timestamp <= end_time:
                results.append(activity)
        return results
    
    def get_activities_by_process(self, process_name: str) -> List[NtfsFileActivityData]:
        """
        Get activities initiated by a specific process.
        
        Args:
            process_name: Process name to look for
            
        Returns:
            List of activities by the process
        """
        results = []
        for activity in self._activities:
            if activity.process_name and process_name.lower() in activity.process_name.lower():
                results.append(activity)
        return results
    
    def get_email_attachment_activities(
        self, 
        min_confidence: float = 0.5
    ) -> List[EmailAttachmentActivityData]:
        """
        Get activities identified as email attachments.
        
        Args:
            min_confidence: Minimum confidence score
            
        Returns:
            List of email attachment activities
        """
        results = []
        for activity in self._activities:
            if isinstance(activity, EmailAttachmentActivityData) and activity.confidence_score >= min_confidence:
                results.append(activity)
        return results
    
    def clear_activities(self):
        """Clear all collected activities."""
        self._activities = []
        self._metadata.activity_count = 0
    
    # Implement CollectorBase abstract methods
    def get_collector_characteristics(self) -> List[ActivityDataCharacteristics]:
        """Get the characteristics of this collector."""
        return [
            ActivityDataCharacteristics.ACTIVITY_DATA_SYSTEM_ACTIVITY,
            ActivityDataCharacteristics.ACTIVITY_DATA_FILE_ACTIVITY
        ]
    
    def get_collector_name(self) -> str:
        """Get the name of the collector."""
        return self._name
    
    def get_provider_id(self) -> uuid.UUID:
        """Get the ID of the collector."""
        return self._provider_id
    
    def retrieve_data(self, data_id: uuid.UUID) -> Dict:
        """
        Retrieve data for a specific ID.
        
        Args:
            data_id: The ID to retrieve data for
            
        Returns:
            The requested data
        """
        activity = self.get_activity_by_id(data_id)
        if activity:
            return activity.model_dump()
        return {}
    
    def get_cursor(self, activity_context: uuid.UUID) -> uuid.UUID:
        """
        Get a cursor for the provided activity context.
        
        Args:
            activity_context: The activity context
            
        Returns:
            A cursor UUID
        """
        # In this simple implementation, just return a new UUID
        # In a more complex implementation, this would return a cursor
        # that can be used to efficiently retrieve data from this provider
        return uuid.uuid4()
    
    def cache_duration(self) -> timedelta:
        """
        Get the cache duration for this collector's data.
        
        Returns:
            The cache duration
        """
        return timedelta(minutes=5)
    
    def get_description(self) -> str:
        """
        Get a description of this collector.
        
        Returns:
            The collector description
        """
        return self._description
    
    def get_json_schema(self) -> dict:
        """
        Get the JSON schema for this collector's data.
        
        Returns:
            The JSON schema
        """
        return NtfsActivityData.model_json_schema()
    
    def collect_data(self) -> None:
        """Collect data from the provider."""
        # The collector runs continuously in the background so this
        # method just ensures that monitoring is active
        if not self._active:
            self.start_monitoring()
    
    def process_data(self, data: Any) -> Dict[str, Any]:
        """
        Process the collected data.
        
        Args:
            data: Raw data to process
            
        Returns:
            Processed data
        """
        # The processing is done asynchronously in the monitoring threads
        activity_data = NtfsActivityData(
            metadata=self._metadata,
            activities=self._activities,
            Timestamp=IndalekoTimestamp()
        )
        return activity_data.model_dump()
    
    def store_data(self, data: Dict[str, Any]) -> None:
        """
        Store the processed data.
        
        Args:
            data: Data to store
        """
        # This is a collector, not a recorder. Storage is handled by the recorder.
        pass


def main():
    """Main function for testing the collector."""
    logging.basicConfig(level=logging.INFO)
    
    # Check if running on Windows
    if platform.system() != "Windows":
        print("This collector only works on Windows")
        return
    
    # Create a collector
    collector = NtfsActivityCollector(
        volumes=["C:"],
        include_close_events=False,
        auto_start=True
    )
    
    print(f"Started monitoring NTFS activity on volumes: {collector._volumes}")
    print("Press Ctrl+C to stop...")
    
    try:
        # Monitor for a while
        start_time = datetime.now()
        while (datetime.now() - start_time).total_seconds() < 60:
            time.sleep(1)
            activity_count = len(collector._activities)
            if activity_count > 0:
                print(f"Collected {activity_count} activities so far...")
                
                # Print details of the last activity
                last_activity = collector._activities[-1]
                print(f"Latest activity: {last_activity.activity_type} - {last_activity.file_name}")
            
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        # Stop monitoring
        collector.stop_monitoring()
        
        # Print summary
        activities = collector._activities
        print(f"\nCollected {len(activities)} activities:")
        
        # Group by type
        activity_types = {}
        for activity in activities:
            activity_type = activity.activity_type
            if activity_type not in activity_types:
                activity_types[activity_type] = 0
            activity_types[activity_type] += 1
        
        for activity_type, count in activity_types.items():
            print(f"  {activity_type}: {count}")
        
        # Show email attachment statistics if any
        email_attachments = collector.get_email_attachment_activities()
        if email_attachments:
            print(f"\nDetected {len(email_attachments)} potential email attachments:")
            for attachment in email_attachments:
                confidence = attachment.confidence_score
                confidence_str = f"{confidence:.2f}"
                print(f"  {attachment.file_name} (confidence: {confidence_str})")


if __name__ == "__main__":
    import struct  # Required for parsing USN records
    main()