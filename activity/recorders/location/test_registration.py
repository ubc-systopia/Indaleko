"""
Test script for Location recorder service registration.

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
    """Main function to test location recorder registration."""
    try:
        # Try to import Windows-specific location recorder
        try:
            from activity.recorders.location.windows_gps_location import WindowsGPSLocationRecorder
            
            # Initialize recorder
            logger.info("Initializing Windows GPS Location recorder...")
            recorder = WindowsGPSLocationRecorder()
            
            logger.info(f"Windows GPS Location recorder initialized with ID: {recorder.get_recorder_id()}")
            logger.info(f"Collection name: {recorder.collection.name}")
        except ImportError as e:
            logger.warning(f"Windows GPS location recorder unavailable: {e}")
            
        # Try to import the base location data recorder
        from activity.recorders.location.location_data_recorder import BaseLocationDataRecorder
        
        # Show available location recorders
        logger.info("Available location recorder classes:")
        logger.info(f" - BaseLocationDataRecorder")
        
        # Check if IP location recorder is available
        try:
            from activity.recorders.location.ip_location_recorder import IPLocationRecorder
            logger.info(f" - IPLocationRecorder")
        except ImportError:
            logger.info(f" - IPLocationRecorder (unavailable)")
            
        # Check if WiFi location recorder is available
        try:
            from activity.recorders.location.wifi_location_recorder import WiFiLocationRecorder
            logger.info(f" - WiFiLocationRecorder")
        except ImportError:
            logger.info(f" - WiFiLocationRecorder (unavailable)")
            
        # Check if Tile location recorder is available
        try:
            from activity.recorders.location.tile_location_recorder import TileLocationRecorder
            logger.info(f" - TileLocationRecorder")
        except ImportError:
            logger.info(f" - TileLocationRecorder (unavailable)")
            
        logger.info("Registration test completed successfully")
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("This module requires specific Python packages.")
    except Exception as e:
        logger.error(f"Error testing registration: {e}")

if __name__ == "__main__":
    main()