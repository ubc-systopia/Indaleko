"""
Calendar event data model for Indaleko collaboration activity.

This module defines data models for calendar events and meetings from
services like Microsoft Outlook Calendar and Google Calendar.

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
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

# Ensure INDALEKO_ROOT is available
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Indaleko imports
from activity.collectors.collaboration.data_models.collaboration_data_model import (
    BaseCollaborationDataModel,
)
from activity.collectors.collaboration.data_models.shared_file import SharedFileData
from data_models.base import IndalekoBaseModel


class EventRecurrence(str, Enum):
    """Enum representing possible calendar event recurrence patterns"""

    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    BI_WEEKLY = "biweekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class EventStatus(str, Enum):
    """Enum representing possible calendar event status values"""

    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class EventResponse(str, Enum):
    """Enum representing possible responses to calendar event invitations"""

    ACCEPTED = "accepted"
    TENTATIVE = "tentative"
    DECLINED = "declined"
    NOT_RESPONDED = "notResponded"
    ORGANIZER = "organizer"


class EventAttendee(IndalekoBaseModel):
    """Model representing a calendar event attendee"""

    email: str
    name: str | None = None
    response: EventResponse = EventResponse.NOT_RESPONDED
    required: bool = True  # True for required, False for optional attendees
    organizer: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "name": "John Doe",
                "response": "accepted",
                "required": True,
                "organizer": False,
            },
        }


class EventLocation(IndalekoBaseModel):
    """Model representing a calendar event location"""

    display_name: str
    address: str | None = None
    coordinates: dict[str, float] | None = None  # {"latitude": 42.3, "longitude": -71.1}
    is_virtual: bool = False
    join_url: str | None = None  # For virtual meetings (Teams, Zoom, etc.)

    class Config:
        json_schema_extra = {
            "example": {
                "display_name": "Conference Room A",
                "address": "123 Main St, Boston, MA 02108",
                "coordinates": {"latitude": 42.3601, "longitude": -71.0589},
                "is_virtual": False,
                "join_url": None,
            },
        }


class RecurrencePattern(IndalekoBaseModel):
    """Model representing a calendar event recurrence pattern"""

    type: EventRecurrence
    interval: int = 1  # How often the pattern repeats (e.g., every 2 weeks)
    day_of_week: list[int] | None = None  # 0=Sunday, 1=Monday, etc.
    day_of_month: int | None = None
    month_of_year: int | None = None
    first_date: datetime
    until_date: datetime | None = None
    occurrence_count: int | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "type": "weekly",
                "interval": 1,
                "day_of_week": [1],  # Monday
                "day_of_month": None,
                "month_of_year": None,
                "first_date": "2023-01-01T10:00:00Z",
                "until_date": "2023-12-31T10:00:00Z",
                "occurrence_count": None,
            },
        }


class EventAttachment(IndalekoBaseModel):
    """Model representing an attachment to a calendar event"""

    name: str
    content_type: str
    uri: str | None = None
    size: int | None = None
    last_modified: datetime | None = None
    file_id: str | None = None  # Provider-specific identifier

    class Config:
        json_schema_extra = {
            "example": {
                "name": "agenda.docx",
                "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "uri": "https://example.com/files/agenda.docx",
                "size": 25600,
                "last_modified": "2023-05-15T09:30:00Z",
                "file_id": "12345abcde",
            },
        }


class CalendarEvent(BaseCollaborationDataModel):
    """
    Model representing a calendar event from services like Microsoft Outlook or Google Calendar.
    Extends the base collaboration data model to fit into Indaleko's activity tracking system.
    """

    # Event identifiers
    event_id: str  # The original ID from the calendar provider
    provider_name: str  # "outlook", "google", etc.
    calendar_id: str  # The ID of the calendar containing this event

    # Event basic details
    subject: str
    body: str | None = None
    body_type: str | None = None  # "text" or "html"
    start_time: datetime
    end_time: datetime
    is_all_day: bool = False

    # Status and importance
    status: EventStatus = EventStatus.CONFIRMED
    sensitivity: str | None = None  # "normal", "personal", "private", "confidential"
    importance: str | None = None  # "low", "normal", "high"

    # Recurrence
    is_recurring: bool = False
    recurrence: RecurrencePattern | None = None
    series_master_id: str | None = None  # If this is a recurring instance, the ID of the master
    instance_index: int | None = None  # For recurring events, which occurrence this is

    # People
    organizer: EventAttendee
    attendees: list[EventAttendee] = []

    # Location
    location: EventLocation | None = None

    # Content
    categories: list[str] = []
    has_attachments: bool = False
    attachments: list[EventAttachment] = []
    related_files: list[SharedFileData] = []  # Links to files shared during the meeting

    # Meeting-specific
    is_online_meeting: bool = False
    online_meeting_provider: str | None = None  # "teams", "zoom", "webex", etc.
    join_url: str | None = None  # URL to join the meeting

    # Timestamps
    created_time: datetime
    last_modified_time: datetime

    # User's relationship to this event
    is_organizer: bool = False
    response_status: EventResponse = EventResponse.NOT_RESPONDED

    # Indaleko specific
    event_uuid: UUID = None

    def __init__(self, **data):
        super().__init__(**data)
        # Ensure event_uuid is set
        if not self.event_uuid:
            self.event_uuid = uuid4()

        # Ensure timestamps have timezone
        if self.created_time.tzinfo is None:
            self.created_time = self.created_time.replace(tzinfo=UTC)
        if self.last_modified_time.tzinfo is None:
            self.last_modified_time = self.last_modified_time.replace(
                tzinfo=UTC,
            )
        if self.start_time.tzinfo is None:
            self.start_time = self.start_time.replace(tzinfo=UTC)
        if self.end_time.tzinfo is None:
            self.end_time = self.end_time.replace(tzinfo=UTC)

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "AAMkADE1YjPTE0ZDEtZGQ5ZC00MzI1LTg1ZGUtY2U3MGRjZWRkN2RkOgBGAAAAAAAhYw7Rg9d6SpfyL0LaGimMBwDRo9ZkALTmQLr8D7L3Jf4lAAAAAAENAADRo9ZkALTmQLr8D7L3Jf4lAABhG7SEAAA=",
                "provider_name": "outlook",
                "calendar_id": "AQMkADE1YjU3YjE0LWRkOWMtNDMyNS04NWRlLWNlNzBkY2VkZDdkZAAuAAADIWMO0YPXekqX8i9C2hopjAEA0aPWZAC05kC6_A-y9yX-JQAAAgENAAAA",
                "subject": "Team Planning Meeting",
                "body": "Let's discuss our Q2 goals and projects.",
                "body_type": "text",
                "start_time": "2023-06-01T14:00:00Z",
                "end_time": "2023-06-01T15:00:00Z",
                "is_all_day": False,
                "status": "confirmed",
                "sensitivity": "normal",
                "importance": "normal",
                "is_recurring": True,
                "recurrence": {
                    "type": "weekly",
                    "interval": 1,
                    "day_of_week": [3],  # Wednesday
                    "first_date": "2023-06-01T14:00:00Z",
                    "until_date": "2023-12-31T14:00:00Z",
                },
                "organizer": {
                    "email": "organizer@example.com",
                    "name": "Jane Smith",
                    "response": "organizer",
                    "required": True,
                    "organizer": True,
                },
                "attendees": [
                    {
                        "email": "attendee1@example.com",
                        "name": "John Doe",
                        "response": "accepted",
                        "required": True,
                        "organizer": False,
                    },
                    {
                        "email": "attendee2@example.com",
                        "name": "Alice Johnson",
                        "response": "tentative",
                        "required": False,
                        "organizer": False,
                    },
                ],
                "location": {
                    "display_name": "Conference Room B",
                    "is_virtual": True,
                    "join_url": "https://teams.microsoft.com/l/meetup-join/...",
                },
                "categories": ["Planning", "Team"],
                "has_attachments": True,
                "attachments": [
                    {
                        "name": "Q2_Goals.pptx",
                        "content_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        "size": 2560000,
                    },
                ],
                "is_online_meeting": True,
                "online_meeting_provider": "teams",
                "join_url": "https://teams.microsoft.com/l/meetup-join/...",
                "created_time": "2023-05-25T10:15:00Z",
                "last_modified_time": "2023-05-28T15:30:00Z",
                "is_organizer": False,
                "response_status": "accepted",
            },
        }
