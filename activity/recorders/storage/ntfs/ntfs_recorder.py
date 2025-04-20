"""
NTFS Storage Activity Recorder for Indaleko.

This module provides a recorder for NTFS file system activities that
stores the activities collected by the NTFS storage activity collector.

Features:
- Records file system activity from the NTFS USN Journal
- Volume GUID support for stable path references (immune to drive letter changes)
- Timezone-aware datetime handling for ArangoDB compatibility
- Mock data generation for testing and development
- Fallback modes for error conditions
- Command-line interface for testing and monitoring

Usage (command-line):
    # Basic usage without database (volume GUIDs used by default)
    python ntfs_recorder.py --volume C: --duration 60 --no-db

    # Disable volume GUIDs if needed (not recommended)
    python ntfs_recorder.py --volume C: --no-volume-guids --duration 60

    # Mock mode and debugging
    python ntfs_recorder.py --mock --debug

    # Show all options
    python ntfs_recorder.py --help

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
import socket
import logging
import time
import hashlib
from datetime import timedelta
from typing import Dict, List, Optional, Any, Union


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.recorders.storage.base import StorageActivityRecorder
from activity.collectors.storage.ntfs.ntfs_collector \
    import NtfsStorageActivityCollector
from activity.collectors.storage.data_models.storage_activity_data_model \
    import (
        NtfsStorageActivityData,
        StorageProviderType,
        StorageActivityMetadata,
    )
from activity.collectors.storage.semantic_attributes import (
    get_semantic_attributes_for_activity,
    StorageActivityAttributes
)
from activity.characteristics import ActivityDataCharacteristics
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
# Import ServiceManager upfront to avoid late binding issues
from db.service_manager import IndalekoServiceManager
from activity.recorders.storage.ntfs.activity_context_integration import NtfsActivityContextIntegration
# pylint: enable=wrong-import-position


class NtfsStorageActivityRecorder(StorageActivityRecorder):
    """
    Recorder for NTFS storage activities.

    This recorder extends the base storage activity recorder and adds NTFS-specific
    functionality for storing and querying NTFS file system activities.
    """

    def __init__(self, **kwargs):
        """
        Initialize the NTFS storage activity recorder.

        Args:
            collector: Optional NtfsStorageActivityCollector instance to use
            collection_name: Optional custom collection name
            db_config_path: Optional path to database configuration
            register_service: Whether to register with the service manager
            auto_connect: Whether to connect to the database automatically
            debug: Whether to enable debug mode
            no_db: Whether to run without database connection
        """
        # Configure logging first so we can log initialization issues
        logging.basicConfig(level=logging.DEBUG if kwargs.get("debug", False) else logging.INFO)
        self._logger = logging.getLogger("NtfsStorageActivityRecorder")

        # Set NTFS-specific defaults
        kwargs["name"] = kwargs.get("name", "NTFS Storage Activity Recorder")
        kwargs["recorder_id"] = kwargs.get(
            "recorder_id", uuid.UUID("9b3a7e8c-6d2f-4e91-8b5a-f3c7d2e1a0b9")
        )
        kwargs["provider_type"] = StorageProviderType.LOCAL_NTFS
        kwargs["description"] = kwargs.get(
            "description", "Records storage activities from the NTFS file system"
        )
        # Collection name should be determined by registration service, not user
        # We'll use a UUID-based name pattern for NTFS activity collection
        provider_id_hash = hashlib.md5(str(kwargs["recorder_id"]).encode()).hexdigest()
        kwargs["collection_name"] = f"NtfsStorageActivity_{provider_id_hash[:8]}"

        # If no_db is specified, disable database connection
        if kwargs.get("no_db", False):
            kwargs["auto_connect"] = False
            self._logger.info("Running without database connection (no_db=True)")

        # Get or create NTFS collector
        collector = kwargs.get("collector")
        try:
            if collector is None:
                # If no collector is provided, create one with default settings
                self._logger.debug("No collector provided, creating default collector")
                try:
                    collector = NtfsStorageActivityCollector(
                        auto_start=False,  # Don't start automatically here
                        debug=kwargs.get("debug", False)
                    )
                    kwargs["collector"] = collector
                except Exception as e:
                    self._logger.error(f"Failed to create NTFS collector: {e}")
                    # Create a minimal collector that can generate mock data
                    self._logger.warning("Creating fallback collector with mock data generation")
                    collector = NtfsStorageActivityCollector(
                        auto_start=False,
                        debug=kwargs.get("debug", False),
                        volumes=[kwargs.get("volume", "C:")]
                    )
                    kwargs["collector"] = collector
            elif not isinstance(collector, NtfsStorageActivityCollector):
                raise ValueError("collector must be an instance of NtfsStorageActivityCollector")
        except Exception as e:
            self._logger.error(f"Error during collector setup: {e}")
            if not kwargs.get("no_db", False):
                raise  # Only re-raise if we're supposed to connect to the database

        # Update registration service import
        # Note: We already imported IndalekoServiceManager at the top of this file
        if kwargs.get("register_service", True):
            try:
                # Ensure we can access the class
                if 'IndalekoServiceManager' not in globals():
                    self._logger.warning("IndalekoServiceManager not available in globals - will not register with service")
                    kwargs["register_service"] = False
                else:
                    # We use the already imported class
                    kwargs["_service_manager"] = IndalekoServiceManager
            except Exception as e:
                self._logger.warning(f"Error setting up service manager: {e} - will not register with service")
                kwargs["register_service"] = False

        # Call parent initializer
        try:
            super().__init__(**kwargs)
        except Exception as e:
            self._logger.error(f"Error during parent initialization: {e}")
            if not kwargs.get("no_db", False):
                raise  # Only re-raise if we're supposed to connect to the database

        # NTFS-specific setup
        self._ntfs_collector = collector

        # Initialize activity context integration
        self._activity_context_integration = NtfsActivityContextIntegration(
            debug=kwargs.get("debug", False)
        )
        self._logger.info(f"Activity context integration available: {self._activity_context_integration.is_context_available()}")

        # Add NTFS-specific metadata
        try:
            volumes = getattr(self._ntfs_collector, "_volumes", ["C:"])
            self._metadata = StorageActivityMetadata(
                provider_type=StorageProviderType.LOCAL_NTFS,
                provider_name=self._name,
                source_machine=socket.gethostname(),
                storage_location=",".join(volumes),
                # Note: No provenance field is needed as it's now optional
            )
        except Exception as e:
            self._logger.error(f"Error setting up metadata: {e}")
            # Create minimal metadata
            self._metadata = StorageActivityMetadata(
                provider_type=StorageProviderType.LOCAL_NTFS,
                provider_name=self._name,
                source_machine=socket.gethostname()
            )

    def store_activities(self, activities: List[NtfsStorageActivityData]) -> List[uuid.UUID]:
        """
        Store multiple NTFS activities in the database.

        Args:
            activities: List of NTFS activity data to store

        Returns:
            List of UUIDs of the stored activities
        """
        if not activities:
            return []
            
        activity_ids = []
        
        # Batch update activity context if available
        if (hasattr(self, "_activity_context_integration") and 
            self._activity_context_integration.is_context_available()):
            try:
                self._logger.info(f"Batch updating activity context with {len(activities)} activities")
                updates = self._activity_context_integration.batch_update_context(activities)
                self._logger.debug(f"Successfully updated {updates} activities in context")
            except Exception as e:
                self._logger.error(f"Error batch updating activity context: {e}")
        
        # Store each activity in the database
        for activity in activities:
            try:
                activity_id = self.store_activity(activity)
                activity_ids.append(activity_id)
            except Exception as e:
                self._logger.error(f"Error storing activity: {e}")
                
        return activity_ids
        
    def collect_and_store_activities(self, start_monitoring: bool = True) -> List[uuid.UUID]:
        """
        Collect and store NTFS activities in one operation.

        Args:
            start_monitoring: Whether to start monitoring if not already active

        Returns:
            List of activity UUIDs that were stored
        """
        # Start monitoring if requested and not already active
        if start_monitoring and not self._ntfs_collector._active:
            self._logger.info("Starting NTFS activity monitoring")
            self._ntfs_collector.start_monitoring()
        elif self._ntfs_collector._active:
            self._logger.info("NTFS activity monitoring already active")
        else:
            self._logger.warning("Not starting NTFS monitoring as requested (start_monitoring=False)")

        # Get current activities from the collector
        activities = self._ntfs_collector.get_activities()
        self._logger.info(f"Retrieved {len(activities)} activities from collector")
        
        # Print out some activity details for debugging
        if len(activities) > 0:
            self._logger.info("Sample of activities retrieved:")
            for i, activity in enumerate(activities[:min(5, len(activities))]):
                self._logger.info(f"  Activity {i+1}: {activity.activity_type} - {activity.file_name}")
                if hasattr(activity, 'file_path'):
                    self._logger.info(f"    Path: {activity.file_path}")
                if hasattr(activity, 'timestamp'):
                    self._logger.info(f"    Time: {activity.timestamp}")
        else:
            self._logger.warning("No activities retrieved from collector")
            
            # Try to diagnose why no activities are present
            self._logger.info("Diagnostic information:")
            self._logger.info(f"  Collector active: {self._ntfs_collector._active}")
            self._logger.info(f"  Monitored volumes: {self._ntfs_collector._volumes}")
            self._logger.info(f"  Using mock data: {self._ntfs_collector._use_mock}")
            
            # Check if we're capturing in real-time now by adding a file
            try:
                if len(self._ntfs_collector._volumes) > 0:
                    volume = self._ntfs_collector._volumes[0]
                    test_dir = os.path.join(volume, "Indaleko_Test")
                    if not os.path.exists(test_dir):
                        os.makedirs(test_dir, exist_ok=True)
                    test_file = os.path.join(test_dir, f"recorder_test_{int(time.time())}.txt")
                    
                    self._logger.info(f"Creating test file {test_file} to trigger USN activity")
                    with open(test_file, 'w') as f:
                        f.write(f"Recorder test file - {datetime.now()}")
                    
                    # Wait briefly for the collector to process
                    time.sleep(1)
                    
                    # Check again for activities
                    new_activities = self._ntfs_collector.get_activities()
                    if len(new_activities) > len(activities):
                        self._logger.info(f"After creating test file, found {len(new_activities)} activities")
                        activities = new_activities
                    else:
                        self._logger.warning("Still no new activities after creating test file")
            except Exception as e:
                self._logger.warning(f"Error during diagnosis: {e}")

        # Store activities and return their IDs
        activity_ids = self.store_activities(activities)
        self._logger.info(f"Stored {len(activity_ids)} activities in the database")
        return activity_ids

    def stop_monitoring(self) -> None:
        """Stop monitoring NTFS activities."""
        if self._ntfs_collector._active:
            self._ntfs_collector.stop_monitoring()

    def get_activities_by_volume(
        self,
        volume: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get activities for a specific volume.

        Args:
            volume: The volume to get activities for (e.g., "C:")
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of activity documents for the volume
        """
        # Query the database
        query = """
            FOR doc IN @@collection
            FILTER doc.Record.Data.volume_name == @volume
            SORT doc.Record.Data.timestamp DESC
            LIMIT @offset, @limit
            RETURN doc
        """

        # Execute query
        cursor = self._db.db.aql.execute(
            query,
            bind_vars={
                "@collection": self._collection_name,
                "volume": volume,
                "offset": offset,
                "limit": limit
            }
        )

        # Return results
        return [doc for doc in cursor]

    def get_activities_by_file_reference(
        self,
        file_reference: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get activities for a specific file reference number.

        Args:
            file_reference: The NTFS file reference number to get activities for
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of activity documents for the file reference
        """
        # Query the database
        query = """
            FOR doc IN @@collection
            FILTER doc.Record.Data.file_reference_number == @file_reference
            SORT doc.Record.Data.timestamp DESC
            LIMIT @offset, @limit
            RETURN doc
        """

        # Execute query
        cursor = self._db.db.aql.execute(
            query,
            bind_vars={
                "@collection": self._collection_name,
                "file_reference": file_reference,
                "offset": offset,
                "limit": limit
            }
        )

        # Return results
        return [doc for doc in cursor]

    def get_activities_by_reason_flags(
        self,
        reason_flags: int,
        match_all: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get activities matching specific USN Journal reason flags.

        Args:
            reason_flags: The reason flags to match
            match_all: If True, all flags must match; if False, any flag match is sufficient
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of activity documents matching the reason flags
        """
        # Determine filter expression based on match_all
        if match_all:
            filter_expr = "doc.Record.Data.reason_flags & @reason_flags == @reason_flags"
        else:
            filter_expr = "doc.Record.Data.reason_flags & @reason_flags > 0"

        # Query the database
        query = f"""
            FOR doc IN @@collection
            FILTER {filter_expr}
            SORT doc.Record.Data.timestamp DESC
            LIMIT @offset, @limit
            RETURN doc
        """

        # Execute query
        cursor = self._db.db.aql.execute(
            query,
            bind_vars={
                "@collection": self._collection_name,
                "reason_flags": reason_flags,
                "offset": offset,
                "limit": limit
            }
        )

        # Return results
        return [doc for doc in cursor]

    def get_ntfs_specific_statistics(self) -> Dict[str, Any]:
        """
        Get NTFS-specific statistics about the activities.

        Returns:
            Dictionary of NTFS-specific statistics
        """
        # Get basic statistics from parent class
        stats = self.get_activity_statistics()

        # Add NTFS-specific statistics

        # Query for count by volume
        volume_query = """
            FOR doc IN @@collection
            COLLECT volume = doc.Record.Data.volume_name WITH COUNT INTO count
            RETURN { volume, count }
        """

        # Query for count by reason flags (most common flags)
        reason_query = """
            FOR doc IN @@collection
            COLLECT reason = doc.Record.Data.reason_flags WITH COUNT INTO count
            SORT count DESC
            LIMIT 10
            RETURN { reason, count }
        """

        # Execute NTFS-specific queries
        volume_cursor = self._db.db.aql.execute(
            volume_query,
            bind_vars={"@collection": self._collection_name}
        )
        reason_cursor = self._db.db.aql.execute(
            reason_query,
            bind_vars={"@collection": self._collection_name}
        )

        # Add to statistics
        stats["by_volume"] = {item["volume"]: item["count"] for item in volume_cursor}
        stats["by_reason_flags"] = {str(item["reason"]): item["count"] for item in reason_cursor}

        # Add information about monitored volumes
        stats["monitored_volumes"] = self._ntfs_collector._volumes
        stats["monitoring_active"] = self._ntfs_collector._active

        return stats

    def _build_ntfs_activity_document(
        self,
        activity_data: NtfsStorageActivityData,
        semantic_attributes: Optional[List[IndalekoSemanticAttributeDataModel]] = None
    ) -> Dict:
        """
        Build a document for storing an NTFS activity in the database.

        Args:
            activity_data: The NTFS activity data to store
            semantic_attributes: Optional list of semantic attributes

        Returns:
            Document for the database
        """
        # Ensure we have semantic attributes specific to NTFS
        if semantic_attributes is None:
            # Get common storage activity attributes
            semantic_attributes = get_semantic_attributes_for_activity(
                activity_data.model_dump()
            )

            # Add NTFS-specific attributes if needed
            ntfs_attribute = IndalekoSemanticAttributeDataModel(
                Identifier=str(StorageActivityAttributes.STORAGE_NTFS.value),
                Label="NTFS Storage Activity",
                Description="Storage activity from NTFS file system"
            )

            # Check if NTFS attribute is already present
            ntfs_attribute_present = False
            for attr in semantic_attributes:
                if attr.Identifier == str(StorageActivityAttributes.STORAGE_NTFS.value):
                    ntfs_attribute_present = True
                    break

            if not ntfs_attribute_present:
                semantic_attributes.append(ntfs_attribute)

        # Use the parent class method to build the document
        return super().build_activity_document(activity_data, semantic_attributes)

    def store_activity(
        self,
        activity_data: Union[NtfsStorageActivityData, Dict]
    ) -> uuid.UUID:
        """
        Store an NTFS activity in the database.

        Args:
            activity_data: NTFS activity data to store

        Returns:
            UUID of the stored activity
        """
        # Convert dict to NtfsStorageActivityData if needed
        if isinstance(activity_data, dict):
            # Create NtfsStorageActivityData from dict
            activity_data = NtfsStorageActivityData(**activity_data)

        # Integrate with activity context if available
        if hasattr(self, "_activity_context_integration") and self._activity_context_integration.is_context_available():
            # Associate with current activity context
            try:
                self._logger.debug(f"Associating activity {activity_data.activity_id} with activity context")
                enhanced_data = self._activity_context_integration.associate_with_activity_context(activity_data)
                
                # If we get a dictionary back, convert it to NtfsStorageActivityData
                if isinstance(enhanced_data, dict):
                    # Preserve original activity_id and create new object with context
                    original_id = activity_data.activity_id
                    activity_data = NtfsStorageActivityData(**enhanced_data)
                    activity_data.activity_id = original_id
            except Exception as e:
                self._logger.error(f"Error integrating with activity context: {e}")
                # Continue with original activity data

        # Build document with NTFS-specific attributes
        document = self._build_ntfs_activity_document(activity_data)

        # Store in database
        result = self._collection.add_document(document)

        return activity_data.activity_id

    # Override parent class methods as needed

    def get_recorder_characteristics(self) -> List[ActivityDataCharacteristics]:
        """Get the characteristics of this recorder."""
        # Check what characteristics are available
        result = [
            ActivityDataCharacteristics.ACTIVITY_DATA_SYSTEM_ACTIVITY,
            ActivityDataCharacteristics.ACTIVITY_DATA_FILE_ACTIVITY
        ]

        # Add Windows-specific characteristic if available
        try:
            result.append(ActivityDataCharacteristics.ACTIVITY_DATA_WINDOWS_SPECIFIC)
        except AttributeError:
            # Windows-specific characteristic not defined, possibly using an older version
            self._logger.warning("ACTIVITY_DATA_WINDOWS_SPECIFIC characteristic not available")

        return result

    def get_json_schema(self) -> dict:
        """
        Get the JSON schema for this recorder's data.

        Returns:
            The JSON schema
        """
        return NtfsStorageActivityData.model_json_schema()

    def cache_duration(self) -> timedelta:
        """
        Get the cache duration for this recorder's data.

        NTFS file operations are very frequent, so we use a shorter cache duration.

        Returns:
            The cache duration
        """
        return timedelta(minutes=30)

# Command-line interface
if __name__ == "__main__":
    import argparse
    import sys

    # Configure command-line interface
    parser = argparse.ArgumentParser(
        description="NTFS Storage Activity Recorder",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Add general arguments
    parser.add_argument("--volume", type=str, default="C:",
                        help="Volume to monitor (e.g., 'C:', 'D:')")
    parser.add_argument("--duration", type=int, default=30,
                        help="Monitoring duration in seconds (0 = forever)")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    # Collection is determined by the registration service, not user-configurable
    # Collection parameter removed as it should be managed by the registration system

    # Add mode-related arguments
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--no-db", action="store_true",
                           help="Run without database connection")
    mode_group.add_argument("--db-config", type=str, default=None,
                           help="Path to database configuration file")

    # Add monitoring options
    parser.add_argument("--interval", type=float, default=1.0,
                        help="Monitoring interval in seconds")
    parser.add_argument("--include-close", action="store_true",
                        help="Include file close events")

    # Add output options
    parser.add_argument("--stats-only", action="store_true",
                        help="Only show statistics, not individual activities")
    parser.add_argument("--mock", action="store_true",
                        help="Use mock data even if real monitoring is available")
    parser.add_argument("--limit", type=int, default=5,
                        help="Maximum number of activities to display")
    parser.add_argument("--no-volume-guids", action="store_true",
                        help="Use drive letters instead of volume GUIDs for file paths (not recommended)")

    # Parse arguments
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("NtfsStorageActivityRecorder")

    # Display configuration
    print("=== NTFS Storage Activity Recorder ===")
    print(f"- Volume: {args.volume}")
    print(f"- Duration: {args.duration if args.duration > 0 else 'Forever'} seconds")
    print(f"- Debug mode: {'Enabled' if args.debug else 'Disabled'}")
    print(f"- Database: {'Disabled' if args.no_db else 'Enabled'}")
    if args.db_config:
        print(f"- DB Config: {args.db_config}")
    print(f"- Monitor interval: {args.interval} seconds")
    print(f"- Include close events: {'Yes' if args.include_close else 'No'}")
    print(f"- Mock data: {'Yes' if args.mock else 'No'}")
    print(f"- Use volume GUIDs: {'No' if args.no_volume_guids else 'Yes (default)'}")
    print("")

    try:
        # Create collector with settings from arguments
        collector_args = {
            "volumes": [args.volume],
            "auto_start": False,  # We'll start it manually
            "debug": args.debug,
            "monitor_interval": args.interval,
            "include_close_events": args.include_close,
            "use_volume_guids": not args.no_volume_guids  # Volume GUIDs are used by default
        }

        # If mock mode is forced, use special arguments
        if args.mock:
            collector_args["mock"] = True

        # Create the collector
        try:
            collector = NtfsStorageActivityCollector(**collector_args)
            print(f"Created NTFS Storage Activity Collector for volume {args.volume}")
        except Exception as e:
            logger.error(f"Failed to create collector: {e}")
            print(f"Error creating collector: {e}")
            print("Creating fallback collector with mock data...")
            collector_args["mock"] = True
            collector = NtfsStorageActivityCollector(**collector_args)

        # Start monitoring
        collector.start_monitoring()
        print("Started monitoring NTFS activities...")

        # Create recorder if using database
        recorder = None
        if not args.no_db:
            try:
                recorder = NtfsStorageActivityRecorder(
                    collector=collector,
                    debug=args.debug,
                    db_config_path=args.db_config
                    # Collection name is determined by registration service
                )
                print("Connected to database, using collection managed by registration service")
            except Exception as e:
                logger.error(f"Failed to create recorder: {e}")
                print(f"Error creating recorder: {e}")
                print("Running in collection-only mode (no database)")

        # Monitor for the specified duration
        if args.duration > 0:
            print(f"Monitoring for {args.duration} seconds...")
            time.sleep(args.duration)
        else:
            print("Press Ctrl+C to stop monitoring...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nMonitoring stopped by user")

        # Get collected activities
        activities = collector.get_activities()
        print(f"\nCollected {len(activities)} activities")

        # Display activities if not in stats-only mode
        if not args.stats_only and activities:
            display_limit = min(args.limit, len(activities))
            print(f"\nShowing {display_limit} most recent activities:")
            for i, activity in enumerate(activities[:display_limit]):
                print(f"Activity {i+1}:")
                print(f"  Type: {activity.activity_type}")
                print(f"  File: {activity.file_name}")
                print(f"  Path: {activity.file_path}")
                print(f"  Time: {activity.timestamp}")
                print("")

            if len(activities) > display_limit:
                print(f"... and {len(activities) - display_limit} more")

        # Store activities if using database
        if recorder:
            try:
                # Store the activities
                activity_ids = recorder.store_activities(activities)
                print(f"\nStored {len(activity_ids)} activities in the database")

                # Get and display statistics
                try:
                    stats = recorder.get_ntfs_specific_statistics()
                    print("\nActivity Statistics:")

                    # Format the statistics for better display
                    if "total_count" in stats:
                        print(f"  Total activities: {stats['total_count']}")

                    if "by_type" in stats:
                        print("  Activities by type:")
                        for activity_type, count in stats["by_type"].items():
                            print(f"    {activity_type}: {count}")

                    if "by_volume" in stats:
                        print("  Activities by volume:")
                        for volume, count in stats["by_volume"].items():
                            print(f"    {volume}: {count}")

                    if "monitoring_active" in stats:
                        print(f"  Monitoring active: {stats['monitoring_active']}")

                except Exception as e:
                    logger.error(f"Failed to get statistics: {e}")
                    print(f"Error getting statistics: {e}")
            except Exception as e:
                logger.error(f"Failed to store activities: {e}")
                print(f"Error storing activities: {e}")

    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        print(f"Unhandled error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Clean up
        try:
            if 'collector' in locals() and collector:
                collector.stop_monitoring()
                print("Monitoring stopped")
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}")
            print(f"Error during cleanup: {e}")

    print("\nDone.")
