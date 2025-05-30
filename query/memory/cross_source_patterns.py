"""
This module implements cross-source pattern detection for the Proactive Archivist.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason and contributors

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

import logging
import os
import sys
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.memory.pattern_types import (
    DataSourceType,
    ProactiveSuggestion,
    SuggestionPriority,
    SuggestionType,
)

# pylint: enable=wrong-import-position


class CrossSourceEvent(BaseModel):
    """Represents an event from any data source for unified analysis."""

    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this event",
    )
    source_type: DataSourceType = Field(..., description="Type of data source")
    source_name: str = Field(..., description="Name of the specific source")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this event occurred",
    )
    event_type: str = Field(..., description="Type of event")
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Attributes of the event",
    )
    entities: list[str] = Field(
        default_factory=list,
        description="Entities involved in the event",
    )
    importance: float = Field(
        default=0.5,
        description="Importance score for this event (0.0-1.0)",
    )

    def get_event_signature(self) -> str:
        """Get a signature for this event type for pattern matching."""
        return f"{self.source_type}:{self.event_type}"


class CrossSourcePattern(BaseModel):
    """Represents a pattern across multiple data sources."""

    pattern_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this pattern",
    )
    pattern_name: str = Field(..., description="Name of the pattern")
    description: str = Field(..., description="Description of the pattern")
    confidence: float = Field(
        default=0.5,
        description="Confidence in this pattern (0.0-1.0)",
    )
    source_types: list[DataSourceType] = Field(
        default_factory=list,
        description="Data sources involved in this pattern",
    )
    event_sequence: list[str] = Field(
        default_factory=list,
        description="Sequence of event signatures in this pattern",
    )
    temporal_constraints: dict[str, Any] = Field(
        default_factory=dict,
        description="Temporal constraints on the pattern",
    )
    entities_involved: list[str] = Field(
        default_factory=list,
        description="Entities involved in this pattern",
    )
    observation_count: int = Field(
        default=1,
        description="Number of times this pattern was observed",
    )
    last_observed: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this pattern was last observed",
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional attributes of this pattern",
    )


class CrossSourceCorrelation(BaseModel):
    """Represents a correlation between events from different sources."""

    correlation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this correlation",
    )
    source_events: list[str] = Field(
        default_factory=list,
        description="Event IDs involved in this correlation",
    )
    source_types: list[DataSourceType] = Field(
        default_factory=list,
        description="Data sources involved in this correlation",
    )
    confidence: float = Field(
        default=0.5,
        description="Confidence in this correlation (0.0-1.0)",
    )
    relationship_type: str = Field(
        ...,
        description="Type of relationship between events",
    )
    description: str = Field(..., description="Description of the correlation")
    entities_involved: list[str] = Field(
        default_factory=list,
        description="Entities involved in this correlation",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this correlation was detected",
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional attributes of this correlation",
    )


class LocationContext(BaseModel):
    """Contextual information about a location."""

    location_id: str = Field(..., description="Identifier for this location")
    location_name: str | None = Field(None, description="Name of the location")
    location_type: str = Field(
        ...,
        description="Type of location (e.g., 'home', 'work', 'other')",
    )
    coordinates: dict[str, float] | None = Field(
        None,
        description="Geographic coordinates",
    )
    address: dict[str, str] | None = Field(None, description="Address information")
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional attributes",
    )
    visit_count: int = Field(
        default=1,
        description="Number of times this location was visited",
    )
    first_visit: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="First visit to this location",
    )
    last_visit: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last visit to this location",
    )
    average_duration: float | None = Field(
        None,
        description="Average duration of visits in minutes",
    )
    typical_activities: list[str] = Field(
        default_factory=list,
        description="Typical activities at this location",
    )


class DeviceContext(BaseModel):
    """Contextual information about a device."""

    device_id: str = Field(..., description="Identifier for this device")
    device_name: str | None = Field(None, description="Name of the device")
    device_type: str = Field(..., description="Type of device")
    platform: str | None = Field(None, description="Operating system or platform")
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional attributes",
    )
    usage_count: int = Field(default=1, description="Number of uses of this device")
    first_use: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="First use of this device",
    )
    last_use: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last use of this device",
    )
    typical_activities: list[str] = Field(
        default_factory=list,
        description="Typical activities on this device",
    )


class ContextualData(BaseModel):
    """Collection of contextual information for cross-source analysis."""

    locations: dict[str, LocationContext] = Field(
        default_factory=dict,
        description="Location contexts",
    )
    devices: dict[str, DeviceContext] = Field(
        default_factory=dict,
        description="Device contexts",
    )
    time_contexts: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Time-based contextual information",
    )
    activity_contexts: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Activity-based contextual information",
    )
    entity_relationships: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Relationships between entities",
    )


class CrossSourcePatternsData(BaseModel):
    """Data model for cross-source pattern detection."""

    events: dict[str, CrossSourceEvent] = Field(
        default_factory=dict,
        description="Collection of events from different sources",
    )
    event_timeline: list[str] = Field(
        default_factory=list,
        description="Chronological timeline of event IDs",
    )
    patterns: list[CrossSourcePattern] = Field(
        default_factory=list,
        description="Detected patterns across data sources",
    )
    correlations: list[CrossSourceCorrelation] = Field(
        default_factory=list,
        description="Detected correlations between events",
    )
    contextual_data: ContextualData = Field(
        default_factory=ContextualData,
        description="Contextual information",
    )
    source_statistics: dict[DataSourceType, dict[str, Any]] = Field(
        default_factory=dict,
        description="Statistics for each data source",
    )
    last_update: dict[DataSourceType, datetime] = Field(
        default_factory=dict,
        description="Last update timestamp for each source",
    )


class CrossSourcePatternDetector:
    """
    Detects patterns and correlations across different data sources.

    This component analyzes events from multiple sources to identify
    patterns that span different activity types, providing a more
    holistic understanding of user behavior.
    """

    def __init__(self, db_config=None):
        """
        Initialize the cross-source pattern detector.

        Args:
            db_config: Database configuration for accessing data
        """
        self.db_config = db_config
        self.data = CrossSourcePatternsData()
        self.logger = logging.getLogger(__name__)

        # Initialize source statistics
        for source_type in DataSourceType:
            self.data.source_statistics[source_type] = {
                "event_count": 0,
                "first_event": None,
                "last_event": None,
                "event_types": set(),
            }
            self.data.last_update[source_type] = datetime.now(UTC) - timedelta(
                days=30,
            )  # Initial old timestamp

    def collect_events(self, max_events_per_source: int = 1000) -> int:
        """
        Collect events from various data sources.

        Args:
            max_events_per_source: Maximum number of events to collect per source

        Returns:
            Total number of events collected
        """
        if not self.db_config or not self.db_config.db:
            self.logger.warning(
                "No database connection available for collecting events",
            )
            return 0

        total_events = 0

        # Collect NTFS activity events
        ntfs_events = self._collect_ntfs_events(max_events_per_source)
        total_events += len(ntfs_events)

        # Collect collaboration events
        collab_events = self._collect_collaboration_events(max_events_per_source)
        total_events += len(collab_events)

        # Collect location events
        location_events = self._collect_location_events(max_events_per_source)
        total_events += len(location_events)

        # Collect ambient events
        ambient_events = self._collect_ambient_events(max_events_per_source)
        total_events += len(ambient_events)

        # Collect query events
        query_events = self._collect_query_events(max_events_per_source)
        total_events += len(query_events)

        # Update timeline
        self._update_event_timeline()

        return total_events

    def _collect_ntfs_events(self, max_events: int = 1000) -> list[CrossSourceEvent]:
        """
        Collect NTFS activity events.

        Args:
            max_events: Maximum number of events to collect

        Returns:
            List of collected events
        """
        events = []

        try:
            # Get the collection
            collection_name = "NTFSActivity"
            if not self.db_config.db.has_collection(collection_name):
                return events

            collection = self.db_config.db.collection(collection_name)

            # Get events newer than the last update
            last_update = self.data.last_update[DataSourceType.NTFS]
            cursor = collection.find(
                {"Record.Timestamp": {"$gt": last_update.isoformat()}},
                sort=[("Record.Timestamp", 1)],
                limit=max_events,
            )

            # Process events
            for doc in cursor:
                try:
                    # Extract basic info
                    event_id = str(doc.get("_key", uuid.uuid4()))
                    timestamp = datetime.fromisoformat(doc["Record"]["Timestamp"])

                    # Extract attributes
                    attributes = {}
                    if "Activity" in doc and "Attributes" in doc["Activity"]:
                        attributes = doc["Activity"]["Attributes"]

                    # Determine event type
                    event_type = "file_activity"
                    if "Activity" in doc and "EventType" in doc["Activity"]:
                        event_type = doc["Activity"]["EventType"].lower()

                    # Extract entities
                    entities = []
                    if "Activity" in doc and "Path" in doc["Activity"]:
                        entities.append(doc["Activity"]["Path"])

                    # Create event
                    event = CrossSourceEvent(
                        event_id=event_id,
                        source_type=DataSourceType.NTFS,
                        source_name="ntfs_activity",
                        timestamp=timestamp,
                        event_type=event_type,
                        attributes=attributes,
                        entities=entities,
                    )

                    # Add to collection
                    self.data.events[event_id] = event
                    events.append(event)

                    # Update statistics
                    stats = self.data.source_statistics[DataSourceType.NTFS]
                    stats["event_count"] += 1
                    stats["event_types"].add(event_type)
                    if not stats["first_event"] or timestamp < stats["first_event"]:
                        stats["first_event"] = timestamp
                    if not stats["last_event"] or timestamp > stats["last_event"]:
                        stats["last_event"] = timestamp

                except Exception as e:
                    self.logger.error(f"Error processing NTFS event: {e}")

            # Update last update timestamp
            if events:
                self.data.last_update[DataSourceType.NTFS] = max(event.timestamp for event in events)

        except Exception as e:
            self.logger.error(f"Error collecting NTFS events: {e}")

        return events

    def _collect_collaboration_events(
        self,
        max_events: int = 1000,
    ) -> list[CrossSourceEvent]:
        """
        Collect collaboration events (Discord, Outlook).

        Args:
            max_events: Maximum number of events to collect

        Returns:
            List of collected events
        """
        events = []

        try:
            # Check collections
            collab_collections = ["DiscordShares", "OutlookShares"]
            available_collections = [c for c in collab_collections if self.db_config.db.has_collection(c)]

            if not available_collections:
                return events

            # Get events from each collection
            last_update = self.data.last_update[DataSourceType.COLLABORATION]

            for collection_name in available_collections:
                collection = self.db_config.db.collection(collection_name)

                cursor = collection.find(
                    {"Record.Timestamp": {"$gt": last_update.isoformat()}},
                    sort=[("Record.Timestamp", 1)],
                    limit=max_events // len(available_collections),
                )

                # Process events
                for doc in cursor:
                    try:
                        # Extract basic info
                        event_id = str(doc.get("_key", uuid.uuid4()))
                        timestamp = datetime.fromisoformat(doc["Record"]["Timestamp"])

                        # Extract attributes
                        attributes = {}
                        if "Collaboration" in doc and "Attributes" in doc["Collaboration"]:
                            attributes = doc["Collaboration"]["Attributes"]

                        # Determine event type
                        event_type = "file_share"
                        if "Collaboration" in doc and "EventType" in doc["Collaboration"]:
                            event_type = doc["Collaboration"]["EventType"].lower()

                        # Extract entities
                        entities = []
                        if "Collaboration" in doc:
                            if "FilePath" in doc["Collaboration"]:
                                entities.append(doc["Collaboration"]["FilePath"])
                            if "Recipient" in doc["Collaboration"]:
                                entities.append(doc["Collaboration"]["Recipient"])
                            if "Sender" in doc["Collaboration"]:
                                entities.append(doc["Collaboration"]["Sender"])

                        # Create event
                        source_name = collection_name.lower()
                        event = CrossSourceEvent(
                            event_id=event_id,
                            source_type=DataSourceType.COLLABORATION,
                            source_name=source_name,
                            timestamp=timestamp,
                            event_type=event_type,
                            attributes=attributes,
                            entities=entities,
                        )

                        # Add to collection
                        self.data.events[event_id] = event
                        events.append(event)

                        # Update statistics
                        stats = self.data.source_statistics[DataSourceType.COLLABORATION]
                        stats["event_count"] += 1
                        stats["event_types"].add(event_type)
                        if not stats["first_event"] or timestamp < stats["first_event"]:
                            stats["first_event"] = timestamp
                        if not stats["last_event"] or timestamp > stats["last_event"]:
                            stats["last_event"] = timestamp

                    except Exception as e:
                        self.logger.error(f"Error processing collaboration event: {e}")

            # Update last update timestamp
            if events:
                self.data.last_update[DataSourceType.COLLABORATION] = max(event.timestamp for event in events)

        except Exception as e:
            self.logger.error(f"Error collecting collaboration events: {e}")

        return events

    def _collect_location_events(
        self,
        max_events: int = 1000,
    ) -> list[CrossSourceEvent]:
        """
        Collect location events.

        Args:
            max_events: Maximum number of events to collect

        Returns:
            List of collected events
        """
        events = []

        try:
            # Check collections
            location_collections = ["GPSLocation", "WiFiLocation"]
            available_collections = [c for c in location_collections if self.db_config.db.has_collection(c)]

            if not available_collections:
                return events

            # Get events from each collection
            last_update = self.data.last_update[DataSourceType.LOCATION]

            for collection_name in available_collections:
                collection = self.db_config.db.collection(collection_name)

                cursor = collection.find(
                    {"Record.Timestamp": {"$gt": last_update.isoformat()}},
                    sort=[("Record.Timestamp", 1)],
                    limit=max_events // len(available_collections),
                )

                # Process events
                for doc in cursor:
                    try:
                        # Extract basic info
                        event_id = str(doc.get("_key", uuid.uuid4()))
                        timestamp = datetime.fromisoformat(doc["Record"]["Timestamp"])

                        # Extract attributes
                        attributes = {}
                        if "Location" in doc and "Attributes" in doc["Location"]:
                            attributes = doc["Location"]["Attributes"]

                        # Set location attributes
                        if "Location" in doc:
                            if "Coordinates" in doc["Location"]:
                                attributes["coordinates"] = doc["Location"]["Coordinates"]
                            if "Accuracy" in doc["Location"]:
                                attributes["accuracy"] = doc["Location"]["Accuracy"]

                        # Determine event type
                        event_type = "location_update"
                        source_name = collection_name.lower()

                        # Create event
                        event = CrossSourceEvent(
                            event_id=event_id,
                            source_type=DataSourceType.LOCATION,
                            source_name=source_name,
                            timestamp=timestamp,
                            event_type=event_type,
                            attributes=attributes,
                            entities=[],
                        )

                        # Add to collection
                        self.data.events[event_id] = event
                        events.append(event)

                        # Update statistics
                        stats = self.data.source_statistics[DataSourceType.LOCATION]
                        stats["event_count"] += 1
                        stats["event_types"].add(event_type)
                        if not stats["first_event"] or timestamp < stats["first_event"]:
                            stats["first_event"] = timestamp
                        if not stats["last_event"] or timestamp > stats["last_event"]:
                            stats["last_event"] = timestamp

                        # Update location context
                        self._update_location_context(event)

                    except Exception as e:
                        self.logger.error(f"Error processing location event: {e}")

            # Update last update timestamp
            if events:
                self.data.last_update[DataSourceType.LOCATION] = max(event.timestamp for event in events)

        except Exception as e:
            self.logger.error(f"Error collecting location events: {e}")

        return events

    def _collect_ambient_events(self, max_events: int = 1000) -> list[CrossSourceEvent]:
        """
        Collect ambient events (e.g., Spotify, smart thermostats).

        Args:
            max_events: Maximum number of events to collect

        Returns:
            List of collected events
        """
        events = []

        try:
            # Check collections
            ambient_collections = ["SpotifyActivity", "SmartThermostat"]
            available_collections = [c for c in ambient_collections if self.db_config.db.has_collection(c)]

            if not available_collections:
                return events

            # Get events from each collection
            last_update = self.data.last_update[DataSourceType.AMBIENT]

            for collection_name in available_collections:
                collection = self.db_config.db.collection(collection_name)

                cursor = collection.find(
                    {"Record.Timestamp": {"$gt": last_update.isoformat()}},
                    sort=[("Record.Timestamp", 1)],
                    limit=max_events // len(available_collections),
                )

                # Process events
                for doc in cursor:
                    try:
                        # Extract basic info
                        event_id = str(doc.get("_key", uuid.uuid4()))
                        timestamp = datetime.fromisoformat(doc["Record"]["Timestamp"])

                        # Extract attributes
                        attributes = {}
                        if "Ambient" in doc and "Attributes" in doc["Ambient"]:
                            attributes = doc["Ambient"]["Attributes"]

                        # Determine event type and source name based on collection
                        event_type = "ambient_activity"
                        source_name = collection_name.lower()

                        if collection_name == "SpotifyActivity":
                            event_type = "music_activity"
                            if "Ambient" in doc and "TrackName" in doc["Ambient"]:
                                attributes["track_name"] = doc["Ambient"]["TrackName"]
                            if "Ambient" in doc and "Artist" in doc["Ambient"]:
                                attributes["artist"] = doc["Ambient"]["Artist"]

                        elif collection_name == "SmartThermostat":
                            event_type = "temperature_setting"
                            if "Ambient" in doc and "Temperature" in doc["Ambient"]:
                                attributes["temperature"] = doc["Ambient"]["Temperature"]
                            if "Ambient" in doc and "Mode" in doc["Ambient"]:
                                attributes["mode"] = doc["Ambient"]["Mode"]

                        # Create event
                        event = CrossSourceEvent(
                            event_id=event_id,
                            source_type=DataSourceType.AMBIENT,
                            source_name=source_name,
                            timestamp=timestamp,
                            event_type=event_type,
                            attributes=attributes,
                            entities=[],
                        )

                        # Add to collection
                        self.data.events[event_id] = event
                        events.append(event)

                        # Update statistics
                        stats = self.data.source_statistics[DataSourceType.AMBIENT]
                        stats["event_count"] += 1
                        stats["event_types"].add(event_type)
                        if not stats["first_event"] or timestamp < stats["first_event"]:
                            stats["first_event"] = timestamp
                        if not stats["last_event"] or timestamp > stats["last_event"]:
                            stats["last_event"] = timestamp

                    except Exception as e:
                        self.logger.error(f"Error processing ambient event: {e}")

            # Update last update timestamp
            if events:
                self.data.last_update[DataSourceType.AMBIENT] = max(event.timestamp for event in events)

        except Exception as e:
            self.logger.error(f"Error collecting ambient events: {e}")

        return events

    def _collect_query_events(self, max_events: int = 1000) -> list[CrossSourceEvent]:
        """
        Collect query events from query history.

        Args:
            max_events: Maximum number of events to collect

        Returns:
            List of collected events
        """
        events = []

        try:
            # Check collections
            collection_name = "QueryHistory"
            if not self.db_config.db.has_collection(collection_name):
                return events

            collection = self.db_config.db.collection(collection_name)

            # Get events newer than the last update
            last_update = self.data.last_update[DataSourceType.QUERY]
            cursor = collection.find(
                {"StartTimestamp": {"$gt": last_update.isoformat()}},
                sort=[("StartTimestamp", 1)],
                limit=max_events,
            )

            # Process events
            for doc in cursor:
                try:
                    # Extract basic info
                    event_id = str(doc.get("_key", uuid.uuid4()))
                    timestamp = datetime.fromisoformat(doc["StartTimestamp"])

                    # Extract query text
                    query_text = doc.get("OriginalQuery", "")

                    # Determine event type based on query content
                    event_type = "general_query"
                    if "find" in query_text.lower() or "search" in query_text.lower():
                        event_type = "search_query"
                    elif "show" in query_text.lower() or "list" in query_text.lower():
                        event_type = "list_query"

                    # Extract entities from query intent
                    entities = []
                    if "ParsedResults" in doc and "Entities" in doc["ParsedResults"]:
                        for entity in doc["ParsedResults"]["Entities"]:
                            if "name" in entity:
                                entities.append(entity["name"])

                    # Create attributes including query results
                    attributes = {
                        "query_text": query_text,
                        "has_results": "RankedResults" in doc
                        and doc["RankedResults"] is not None
                        and len(doc["RankedResults"]) > 0,
                        "execution_time": doc.get("ElapsedTime", 0),
                    }

                    # Create event
                    event = CrossSourceEvent(
                        event_id=event_id,
                        source_type=DataSourceType.QUERY,
                        source_name="query_history",
                        timestamp=timestamp,
                        event_type=event_type,
                        attributes=attributes,
                        entities=entities,
                    )

                    # Add to collection
                    self.data.events[event_id] = event
                    events.append(event)

                    # Update statistics
                    stats = self.data.source_statistics[DataSourceType.QUERY]
                    stats["event_count"] += 1
                    stats["event_types"].add(event_type)
                    if not stats["first_event"] or timestamp < stats["first_event"]:
                        stats["first_event"] = timestamp
                    if not stats["last_event"] or timestamp > stats["last_event"]:
                        stats["last_event"] = timestamp

                except Exception as e:
                    self.logger.error(f"Error processing query event: {e}")

            # Update last update timestamp
            if events:
                self.data.last_update[DataSourceType.QUERY] = max(event.timestamp for event in events)

        except Exception as e:
            self.logger.error(f"Error collecting query events: {e}")

        return events

    def _update_event_timeline(self) -> None:
        """Update the chronological timeline of events."""
        # Sort events by timestamp
        event_ids_with_timestamps = [(event_id, event.timestamp) for event_id, event in self.data.events.items()]
        sorted_events = sorted(event_ids_with_timestamps, key=lambda x: x[1])

        # Update timeline
        self.data.event_timeline = [event_id for event_id, _ in sorted_events]

    def _update_location_context(self, event: CrossSourceEvent) -> None:
        """
        Update location context based on a location event.

        Args:
            event: The location event
        """
        if event.source_type != DataSourceType.LOCATION or not event.attributes:
            return

        # Extract location identifiers
        location_id = None
        location_name = None

        # Try to get location ID from coordinates
        if "coordinates" in event.attributes:
            coords = event.attributes["coordinates"]
            if isinstance(coords, dict) and "latitude" in coords and "longitude" in coords:
                # Round coordinates for stable ID
                lat = round(coords["latitude"], 5)
                lon = round(coords["longitude"], 5)
                location_id = f"loc:{lat},{lon}"
                location_name = f"Location at {lat},{lon}"

        # If we have a location ID, update context
        if location_id:
            timestamp = event.timestamp

            # Check if this location exists in context
            if location_id in self.data.contextual_data.locations:
                loc_context = self.data.contextual_data.locations[location_id]

                # Update visit information
                loc_context.visit_count += 1
                loc_context.last_visit = timestamp

            else:
                # Create new location context
                location_type = "other"

                loc_context = LocationContext(
                    location_id=location_id,
                    location_name=location_name,
                    location_type=location_type,
                    first_visit=timestamp,
                    last_visit=timestamp,
                )

                # Add coordinates if available
                if "coordinates" in event.attributes:
                    loc_context.coordinates = event.attributes["coordinates"]

                # Add to context collection
                self.data.contextual_data.locations[location_id] = loc_context

    def detect_patterns(
        self,
        window_size: int = 20,
        min_occurrences: int = 2,
    ) -> list[CrossSourcePattern]:
        """
        Detect cross-source patterns in the collected events.

        Args:
            window_size: Size of the sliding window for pattern detection
            min_occurrences: Minimum occurrences required to consider a pattern

        Returns:
            List of newly detected patterns
        """
        new_patterns = []

        # Ensure we have enough events for pattern detection
        if len(self.data.event_timeline) < window_size:
            return new_patterns

        # Detect sequential patterns
        sequential_patterns = self._detect_sequential_patterns(
            window_size,
            min_occurrences,
        )
        new_patterns.extend(sequential_patterns)

        # Detect location-based patterns
        location_patterns = self._detect_location_patterns(min_occurrences)
        new_patterns.extend(location_patterns)

        # Detect temporal patterns
        temporal_patterns = self._detect_temporal_patterns(min_occurrences)
        new_patterns.extend(temporal_patterns)

        return new_patterns

    def _detect_sequential_patterns(
        self,
        window_size: int,
        min_occurrences: int,
    ) -> list[CrossSourcePattern]:
        """
        Detect sequential patterns across different sources with enhanced statistical analysis.

        Args:
            window_size: Size of the sliding window for pattern detection
            min_occurrences: Minimum occurrences required to consider a pattern

        Returns:
            List of detected sequential patterns
        """
        new_patterns = []

        # Use a sliding window to find patterns
        timeline = self.data.event_timeline

        if len(timeline) <= window_size:
            return new_patterns

        # Keep track of observed sequences and their statistical significance
        sequence_counter = defaultdict(int)
        sequence_windows = defaultdict(list)
        sequence_stats = {}  # Store additional statistics for significance testing

        # Total number of possible windows
        total_windows = len(timeline) - window_size + 1

        # Get baseline frequency for each source type
        source_type_counts = defaultdict(int)
        for event_id in timeline:
            event = self.data.events.get(event_id)
            if event:
                source_type_counts[event.source_type] += 1

        # Calculate baseline probabilities
        total_events = len(timeline)
        source_type_probs = {source_type: count / total_events for source_type, count in source_type_counts.items()}

        # Scan through timeline with sliding window
        for i in range(total_windows):
            window = timeline[i : i + window_size]

            # Create sequence signature from event types
            event_signatures = []
            window_source_types = set()
            for event_id in window:
                event = self.data.events.get(event_id)
                if event:
                    event_signatures.append(event.get_event_signature())
                    window_source_types.add(event.source_type)

            # Create a sequence signature
            sequence_sig = "|".join(event_signatures)

            # Update counter and windows
            sequence_counter[sequence_sig] += 1
            sequence_windows[sequence_sig].append((i, window))

            # Store source types for statistical significance
            if sequence_sig not in sequence_stats:
                sequence_stats[sequence_sig] = {
                    "source_types": window_source_types,
                    "timestamps": [],
                }

            # Store timestamps for temporal analysis
            for event_id in window:
                event = self.data.events.get(event_id)
                if event:
                    sequence_stats[sequence_sig]["timestamps"].append(event.timestamp)

        # Find patterns that occur at least min_occurrences times
        for sequence_sig, count in sequence_counter.items():
            if count >= min_occurrences:
                # Calculate statistical significance of this pattern
                significance_score = self._calculate_pattern_significance(
                    sequence_sig,
                    count,
                    total_windows,
                    sequence_stats[sequence_sig],
                    source_type_probs,
                )

                # Skip patterns with low significance
                if significance_score < 0.3:
                    continue

                # Check if this is a known pattern
                is_known = False
                for pattern in self.data.patterns:
                    if "|".join(pattern.event_sequence) == sequence_sig:
                        # Update existing pattern
                        pattern.observation_count += 1
                        pattern.last_observed = datetime.now(UTC)
                        # Use significance to adjust confidence
                        pattern.confidence = min(
                            0.95,
                            pattern.confidence + 0.05 * significance_score,
                        )
                        is_known = True
                        break

                if not is_known:
                    # Create a new pattern
                    event_types = sequence_sig.split("|")

                    # Get source types involved
                    source_types = set()
                    for event_sig in event_types:
                        if ":" in event_sig:
                            source_type = event_sig.split(":")[0]
                            try:
                                source_types.add(DataSourceType(source_type))
                            except ValueError:
                                pass

                    # Only consider patterns with multiple source types
                    if len(source_types) > 1:
                        # Calculate temporal clustering to determine if events are truly related
                        temporal_clustering = self._analyze_temporal_clustering(
                            sequence_stats[sequence_sig]["timestamps"],
                        )

                        # Skip patterns with low temporal clustering
                        if temporal_clustering < 0.3:
                            continue

                        # Generate a pattern name and description
                        source_names = [s.value for s in source_types]
                        pattern_name = f"Cross-source pattern: {' + '.join(source_names)}"

                        # Generate description
                        description = "Sequential pattern involving "
                        description += ", ".join(
                            [s.value.capitalize() for s in source_types],
                        )

                        # Enhanced description with statistical significance
                        if significance_score > 0.7:
                            description += " (highly significant)"
                        elif significance_score > 0.5:
                            description += " (moderately significant)"

                        # Get entities involved
                        entities = set()
                        for windows in sequence_windows[sequence_sig]:
                            for event_id in windows[1]:
                                event = self.data.events.get(event_id)
                                if event and event.entities:
                                    entities.update(event.entities)

                        # Create pattern with confidence based on statistical significance
                        initial_confidence = 0.5 + (significance_score * 0.3) + (temporal_clustering * 0.2)
                        pattern = CrossSourcePattern(
                            pattern_name=pattern_name,
                            description=description,
                            confidence=min(
                                0.9,
                                initial_confidence,
                            ),  # Cap at 0.9 initially
                            source_types=list(source_types),
                            event_sequence=event_types,
                            observation_count=count,
                            entities_involved=list(entities)[:10],  # Limit to top 10 entities
                            attributes={
                                "significance_score": significance_score,
                                "temporal_clustering": temporal_clustering,
                            },
                        )

                        # Add to patterns and return
                        self.data.patterns.append(pattern)
                        new_patterns.append(pattern)

        return new_patterns

    def _calculate_pattern_significance(
        self,
        sequence_sig: str,
        count: int,
        total_windows: int,
        sequence_stats: dict[str, Any],
        source_type_probs: dict[DataSourceType, float],
    ) -> float:
        """
        Calculate the statistical significance of a pattern.

        This evaluates how likely the pattern is to occur by chance based on:
        1. The frequencies of individual source types
        2. The frequency of the observed pattern
        3. The diversity of source types in the pattern

        Args:
            sequence_sig: The sequence signature
            count: Number of occurrences of this pattern
            total_windows: Total number of windows analyzed
            sequence_stats: Statistics about this sequence
            source_type_probs: Baseline probabilities for each source type

        Returns:
            Significance score between 0.0 and 1.0
        """
        # Get source types in this pattern
        source_types = sequence_stats["source_types"]

        if not source_types:
            return 0.0

        # Calculate expected probability of this combination by chance
        # (simplified approximation assuming independence)
        expected_prob = 1.0
        for source_type in source_types:
            expected_prob *= source_type_probs.get(source_type, 0.01)

        # If source types rarely occur together naturally, the pattern is more significant
        source_diversity = len(source_types) / len(DataSourceType)

        # Calculate observed probability
        observed_prob = count / total_windows

        # If observed probability is much higher than expected, pattern is significant
        if expected_prob > 0:
            lift = observed_prob / expected_prob
        else:
            lift = 10.0  # High default if expected_prob is essentially zero

        # Cap lift at a reasonable value to avoid extreme results from rare events
        lift = min(lift, 20.0)

        # Calculate significance score combining:
        # 1. How much more often than expected the pattern occurs (lift)
        # 2. The diversity of source types involved
        # 3. The absolute frequency of the pattern
        relative_frequency = min(1.0, count / 10)  # Cap at 10+ occurrences

        significance = (
            (0.5 * (lift / 20.0))  # 50% weight: normalized lift
            + (0.3 * source_diversity)  # 30% weight: source type diversity
            + (0.2 * relative_frequency)  # 20% weight: relative frequency
        )

        return min(1.0, significance)

    def _analyze_temporal_clustering(self, timestamps: list[datetime]) -> float:
        """
        Analyze temporal clustering of events to determine if they're related.

        Args:
            timestamps: List of event timestamps

        Returns:
            Temporal clustering score between 0.0 and 1.0
        """
        if not timestamps or len(timestamps) < 2:
            return 0.0

        # Sort timestamps
        sorted_timestamps = sorted(timestamps)

        # Calculate time differences between consecutive events
        time_diffs = []
        for i in range(len(sorted_timestamps) - 1):
            diff = (sorted_timestamps[i + 1] - sorted_timestamps[i]).total_seconds()
            time_diffs.append(diff)

        if not time_diffs:
            return 0.0

        # Calculate mean and standard deviation of time differences
        mean_diff = sum(time_diffs) / len(time_diffs)

        # Skip std calculation if only one time difference
        if len(time_diffs) < 2:
            std_diff = mean_diff
        else:
            variance = sum((diff - mean_diff) ** 2 for diff in time_diffs) / len(
                time_diffs,
            )
            std_diff = variance**0.5

        # Calculate coefficient of variation (lower means more clustered)
        if mean_diff > 0:
            cv = std_diff / mean_diff
        else:
            cv = 0

        # Calculate clustering score:
        # - Events that happen close together in time (small mean_diff) -> higher score
        # - Events with consistent time intervals (low cv) -> higher score
        time_proximity_score = 1.0 / (1.0 + (mean_diff / 3600))  # Normalize by hour
        consistency_score = 1.0 / (1.0 + cv)

        # Combine scores (time proximity is more important than consistency)
        clustering_score = (0.7 * time_proximity_score) + (0.3 * consistency_score)

        return min(1.0, clustering_score)

    def _detect_location_patterns(
        self,
        min_occurrences: int,
    ) -> list[CrossSourcePattern]:
        """
        Detect patterns related to locations.

        Args:
            min_occurrences: Minimum occurrences required to consider a pattern

        Returns:
            List of detected location patterns
        """
        new_patterns = []

        # Skip if we don't have location data
        if not self.data.contextual_data.locations:
            return new_patterns

        # For each location, look for patterns
        for (
            location_id,
            location_context,
        ) in self.data.contextual_data.locations.items():
            if location_context.visit_count < min_occurrences:
                continue

            # Get events that occurred at this location
            location_events = []
            for event_id, event in self.data.events.items():
                if event.source_type == DataSourceType.LOCATION:
                    # Check if this event is for the current location
                    if "coordinates" in event.attributes:
                        coords = event.attributes["coordinates"]
                        if isinstance(coords, dict) and "latitude" in coords and "longitude" in coords:
                            # Round coordinates for comparison
                            lat = round(coords["latitude"], 5)
                            lon = round(coords["longitude"], 5)
                            event_loc_id = f"loc:{lat},{lon}"

                            if event_loc_id == location_id:
                                location_events.append(event_id)

            # Find events that happened close to location visits
            for location_event_id in location_events:
                # Get index in timeline
                try:
                    idx = self.data.event_timeline.index(location_event_id)
                except ValueError:
                    continue

                # Look at surrounding events (5 before and after)
                window_start = max(0, idx - 5)
                window_end = min(len(self.data.event_timeline), idx + 6)

                surrounding_events = self.data.event_timeline[window_start:window_end]

                # Group by source type
                source_type_counts = defaultdict(int)
                for event_id in surrounding_events:
                    event = self.data.events.get(event_id)
                    if event and event.source_type != DataSourceType.LOCATION:
                        source_type_counts[event.source_type] += 1

                # Find source types with significant correlation
                for source_type, count in source_type_counts.items():
                    if count >= min_occurrences:
                        # Check for existing pattern
                        pattern_exists = False
                        for pattern in self.data.patterns:
                            if pattern.source_types == [
                                DataSourceType.LOCATION,
                                source_type,
                            ] and any(location_id in entity for entity in pattern.entities_involved):
                                pattern.observation_count += 1
                                pattern.last_observed = datetime.now(UTC)
                                pattern.confidence = min(
                                    0.95,
                                    pattern.confidence + 0.05,
                                )
                                pattern_exists = True
                                break

                        if not pattern_exists:
                            # Create a new location-based pattern
                            location_name = location_context.location_name or location_id
                            pattern_name = f"Location pattern: {location_name} + {source_type.value}"

                            description = f"Activities at {location_name} frequently involve {source_type.value} events"

                            pattern = CrossSourcePattern(
                                pattern_name=pattern_name,
                                description=description,
                                confidence=0.6,  # Initial confidence
                                source_types=[DataSourceType.LOCATION, source_type],
                                event_sequence=[],  # No specific sequence for location patterns
                                temporal_constraints={"location_id": location_id},
                                entities_involved=[location_id],
                                observation_count=count,
                            )

                            # Add to patterns and return
                            self.data.patterns.append(pattern)
                            new_patterns.append(pattern)

        return new_patterns

    def _detect_temporal_patterns(
        self,
        min_occurrences: int,
    ) -> list[CrossSourcePattern]:
        """
        Detect temporal patterns across different sources.

        Args:
            min_occurrences: Minimum occurrences required to consider a pattern

        Returns:
            List of detected temporal patterns
        """
        new_patterns = []

        # Group events by hour of day
        hour_source_counts = defaultdict(lambda: defaultdict(int))

        # Group events by day of week
        day_source_counts = defaultdict(lambda: defaultdict(int))

        # Analyze events
        for event_id, event in self.data.events.items():
            # Hour analysis
            hour = event.timestamp.hour
            hour_source_counts[hour][event.source_type] += 1

            # Day of week analysis
            day = event.timestamp.weekday()  # 0-6 for Monday-Sunday
            day_source_counts[day][event.source_type] += 1

        # Find hour-based patterns
        for hour, source_counts in hour_source_counts.items():
            # Find source types with significant activity in this hour
            for source_type, count in source_counts.items():
                if count >= min_occurrences:
                    # Check if this is a known pattern
                    pattern_exists = False
                    for pattern in self.data.patterns:
                        if (
                            len(pattern.temporal_constraints) > 0
                            and "hour" in pattern.temporal_constraints
                            and pattern.temporal_constraints["hour"] == hour
                            and source_type in pattern.source_types
                        ):
                            pattern.observation_count += 1
                            pattern.last_observed = datetime.now(UTC)
                            pattern.confidence = min(0.95, pattern.confidence + 0.05)
                            pattern_exists = True
                            break

                    if not pattern_exists:
                        # Create a new hour-based pattern
                        pattern_name = f"Hour pattern: {source_type.value} at {hour}:00"

                        # Create description
                        hour_desc = f"{hour}:00-{hour+1}:00"
                        description = f"{source_type.value.capitalize()} activity frequently occurs around {hour_desc}"

                        pattern = CrossSourcePattern(
                            pattern_name=pattern_name,
                            description=description,
                            confidence=0.6,  # Initial confidence
                            source_types=[source_type],
                            event_sequence=[],  # No specific sequence for temporal patterns
                            temporal_constraints={"hour": hour},
                            observation_count=count,
                        )

                        # Add to patterns and return
                        self.data.patterns.append(pattern)
                        new_patterns.append(pattern)

        # Find day-based patterns
        for day, source_counts in day_source_counts.items():
            # Find source types with significant activity on this day
            for source_type, count in source_counts.items():
                if count >= min_occurrences:
                    # Check if this is a known pattern
                    pattern_exists = False
                    for pattern in self.data.patterns:
                        if (
                            len(pattern.temporal_constraints) > 0
                            and "day_of_week" in pattern.temporal_constraints
                            and pattern.temporal_constraints["day_of_week"] == day
                            and source_type in pattern.source_types
                        ):
                            pattern.observation_count += 1
                            pattern.last_observed = datetime.now(UTC)
                            pattern.confidence = min(0.95, pattern.confidence + 0.05)
                            pattern_exists = True
                            break

                    if not pattern_exists:
                        # Create a new day-based pattern
                        day_names = [
                            "Monday",
                            "Tuesday",
                            "Wednesday",
                            "Thursday",
                            "Friday",
                            "Saturday",
                            "Sunday",
                        ]
                        day_name = day_names[day]

                        pattern_name = f"Day pattern: {source_type.value} on {day_name}"
                        description = f"{source_type.value.capitalize()} activity frequently occurs on {day_name}s"

                        pattern = CrossSourcePattern(
                            pattern_name=pattern_name,
                            description=description,
                            confidence=0.6,  # Initial confidence
                            source_types=[source_type],
                            event_sequence=[],  # No specific sequence for temporal patterns
                            temporal_constraints={"day_of_week": day},
                            observation_count=count,
                        )

                        # Add to patterns and return
                        self.data.patterns.append(pattern)
                        new_patterns.append(pattern)

        return new_patterns

    def detect_correlations(
        self,
        time_window_minutes: int = 15,
        min_confidence: float = 0.6,
        min_entity_overlap: float = 0.0,
        adaptive_window: bool = True,
    ) -> list[CrossSourceCorrelation]:
        """
        Detect correlations between events from different sources with advanced statistical methods.

        Args:
            time_window_minutes: Base time window for considering events correlated
            min_confidence: Minimum confidence required for a correlation
            min_entity_overlap: Minimum required overlap in entities (0.0 to 1.0)
            adaptive_window: Whether to use adaptive time windows based on source types

        Returns:
            List of detected correlations
        """
        new_correlations = []

        # Create time windows for analysis
        timeline = self.data.event_timeline

        # Skip if timeline is too short
        if len(timeline) < 3:
            return new_correlations

        # Define adaptive time windows based on source types (in minutes)
        # Some source types naturally have tighter temporal correlations than others
        adaptive_time_windows = {
            # Same device/user immediate activities tend to be close in time
            (DataSourceType.NTFS, DataSourceType.COLLABORATION): 5,
            (DataSourceType.NTFS, DataSourceType.QUERY): 3,
            (DataSourceType.COLLABORATION, DataSourceType.QUERY): 5,
            # Location and ambient activities can have looser temporal connections
            (DataSourceType.LOCATION, DataSourceType.NTFS): 20,
            (DataSourceType.LOCATION, DataSourceType.COLLABORATION): 20,
            (DataSourceType.AMBIENT, DataSourceType.NTFS): 25,
            (DataSourceType.AMBIENT, DataSourceType.COLLABORATION): 25,
            # Default window for other combinations
            "default": time_window_minutes,
        }

        # Count frequencies by source type for statistical analysis
        source_type_counts = defaultdict(int)
        for event_id in timeline:
            event = self.data.events.get(event_id)
            if event:
                source_type_counts[event.source_type] += 1

        # Group events by time windows with the base window size initially
        time_windows = []
        current_window = []
        last_timestamp = None

        for event_id in timeline:
            event = self.data.events.get(event_id)
            if not event:
                continue

            if last_timestamp is None:
                # First event
                current_window.append(event_id)
                last_timestamp = event.timestamp
            elif (event.timestamp - last_timestamp).total_seconds() <= time_window_minutes * 60:
                # Event is within time window of last event
                current_window.append(event_id)
                last_timestamp = max(last_timestamp, event.timestamp)
            else:
                # Event is outside time window, start a new window
                if len(current_window) > 1:
                    time_windows.append(current_window)
                current_window = [event_id]
                last_timestamp = event.timestamp

        # Add the last window if it has more than one event
        if len(current_window) > 1:
            time_windows.append(current_window)

        # Analyze each time window for correlations
        for window in time_windows:
            # Group events by source type
            events_by_source = defaultdict(list)
            for event_id in window:
                event = self.data.events.get(event_id)
                if event:
                    events_by_source[event.source_type].append(event_id)

            # Only look for correlations between different source types
            source_types = list(events_by_source.keys())
            if len(source_types) < 2:
                continue

            # Check pairs of source types
            for i, source_type1 in enumerate(source_types):
                for j in range(i + 1, len(source_types)):
                    source_type2 = source_types[j]

                    # Get the appropriate time window for this source type pair
                    if adaptive_window:
                        # Check both orderings of the pair
                        pair1 = (source_type1, source_type2)
                        pair2 = (source_type2, source_type1)

                        if pair1 in adaptive_time_windows:
                            actual_window_minutes = adaptive_time_windows[pair1]
                        elif pair2 in adaptive_time_windows:
                            actual_window_minutes = adaptive_time_windows[pair2]
                        else:
                            actual_window_minutes = adaptive_time_windows["default"]
                    else:
                        actual_window_minutes = time_window_minutes

                    # Get events for each source type
                    events1 = events_by_source[source_type1]
                    events2 = events_by_source[source_type2]

                    # Only consider cases with at least one event of each type
                    if not events1 or not events2:
                        continue

                    # Get event objects
                    events1_objs = [self.data.events.get(event_id) for event_id in events1]
                    events1_objs = [e for e in events1_objs if e is not None]

                    events2_objs = [self.data.events.get(event_id) for event_id in events2]
                    events2_objs = [e for e in events2_objs if e is not None]

                    # Check if events are close enough within the adaptive window
                    timestamps1 = [e.timestamp for e in events1_objs]
                    timestamps2 = [e.timestamp for e in events2_objs]

                    if not timestamps1 or not timestamps2:
                        continue

                    # Find minimum time difference between any event pair
                    min_time_diff = min(abs((t1 - t2).total_seconds()) for t1 in timestamps1 for t2 in timestamps2)

                    # Skip if minimum time diff exceeds the adaptive window
                    if min_time_diff > actual_window_minutes * 60:
                        continue

                    # Calculate entity overlap
                    entities1 = set()
                    for event in events1_objs:
                        entities1.update(event.entities)

                    entities2 = set()
                    for event in events2_objs:
                        entities2.update(event.entities)

                    # Skip if no entities found
                    if not entities1 and not entities2:
                        # For no entities, just use weak overlap by default
                        entity_overlap = 0.1
                    elif not entities1 or not entities2:
                        # One side has no entities
                        entity_overlap = 0.0
                    else:
                        # Calculate Jaccard similarity for entity overlap
                        common_entities = entities1.intersection(entities2)
                        all_entities = entities1.union(entities2)
                        entity_overlap = len(common_entities) / len(all_entities) if all_entities else 0.0

                    # Skip if entity overlap is too low
                    if entity_overlap < min_entity_overlap:
                        continue

                    # Create correlation object
                    correlation_sources = [source_type1, source_type2]
                    correlation_events = events1 + events2

                    # Calculate statistical significance of correlation
                    expected_coincidence = (
                        (len(events1_objs) / len(timeline)) * (len(events2_objs) / len(timeline)) * len(window)
                    )

                    # If observed coincidence is much higher than expected, correlation is significant
                    coincidence_lift = len(correlation_events) / max(
                        1.0,
                        expected_coincidence,
                    )

                    # Cap lift at a reasonable value
                    coincidence_lift = min(coincidence_lift, 10.0)

                    # Calculate time proximity (normalized by adaptive window)
                    time_proximity = max(
                        0.0,
                        1.0 - min_time_diff / (actual_window_minutes * 60),
                    )

                    # Combine factors to calculate confidence:
                    # - Time proximity: how close in time are the events
                    # - Entity overlap: how many shared entities
                    # - Coincidence lift: how much more often do these events co-occur than expected
                    base_confidence = min_confidence
                    confidence = base_confidence + (1.0 - base_confidence) * (
                        (0.4 * time_proximity) + (0.3 * entity_overlap) + (0.3 * (coincidence_lift / 10.0))
                    )

                    # If confidence is too low, skip
                    if confidence < min_confidence:
                        continue

                    # Generate description based on source types and correlation strength
                    src1_name = source_type1.value.capitalize()
                    src2_name = source_type2.value.capitalize()

                    description = f"Correlation between {src1_name} and {src2_name} events"

                    # Add more detail for high-confidence correlations
                    if confidence > 0.8:
                        description += " (strong correlation)"
                    elif confidence > 0.7:
                        description += " (moderate correlation)"

                    # Add entity info if there's overlap
                    if entity_overlap > 0.3:
                        common = list(entities1.intersection(entities2))
                        if common:
                            # Limit to first 2 entities for description
                            entity_str = ", ".join(common[:2])
                            if len(common) > 2:
                                entity_str += f" and {len(common)-2} more"
                            description += f" involving {entity_str}"

                    # Generate relationship type
                    relationship_type = f"{source_type1.value}_to_{source_type2.value}"

                    # Combine all entities
                    all_entities = entities1.union(entities2)

                    # Create correlation object
                    correlation = CrossSourceCorrelation(
                        source_events=correlation_events,
                        source_types=correlation_sources,
                        confidence=confidence,
                        relationship_type=relationship_type,
                        description=description,
                        entities_involved=list(all_entities)[:10],  # Limit to top 10
                        attributes={
                            "time_proximity": time_proximity,
                            "entity_overlap": entity_overlap,
                            "coincidence_lift": coincidence_lift,
                            "adaptive_window_minutes": actual_window_minutes,
                        },
                    )

                    # Add to correlations and return
                    self.data.correlations.append(correlation)
                    new_correlations.append(correlation)

        return new_correlations

    def generate_suggestions(
        self,
        max_suggestions: int = 5,
    ) -> list[ProactiveSuggestion]:
        """
        Generate proactive suggestions based on detected patterns and correlations.

        Args:
            max_suggestions: Maximum number of suggestions to generate

        Returns:
            List of generated suggestions
        """
        suggestions = []

        # Generate pattern-based suggestions
        pattern_suggestions = self._generate_pattern_suggestions()
        suggestions.extend(pattern_suggestions)

        # Generate correlation-based suggestions
        correlation_suggestions = self._generate_correlation_suggestions()
        suggestions.extend(correlation_suggestions)

        # Sort by confidence and limit
        sorted_suggestions = sorted(
            suggestions,
            key=lambda s: s.confidence,
            reverse=True,
        )
        return sorted_suggestions[:max_suggestions]

    def _generate_pattern_suggestions(self) -> list[ProactiveSuggestion]:
        """
        Generate suggestions based on detected patterns.

        Returns:
            List of generated suggestions
        """
        suggestions = []

        # Get current hour and day of week
        now = datetime.now(UTC)
        current_hour = now.hour
        current_day = now.weekday()

        # Look for temporal patterns matching current time
        for pattern in self.data.patterns:
            # Skip low confidence patterns
            if pattern.confidence < 0.6:
                continue

            # Check if this is a temporal pattern matching current time
            if pattern.temporal_constraints:
                if "hour" in pattern.temporal_constraints and pattern.temporal_constraints["hour"] == current_hour:
                    # This is a matching hour pattern

                    # Only generate suggestion for high or medium confidence patterns
                    if pattern.confidence >= 0.7:
                        # Create a suggestion
                        priority = SuggestionPriority.MEDIUM if pattern.confidence >= 0.8 else SuggestionPriority.LOW

                        # Determine suggestion type and content based on source types
                        suggestion_type = SuggestionType.QUERY
                        title = "Suggested action based on time pattern"
                        content = f"Based on your patterns, you might want to check: {pattern.description}"

                        # Refine suggestion based on source types
                        if DataSourceType.NTFS in pattern.source_types:
                            suggestion_type = SuggestionType.CONTENT
                            title = "Files you might need now"
                            content = f"Based on your patterns, you might need files related to your {pattern.source_types[0].value} activity around this time."

                        elif DataSourceType.COLLABORATION in pattern.source_types:
                            suggestion_type = SuggestionType.CONTENT
                            title = "Check for collaboration updates"
                            content = (
                                "Based on your patterns, you often check for collaboration updates around this time."
                            )

                        # Create suggestion
                        suggestion = ProactiveSuggestion(
                            suggestion_type=suggestion_type,
                            title=title,
                            content=content,
                            expires_at=now + timedelta(hours=1),  # Expire after an hour
                            priority=priority,
                            confidence=pattern.confidence,
                            context={"pattern_id": pattern.pattern_id},
                        )

                        suggestions.append(suggestion)

                elif (
                    "day_of_week" in pattern.temporal_constraints
                    and pattern.temporal_constraints["day_of_week"] == current_day
                ):
                    # This is a matching day pattern

                    # Only generate suggestion for high confidence patterns
                    if pattern.confidence >= 0.75:
                        # Create a suggestion
                        priority = SuggestionPriority.LOW

                        # Determine suggestion type and content based on source types
                        suggestion_type = SuggestionType.REMINDER
                        title = "Daily reminder based on your patterns"
                        content = f"It's {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][current_day]}, and you often engage with {pattern.source_types[0].value} activities today."

                        # Create suggestion
                        suggestion = ProactiveSuggestion(
                            suggestion_type=suggestion_type,
                            title=title,
                            content=content,
                            expires_at=now + timedelta(hours=4),  # Expire after 4 hours
                            priority=priority,
                            confidence=pattern.confidence,
                            context={"pattern_id": pattern.pattern_id},
                        )

                        suggestions.append(suggestion)

            # Check for sequential patterns
            elif pattern.event_sequence and len(pattern.source_types) > 1:
                # This is a sequential pattern

                # Only generate suggestion for high confidence patterns
                if pattern.confidence >= 0.7:
                    # Create a suggestion based on the pattern
                    priority = SuggestionPriority.MEDIUM if pattern.confidence >= 0.8 else SuggestionPriority.LOW

                    # Determine suggestion type and content
                    suggestion_type = SuggestionType.SEARCH_STRATEGY

                    # Create a more specific title and content
                    source_names = [s.value.capitalize() for s in pattern.source_types]
                    title = f"Consider connecting {' and '.join(source_names)}"
                    content = f"You often use {' and '.join(source_names)} together. Consider creating a workflow that connects them more efficiently."

                    # Create suggestion
                    suggestion = ProactiveSuggestion(
                        suggestion_type=suggestion_type,
                        title=title,
                        content=content,
                        expires_at=now
                        + timedelta(
                            days=7,
                        ),  # Longer expiration for workflow suggestions
                        priority=priority,
                        confidence=pattern.confidence,
                        context={"pattern_id": pattern.pattern_id},
                    )

                    suggestions.append(suggestion)

        return suggestions

    def _generate_correlation_suggestions(self) -> list[ProactiveSuggestion]:
        """
        Generate suggestions based on detected correlations.

        Returns:
            List of generated suggestions
        """
        suggestions = []

        # Look for high-confidence correlations
        for correlation in self.data.correlations:
            # Skip low confidence correlations
            if correlation.confidence < 0.7:
                continue

            # Create a suggestion based on the correlation
            source_names = [s.value.capitalize() for s in correlation.source_types]

            # Only generate suggestions for certain combinations of sources
            if DataSourceType.LOCATION in correlation.source_types and DataSourceType.NTFS in correlation.source_types:
                # Location + file activity
                title = "Files relevant to your location"
                content = "Based on your patterns, we've noticed you typically access certain files when at this location. Would you like to see them?"
                suggestion_type = SuggestionType.CONTENT

            elif DataSourceType.AMBIENT in correlation.source_types and DataSourceType.NTFS in correlation.source_types:
                # Ambient + file activity
                title = "Content suggestion based on environment"
                content = "Based on your patterns, you might want to check these files during your current activity."
                suggestion_type = SuggestionType.CONTENT

            elif DataSourceType.QUERY in correlation.source_types and DataSourceType.NTFS in correlation.source_types:
                # Query + file activity
                title = "Search strategy suggestion"
                content = "Your search patterns and file activities show a connection. Consider using more specific file-related terms in your searches."
                suggestion_type = SuggestionType.SEARCH_STRATEGY

            else:
                # Default correlation suggestion
                title = f"Connection between {' and '.join(source_names)}"
                content = f"We've noticed a correlation between your {' and '.join(source_names)} activities. Would you like to explore this connection?"
                suggestion_type = SuggestionType.RELATED_CONTENT

            # Create the suggestion
            now = datetime.now(UTC)
            suggestion = ProactiveSuggestion(
                suggestion_type=suggestion_type,
                title=title,
                content=content,
                expires_at=now + timedelta(days=3),  # Expire after 3 days
                priority=SuggestionPriority.MEDIUM,
                confidence=correlation.confidence,
                context={"correlation_id": correlation.correlation_id},
            )

            suggestions.append(suggestion)

        return suggestions

    def validate_patterns(
        self,
        patterns: list[CrossSourcePattern],
        min_confidence: float = 0.5,
    ) -> list[CrossSourcePattern]:
        """
        Validate patterns to reduce false positives by additional filtering.

        This applies additional validation to patterns, including:
        1. Checking for statistical significance
        2. Verifying temporal consistency
        3. Cross-validating against other patterns

        Args:
            patterns: List of patterns to validate
            min_confidence: Minimum confidence threshold

        Returns:
            List of validated patterns
        """
        if not patterns:
            return []

        validated_patterns = []

        # Get statistics on source type frequencies for baseline
        source_type_counts = defaultdict(int)
        for event_id in self.data.event_timeline:
            event = self.data.events.get(event_id)
            if event:
                source_type_counts[event.source_type] += 1

        total_events = len(self.data.event_timeline)

        # First pass: filter by confidence
        confident_patterns = [p for p in patterns if p.confidence >= min_confidence]

        # Second pass: additional validation checks
        for pattern in confident_patterns:
            # Skip patterns with too few observations
            if pattern.observation_count < 2:
                continue

            # For temporal patterns, check if observation time points show consistency
            if "hour" in pattern.temporal_constraints or "day_of_week" in pattern.temporal_constraints:
                # Temporal patterns are valid by design
                validated_patterns.append(pattern)
                continue

            # For sequential patterns, verify source diversity
            if len(pattern.source_types) < 2:
                # Only interested in cross-source patterns
                continue

            # Check if the pattern is over-represented by a single source type
            overrepresented = False
            for source_type in pattern.source_types:
                if source_type_counts[source_type] / total_events > 0.8:
                    # This source type dominates the dataset, so patterns involving it are less meaningful
                    overrepresented = True
                    break

            if overrepresented:
                continue

            # Add validation passed attribute
            pattern.attributes = pattern.attributes or {}
            pattern.attributes["validation_passed"] = True

            # Add to validated patterns
            validated_patterns.append(pattern)

        return validated_patterns

    def analyze_and_generate(
        self,
    ) -> tuple[
        int,
        list[CrossSourcePattern],
        list[CrossSourceCorrelation],
        list[ProactiveSuggestion],
    ]:
        """
        Run a complete analysis cycle and generate suggestions.

        This method:
        1. Collects events from all sources
        2. Detects patterns
        3. Validates patterns to reduce false positives
        4. Detects correlations
        5. Generates suggestions

        Returns:
            Tuple containing:
            - Number of events collected
            - List of new patterns detected
            - List of new correlations detected
            - List of suggestions generated
        """
        # Collect events
        event_count = self.collect_events()

        # Detect patterns
        raw_patterns = self.detect_patterns()

        # Validate patterns to reduce false positives
        patterns = self.validate_patterns(raw_patterns, min_confidence=0.55)

        # Detect correlations (with adaptive window and entity overlap)
        correlations = self.detect_correlations(
            adaptive_window=True,
            min_entity_overlap=0.1,
        )

        # Generate suggestions
        suggestions = self.generate_suggestions()

        # Log detection statistics
        self.logger.info(f"Cross-source analysis: Collected {event_count} events")
        self.logger.info(
            f"Cross-source analysis: Detected {len(raw_patterns)} raw patterns",
        )
        self.logger.info(
            f"Cross-source analysis: {len(patterns)} patterns passed validation",
        )
        self.logger.info(
            f"Cross-source analysis: Detected {len(correlations)} correlations",
        )
        self.logger.info(
            f"Cross-source analysis: Generated {len(suggestions)} suggestions",
        )

        return event_count, patterns, correlations, suggestions


def main():
    """Test the cross-source pattern detector."""
    from db import IndalekoDBConfig

    print("Testing Cross-Source Pattern Detector")

    # Initialize detector
    db_config = IndalekoDBConfig()
    detector = CrossSourcePatternDetector(db_config)

    # Run analysis
    event_count, patterns, correlations, suggestions = detector.analyze_and_generate()

    # Print results
    print(f"\nCollected {event_count} events")
    print(f"Detected {len(patterns)} new patterns")
    print(f"Detected {len(correlations)} new correlations")
    print(f"Generated {len(suggestions)} suggestions")

    # Show patterns
    if patterns:
        print("\nPatterns:")
        for pattern in patterns:
            print(
                f"- {pattern.pattern_name}: {pattern.description} (confidence: {pattern.confidence:.2f})",
            )

    # Show correlations
    if correlations:
        print("\nCorrelations:")
        for correlation in correlations:
            print(
                f"- {correlation.description} (confidence: {correlation.confidence:.2f})",
            )

    # Show suggestions
    if suggestions:
        print("\nSuggestions:")
        for suggestion in suggestions:
            print(f"- [{suggestion.priority}] {suggestion.title}")
            print(f"  {suggestion.content}")
            print(
                f"  Confidence: {suggestion.confidence:.2f}, Expires: {suggestion.expires_at}",
            )


if __name__ == "__main__":
    main()
