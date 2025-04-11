"""
Outlook attachment tracker for Indaleko.

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
import logging
import threading
import time
import win32com.client
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Set, Tuple

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.ntfs_activity.ntfs_activity_collector import NtfsActivityCollector
from activity.collectors.ntfs_activity.data_models.ntfs_activity_data_model import (
    FileActivityType,
    NtfsFileActivityData,
    EmailAttachmentActivityData
)
# pylint: enable=wrong-import-position


class OutlookAttachmentTracker:
    """
    Specialized component for tracking Outlook attachments using NTFS activities.
    
    This component connects to Outlook via COM and monitors both the NTFS
    activity feed and Outlook email/attachment events to correlate saved
    attachments with their source emails.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize the Outlook attachment tracker.
        
        Args:
            ntfs_collector: NtfsActivityCollector instance to use
            polling_interval: How often to check for new emails (in seconds)
            max_history: Maximum number of emails to keep in history
            attachment_folder_hints: List of folder names likely to contain attachments
        """
        # Get or create NTFS collector
        self._ntfs_collector = kwargs.get("ntfs_collector", None)
        if not self._ntfs_collector:
            collector_kwargs = kwargs.get("collector_kwargs", {})
            # Auto-start is set to False to avoid starting monitoring before we're ready
            collector_kwargs["auto_start"] = False
            self._ntfs_collector = NtfsActivityCollector(**collector_kwargs)
        
        # Configuration
        self._polling_interval = kwargs.get("polling_interval", 30)
        self._max_history = kwargs.get("max_history", 1000)
        self._attachment_folder_hints = kwargs.get("attachment_folder_hints", [
            "Downloads", "Documents", "Desktop", "Temp", "Attachments"
        ])
        
        # Data structures
        self._recent_emails = []
        self._attachment_info = {}
        self._processed_ids = set()
        self._matched_activities = []
        
        # Thread control
        self._active = False
        self._stop_event = threading.Event()
        self._outlook_thread = None
        
        # Outlook COM objects
        self._outlook = None
        self._namespace = None
        self._inbox = None
        
        # Setup logging
        self._logger = logging.getLogger("OutlookAttachmentTracker")
        
        # Start tracking if auto_start is True
        if kwargs.get("auto_start", False):
            self.start_tracking()
    
    def start_tracking(self):
        """Start tracking Outlook attachments."""
        if self._active:
            return
            
        self._active = True
        self._stop_event.clear()
        
        # Start the NTFS collector if it's not already running
        if not self._ntfs_collector._active:
            self._ntfs_collector.start_monitoring()
        
        # Start the Outlook monitoring thread
        self._outlook_thread = threading.Thread(
            target=self._outlook_monitoring_thread,
            daemon=True
        )
        self._outlook_thread.start()
    
    def stop_tracking(self):
        """Stop tracking Outlook attachments."""
        if not self._active:
            return
            
        # Signal the thread to stop
        self._stop_event.set()
        self._active = False
        
        # Wait for the thread to stop
        if self._outlook_thread:
            self._outlook_thread.join(timeout=5.0)
        
        # Release COM objects
        self._release_outlook_objects()
    
    def _release_outlook_objects(self):
        """Release Outlook COM objects."""
        if self._outlook:
            try:
                self._outlook.Quit()
            except:
                pass
            self._outlook = None
            self._namespace = None
            self._inbox = None
    
    def _outlook_monitoring_thread(self):
        """Thread for monitoring Outlook emails and attachments."""
        try:
            # Connect to Outlook
            if not self._connect_to_outlook():
                self._logger.error("Failed to connect to Outlook")
                return
            
            self._logger.info("Connected to Outlook")
            
            # Initial scan of recent emails
            self._scan_recent_emails()
            
            # Monitor for new emails and NTFS activities
            while not self._stop_event.is_set():
                try:
                    # Check for new emails
                    self._check_new_emails()
                    
                    # Look for matches between NTFS activities and email attachments
                    self._match_activities_with_attachments()
                    
                    # Sleep for the polling interval
                    time.sleep(self._polling_interval)
                    
                except Exception as e:
                    self._logger.error(f"Error in Outlook monitoring loop: {e}")
                    time.sleep(5)  # Wait a bit before retrying
        
        except Exception as e:
            self._logger.error(f"Error in Outlook monitoring thread: {e}")
        
        finally:
            # Release COM objects
            self._release_outlook_objects()
    
    def _connect_to_outlook(self) -> bool:
        """
        Connect to Outlook via COM.
        
        Returns:
            True if connected successfully, False otherwise
        """
        try:
            # Create Outlook application object
            self._outlook = win32com.client.Dispatch("Outlook.Application")
            
            # Get MAPI namespace
            self._namespace = self._outlook.GetNamespace("MAPI")
            
            # Get inbox folder
            self._inbox = self._namespace.GetDefaultFolder(6)  # 6 is Inbox
            
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to connect to Outlook: {e}")
            self._release_outlook_objects()
            return False
    
    def _scan_recent_emails(self):
        """Scan recent emails for attachments."""
        try:
            # Get emails from inbox
            emails = self._inbox.Items
            
            # Sort by received time descending
            emails.Sort("[ReceivedTime]", True)
            
            # Get recent emails (up to max_history)
            count = min(emails.Count, self._max_history)
            
            for i in range(count):
                try:
                    email = emails[i]
                    self._process_email(email)
                except Exception as e:
                    self._logger.error(f"Error processing email: {e}")
        
        except Exception as e:
            self._logger.error(f"Error scanning recent emails: {e}")
    
    def _check_new_emails(self):
        """Check for new emails since last check."""
        try:
            # Get emails from inbox
            emails = self._inbox.Items
            
            # Sort by received time descending
            emails.Sort("[ReceivedTime]", True)
            
            # Get new emails (those received since the newest one we've processed)
            last_received_time = None
            if self._recent_emails:
                last_received_time = self._recent_emails[0].get("received_time")
            
            # Process new emails
            for i in range(min(50, emails.Count)):  # Limit to 50 to avoid performance issues
                try:
                    email = emails[i]
                    
                    # Check if this is a new email
                    if last_received_time and email.ReceivedTime <= last_received_time:
                        break
                    
                    # Process the email
                    self._process_email(email)
                    
                except Exception as e:
                    self._logger.error(f"Error checking new email: {e}")
        
        except Exception as e:
            self._logger.error(f"Error checking new emails: {e}")
    
    def _process_email(self, email):
        """
        Process an email for attachment tracking.
        
        Args:
            email: Outlook email item
        """
        try:
            # Skip if we've already processed this email
            email_id = str(email.EntryID)
            if email_id in self._processed_ids:
                return
            
            # Convert received time to datetime with timezone
            received_time = datetime.fromtimestamp(
                int(email.ReceivedTime.timestamp()),
                timezone.utc
            )
            
            # Extract email data
            email_data = {
                "id": email_id,
                "subject": email.Subject,
                "sender": email.SenderEmailAddress,
                "received_time": received_time,
                "has_attachments": email.Attachments.Count > 0,
                "attachments": []
            }
            
            # Process attachments if any
            if email.Attachments.Count > 0:
                for i in range(1, email.Attachments.Count + 1):
                    attachment = email.Attachments.Item(i)
                    attachment_data = {
                        "filename": attachment.FileName,
                        "size": attachment.Size,
                        "content_type": getattr(attachment, "ContentType", None)
                    }
                    email_data["attachments"].append(attachment_data)
                    
                    # Store attachment info for matching
                    self._attachment_info[attachment.FileName] = {
                        "email_id": email_id,
                        "email_subject": email.Subject,
                        "email_sender": email.SenderEmailAddress,
                        "email_received_time": received_time,
                        "attachment_filename": attachment.FileName,
                        "attachment_size": attachment.Size
                    }
            
            # Add to recent emails (at the beginning)
            self._recent_emails.insert(0, email_data)
            
            # Trim the list if it gets too long
            if len(self._recent_emails) > self._max_history:
                self._recent_emails = self._recent_emails[:self._max_history]
            
            # Mark as processed
            self._processed_ids.add(email_id)
            
        except Exception as e:
            self._logger.error(f"Error processing email: {e}")
    
    def _match_activities_with_attachments(self):
        """Match NTFS activities with email attachments."""
        # Get recent file creation activities
        recent_activities = [
            activity for activity in self._ntfs_collector._activities
            if (activity.activity_type == FileActivityType.CREATE and
                not hasattr(activity, "attachment_matched"))
        ]
        
        if not recent_activities:
            return
        
        # Try to match activities with attachments
        for activity in recent_activities:
            try:
                # Extract the filename
                filename = activity.file_name
                
                # Skip if not a file
                if activity.is_directory:
                    continue
                
                # Skip if in unlikely location for attachments
                if activity.file_path:
                    is_likely_attachment_path = False
                    for folder in self._attachment_folder_hints:
                        if f"\\{folder}\\" in activity.file_path:
                            is_likely_attachment_path = True
                            break
                    
                    if not is_likely_attachment_path:
                        continue
                
                # Look for exact filename match
                if filename in self._attachment_info:
                    attachment_info = self._attachment_info[filename]
                    
                    # Check time proximity
                    time_diff = (activity.timestamp - attachment_info["email_received_time"]).total_seconds()
                    if time_diff < 0:
                        continue  # File created before email received
                    
                    if time_diff > 3600:
                        continue  # More than an hour difference
                    
                    # Create EmailAttachmentActivityData
                    email_activity = self._create_email_attachment_activity(
                        activity,
                        attachment_info
                    )
                    
                    # Add to matched activities
                    self._matched_activities.append(email_activity)
                    
                    # Mark original activity as matched
                    setattr(activity, "attachment_matched", True)
                    
                    # Update activity in collector's list
                    for i, a in enumerate(self._ntfs_collector._activities):
                        if a.activity_id == activity.activity_id:
                            self._ntfs_collector._activities[i] = email_activity
                            break
                    
                    continue
                
                # Try fuzzy matching
                best_match = None
                best_score = 0.0
                
                for attachment_filename, info in self._attachment_info.items():
                    # Calculate similarity score
                    score = self._calculate_filename_similarity(filename, attachment_filename)
                    
                    # Check time proximity
                    time_diff = (activity.timestamp - info["email_received_time"]).total_seconds()
                    time_score = 0.0
                    
                    if 0 <= time_diff <= 60:  # Within 1 minute
                        time_score = 0.5
                    elif 60 < time_diff <= 300:  # Within 5 minutes
                        time_score = 0.3
                    elif 300 < time_diff <= 3600:  # Within 1 hour
                        time_score = 0.1
                    
                    combined_score = score + time_score
                    
                    if combined_score > best_score and combined_score > 0.7:
                        best_score = combined_score
                        best_match = (attachment_filename, info)
                
                if best_match:
                    attachment_filename, attachment_info = best_match
                    
                    # Create EmailAttachmentActivityData
                    email_activity = self._create_email_attachment_activity(
                        activity,
                        attachment_info,
                        confidence_score=best_score
                    )
                    
                    # Add to matched activities
                    self._matched_activities.append(email_activity)
                    
                    # Mark original activity as matched
                    setattr(activity, "attachment_matched", True)
                    
                    # Update activity in collector's list
                    for i, a in enumerate(self._ntfs_collector._activities):
                        if a.activity_id == activity.activity_id:
                            self._ntfs_collector._activities[i] = email_activity
                            break
            
            except Exception as e:
                self._logger.error(f"Error matching activity with attachment: {e}")
    
    def _calculate_filename_similarity(self, filename1: str, filename2: str) -> float:
        """
        Calculate similarity between two filenames.
        
        Args:
            filename1: First filename
            filename2: Second filename
            
        Returns:
            Similarity score (0.0-1.0)
        """
        # Simple similarity calculation based on filename, extension, and common patterns
        
        # Remove extension
        base1 = os.path.splitext(filename1)[0].lower()
        base2 = os.path.splitext(filename2)[0].lower()
        
        # Check extension match
        ext1 = os.path.splitext(filename1)[1].lower()
        ext2 = os.path.splitext(filename2)[0].lower()
        
        ext_match = ext1 == ext2
        
        # Check if one is substring of the other
        is_substring = base1 in base2 or base2 in base1
        
        # Check common prefixes/suffixes that are added when saving attachments
        common_patterns = ["att", "attachment", "copy of", "fw_", "fwd_", "re_"]
        pattern_match = False
        
        for pattern in common_patterns:
            if (pattern in base1 and not pattern in base2) or (pattern in base2 and not pattern in base1):
                pattern_match = True
                break
        
        # Calculate score
        score = 0.0
        
        if filename1 == filename2:
            score = 1.0
        elif is_substring:
            score = 0.8
        elif ext_match:
            score = 0.3
        
        if pattern_match:
            score += 0.2
        
        return min(score, 1.0)
    
    def _create_email_attachment_activity(
        self,
        activity_data: NtfsFileActivityData,
        attachment_info: Dict[str, Any],
        confidence_score: float = 0.9
    ) -> EmailAttachmentActivityData:
        """
        Create an email attachment activity from a file activity.
        
        Args:
            activity_data: The base file activity data
            attachment_info: Information about the attachment
            confidence_score: Confidence score that this is an email attachment
            
        Returns:
            EmailAttachmentActivityData object
        """
        # Determine matching signals
        matching_signals = []
        
        if attachment_info["attachment_filename"] == activity_data.file_name:
            matching_signals.append("exact_filename_match")
        else:
            matching_signals.append("similar_filename")
        
        time_diff = (activity_data.timestamp - attachment_info["email_received_time"]).total_seconds()
        if time_diff <= 60:
            matching_signals.append("time_proximity_high")
        elif time_diff <= 300:
            matching_signals.append("time_proximity_medium")
        else:
            matching_signals.append("time_proximity_low")
        
        if activity_data.process_name and "outlook" in activity_data.process_name.lower():
            matching_signals.append("outlook_process")
        
        # Create a copy of the activity data dict
        activity_dict = activity_data.model_dump()
        
        # Add email attachment specific fields
        activity_dict["email_source"] = attachment_info["email_sender"]
        activity_dict["email_subject"] = attachment_info["email_subject"]
        activity_dict["email_timestamp"] = attachment_info["email_received_time"]
        activity_dict["attachment_original_name"] = attachment_info["attachment_filename"]
        activity_dict["confidence_score"] = confidence_score
        activity_dict["email_id"] = attachment_info["email_id"]
        activity_dict["matching_signals"] = matching_signals
        
        # Create and return the email attachment activity
        return EmailAttachmentActivityData(**activity_dict)
    
    def get_matched_activities(self) -> List[EmailAttachmentActivityData]:
        """
        Get all activities matched with email attachments.
        
        Returns:
            List of email attachment activities
        """
        return self._matched_activities
    
    def get_matched_activity_by_id(self, activity_id: uuid.UUID) -> Optional[EmailAttachmentActivityData]:
        """
        Get a matched activity by its ID.
        
        Args:
            activity_id: The activity ID to look for
            
        Returns:
            The email attachment activity if found, None otherwise
        """
        for activity in self._matched_activities:
            if activity.activity_id == activity_id:
                return activity
        return None
    
    def get_matched_activities_by_email_id(self, email_id: str) -> List[EmailAttachmentActivityData]:
        """
        Get matched activities for a specific email.
        
        Args:
            email_id: Email ID to look for
            
        Returns:
            List of email attachment activities for the email
        """
        return [
            activity for activity in self._matched_activities
            if activity.email_id == email_id
        ]


def main():
    """Main function for testing the Outlook attachment tracker."""
    logging.basicConfig(level=logging.INFO)
    
    import platform
    
    # Check if running on Windows
    if platform.system() != "Windows":
        print("This component only works on Windows")
        return
    
    try:
        # Create a tracker
        tracker = OutlookAttachmentTracker(auto_start=True)
        
        print("Started Outlook attachment tracking")
        print("Press Ctrl+C to stop...")
        
        try:
            # Monitor for a while
            start_time = datetime.now()
            while (datetime.now() - start_time).total_seconds() < 300:  # 5 minutes
                time.sleep(5)
                
                # Print statistics
                email_count = len(tracker._recent_emails)
                activity_count = len(tracker._ntfs_collector._activities)
                matched_count = len(tracker._matched_activities)
                
                print(f"\rEmails: {email_count}, Activities: {activity_count}, Matches: {matched_count}", end="")
                
                if matched_count > 0 and matched_count % 5 == 0:
                    print("\nMatched activities:")
                    for activity in tracker._matched_activities[-5:]:
                        confidence = activity.confidence_score
                        confidence_str = f"{confidence:.2f}"
                        print(f"  {activity.file_name} (confidence: {confidence_str})")
                        print(f"    From: {activity.email_source}")
                        print(f"    Subject: {activity.email_subject}")
                        print(f"    Signals: {', '.join(activity.matching_signals)}")
                    print()
            
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            # Stop tracking
            tracker.stop_tracking()
            
            # Print summary
            matched_activities = tracker.get_matched_activities()
            print(f"\nMatched {len(matched_activities)} activities with email attachments:")
            
            # Group by confidence level
            confidence_levels = {
                "high": [],
                "medium": [],
                "low": []
            }
            
            for activity in matched_activities:
                if activity.confidence_score >= 0.8:
                    confidence_levels["high"].append(activity)
                elif activity.confidence_score >= 0.6:
                    confidence_levels["medium"].append(activity)
                else:
                    confidence_levels["low"].append(activity)
            
            for level, activities in confidence_levels.items():
                if activities:
                    print(f"\n{level.capitalize()} confidence matches ({len(activities)}):")
                    for activity in activities[:5]:  # Show up to 5 per level
                        print(f"  {activity.file_name} ({activity.confidence_score:.2f})")
                        print(f"    From: {activity.email_source}")
                        print(f"    Subject: {activity.email_subject}")
    
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()