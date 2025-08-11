"""
Calendar event recorder for Indaleko.

This module provides functionality to record calendar events from various
calendar providers like Microsoft Outlook and Google Calendar into the Indaleko database.

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

import datetime
import json
import logging
import os
import sys
import uuid

from typing import Any


# Ensure INDALEKO_ROOT is available
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Indaleko imports
from Indaleko import Indaleko
from activity.collectors.collaboration.calendar.google_calendar import (
    GoogleCalendarCollector,
)
from activity.collectors.collaboration.calendar.outlook_calendar import (
    OutlookCalendarCollector,
)
from activity.collectors.collaboration.data_models.calendar_event import CalendarEvent
from activity.collectors.collaboration.semantic_attributes import (
    ADP_COLLABORATION_CALENDAR,
    ADP_COLLABORATION_GOOGLE_CALENDAR,
    ADP_COLLABORATION_OUTLOOK_CALENDAR,
    CALENDAR_EVENT_ATTENDEES,
    CALENDAR_EVENT_END_TIME,
    CALENDAR_EVENT_ID,
    CALENDAR_EVENT_LOCATION,
    CALENDAR_EVENT_ORGANIZER,
    CALENDAR_EVENT_RECURRENCE,
    CALENDAR_EVENT_RESPONSE,
    CALENDAR_EVENT_START_TIME,
    CALENDAR_EVENT_STATUS,
    CALENDAR_EVENT_SUBJECT,
    CALENDAR_MEETING_TYPE,
    CALENDAR_MEETING_URL,
)
from activity.recorders.base import RecorderBase
from activity.recorders.registration_service import (
    IndalekoActivityDataRegistrationService,
)
from data_models.activity_data_registration import (
    IndalekoActivityDataRegistrationDataModel,
)
from data_models.i_uuid import IndalekoUUIDDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel


class CalendarRecorder(RecorderBase):
    """Calendar event recorder for Indaleko.

    This class records calendar events from various providers (Google Calendar,
    Outlook Calendar) into the Indaleko database.
    """

    def __init__(self, **kwargs) -> None:
        """Initialize the calendar recorder.

        Args:
            collection_name: Name of the collection to store data in
            collector: Optional calendar collector instance
            **kwargs: Additional keyword arguments
        """
        # Initialize base attributes
        self._name = kwargs.get("name", "Calendar Event Recorder")
        self._recorder_id = kwargs.get(
            "recorder_id",
            uuid.UUID("f7d8e9c0-a1b2-c3d4-e5f6-a7b8c9d0e1f2"),
        )
        self._collection_name = kwargs.get("collection_name", "CalendarEvents")

        # Set up logger
        self.logger = logging.getLogger(f"Indaleko.{self.__class__.__name__}")

        # Optional collector instance
        self.collector = kwargs.get("collector")

        # Initialize database connection
        self._db = Indaleko()
        self._db.connect()

        # Get or create the collection
        self._ensure_collection_exists()

        # Processing state
        self.processing_time = datetime.datetime.now(datetime.UTC)

        # Register with activity service manager
        self._register_with_service_manager()

    def _ensure_collection_exists(self) -> None:
        """Ensure the calendar events collection exists in the database."""
        try:
            # Try to get the collection from the central registry
            from db.i_collections import IndalekoCollections

            try:
                # Check if collection exists in registry
                collection_obj = IndalekoCollections.get_collection(
                    self._collection_name,
                )
                self._collection = collection_obj._arangodb_collection
                self.logger.info(f"Using existing collection {self._collection_name}")
            except ValueError:
                # If not in registry, use dynamic registration service
                self.logger.info(
                    f"Collection {self._collection_name} not found in registry",
                )

                # Get or create the registration service for activity data
                from activity.registration_service import ActivityRegistrationService

                registration_service = ActivityRegistrationService()

                # Register this collection with a generated UUID for consistency
                import hashlib

                # Generate deterministic UUID from collection name
                name_hash = hashlib.md5(self._collection_name.encode()).hexdigest()
                provider_id = str(uuid.UUID(name_hash))

                # Create provider collection
                provider_collection = registration_service.lookup_provider_collection(
                    provider_id,
                )
                if provider_collection is None:
                    self.logger.info(
                        f"Creating collection for {self._collection_name} via registration service",
                    )
                    provider_collection = registration_service.create_provider_collection(
                        identifier=provider_id,
                        schema=None,  # No schema validation for now
                        edge=False,
                    )

                self._collection = provider_collection.collection

        except Exception as e:
            self.logger.exception(f"Error ensuring collection exists: {e}")
            raise

    def get_recorder_characteristics(self) -> list[str]:
        """Get the characteristics of this recorder.

        Returns:
            List[str]: List of recorder characteristics UUIDs
        """
        return [ADP_COLLABORATION_CALENDAR]

    def get_recorder_name(self) -> str:
        """Get the name of the recorder.

        Returns:
            str: Recorder name
        """
        return self._name

    def get_recorder_id(self) -> uuid.UUID:
        """Get the ID of the recorder.

        Returns:
            uuid.UUID: Recorder ID
        """
        return self._recorder_id

    def get_collection_name(self) -> str:
        """Get the name of the collection.

        Returns:
            str: Collection name
        """
        return self._collection_name

    def get_cursor(self) -> str | None:
        """Get a cursor for the current recording state.

        Returns:
            Optional[str]: JSON string cursor or None
        """
        return json.dumps({"processing_time": self.processing_time.isoformat()})

    def set_cursor(self, cursor: str) -> None:
        """Set the recording state from a cursor.

        Args:
            cursor: JSON string cursor
        """
        if cursor:
            try:
                cursor_data = json.loads(cursor)
                processing_time = cursor_data.get("processing_time")
                if processing_time:
                    self.processing_time = datetime.datetime.fromisoformat(
                        processing_time,
                    )
            except Exception as e:
                self.logger.exception(f"Error parsing cursor: {e}")

    def _create_semantic_attributes(
        self,
        event: CalendarEvent,
    ) -> list[IndalekoSemanticAttributeDataModel]:
        """Create semantic attributes for a calendar event.

        Args:
            event: Calendar event to create attributes for

        Returns:
            List[IndalekoSemanticAttributeDataModel]: List of semantic attributes
        """
        attributes = []

        # Add event ID attribute
        attributes.append(
            IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=CALENDAR_EVENT_ID,
                    Label="Calendar Event ID",
                ),
                Value=event.event_id,
            ),
        )

        # Add event subject attribute
        attributes.append(
            IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=CALENDAR_EVENT_SUBJECT,
                    Label="Calendar Event Subject",
                ),
                Value=event.subject,
            ),
        )

        # Add start time attribute
        attributes.append(
            IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=CALENDAR_EVENT_START_TIME,
                    Label="Calendar Event Start Time",
                ),
                Value=event.start_time.isoformat(),
            ),
        )

        # Add end time attribute
        attributes.append(
            IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=CALENDAR_EVENT_END_TIME,
                    Label="Calendar Event End Time",
                ),
                Value=event.end_time.isoformat(),
            ),
        )

        # Add location attribute if available
        if event.location and event.location.display_name:
            attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=CALENDAR_EVENT_LOCATION,
                        Label="Calendar Event Location",
                    ),
                    Value=event.location.display_name,
                ),
            )

        # Add organizer attribute
        if event.organizer:
            organizer_value = f"{event.organizer.name} <{event.organizer.email}>"
            attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=CALENDAR_EVENT_ORGANIZER,
                        Label="Calendar Event Organizer",
                    ),
                    Value=organizer_value,
                ),
            )

        # Add status attribute
        attributes.append(
            IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=CALENDAR_EVENT_STATUS,
                    Label="Calendar Event Status",
                ),
                Value=event.status.value,
            ),
        )

        # Add recurrence attribute if applicable
        if event.is_recurring and event.recurrence:
            attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=CALENDAR_EVENT_RECURRENCE,
                        Label="Calendar Event Recurrence",
                    ),
                    Value=event.recurrence.type.value,
                ),
            )

        # Add meeting type attribute if it's a meeting
        if event.is_online_meeting and event.online_meeting_provider:
            attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=CALENDAR_MEETING_TYPE,
                        Label="Calendar Meeting Type",
                    ),
                    Value=event.online_meeting_provider,
                ),
            )

        # Add meeting URL attribute if available
        if event.is_online_meeting and event.join_url:
            attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=CALENDAR_MEETING_URL,
                        Label="Calendar Meeting URL",
                    ),
                    Value=event.join_url,
                ),
            )

        # Add attendees attribute if available
        if event.attendees:
            attendee_value = json.dumps(
                [
                    {
                        "name": attendee.name,
                        "email": attendee.email,
                        "response": attendee.response.value,
                        "required": attendee.required,
                    }
                    for attendee in event.attendees
                ],
            )

            attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=CALENDAR_EVENT_ATTENDEES,
                        Label="Calendar Event Attendees",
                    ),
                    Value=attendee_value,
                ),
            )

        # Add response status attribute
        attributes.append(
            IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=CALENDAR_EVENT_RESPONSE,
                    Label="Calendar Event Response",
                ),
                Value=event.response_status.value,
            ),
        )

        # Add provider-specific attribute
        provider_attribute = None
        if event.provider_name == "google":
            provider_attribute = IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=ADP_COLLABORATION_GOOGLE_CALENDAR,
                    Label="Google Calendar",
                ),
                Value="true",
            )
        elif event.provider_name == "outlook":
            provider_attribute = IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=ADP_COLLABORATION_OUTLOOK_CALENDAR,
                    Label="Outlook Calendar",
                ),
                Value="true",
            )

        if provider_attribute:
            attributes.append(provider_attribute)

        return attributes

    def store_calendar_events(self, events: list[CalendarEvent]) -> int:
        """Store calendar events in the database.

        Args:
            events: List of calendar events to store

        Returns:
            int: Number of events stored
        """
        if not events:
            self.logger.info("No events to store")
            return 0

        stored_count = 0

        for event in events:
            try:
                # Create document for ArangoDB
                event_doc = event.build_arangodb_doc()

                # Add semantic attributes
                event_doc["SemanticAttributes"] = [
                    attr.model_dump() for attr in self._create_semantic_attributes(event)
                ]

                # Check if this event already exists in the database
                existing_event = self._collection.find_one(
                    {
                        "event_id": event.event_id,
                        "provider_name": event.provider_name,
                        "calendar_id": event.calendar_id,
                    },
                )

                if existing_event:
                    # Update existing event
                    self._collection.update_one(
                        {"_key": existing_event["_key"]},
                        event_doc,
                    )
                else:
                    # Insert new event
                    self._collection.insert_one(event_doc)

                stored_count += 1

            except Exception as e:
                self.logger.exception(f"Error storing event {event.event_id}: {e}")

        self.logger.info(f"Stored {stored_count} calendar events")

        # Update processing time
        self.processing_time = datetime.datetime.now(datetime.UTC)

        return stored_count

    def collect_and_store(
        self,
        collector_type: str = "google",
        start_days: int = 30,
        end_days: int = 90,
        **kwargs,
    ) -> int:
        """Collect and store calendar events using the specified collector.

        Args:
            collector_type: Type of collector to use ("google" or "outlook")
            start_days: Number of days in the past to collect events from
            end_days: Number of days in the future to collect events to
            **kwargs: Additional arguments for the collector

        Returns:
            int: Number of events stored
        """
        # Create collector if not provided
        collector = self.collector

        if not collector:
            if collector_type.lower() == "google":
                try:
                    # Try to create Google Calendar collector
                    collector = GoogleCalendarCollector(**kwargs)
                except ImportError:
                    self.logger.exception(
                        "Google API libraries not available. Please install required packages.",
                    )
                    return 0
            elif collector_type.lower() == "outlook":
                # Create Outlook Calendar collector
                collector = OutlookCalendarCollector(**kwargs)
            else:
                self.logger.error(f"Unknown collector type: {collector_type}")
                return 0

        # Calculate time range
        now = datetime.datetime.now(datetime.UTC)
        start_time = now - datetime.timedelta(days=start_days)
        end_time = now + datetime.timedelta(days=end_days)

        # Collect data
        collector.collect_data(
            start_time=start_time,
            end_time=end_time,
            updated_since=self.processing_time,
        )

        # Process data
        events = collector.process_data()

        # Store data
        return self.store_calendar_events(events)

    def process_data(self, data: Any) -> list[CalendarEvent]:
        """Process data for storage.

        Args:
            data: Data to process (list of CalendarEvent objects)

        Returns:
            List[CalendarEvent]: Processed calendar events
        """
        if isinstance(data, list) and all(isinstance(event, CalendarEvent) for event in data):
            return data
        self.logger.error(
            "Invalid data format. Expected list of CalendarEvent objects.",
        )
        return []

    def store_data(self, data: list[CalendarEvent]) -> None:
        """Store processed data in the database.

        Args:
            data: List of CalendarEvent objects to store
        """
        self.store_calendar_events(data)

    def update_data(self, data: Any) -> None:
        """Update existing data in the database.

        Args:
            data: Data to update
        """
        self.store_data(data)

    def _register_with_service_manager(self) -> None:
        """Register the calendar recorder with the activity service manager."""
        try:
            # Create registration data model
            registration_data = IndalekoActivityDataRegistrationDataModel(
                Identifier=str(self._recorder_id),
                Name=self._name,
                Description="Calendar events from Google Calendar and Microsoft Outlook Calendar",
                Version="1.0",
                DataProvider="Calendar Events",
                DataProviderType="Activity",
                DataProviderSubType="Collaboration",
                DataProviderURL="",
                DataProviderCollectionName=self._collection_name,
                DataFormat="JSON",
                DataFormatVersion="1.0",
                DataAccess="Read",
                DataAccessURL="",
                DataAccessCredentials="",
                DataAccessCredentialsType="",
                DataAccessCredentialsExpiration="",
                DataAccessCredentialsRefresh="",
                DataAccessCredentialsRefreshURL="",
                DataAccessCredentialsRefreshToken="",
                DataAccessCredentialsRefreshTokenExpiration="",
                CreateCollection=True,
                SourceIdentifiers=[
                    str(ADP_COLLABORATION_CALENDAR),
                    str(ADP_COLLABORATION_GOOGLE_CALENDAR),
                    str(ADP_COLLABORATION_OUTLOOK_CALENDAR),
                ],
                SchemaIdentifiers=[
                    str(CALENDAR_EVENT_ID),
                    str(CALENDAR_EVENT_SUBJECT),
                    str(CALENDAR_EVENT_START_TIME),
                    str(CALENDAR_EVENT_END_TIME),
                    str(CALENDAR_EVENT_LOCATION),
                    str(CALENDAR_EVENT_ORGANIZER),
                    str(CALENDAR_EVENT_STATUS),
                    str(CALENDAR_EVENT_RECURRENCE),
                    str(CALENDAR_MEETING_TYPE),
                    str(CALENDAR_MEETING_URL),
                    str(CALENDAR_EVENT_ATTENDEES),
                    str(CALENDAR_EVENT_RESPONSE),
                ],
                Tags=["calendar", "event", "meeting", "collaboration"],
            )

            # Register with service manager
            service = IndalekoActivityDataRegistrationService()
            service.register_provider(**registration_data.model_dump())

            self.logger.info(
                f"Registered calendar recorder with service manager: {self._recorder_id}",
            )

        except Exception as e:
            self.logger.exception(f"Error registering with service manager: {e}")

    def get_latest_db_update(self) -> datetime.datetime:
        """Get the timestamp of the latest database update.

        Returns:
            datetime.datetime: Timestamp of the latest update
        """
        return self.processing_time

    def get_calendar_events(
        self,
        start_time: datetime.datetime | None = None,
        end_time: datetime.datetime | None = None,
        provider: str | None = None,
        subject_search: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query calendar events from the database.

        Args:
            start_time: Optional start time filter
            end_time: Optional end time filter
            provider: Optional provider filter ("google" or "outlook")
            subject_search: Optional subject search string
            limit: Maximum number of events to return

        Returns:
            List[Dict[str, Any]]: List of calendar events
        """
        try:
            # Build query
            query = "FOR event IN @@collection"
            bind_vars = {"@collection": self._collection_name}
            filters = []

            # Add filters
            if start_time:
                filters.append("event.start_time >= @start_time")
                bind_vars["start_time"] = start_time.isoformat()

            if end_time:
                filters.append("event.end_time <= @end_time")
                bind_vars["end_time"] = end_time.isoformat()

            if provider:
                filters.append("event.provider_name == @provider")
                bind_vars["provider"] = provider

            if subject_search:
                filters.append("LIKE(event.subject, @subject, true)")
                bind_vars["subject"] = f"%{subject_search}%"

            # Add filters to query
            if filters:
                query += " FILTER " + " AND ".join(filters)

            # Add sorting
            query += " SORT event.start_time DESC"

            # Add limit
            query += " LIMIT @limit"
            bind_vars["limit"] = limit

            # Add return
            query += " RETURN event"

            # Execute query
            cursor = self._db.aql.execute(query, bind_vars=bind_vars)

            # Return results
            return list(cursor)

        except Exception as e:
            self.logger.exception(f"Error querying calendar events: {e}")
            return []
