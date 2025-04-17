"""
Test script for NTFS Storage Activity recorder service registration.

This script tests the registration of the NTFS Storage Activity recorder with 
the Indaleko activity service registration system. It demonstrates proper 
integration with the registration service and the collection creation process.

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
import logging
import hashlib
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set up Indaleko root
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

def main():
    """Main function to test NTFS storage activity recorder registration."""
    try:
        # Try to import NTFS storage activity recorder
        try:
            from activity.recorders.storage.ntfs.ntfs_recorder import NtfsStorageActivityRecorder
            
            # Initialize recorder with no_db to avoid actual database connection
            logger.info("Initializing NTFS Storage Activity recorder...")
            recorder = NtfsStorageActivityRecorder(
                no_db=True, 
                mock=True,  # Use mock mode for cross-platform testing
                debug=True
            )
            
            # Calculate expected collection name
            recorder_id = uuid.UUID("9b3a7e8c-6d2f-4e91-8b5a-f3c7d2e1a0b9")  # Fixed ID from the class
            provider_id_hash = hashlib.md5(str(recorder_id).encode()).hexdigest()
            expected_collection_name = f"NtfsStorageActivity_{provider_id_hash[:8]}"
            
            logger.info(f"NTFS Storage Activity recorder initialized with ID: {recorder.get_recorder_id()}")
            logger.info(f"Expected collection name: {expected_collection_name}")
            logger.info(f"Actual collection name: {recorder._collection_name}")
            
            # Verify collection name follows the expected pattern
            if recorder._collection_name == expected_collection_name:
                logger.info("✅ Collection name matches expected pattern")
            else:
                logger.warning("❌ Collection name does not match expected pattern")
                
            # Show recorder characteristics
            characteristics = recorder.get_recorder_characteristics()
            logger.info("Recorder characteristics:")
            for char in characteristics:
                logger.info(f"  - {char}")
                
            # Check collector status
            collector = recorder._ntfs_collector if hasattr(recorder, '_ntfs_collector') else None
            activities = []
            
            if collector:
                logger.info(f"Using collector with provider ID: {collector._provider_id}")
                logger.info(f"Volume GUID support: {'Enabled' if hasattr(collector, '_use_volume_guids') and collector._use_volume_guids else 'Disabled'}")
                
                # Try to generate some mock activity data
                logger.info("Generating mock activity data...")
                collector.start_monitoring()
                import time
                time.sleep(3)  # Wait for some mock data
                activities = collector.get_activities()
                logger.info(f"Generated {len(activities)} mock activities")
                
                # Stop monitoring
                collector.stop_monitoring()
            else:
                logger.warning("No NTFS collector available - skipping activity generation")
            
            # Show first activity details if available
            if activities and len(activities) > 0:
                activity = activities[0]
                logger.info("Sample activity details:")
                logger.info(f"  - Type: {activity.activity_type}")
                logger.info(f"  - File: {activity.file_name}")
                logger.info(f"  - Path: {activity.file_path}")
                logger.info(f"  - Timestamp: {activity.timestamp}")
                
                # Check if path uses volume GUID format
                if activity.file_path and "\\\\?\\Volume{" in activity.file_path:
                    logger.info("✅ Activity file path uses volume GUID format")
                else:
                    logger.info("❓ Activity file path does not use volume GUID format")
                    
                # Check timestamp timezone awareness
                if activity.timestamp.tzinfo:
                    logger.info("✅ Activity timestamp is timezone-aware")
                else:
                    logger.warning("❌ Activity timestamp is not timezone-aware")
                
        except ImportError as e:
            logger.warning(f"NTFS storage activity recorder unavailable: {e}")
            logger.warning("This module may require Windows or specific Python packages.")
            
        # Show information about StorageActivityRecorder base class
        from activity.recorders.storage.base import StorageActivityRecorder
        
        logger.info("Storage activity recorder base class information:")
        logger.info(f"  - Collection name attribute: {'_collection_name' in dir(StorageActivityRecorder)}")
        logger.info(f"  - Registration method: {'_register_with_activity_service' in dir(StorageActivityRecorder)}")
        
        # Try to import other storage activity recorders
        logger.info("Checking for other available storage activity recorders:")
        
        try:
            from activity.recorders.storage.cloud.dropbox.dropbox_recorder import DropboxStorageActivityRecorder
            logger.info(f"  - DropboxStorageActivityRecorder")
        except ImportError:
            logger.info(f"  - DropboxStorageActivityRecorder (unavailable)")
            
        try:
            from activity.recorders.storage.cloud.onedrive.onedrive_recorder import OneDriveStorageActivityRecorder
            logger.info(f"  - OneDriveStorageActivityRecorder")
        except ImportError:
            logger.info(f"  - OneDriveStorageActivityRecorder (unavailable)")
            
        try:
            from activity.recorders.storage.cloud.gdrive.gdrive_recorder import GDriveStorageActivityRecorder
            logger.info(f"  - GDriveStorageActivityRecorder")
        except ImportError:
            logger.info(f"  - GDriveStorageActivityRecorder (unavailable)")
            
        logger.info("Registration test completed successfully")
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("This module requires specific Python packages.")
    except Exception as e:
        logger.error(f"Error testing registration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
