"""
Activity Context Integration for NTFS Storage Activity Recorders.

This module provides functionality to integrate NTFS storage activity with
the Indaleko Activity Context system, allowing file system operations to be
connected to the broader user activity context.

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
from typing import Dict, Optional, Union, List, Any

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.context.service import IndalekoActivityContextService
from activity.collectors.storage.data_models.storage_activity_data_model import (
    NtfsStorageActivityData,
    StorageActivityType
)
# pylint: enable=wrong-import-position


class NtfsActivityContextIntegration:
    """
    Integrates NTFS storage activity with the Indaleko Activity Context system.
    
    This class provides functionality to associate NTFS file system activities
    with the broader user activity context, allowing for richer contextual
    understanding of file operations.
    """
    
    # Provider ID for NTFS activity context
    NTFS_CONTEXT_PROVIDER_ID = uuid.UUID("f3da4782-5c9e-49b3-a8d1-fb3792e5b2c7")
    
    def __init__(self, **kwargs):
        """
        Initialize the NTFS Activity Context Integration.
        
        Args:
            debug: Whether to enable debug logging
        """
        # Set up logging
        self._logger = logging.getLogger("NtfsActivityContextIntegration")
        self._debug = kwargs.get("debug", False)
        if self._debug:
            self._logger.setLevel(logging.DEBUG)
        
        # Get or create activity context service
        try:
            self._context_service = IndalekoActivityContextService()
            self._logger.info("Connected to Activity Context Service")
        except Exception as e:
            self._logger.error(f"Error connecting to Activity Context Service: {e}")
            self._context_service = None
            
        # Track whether context is available
        self._context_available = self._context_service is not None
        
        # Cache for activity handle to avoid repeated lookups
        self._current_activity_handle = None
        
    def is_context_available(self) -> bool:
        """Check if activity context service is available."""
        return self._context_available and self._context_service is not None
        
    def get_activity_handle(self) -> Optional[uuid.UUID]:
        """
        Get the current activity context handle.
        
        This handle can be used to associate NTFS activities with the
        broader user activity context.
        
        Returns:
            UUID handle for the current activity context, or None if
            activity context service is not available.
        """
        if not self.is_context_available():
            return None
            
        try:
            # Get the current activity handle
            self._current_activity_handle = self._context_service.get_activity_handle()
            return self._current_activity_handle
        except Exception as e:
            self._logger.error(f"Error getting activity handle: {e}")
            return None
            
    def update_activity_context(
        self,
        activity_data: Union[NtfsStorageActivityData, Dict],
        batch_update: bool = False
    ) -> bool:
        """
        Update the activity context with NTFS activity data.
        
        This method sends information about the NTFS activity to the
        Activity Context Service, allowing it to be incorporated into
        the user's activity context.
        
        Args:
            activity_data: NTFS activity data to add to context
            batch_update: Whether this is part of a batch update
            
        Returns:
            True if the context was updated, False otherwise
        """
        if not self.is_context_available():
            return False
            
        try:
            # Convert dict to proper format if needed
            if isinstance(activity_data, dict):
                # Extract or create the necessary fields
                activity_type = activity_data.get("activity_type", "unknown")
                file_path = activity_data.get("file_path", "")
                file_name = activity_data.get("file_name", "")
                timestamp = activity_data.get("timestamp", None)
                data_dict = activity_data
            else:
                # Extract fields from NtfsStorageActivityData
                activity_type = activity_data.activity_type
                file_path = activity_data.file_path
                file_name = activity_data.file_name
                timestamp = activity_data.timestamp
                data_dict = activity_data.model_dump(mode='json')
            
            # Create a reference for this activity
            activity_reference = activity_data.activity_id if hasattr(activity_data, "activity_id") else uuid.uuid4()
            
            # Create an attributes dictionary with key information
            attributes = {
                "activity_type": activity_type,
                "file_path": file_path,
                "file_name": file_name
            }
            
            # Add different attributes based on activity type
            if activity_type == StorageActivityType.CREATE:
                attributes["operation"] = "created"
            elif activity_type == StorageActivityType.MODIFY:
                attributes["operation"] = "modified"
            elif activity_type == StorageActivityType.DELETE:
                attributes["operation"] = "deleted"
            elif activity_type == StorageActivityType.RENAME:
                attributes["operation"] = "renamed"
                # Add old and new names for rename operations if available
                if "rename_type" in data_dict:
                    attributes["rename_type"] = data_dict["rename_type"]
                if "old_name" in data_dict:
                    attributes["old_name"] = data_dict["old_name"]
                if "new_name" in data_dict:
                    attributes["new_name"] = data_dict["new_name"]
            
            # Add timestamp if available
            if timestamp:
                attributes["timestamp"] = str(timestamp)
            
            # Create a summary of the activity for the context
            data_summary = f"{attributes.get('operation', 'accessed')} {file_name}"
            
            # Update the context with this NTFS activity
            updated = self._context_service.update_cursor(
                provider=self.NTFS_CONTEXT_PROVIDER_ID,
                provider_reference=activity_reference,
                provider_data=data_summary,
                provider_attributes=attributes
            )
            
            # Write to database if updated and not part of a batch
            if updated and not batch_update:
                self._context_service.write_activity_context_to_database()
                
            return updated
            
        except Exception as e:
            self._logger.error(f"Error updating activity context: {e}")
            return False
            
    def batch_update_context(self, activities: List[Union[NtfsStorageActivityData, Dict]]) -> int:
        """
        Update the activity context with multiple NTFS activities at once.
        
        Args:
            activities: List of NTFS activity data to add to context
            
        Returns:
            Number of successful updates
        """
        if not self.is_context_available() or not activities:
            return 0
            
        successful_updates = 0
        for activity in activities:
            if self.update_activity_context(activity, batch_update=True):
                successful_updates += 1
                
        # Write the aggregated updates to the database
        if successful_updates > 0:
            try:
                self._context_service.write_activity_context_to_database()
            except Exception as e:
                self._logger.error(f"Error writing batch updates to database: {e}")
                
        return successful_updates
        
    def associate_with_activity_context(
        self,
        activity_data: Union[NtfsStorageActivityData, Dict]
    ) -> Dict:
        """
        Associate NTFS activity data with the current activity context.
        
        This method adds the activity context handle to the activity data
        and updates the activity context with this NTFS activity.
        
        Args:
            activity_data: NTFS activity data to associate with context
            
        Returns:
            Updated activity data with activity context handle
        """
        if not self.is_context_available():
            return activity_data
            
        try:
            # Get dict representation if needed
            if isinstance(activity_data, NtfsStorageActivityData):
                data_dict = activity_data.model_dump(mode='json')
            else:
                data_dict = activity_data
                
            # Get current activity handle
            activity_handle = self.get_activity_handle()
            if activity_handle:
                # Add activity handle to data
                data_dict["activity_context_handle"] = str(activity_handle)
                
                # Update activity context with this activity
                self.update_activity_context(data_dict)
                
            return data_dict
            
        except Exception as e:
            self._logger.error(f"Error associating with activity context: {e}")
            if isinstance(activity_data, dict):
                return activity_data
            else:
                return activity_data.model_dump(mode='json')


def main():
    """Test functionality of NtfsActivityContextIntegration."""
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("main")
    
    # Create integration
    integration = NtfsActivityContextIntegration(debug=True)
    logger.info(f"Context available: {integration.is_context_available()}")
    
    # Get activity handle
    handle = integration.get_activity_handle()
    logger.info(f"Activity handle: {handle}")
    
    # Create test activity
    test_activity = {
        "activity_id": uuid.uuid4(),
        "activity_type": "create",
        "file_path": "C:\\Users\\Test\\Documents\\test.txt",
        "file_name": "test.txt",
        "timestamp": "2023-04-10T15:30:00Z",
    }
    
    # Associate with context
    enhanced_activity = integration.associate_with_activity_context(test_activity)
    logger.info(f"Enhanced activity: {enhanced_activity}")
    
    # Test batch update
    test_activities = [
        {
            "activity_id": uuid.uuid4(),
            "activity_type": "create",
            "file_path": "C:\\Users\\Test\\Documents\\test1.txt",
            "file_name": "test1.txt",
            "timestamp": "2023-04-10T15:35:00Z",
        },
        {
            "activity_id": uuid.uuid4(),
            "activity_type": "modify",
            "file_path": "C:\\Users\\Test\\Documents\\test2.txt",
            "file_name": "test2.txt",
            "timestamp": "2023-04-10T15:40:00Z",
        }
    ]
    
    updates = integration.batch_update_context(test_activities)
    logger.info(f"Batch updates: {updates}")
    

if __name__ == "__main__":
    main()