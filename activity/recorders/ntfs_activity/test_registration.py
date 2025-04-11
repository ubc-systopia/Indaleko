"""
Test script for NTFS activity recorder service registration.

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
    """Main function to test NTFS activity recorder registration."""
    try:
        # Import here to avoid import errors when running on non-Windows platforms
        from activity.recorders.ntfs_activity.ntfs_activity_recorder import NtfsActivityRecorder
        
        # Initialize recorder without auto-connecting to the database
        logger.info("Initializing NTFS activity recorder...")
        recorder = NtfsActivityRecorder(
            auto_connect=False,  # Don't connect to the database
            register_service=False  # Don't register service yet
        )
        
        # Test registration
        logger.info("Testing registration...")
        recorder._register_with_service_manager()
        
        logger.info("Registration completed successfully")
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("This module requires Windows and specific Python packages.")
    except Exception as e:
        logger.error(f"Error testing registration: {e}")

if __name__ == "__main__":
    main()