"""
Base class for calendar activity collectors.

This module provides a base class for collecting calendar events from
various calendar providers like Microsoft Outlook and Google Calendar.

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
from abc import abstractmethod
from typing import Any

# Ensure INDALEKO_ROOT is available
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Indaleko imports
from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.collaboration.base import CollaborationCollector
from activity.collectors.collaboration.data_models.calendar_event import CalendarEvent
from activity.collectors.collaboration.semantic_attributes import (
    ADP_COLLABORATION_CALENDAR,
)


class CalendarCollectorBase(CollaborationCollector):
    """Base class for calendar activity collectors.

    This class provides common functionality for calendar collectors, including
    event retrieval, processing, and data model conversion.
    """

    def __init__(self, **kwargs):
        """Initialize the calendar collector base.

        Args:
            **kwargs: Keyword arguments to pass to the parent class
        """
        super().__init__(**kwargs)

        # Default logger setup
        self.logger = logging.getLogger(f"Indaleko.{self.__class__.__name__}")

        # Cache for calendar events
        self._events_cache = {}
        self._calendars_cache = {}

        # Configuration
        self.config = kwargs.get("config", {})

        # Event count limit (for testing/debugging)
        self.event_limit = kwargs.get("event_limit", None)

        # Initialize event collection state
        self.collected_events = []
        self.last_sync_time = None

    def get_collector_characteristics(self) -> list[str]:
        """Get the characteristics of this collector.

        Returns:
            List[str]: List of collector characteristics UUIDs
        """
        return [
            ActivityDataCharacteristics.ACTIVITY_DATA_COLLABORATION,
            ADP_COLLABORATION_CALENDAR,
        ]

    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the calendar service.

        Returns:
            bool: True if authentication was successful, False otherwise
        """

    @abstractmethod
    def get_calendars(self) -> list[dict[str, Any]]:
        """Get a list of available calendars.

        Returns:
            List[Dict[str, Any]]: List of calendar information dictionaries
        """

    @abstractmethod
    def get_events(
        self,
        calendar_id: str,
        start_time: datetime.datetime | None = None,
        end_time: datetime.datetime | None = None,
        updated_since: datetime.datetime | None = None,
        max_results: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get events from a calendar.

        Args:
            calendar_id: ID of the calendar to retrieve events from
            start_time: Optional start time filter
            end_time: Optional end time filter
            updated_since: Optional filter for events updated since a specific time
            max_results: Optional maximum number of results to return

        Returns:
            List[Dict[str, Any]]: List of event dictionaries
        """

    @abstractmethod
    def get_event_details(self, calendar_id: str, event_id: str) -> dict[str, Any]:
        """Get detailed information about a specific event.

        Args:
            calendar_id: ID of the calendar containing the event
            event_id: ID of the event to retrieve

        Returns:
            Dict[str, Any]: Event details dictionary
        """

    @abstractmethod
    def convert_to_calendar_event(
        self, event_data: dict[str, Any], calendar_id: str,
    ) -> CalendarEvent:
        """Convert provider-specific event data to CalendarEvent model.

        Args:
            event_data: Provider-specific event data dictionary
            calendar_id: ID of the calendar containing the event

        Returns:
            CalendarEvent: Converted event model
        """

    def collect_data(self, **kwargs) -> None:
        """Collect calendar events.

        This method retrieves events from all available calendars,
        converts them to CalendarEvent models, and stores them for processing.

        Args:
            **kwargs: Additional arguments for collection
        """
        # Reset collection state
        self.collected_events = []

        # Get collection parameters
        start_time = kwargs.get("start_time")
        end_time = kwargs.get("end_time")
        updated_since = kwargs.get("updated_since", self.last_sync_time)
        max_results = kwargs.get("max_results", self.event_limit)

        # Authenticate with the calendar service
        if not self.authenticate():
            self.logger.error("Authentication failed")
            return

        # Get available calendars
        calendars = self.get_calendars()
        if not calendars:
            self.logger.warning("No calendars found or accessible")
            return

        # Process each calendar
        total_events = 0
        for calendar in calendars:
            calendar_id = calendar.get("id")
            calendar_name = calendar.get("name", "Unknown")

            self.logger.info(
                f"Collecting events from calendar: {calendar_name} ({calendar_id})",
            )

            # Get events from the calendar
            events = self.get_events(
                calendar_id=calendar_id,
                start_time=start_time,
                end_time=end_time,
                updated_since=updated_since,
                max_results=max_results,
            )

            # Process events
            for event in events:
                try:
                    # Convert to CalendarEvent model
                    calendar_event = self.convert_to_calendar_event(event, calendar_id)
                    if calendar_event:
                        self.collected_events.append(calendar_event)
                        total_events += 1

                        # Check if we've reached the limit
                        if max_results and total_events >= max_results:
                            self.logger.info(f"Reached event limit of {max_results}")
                            break

                except Exception as e:
                    self.logger.error(f"Error processing event: {e}")
                    continue

            # Check if we've reached the limit
            if max_results and total_events >= max_results:
                break

        # Update last sync time
        self.last_sync_time = datetime.datetime.now(datetime.UTC)

        self.logger.info(
            f"Collected {total_events} events from {len(calendars)} calendars",
        )

    def process_data(self) -> list[CalendarEvent]:
        """Process collected calendar events.

        Returns:
            List[CalendarEvent]: List of processed calendar events
        """
        return self.collected_events

    def store_data(self, data: list[CalendarEvent]) -> None:
        """Store processed calendar events.

        In most cases, this method will be overridden by concrete implementations
        or handled by a recorder.

        Args:
            data: List of calendar events to store
        """
        self.logger.info(f"Storing {len(data)} calendar events")

    def get_time_range(self, days_back: int = 30, days_forward: int = 90) -> tuple:
        """Get a time range for event retrieval.

        Args:
            days_back: Number of days to look back
            days_forward: Number of days to look forward

        Returns:
            tuple: (start_time, end_time) as datetime objects
        """
        now = datetime.datetime.now(datetime.UTC)
        start_time = now - datetime.timedelta(days=days_back)
        end_time = now + datetime.timedelta(days=days_forward)
        return start_time, end_time

    def get_cursor(self) -> str | None:
        """Get a cursor for the current collection state.

        Returns:
            Optional[str]: JSON string cursor or None
        """
        if self.last_sync_time:
            return json.dumps({"last_sync_time": self.last_sync_time.isoformat()})
        return None

    def set_cursor(self, cursor: str) -> None:
        """Set the collection state from a cursor.

        Args:
            cursor: JSON string cursor
        """
        if cursor:
            try:
                cursor_data = json.loads(cursor)
                last_sync_time = cursor_data.get("last_sync_time")
                if last_sync_time:
                    self.last_sync_time = datetime.datetime.fromisoformat(
                        last_sync_time,
                    )
            except Exception as e:
                self.logger.error(f"Error parsing cursor: {e}")
