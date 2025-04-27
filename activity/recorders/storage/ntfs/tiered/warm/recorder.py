#!/usr/bin/env python
"""
NTFS Warm Tier Recorder for Indaleko.

This module implements the "Warm" tier of the NTFS activity recorder,
focusing on efficient, aggregate storage of file system activities
after they transition from the hot tier.

Features:
- Efficient storage of older file system activities
- Aggregation and compression of similar activities
- Automatic acquisition of data from hot tier before expiration
- Importance-based retention policies
- Configurable retention duration and compression levels
- Support for both direct collection and hot tier transition

The warm tier is part of Indaleko's tiered memory architecture modeled after
human memory systems, providing a balance between detail preservation and
storage efficiency.

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

import hashlib
import logging
import os
import socket
import sys
import uuid

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any


# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.storage.data_models.storage_activity_data_model import (
    NtfsStorageActivityData,
    StorageActivityMetadata,
    StorageActivityType,
    StorageProviderType,
)
from activity.collectors.storage.semantic_attributes import (
    StorageActivityAttributes,
    get_semantic_attributes_for_activity,
)

# pylint: disable=wrong-import-position
from activity.recorders.storage.base import StorageActivityRecorder
from activity.recorders.storage.ntfs.tiered.importance_scorer import ImportanceScorer
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel


# Import ServiceManager upfront to avoid late binding issues


# pylint: enable=wrong-import-position


class NtfsWarmTierRecorder(StorageActivityRecorder):
    """
    Warm tier recorder for NTFS storage activities.

    Handles the efficient storage of older NTFS file system activities
    through aggregation, summarization, and importance-based retention.
    """

    # Default settings
    DEFAULT_TTL_DAYS = 30  # Default retention in warm tier
    DEFAULT_COLLECTION_NAME = "ntfs_activities_warm"
    DEFAULT_RECORDER_ID = uuid.UUID("a6b23c79-5f82-4970-b8e1-c42c78f9a5d3")
    HOT_TIER_COLLECTION_SUFFIX = "_hot_"  # Used to identify hot tier collections

    # Importance thresholds
    DEFAULT_IMPORTANCE_THRESHOLDS = {
        "high": 0.7,  # Important events stored nearly in full
        "medium": 0.4,  # Medium importance events get moderate aggregation
        "low": 0.2,  # Low importance events get significant aggregation
    }

    def __init__(self, **kwargs):
        """
        Initialize the warm tier recorder.

        Args:
            ttl_days: Number of days to keep data in warm tier (default: 30)
            collection_name: Name of the warm tier collection
            hot_tier_collection_name: Name of the hot tier to pull data from
            db_config_path: Path to database configuration
            debug: Whether to enable debug logging
            no_db: Whether to run without database connection
            transition_enabled: Whether to enable automated transition
            importance_thresholds: Custom importance thresholds
            aggregation_window: Time window for activity aggregation (hours)
        """
        # Configure logging first
        logging.basicConfig(level=logging.DEBUG if kwargs.get("debug", False) else logging.INFO)
        self._logger = logging.getLogger("NtfsWarmTierRecorder")

        # Initialize instance variables
        self._ttl_days = kwargs.get("ttl_days", self.DEFAULT_TTL_DAYS)
        self._collection_name = kwargs.get("collection_name", self.DEFAULT_COLLECTION_NAME)
        self._entity_collection_name = kwargs.get("entity_collection_name", "file_entities")
        self._transition_enabled = kwargs.get("transition_enabled", False)
        self._aggregation_window = kwargs.get("aggregation_window", 6)  # 6 hours

        # Configure importance thresholds
        self._importance_thresholds = kwargs.get(
            "importance_thresholds",
            self.DEFAULT_IMPORTANCE_THRESHOLDS.copy(),
        )

        # Initialize importance scorer
        self._scorer = ImportanceScorer(debug=kwargs.get("debug", False))

        # Set recorder-specific defaults
        kwargs["name"] = kwargs.get("name", "NTFS Warm Tier Recorder")
        kwargs["recorder_id"] = kwargs.get("recorder_id", self.DEFAULT_RECORDER_ID)
        kwargs["provider_type"] = StorageProviderType.LOCAL_NTFS
        kwargs["description"] = kwargs.get(
            "description",
            "Records aged NTFS file system activities in the warm tier",
        )

        # Use consistent collection name based on recorder ID to avoid conflicts
        if "collection_name" not in kwargs:
            recorder_id_hash = hashlib.md5(str(kwargs["recorder_id"]).encode()).hexdigest()
            kwargs["collection_name"] = f"{self._collection_name}_{recorder_id_hash[:8]}"

        # If no_db is specified, disable database connection
        if kwargs.get("no_db", False):
            kwargs["auto_connect"] = False
            self._logger.info("Running without database connection (no_db=True)")

        # Call parent initializer with updated kwargs
        try:
            super().__init__(**kwargs)
        except Exception as e:
            self._logger.error(f"Error during parent initialization: {e}")
            if not kwargs.get("no_db", False):
                raise  # Only re-raise if we're supposed to connect to the database

        # Add NTFS-specific metadata
        try:
            self._metadata = StorageActivityMetadata(
                provider_type=StorageProviderType.LOCAL_NTFS,
                provider_name=self._name,
                source_machine=socket.gethostname(),
                storage_location="warm_tier",
            )
        except Exception as e:
            self._logger.error(f"Error setting up metadata: {e}")
            # Create minimal metadata
            self._metadata = StorageActivityMetadata(
                provider_type=StorageProviderType.LOCAL_NTFS,
                provider_name=self._name,
                source_machine=socket.gethostname(),
            )

        # Set up collections and indices if connected to database
        if hasattr(self, "_db") and self._db:
            self._setup_collections()
            self._setup_indices()

        # Store the hot tier collection name for transitions
        self._hot_tier_collection_name = kwargs.get("hot_tier_collection_name", None)

        # Register with activity registration service if enabled
        if self._register_enabled and not kwargs.get("no_db", False):
            self._register_with_service_manager()

    def _register_with_service_manager(self) -> None:
        """Register with the activity service manager."""
        try:
            # Get semantic attributes for storage activity
            from activity.collectors.storage.semantic_attributes import (
                get_storage_activity_semantic_attributes,
            )

            attributes = get_storage_activity_semantic_attributes()
            semantic_attribute_ids = [str(attr.Identifier) for attr in attributes]

            # Import required components
            from activity.recorders.registration_service import (
                IndalekoActivityDataRegistrationService,
            )
            from data_models.record import IndalekoRecordDataModel
            from data_models.source_identifier import IndalekoSourceIdentifierDataModel

            # Create source identifier for the record
            source_identifier = IndalekoSourceIdentifierDataModel(
                SourceID=str(self._recorder_id),
                SourceIdName=self._name,
                SourceDescription=self._description,
                SourceVersion=self._version,
            )

            # Create record data model
            record = IndalekoRecordDataModel(
                SourceId=source_identifier,
                Timestamp=datetime.now(UTC),
                Data={},
            )

            # Add warm tier specific tag to identify this as a tiered recorder
            warm_tier_tag = "warm_tier"

            # Prepare registration data
            registration_kwargs = {
                "Identifier": str(self._recorder_id),
                "Name": self._name,
                "Description": self._description,
                "Version": self._version,
                "Record": record,
                "DataProvider": f"{self._provider_type} Warm Tier Storage Activity",
                "DataProviderType": "Activity",
                "DataProviderSubType": "Storage",
                "DataProviderURL": "",
                "DataProviderCollectionName": self._collection_name,
                "DataFormat": "JSON",
                "DataFormatVersion": "1.0",
                "DataAccess": "Read",
                "DataAccessURL": "",
                "CreateCollection": True,
                "SourceIdentifiers": [
                    str(StorageActivityAttributes.STORAGE_ACTIVITY.value),
                    str(StorageActivityAttributes.STORAGE_NTFS.value),
                ],
                "SchemaIdentifiers": semantic_attribute_ids,
                "Tags": ["storage", "activity", "ntfs", warm_tier_tag, "tiered"],
            }

            # Register with service manager
            try:
                self._logger.info(
                    f"Registering with activity registration service: {self._recorder_id}"
                )
                service = IndalekoActivityDataRegistrationService()
                service.register_provider(**registration_kwargs)
                self._logger.info(
                    f"Successfully registered with service manager: {self._recorder_id}"
                )
            except Exception as e:
                self._logger.error(f"Error registering with service manager: {e}")
                import traceback

                self._logger.debug(f"Registration error details: {traceback.format_exc()}")

        except Exception as e:
            self._logger.error(f"Error creating registration data: {e}")
            import traceback

            self._logger.debug(f"Registration data error details: {traceback.format_exc()}")

    def _setup_collections(self):
        """Set up required collections for the warm tier recorder."""
        try:
            # Activities collection should already be created by parent class

            # Ensure entity collection exists using IndalekoCollections centralized mechanism
            try:
                from db.i_collections import IndalekoCollections

                self._logger.info(f"Getting entity collection: {self._entity_collection_name}")
                entity_collection = IndalekoCollections.get_collection(self._entity_collection_name)
                self._logger.info(f"Retrieved entity collection: {entity_collection.name}")
            except Exception as entity_error:
                self._logger.info(f"Error getting entity collection: {entity_error}")
            finally:
                self._logger.info(
                    f"Continuing with entity collection: {self._entity_collection_name}"
                )

        except Exception as e:
            self._logger.error(f"Error setting up collections: {e}")
            if not getattr(self, "_no_db", False):
                raise

    def _setup_indices(self):
        """Set up required indices for the warm tier recorder."""
        try:
            # Set up TTL index on warm tier collection
            self._setup_ttl_index()

            # Set up other indices for query performance
            self._logger.info("Setting up additional indices...")

            # Index on timestamp for time-based queries
            self._collection.add_hash_index(fields=["Record.Data.timestamp"], unique=False)

            # Index on entity_id for entity-based queries
            self._collection.add_hash_index(fields=["Record.Data.entity_id"], unique=False)

            # Index on activity_type for type-based queries
            self._collection.add_hash_index(fields=["Record.Data.activity_type"], unique=False)

            # Index on importance_score for tier management
            self._collection.add_hash_index(fields=["Record.Data.importance_score"], unique=False)

            # Index on is_aggregated for filtering
            self._collection.add_hash_index(fields=["Record.Data.is_aggregated"], unique=False)

            # Set up entity collection indices
            entity_collection = self._db.get_collection(self._entity_collection_name)

            # Index on file_reference_number for FRN to entity mapping
            entity_collection.add_hash_index(fields=["file_reference_number"], unique=False)

            # Index on file_path for path-based lookups
            entity_collection.add_hash_index(fields=["file_path"], unique=False)

            self._logger.info("Finished setting up indices")

        except Exception as e:
            self._logger.error(f"Error setting up indices: {e}")
            if not getattr(self, "_no_db", False):
                raise

    def _setup_ttl_index(self):
        """Set up TTL index for automatic expiration of warm tier data."""
        try:
            # Calculate TTL in seconds
            ttl_seconds = self._ttl_days * 24 * 60 * 60

            self._logger.info(
                f"Setting up TTL index with {self._ttl_days} day expiration ({ttl_seconds} seconds)"
            )

            # Check if TTL index already exists
            existing_indices = self._collection.indexes()
            for index in existing_indices:
                if index.get("type") == "ttl":
                    self._logger.info(f"TTL index already exists: {index}")
                    return

            # Create TTL index on ttl_timestamp field
            self._collection.add_ttl_index(
                fields=["Record.Data.ttl_timestamp"],
                expireAfter=ttl_seconds,
            )

            self._logger.info(f"Created TTL index with {self._ttl_days} day expiration")

        except Exception as e:
            self._logger.error(f"Error setting up TTL index: {e}")
            self._logger.error(
                "This may be due to an unsupported ArangoDB version or configuration"
            )
            self._logger.warning(
                "Warm tier data will not automatically expire - manual cleanup will be needed"
            )

    def find_hot_tier_activities_to_transition(
        self,
        age_threshold_hours: int = 12,
        batch_size: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Find activities in the hot tier that are ready for transition to the warm tier.

        Args:
            age_threshold_hours: Age in hours at which activities should transition
            batch_size: Maximum number of activities to pull at once

        Returns:
            List of hot tier activities ready for transition
        """
        # Skip if not connected to database
        if not hasattr(self, "_db") or self._db is None:
            self._logger.warning("Cannot find hot tier activities: not connected to database")
            return []

        # Hot tier collection needed
        if not self._hot_tier_collection_name:
            # Try to find a hot tier collection
            hot_tier_collections = self._find_hot_tier_collections()
            if not hot_tier_collections:
                self._logger.warning(
                    "Cannot find hot tier activities: no hot tier collection found"
                )
                return []

            # Use the first hot tier collection
            self._hot_tier_collection_name = hot_tier_collections[0]

        # Calculate the age threshold timestamp
        threshold_time = datetime.now(UTC) - timedelta(hours=age_threshold_hours)
        threshold_str = threshold_time.isoformat()

        try:
            # Query for activities older than the threshold that haven't been transitioned
            query = """
                FOR doc IN @@collection
                FILTER doc.Record.Data.timestamp <= @threshold
                FILTER doc.Record.Data.transitioned != true
                SORT doc.Record.Data.timestamp ASC
                LIMIT @batch_size
                RETURN doc
            """

            cursor = self._db._arangodb.aql.execute(
                query,
                bind_vars={
                    "@collection": self._hot_tier_collection_name,
                    "threshold": threshold_str,
                    "batch_size": batch_size,
                },
            )

            activities = [doc for doc in cursor]
            self._logger.info(
                f"Found {len(activities)} activities in hot tier ready for transition"
            )
            return activities

        except Exception as e:
            self._logger.error(f"Error finding hot tier activities: {e}")
            return []

    def _find_hot_tier_collections(self) -> list[str]:
        """
        Find hot tier collections in the database.

        Returns:
            List of hot tier collection names
        """
        hot_tier_collections = []

        # Skip if not connected to database
        if not hasattr(self, "_db") or self._db is None:
            return hot_tier_collections

        try:
            # Get all collections
            all_collections = self._db._arangodb.collections()

            # Filter for hot tier collections
            for collection in all_collections:
                name = collection.get("name", "")
                if self.HOT_TIER_COLLECTION_SUFFIX in name.lower():
                    hot_tier_collections.append(name)

            self._logger.info(
                f"Found {len(hot_tier_collections)} hot tier collections: {hot_tier_collections}"
            )
            return hot_tier_collections

        except Exception as e:
            self._logger.error(f"Error finding hot tier collections: {e}")
            return hot_tier_collections

    def mark_hot_tier_activities_transitioned(self, activities: list[dict[str, Any]]) -> int:
        """
        Mark activities in the hot tier as transitioned.

        Args:
            activities: List of hot tier activities that were transitioned

        Returns:
            Number of activities successfully marked
        """
        # Skip if not connected to database
        if not hasattr(self, "_db") or self._db is None:
            return 0

        # Hot tier collection needed
        if not self._hot_tier_collection_name:
            return 0

        try:
            # Get activity keys
            activity_keys = [activity.get("_key") for activity in activities if "_key" in activity]

            if not activity_keys:
                return 0

            # Update activities in batch
            query = """
                FOR key IN @keys
                UPDATE key WITH {
                    Record: {
                        Data: {
                            transitioned: true,
                            transition_time: @transition_time
                        }
                    }
                } IN @@collection
                RETURN NEW
            """

            cursor = self._db._arangodb.aql.execute(
                query,
                bind_vars={
                    "@collection": self._hot_tier_collection_name,
                    "keys": activity_keys,
                    "transition_time": datetime.now(UTC).isoformat(),
                },
            )

            # Count updated documents
            updated_count = 0
            for _ in cursor:
                updated_count += 1

            self._logger.info(f"Marked {updated_count} activities as transitioned in hot tier")
            return updated_count

        except Exception as e:
            self._logger.error(f"Error marking hot tier activities as transitioned: {e}")
            return 0

    def get_entity_metadata(self, entity_id: str) -> dict[str, Any] | None:
        """
        Get entity metadata for an entity.

        Args:
            entity_id: Entity UUID as string

        Returns:
            Entity metadata or None if not found
        """
        # Skip if not connected to database
        if not hasattr(self, "_db") or self._db is None:
            return None

        try:
            # Query the entity collection
            query = """
                RETURN DOCUMENT(@entity_id)
            """

            cursor = self._db._arangodb.aql.execute(
                query,
                bind_vars={
                    "entity_id": entity_id,
                },
            )

            # Return the entity if found
            for entity in cursor:
                if entity:
                    return entity

            return None

        except Exception as e:
            self._logger.error(f"Error getting entity metadata: {e}")
            return None

    def group_activities_for_aggregation(
        self, activities: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Group activities for aggregation by entity and time window.

        Args:
            activities: List of activities to group

        Returns:
            Dictionary mapping group keys to lists of activities
        """
        # Group by entity_id, activity_type, and time window
        grouped_activities = defaultdict(list)

        for activity in activities:
            data = activity.get("Record", {}).get("Data", {})

            # Skip already aggregated activities
            if data.get("is_aggregated", False):
                continue

            # Extract key fields
            entity_id = data.get("entity_id", "unknown")
            activity_type = data.get("activity_type", "unknown")

            # Get timestamp and determine time window
            timestamp_str = data.get("timestamp", "")
            if not timestamp_str:
                continue

            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                # Calculate the time window (truncate to N-hour windows)
                window_hours = self._aggregation_window
                hour_of_day = timestamp.hour
                window_number = hour_of_day // window_hours
                window_key = f"{timestamp.date()}_{window_number}"
            except Exception:
                # Use a fallback key if timestamp parsing fails
                window_key = "unknown"

            # Create group key
            group_key = f"{entity_id}_{activity_type}_{window_key}"

            # Add to group
            grouped_activities[group_key].append(activity)

        return grouped_activities

    def create_aggregated_activity(
        self, activities: list[dict[str, Any]], group_key: str
    ) -> dict[str, Any]:
        """
        Create an aggregated activity from a list of similar activities.

        Args:
            activities: List of similar activities
            group_key: Group key for these activities

        Returns:
            Aggregated activity document
        """
        if not activities:
            return None

        # Get key fields from the first activity
        first_activity = activities[0]
        data = first_activity.get("Record", {}).get("Data", {})

        entity_id = data.get("entity_id", "unknown")
        activity_type = data.get("activity_type", "unknown")
        file_path = data.get("file_path", "unknown")
        file_name = data.get("file_name", "unknown")
        volume_name = data.get("volume_name", "unknown")
        is_directory = data.get("is_directory", False)

        # Calculate time range
        timestamps = []
        for activity in activities:
            activity_data = activity.get("Record", {}).get("Data", {})
            timestamp_str = activity_data.get("timestamp", "")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    timestamps.append(timestamp)
                except Exception:
                    pass

        if not timestamps:
            # If no valid timestamps, use current time
            start_time = end_time = datetime.now(UTC)
        else:
            # Sort timestamps and get earliest and latest
            timestamps.sort()
            start_time = timestamps[0]
            end_time = timestamps[-1]

        # Get importance scores
        importance_scores = []
        for activity in activities:
            activity_data = activity.get("Record", {}).get("Data", {})
            score = activity_data.get("importance_score", 0.0)
            importance_scores.append(score)

        # Use maximum importance for the aggregated activity
        importance_score = max(importance_scores) if importance_scores else 0.3

        # Calculate TTL timestamp
        ttl_timestamp = datetime.now(UTC) + timedelta(days=self._ttl_days)

        # Create aggregated activity
        aggregated_activity = {
            "entity_id": entity_id,
            "activity_type": activity_type,
            "file_path": file_path,
            "file_name": file_name,
            "volume_name": volume_name,
            "is_directory": is_directory,
            "timestamp": start_time.isoformat(),  # Use the earliest time as the timestamp
            "end_timestamp": end_time.isoformat(),  # Add the latest time as end_timestamp
            "count": len(activities),
            "is_aggregated": True,
            "aggregation_group": group_key,
            "importance_score": importance_score,
            "ttl_timestamp": ttl_timestamp.isoformat(),
            "original_ids": [
                activity.get("_key", "") for activity in activities if "_key" in activity
            ],
            "attributes": {
                "is_warm_tier": True,
                "aggregated_count": len(activities),
            },
        }

        # Add additional attributes from first activity
        for key, value in data.get("attributes", {}).items():
            if key not in aggregated_activity["attributes"]:
                aggregated_activity["attributes"][key] = value

        return aggregated_activity

    def aggregate_activities(self, activities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Aggregate similar activities to reduce storage requirements.

        Args:
            activities: List of activities to aggregate

        Returns:
            List of aggregated activities
        """
        # Skip if no activities
        if not activities:
            return []

        self._logger.info(f"Aggregating {len(activities)} activities")

        # Group activities
        grouped_activities = self.group_activities_for_aggregation(activities)
        self._logger.info(f"Grouped into {len(grouped_activities)} sets")

        # Create aggregated activities
        aggregated_activities = []
        for group_key, group_activities in grouped_activities.items():
            # Skip small groups if high importance
            if len(group_activities) < 3:
                # Check importance of first activity
                first_data = group_activities[0].get("Record", {}).get("Data", {})
                importance = first_data.get("importance_score", 0.0)

                # If high importance, keep individual activities
                if importance >= self._importance_thresholds["high"]:
                    aggregated_activities.extend(group_activities)
                    continue

            # Create aggregated activity
            aggregated = self.create_aggregated_activity(group_activities, group_key)
            if aggregated:
                aggregated_activities.append(aggregated)

        self._logger.info(f"Created {len(aggregated_activities)} aggregated activities")
        return aggregated_activities

    def process_hot_tier_activities(self, activities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Process activities from the hot tier for transition to warm tier.

        Args:
            activities: List of hot tier activities

        Returns:
            List of processed activities ready for warm tier
        """
        # Skip if no activities
        if not activities:
            return []

        self._logger.info(f"Processing {len(activities)} hot tier activities for warm tier")

        # First, recompute importance scores with updated weights for warm tier
        activities_with_importance = []
        for activity in activities:
            data = activity.get("Record", {}).get("Data", {})

            # Skip already transitioned activities
            if data.get("transitioned", False):
                continue

            # Get entity metadata for better scoring
            entity_id = data.get("entity_id")
            entity_metadata = None
            if entity_id:
                entity_metadata = self.get_entity_metadata(entity_id)

            # Calculate importance score
            importance_score = self._scorer.calculate_importance(
                data,
                entity_metadata,
                search_hits=data.get("search_hits", 0),
            )

            # Update importance score in data
            data["importance_score"] = importance_score

            # Add to list
            activities_with_importance.append(activity)

        # Group by importance tier
        high_importance = []
        medium_importance = []
        low_importance = []

        for activity in activities_with_importance:
            data = activity.get("Record", {}).get("Data", {})
            importance = data.get("importance_score", 0.0)

            if importance >= self._importance_thresholds["high"]:
                high_importance.append(activity)
            elif importance >= self._importance_thresholds["medium"]:
                medium_importance.append(activity)
            else:
                low_importance.append(activity)

        self._logger.info(
            f"Importance distribution: {len(high_importance)} high, "
            f"{len(medium_importance)} medium, {len(low_importance)} low",
        )

        # Process each importance tier differently
        processed_activities = []

        # High importance: keep nearly all details
        processed_activities.extend(high_importance)

        # Medium importance: some aggregation
        if medium_importance:
            # Aggregate medium importance activities
            aggregated_medium = self.aggregate_activities(medium_importance)
            processed_activities.extend(aggregated_medium)

        # Low importance: heavy aggregation
        if low_importance:
            # Aggregate low importance activities more aggressively
            # For now, use the same aggregation but later can implement more aggressive aggregation
            aggregated_low = self.aggregate_activities(low_importance)
            processed_activities.extend(aggregated_low)

        self._logger.info(f"Processed {len(processed_activities)} activities for warm tier")
        return processed_activities

    def transition_from_hot_tier(self) -> int:
        """
        Transition activities from hot tier to warm tier.

        Returns:
            Number of activities transitioned
        """
        # Skip if not connected to database
        if not hasattr(self, "_db") or self._db is None:
            self._logger.warning("Cannot transition: not connected to database")
            return 0

        # Skip if transition disabled
        if not self._transition_enabled:
            self._logger.warning("Transition is not enabled, skipping")
            return 0

        try:
            # Find hot tier activities to transition
            activities = self.find_hot_tier_activities_to_transition()
            if not activities:
                self._logger.info("No hot tier activities found for transition")
                return 0

            # Process activities for warm tier
            warm_tier_activities = self.process_hot_tier_activities(activities)
            if not warm_tier_activities:
                self._logger.info("No activities to store in warm tier after processing")
                return 0

            # Store in warm tier
            successful_transitions = 0
            for activity in warm_tier_activities:
                # For record-based activities from hot tier
                if "Record" in activity:
                    data = activity.get("Record", {}).get("Data", {})
                    # Convert to NtfsStorageActivityData to use standard storage path
                    try:
                        ntfs_data = NtfsStorageActivityData(**data)
                        self.store_activity(ntfs_data)
                        successful_transitions += 1
                    except Exception as e:
                        self._logger.error(f"Error converting hot tier data: {e}")
                else:
                    # For already processed aggregated activities
                    self.store_activity(activity)
                    successful_transitions += 1

            # Mark activities as transitioned in hot tier
            if successful_transitions > 0:
                self.mark_hot_tier_activities_transitioned(activities)

            self._logger.info(
                f"Transitioned {successful_transitions} activities from hot tier to warm tier"
            )
            return successful_transitions

        except Exception as e:
            self._logger.error(f"Error transitioning from hot tier: {e}")
            return 0

    def _build_warm_tier_document(
        self,
        activity_data: NtfsStorageActivityData | dict[str, Any],
    ) -> dict[str, Any]:
        """
        Build a document for storing an activity in the warm tier.

        Args:
            activity_data: The activity data

        Returns:
            Document for the database
        """
        # Handle dict input
        if isinstance(activity_data, dict):
            # If this is already processed data (e.g., aggregated activity)
            if "is_aggregated" in activity_data:
                # Set TTL timestamp if not present
                if "ttl_timestamp" not in activity_data:
                    ttl_timestamp = datetime.now(UTC) + timedelta(days=self._ttl_days)
                    activity_data["ttl_timestamp"] = ttl_timestamp.isoformat()

                # Get semantic attributes
                semantic_attributes = get_semantic_attributes_for_activity(activity_data)

                # Add warm tier attribute
                warm_tier_attribute = IndalekoSemanticAttributeDataModel(
                    Identifier=str(uuid.uuid5(uuid.NAMESPACE_URL, "indaleko:attribute:warm_tier")),
                    Label="Warm Tier",
                    Description="Activity in the warm storage tier",
                )
                semantic_attributes.append(warm_tier_attribute)

                # If this is an aggregated activity, add that attribute
                if activity_data.get("is_aggregated", False):
                    aggregated_attribute = IndalekoSemanticAttributeDataModel(
                        Identifier=str(
                            uuid.uuid5(uuid.NAMESPACE_URL, "indaleko:attribute:aggregated")
                        ),
                        Label="Aggregated Activity",
                        Description="Aggregated from multiple similar activities",
                    )
                    semantic_attributes.append(aggregated_attribute)

                # Convert to NtfsStorageActivityData for proper document building
                try:
                    # Add minimal required fields if not present
                    required_fields = {
                        "activity_id": str(uuid.uuid4()),
                        "activity_type": activity_data.get("activity_type", "unknown"),
                        "file_path": activity_data.get("file_path", "unknown"),
                        "timestamp": activity_data.get("timestamp", datetime.now(UTC).isoformat()),
                    }

                    for field, value in required_fields.items():
                        if field not in activity_data:
                            activity_data[field] = value

                    enhanced_activity = NtfsStorageActivityData(**activity_data)
                    return super().build_activity_document(enhanced_activity, semantic_attributes)
                except Exception as e:
                    self._logger.error(f"Error building document from dict: {e}")
                    # Try to build a document directly
                    return self._build_direct_document(activity_data, semantic_attributes)

        # For NtfsStorageActivityData input
        # Get semantic attributes
        semantic_attributes = get_semantic_attributes_for_activity(activity_data.model_dump())

        # Add NTFS-specific attribute if not present
        ntfs_attribute_present = False
        for attr in semantic_attributes:
            if attr.Identifier == str(StorageActivityAttributes.STORAGE_NTFS.value):
                ntfs_attribute_present = True
                break

        if not ntfs_attribute_present:
            ntfs_attribute = IndalekoSemanticAttributeDataModel(
                Identifier=str(StorageActivityAttributes.STORAGE_NTFS.value),
                Label="NTFS Storage Activity",
                Description="Storage activity from NTFS file system",
            )
            semantic_attributes.append(ntfs_attribute)

        # Add warm tier attribute
        warm_tier_attribute = IndalekoSemanticAttributeDataModel(
            Identifier=str(uuid.uuid5(uuid.NAMESPACE_URL, "indaleko:attribute:warm_tier")),
            Label="Warm Tier",
            Description="Activity in the warm storage tier",
        )
        semantic_attributes.append(warm_tier_attribute)

        # Use parent class method to build the final document
        try:
            return super().build_activity_document(activity_data, semantic_attributes)
        except Exception as e:
            self._logger.error(f"Error building warm tier document: {e}")
            # Fall back to parent implementation directly
            return super().build_activity_document(activity_data, semantic_attributes)

    def _build_direct_document(
        self, activity_data: dict[str, Any], semantic_attributes: list
    ) -> dict[str, Any]:
        """
        Build a document directly from a dictionary when normal path fails.

        Args:
            activity_data: The activity data as a dictionary
            semantic_attributes: List of semantic attributes

        Returns:
            Document for the database
        """
        # Generate a UUID for the document
        doc_id = str(uuid.uuid4())

        # Create source identifier
        from data_models.source_identifier import IndalekoSourceIdentifierDataModel

        source_id = IndalekoSourceIdentifierDataModel(
            SourceID=str(self._recorder_id),
            SourceIdName=self._name,
            SourceDescription=self._description,
            SourceVersion=self._version,
        )

        # Create semantic attributes list
        semantic_attrs = []
        for attr in semantic_attributes:
            if hasattr(attr, "model_dump"):
                semantic_attrs.append(attr.model_dump())
            elif isinstance(attr, dict):
                semantic_attrs.append(attr)

        # Build the document
        document = {
            "_key": doc_id,
            "Record": {
                "Timestamp": datetime.now(UTC).isoformat(),
                "SourceId": source_id.model_dump()
                if hasattr(source_id, "model_dump")
                else source_id,
                "Data": activity_data,
                "Attributes": {
                    "SemanticAttributes": semantic_attrs,
                },
            },
        }

        return document

    def store_activity(self, activity_data: NtfsStorageActivityData | dict[str, Any]) -> uuid.UUID:
        """
        Store an activity in the warm tier.

        Args:
            activity_data: Activity data to store

        Returns:
            UUID of the stored activity
        """
        # Skip if not connected to database
        if not hasattr(self, "_db") or self._db is None:
            self._logger.warning("Cannot store activity: not connected to database")
            return uuid.uuid4()

        try:
            # Build document with warm tier enhancements
            document = self._build_warm_tier_document(activity_data)

            # Store in database
            result = self._collection.add_document(document)

            # Return activity ID
            if isinstance(activity_data, NtfsStorageActivityData):
                return activity_data.activity_id
            else:
                return uuid.UUID(activity_data.get("activity_id", str(uuid.uuid4())))
        except Exception as e:
            self._logger.error(f"Error storing activity in warm tier: {e}")
            return uuid.uuid4()

    def get_warm_tier_statistics(self) -> dict[str, Any]:
        """
        Get statistics about the warm tier.

        Returns:
            Dictionary of warm tier statistics
        """
        # Skip if not connected to database
        if not hasattr(self, "_db") or self._db is None:
            return {"error": "Not connected to database"}

        try:
            stats = {}

            # Get total count
            count_query = """
                RETURN LENGTH(@@collection)
            """

            count_cursor = self._db._arangodb.aql.execute(
                count_query,
                bind_vars={"@collection": self._collection_name},
            )

            for count in count_cursor:
                stats["total_count"] = count
                break

            # Get count by activity type
            type_query = """
                FOR doc IN @@collection
                COLLECT type = doc.Record.Data.activity_type WITH COUNT INTO count
                RETURN { type, count }
            """

            type_cursor = self._db._arangodb.aql.execute(
                type_query,
                bind_vars={"@collection": self._collection_name},
            )

            stats["by_type"] = {item["type"]: item["count"] for item in type_cursor}

            # Get count of aggregated vs. non-aggregated
            agg_query = """
                FOR doc IN @@collection
                COLLECT is_aggregated = doc.Record.Data.is_aggregated WITH COUNT INTO count
                RETURN { is_aggregated, count }
            """

            agg_cursor = self._db._arangodb.aql.execute(
                agg_query,
                bind_vars={"@collection": self._collection_name},
            )

            stats["by_aggregation"] = {}
            for item in agg_cursor:
                key = "aggregated" if item["is_aggregated"] else "individual"
                stats["by_aggregation"][key] = item["count"]

            # Get count by entity importance score range
            importance_query = """
                FOR doc IN @@collection
                COLLECT importance = FLOOR(doc.Record.Data.importance_score * 10) / 10 WITH COUNT INTO count
                SORT importance ASC
                RETURN { importance, count }
            """

            importance_cursor = self._db._arangodb.aql.execute(
                importance_query,
                bind_vars={"@collection": self._collection_name},
            )

            stats["by_importance"] = {
                f"{item['importance']:.1f}": item["count"] for item in importance_cursor
            }

            # Get time-based statistics
            time_query = """
                FOR doc IN @@collection
                COLLECT
                    hour = FLOOR(DATE_DIFF(DATE_NOW(), doc.Record.Data.timestamp, "hour") / 24) * 24
                WITH COUNT INTO count
                FILTER hour <= 168  // Last 7 days (168 hours)
                SORT hour ASC
                RETURN {
                    "hours_ago": hour,
                    "days_ago": FLOOR(hour / 24),
                    "count": count
                }
            """

            time_cursor = self._db._arangodb.aql.execute(
                time_query,
                bind_vars={"@collection": self._collection_name},
            )

            stats["by_time"] = {
                f"{item['days_ago']} days ago": item["count"] for item in time_cursor
            }

            # Get aggregation statistics
            if stats["by_aggregation"].get("aggregated", 0) > 0:
                agg_stats_query = """
                    FOR doc IN @@collection
                    FILTER doc.Record.Data.is_aggregated == true
                    COLLECT AGGREGATE
                        count_sum = SUM(doc.Record.Data.count),
                        count_avg = AVG(doc.Record.Data.count),
                        count_max = MAX(doc.Record.Data.count),
                        count_min = MIN(doc.Record.Data.count)
                    RETURN {
                        count_sum, count_avg, count_max, count_min
                    }
                """

                agg_stats_cursor = self._db._arangodb.aql.execute(
                    agg_stats_query,
                    bind_vars={"@collection": self._collection_name},
                )

                for stats_item in agg_stats_cursor:
                    stats["aggregation_stats"] = stats_item
                    break

            # Add configuration information
            stats["ttl_days"] = self._ttl_days
            stats["collection_name"] = self._collection_name
            stats["recorder_id"] = str(self._recorder_id)
            stats["transition_enabled"] = self._transition_enabled
            stats["importance_thresholds"] = self._importance_thresholds

            return stats

        except Exception as e:
            self._logger.error(f"Error getting warm tier statistics: {e}")
            return {"error": str(e)}

    def get_recorder_name(self) -> str:
        """
        Get the name of the recorder.

        Returns:
            The recorder name
        """
        return self._name

    def get_recorder_id(self) -> uuid.UUID:
        """
        Get the ID of the recorder.

        Returns:
            The recorder UUID
        """
        return self._recorder_id

    def get_description(self) -> str:
        """
        Get a description of this recorder.

        Returns:
            The recorder description
        """
        return self._description

    def get_recorder_characteristics(self) -> list[ActivityDataCharacteristics]:
        """
        Get the characteristics of this recorder.

        Returns:
            List of activity data characteristics
        """
        result = [
            ActivityDataCharacteristics.ACTIVITY_DATA_SYSTEM_ACTIVITY,
            ActivityDataCharacteristics.ACTIVITY_DATA_FILE_ACTIVITY,
        ]

        # Add Windows-specific characteristic if available
        try:
            result.append(ActivityDataCharacteristics.ACTIVITY_DATA_WINDOWS_SPECIFIC)
        except AttributeError:
            # Windows-specific characteristic not defined, possibly using an older version
            self._logger.warning("ACTIVITY_DATA_WINDOWS_SPECIFIC characteristic not available")

        return result

    def get_collector_class_model(self) -> dict[str, type]:
        """
        Get the class models for the collector(s) used by this recorder.

        This method returns a dictionary mapping collector names to their types,
        which is used for type checking and serialization.

        Returns:
            Dictionary mapping collector names to types
        """
        # Import the necessary classes for the collector model
        from activity.collectors.storage.data_models.storage_activity_data_model import (
            NtfsStorageActivityData,
            StorageItemType,
            StorageProviderType,
        )
        from activity.collectors.storage.ntfs.ntfs_collector import (
            NtfsStorageActivityCollector,
        )
        from activity.collectors.storage.ntfs.ntfs_collector_v2 import (
            NtfsStorageActivityCollectorV2,
        )

        return {
            "NtfsStorageActivityCollector": NtfsStorageActivityCollector,
            "NtfsStorageActivityCollectorV2": NtfsStorageActivityCollectorV2,
            "NtfsStorageActivityData": NtfsStorageActivityData,
            "StorageActivityType": StorageActivityType,
            "StorageProviderType": StorageProviderType,
            "StorageItemType": StorageItemType,
        }

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

        Warm tier data changes less frequently, so we use a longer cache duration.

        Returns:
            The cache duration
        """
        return timedelta(hours=3)

    def get_cursor(self, activity_context: uuid.UUID) -> uuid.UUID:
        """
        Get a cursor for the provided activity context.

        This is used for tracking position in data streams. For the warm tier,
        we generate a new cursor each day to ensure consistent batching.

        Args:
            activity_context: The activity context

        Returns:
            A cursor UUID
        """
        # Generate a deterministic cursor based on current date and context
        # This ensures we can resume from a consistent point if needed
        current_date = datetime.now(UTC).date().isoformat()
        cursor_seed = f"{activity_context}:{current_date}"  # Changes daily
        cursor_hash = hashlib.md5(cursor_seed.encode()).hexdigest()
        return uuid.UUID(cursor_hash)

    def update_data(self) -> None:
        """
        Update the data in the database.

        For the warm tier, this method checks for activities in the hot tier
        that are ready for transition, and transitions them to the warm tier.
        """
        if not hasattr(self, "_db") or self._db is None:
            self._logger.warning("Cannot update data: not connected to database")
            return

        self._logger.info("Updating warm tier data")

        try:
            # Check for transition-ready data in hot tier
            if self._transition_enabled:
                # Transition data from hot tier
                self.transition_from_hot_tier()

            self._logger.info("Warm tier data updated successfully")

        except Exception as e:
            self._logger.error(f"Error updating warm tier data: {e}")

    def get_latest_db_update(self) -> dict[str, Any]:
        """
        Get the latest data update information from the database.

        Returns:
            Information about the latest update
        """
        if not hasattr(self, "_db") or self._db is None:
            return {"error": "Not connected to database"}

        try:
            # Query for the most recent activity
            query = """
                FOR doc IN @@collection
                SORT doc.Record.Data.timestamp DESC
                LIMIT 1
                RETURN {
                    activity_id: doc._key,
                    timestamp: doc.Record.Data.timestamp,
                    activity_type: doc.Record.Data.activity_type,
                    entity_id: doc.Record.Data.entity_id,
                    importance: doc.Record.Data.importance_score,
                    is_aggregated: doc.Record.Data.is_aggregated,
                    aggregated_count: doc.Record.Data.count
                }
            """

            cursor = self._db._arangodb.aql.execute(
                query,
                bind_vars={"@collection": self._collection_name},
            )

            # Return the first result, or empty dict if no results
            try:
                latest = next(cursor)

                # Add warm tier information
                latest["tier"] = "warm"
                latest["ttl_days"] = self._ttl_days
                latest["expiration_date"] = (
                    datetime.now(UTC) + timedelta(days=self._ttl_days)
                ).isoformat()

                return latest
            except StopIteration:
                return {
                    "tier": "warm",
                    "ttl_days": self._ttl_days,
                    "status": "empty",
                    "message": "No activities in warm tier",
                }

        except Exception as e:
            self._logger.error(f"Error getting latest update: {e}")
            return {
                "tier": "warm",
                "error": str(e),
                "ttl_days": self._ttl_days,
            }

    def process_data(self, data: Any) -> dict[str, Any]:
        """
        Process the collected data for the warm tier.

        This method enhances the base StorageActivityRecorder processing
        by adding warm tier specific metadata like TTL timestamps,
        importance scores, and aggregation information.

        Args:
            data: Raw data to process

        Returns:
            Processed data ready for storage
        """
        # First, use the parent class to process the basic data
        processed_data = super().process_data(data)

        # Now enhance the processed data with warm tier specific metadata
        try:
            # If data is a list of activities, enhance each one
            if isinstance(processed_data, dict) and "activities" in processed_data:
                activities = processed_data["activities"]
                if isinstance(activities, list):
                    # Enhanced activities list
                    enhanced_activities = []

                    for activity in activities:
                        # Calculate TTL timestamp
                        ttl_timestamp = datetime.now(UTC) + timedelta(days=self._ttl_days)
                        activity["ttl_timestamp"] = ttl_timestamp.isoformat()

                        # Get entity metadata for better scoring
                        entity_id = activity.get("entity_id")
                        entity_metadata = None
                        if entity_id:
                            entity_metadata = self.get_entity_metadata(entity_id)

                        # Calculate importance score with warm tier weights
                        importance_score = self._scorer.calculate_importance(
                            activity,
                            entity_metadata,
                            search_hits=activity.get("search_hits", 0),
                        )
                        activity["importance_score"] = importance_score

                        # Add tier information
                        activity["storage_tier"] = "warm"

                        # Not aggregated by default
                        if "is_aggregated" not in activity:
                            activity["is_aggregated"] = False

                        enhanced_activities.append(activity)

                    # Replace original activities with enhanced ones
                    processed_data["activities"] = enhanced_activities

            # Add tier information to the processed data
            processed_data["tier"] = "warm"
            processed_data["ttl_days"] = self._ttl_days

            return processed_data

        except Exception as e:
            self._logger.error(f"Error enhancing processed data: {e}")
            # Return original processed data as fallback
            return processed_data

    def store_data(self, data: dict[str, Any]) -> None:
        """
        Store the processed data in the warm tier.

        This method stores data in the database, handling both individual
        activities and batches of activities.

        Args:
            data: Processed data to store
        """
        # Skip if not connected to database
        if not hasattr(self, "_db") or self._db is None:
            self._logger.warning("Cannot store data: not connected to database")
            return

        try:
            # If data has an "activities" list, store each activity with warm tier enhancements
            if "activities" in data and isinstance(data["activities"], list):
                activities = data["activities"]
                self._logger.info(f"Storing {len(activities)} activities in warm tier")

                # Check if we should aggregate activities
                if len(activities) > 10:
                    # Aggregate similar activities
                    aggregated_activities = self.aggregate_activities(activities)

                    # Store aggregated activities
                    for activity in aggregated_activities:
                        self.store_activity(activity)
                else:
                    # Store individual activities
                    for activity in activities:
                        self.store_activity(activity)
                return

            # If data has a single "activity", store it
            if "activity" in data and isinstance(data["activity"], dict):
                activity_data = data["activity"]
                self.store_activity(activity_data)
                return

            # Otherwise, try to store the data directly
            try:
                self.store_activity(data)
            except Exception as e:
                self._logger.error(f"Failed to store data in warm tier: {e}")

        except Exception as e:
            self._logger.error(f"Error storing data in warm tier: {e}")


# Command-line interface
if __name__ == "__main__":
    import argparse
    import sys
    import uuid

    # Configure command-line interface
    parser = argparse.ArgumentParser(
        description="NTFS Warm Tier Recorder",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Add general arguments
    parser.add_argument(
        "--hot-tier",
        action="store_true",
        help="Check for activities in hot tier ready for transition",
    )
    parser.add_argument(
        "--ttl-days", type=int, default=30, help="Number of days to keep data in warm tier"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    # Add mode-related arguments
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--no-db", action="store_true", help="Run without database connection")
    mode_group.add_argument(
        "--db-config", type=str, default=None, help="Path to database configuration file"
    )

    # Add operation modes
    parser.add_argument("--stats", action="store_true", help="Show warm tier statistics")
    parser.add_argument(
        "--transition", action="store_true", help="Enable automatic transition from hot tier"
    )

    # Parse arguments
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("NtfsWarmTierRecorder")

    # Display configuration
    print("=== NTFS Warm Tier Recorder ===")
    print(f"- TTL days: {args.ttl_days}")
    print(f"- Debug mode: {'Enabled' if args.debug else 'Disabled'}")
    print(f"- Database: {'Disabled' if args.no_db else 'Enabled'}")
    if args.db_config:
        print(f"- DB Config: {args.db_config}")
    print(f"- Transition: {'Enabled' if args.transition else 'Disabled'}")
    print()

    try:
        # Create recorder
        recorder = NtfsWarmTierRecorder(
            ttl_days=args.ttl_days,
            debug=args.debug,
            no_db=args.no_db,
            db_config_path=args.db_config,
            transition_enabled=args.transition,
        )

        # Show statistics if requested
        if args.stats:
            stats = recorder.get_warm_tier_statistics()

            print("\nWarm Tier Statistics:")
            if "error" in stats:
                print(f"  Error: {stats['error']}")
            else:
                print(f"  Total activities: {stats.get('total_count', 0):,}")

                # Show aggregation statistics
                if "by_aggregation" in stats:
                    print("  Aggregation:")
                    for type_name, count in stats["by_aggregation"].items():
                        print(f"    {type_name}: {count:,}")

                    # Show detailed aggregation stats if available
                    if "aggregation_stats" in stats:
                        agg_stats = stats["aggregation_stats"]
                        print("  Aggregation Statistics:")
                        print(f"    Total original activities: {agg_stats.get('count_sum', 0):,}")
                        print(f"    Average aggregation size: {agg_stats.get('count_avg', 0):.1f}")
                        print(f"    Max aggregation size: {agg_stats.get('count_max', 0):,}")
                        print(f"    Min aggregation size: {agg_stats.get('count_min', 0):,}")

                if "by_type" in stats:
                    print("  Activities by type:")
                    for activity_type, count in stats["by_type"].items():
                        print(f"    {activity_type}: {count:,}")

                if "by_importance" in stats:
                    print("  Activities by importance:")
                    for importance, count in stats["by_importance"].items():
                        print(f"    {importance}: {count:,}")

                if "by_time" in stats:
                    print("  Activities by time:")
                    for time_range, count in stats["by_time"].items():
                        print(f"    {time_range}: {count:,}")

        # Check hot tier for transition-ready activities
        if args.hot_tier:
            print("\nChecking hot tier for transition-ready activities...")
            activities = recorder.find_hot_tier_activities_to_transition()

            if activities:
                print(f"Found {len(activities)} activities ready for transition")

                # If transition is enabled, process them
                if args.transition:
                    print("Processing activities for warm tier...")
                    count = recorder.transition_from_hot_tier()
                    print(f"Transitioned {count} activities to warm tier")
            else:
                print("No activities found ready for transition")

        print("\nDone.")

    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        print(f"Unhandled error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
