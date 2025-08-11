"""
Google Calendar activity collector for Indaleko.

This module provides functionality to collect calendar events from Google Calendar
for inclusion in Indaleko's activity database.

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
import os
import sys
import uuid

from typing import Any


try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

# Ensure INDALEKO_ROOT is available
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Indaleko imports
from activity.collectors.collaboration.calendar.base import CalendarCollectorBase
from activity.collectors.collaboration.data_models.calendar_event import (
    CalendarEvent,
    EventAttachment,
    EventAttendee,
    EventLocation,
    EventRecurrence,
    EventResponse,
    EventStatus,
    RecurrencePattern,
)


class GoogleCalendarCollector(CalendarCollectorBase):
    """Google Calendar activity collector for Indaleko.

    This class collects calendar events from Google Calendar using the Google Calendar API.
    """

    # Define scopes needed for Google Calendar API
    SCOPES = [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
    ]

    def __init__(self, **kwargs) -> None:
        """Initialize the Google Calendar collector.

        Args:
            config_path: Path to the Google Calendar API credentials JSON file
            token_path: Path to store/retrieve the authentication token
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)

        # Provider ID for Google Calendar
        self._provider_id = uuid.UUID("f5f8a1e0-6d1c-4f3a-b7d8-3c3a80a7e1d2")
        self._name = "Google Calendar Collector"

        # Check if Google API is available
        if not GOOGLE_API_AVAILABLE:
            self.logger.error(
                "Google API libraries not available. Please install required packages.",
            )
            self.logger.error(
                "pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib",
            )
            raise ImportError("Required Google API libraries not available")

        # Configuration paths
        self.config_path = kwargs.get(
            "config_path",
            os.path.join(
                os.environ.get("INDALEKO_ROOT"),
                "config",
                "gcalendar_config.json",
            ),
        )
        self.token_path = kwargs.get(
            "token_path",
            os.path.join(
                os.environ.get("INDALEKO_ROOT"),
                "config",
                "gcalendar_token.json",
            ),
        )

        # Make sure directories exist
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.token_path), exist_ok=True)

        # Google Calendar API client
        self.service = None
        self.credentials = None

        # User info
        self.user_email = None
        self.user_name = None

    def get_collector_name(self) -> str:
        """Get the name of the collector.

        Returns:
            str: Collector name
        """
        return self._name

    def get_provider_id(self) -> uuid.UUID:
        """Get the provider ID.

        Returns:
            uuid.UUID: Provider ID
        """
        return self._provider_id

    def load_credentials(self) -> Credentials | None:
        """Load Google API credentials from token file or via OAuth flow.

        Returns:
            Optional[Credentials]: Google API credentials or None if authentication fails
        """
        creds = None

        # Check if token file exists
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path) as token_file:
                    token_info = json.load(token_file)
                    creds = Credentials.from_authorized_user_info(
                        token_info,
                        self.SCOPES,
                    )
            except Exception as e:
                self.logger.exception(f"Error loading token file: {e}")
                # If token is corrupted, we'll recreate it

        # If no valid credentials or they're expired
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    # Refresh the token
                    creds.refresh(Request())
                except Exception as e:
                    self.logger.exception(f"Error refreshing token: {e}")
                    # If refresh fails, we'll recreate it
                    creds = None

            # If still no valid credentials, run the OAuth flow
            if not creds:
                if not os.path.exists(self.config_path):
                    self.logger.error(
                        f"Google Calendar API config file not found: {self.config_path}",
                    )
                    self.logger.error(
                        "Please download OAuth 2.0 Client ID credentials from Google Cloud Console",
                    )
                    self.logger.error(
                        "and save them as 'gcalendar_config.json' in the config directory",
                    )
                    return None

                try:
                    # Run the OAuth flow
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.config_path,
                        self.SCOPES,
                    )
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    self.logger.exception(f"Error running OAuth flow: {e}")
                    return None

            # Save the credentials for future use
            try:
                with open(self.token_path, "w") as token_file:
                    token_info = json.loads(creds.to_json())
                    json.dump(token_info, token_file)
            except Exception as e:
                self.logger.exception(f"Error saving token: {e}")

        return creds

    def authenticate(self) -> bool:
        """Authenticate with Google Calendar API.

        Returns:
            bool: True if authentication was successful, False otherwise
        """
        try:
            # Load credentials
            self.credentials = self.load_credentials()
            if not self.credentials:
                return False

            # Build the service
            self.service = build("calendar", "v3", credentials=self.credentials)

            # Get user information
            user_info_service = build("oauth2", "v2", credentials=self.credentials)
            user_info = user_info_service.userinfo().get().execute()
            self.user_email = user_info.get("email")
            self.user_name = user_info.get("name")

            return True

        except Exception as e:
            self.logger.exception(f"Authentication error: {e}")
            return False

    def get_calendars(self) -> list[dict[str, Any]]:
        """Get a list of available calendars.

        Returns:
            List[Dict[str, Any]]: List of calendar information dictionaries
        """
        if not self.service:
            self.logger.error("Not authenticated. Call authenticate() first.")
            return []

        try:
            # Clear the cache
            self._calendars_cache = {}

            # Get calendar list
            calendars_result = self.service.calendarList().list().execute()
            calendars = calendars_result.get("items", [])

            # Process calendars
            result = []
            for calendar in calendars:
                calendar_id = calendar.get("id")
                self._calendars_cache[calendar_id] = calendar

                result.append(
                    {
                        "id": calendar_id,
                        "name": calendar.get("summary", "Unknown"),
                        "description": calendar.get("description", ""),
                        "primary": calendar.get("primary", False),
                        "access_role": calendar.get("accessRole", ""),
                        "color": calendar.get("backgroundColor", ""),
                    },
                )

            return result

        except HttpError as e:
            self.logger.exception(f"Error retrieving calendars: {e}")
            return []

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
        if not self.service:
            self.logger.error("Not authenticated. Call authenticate() first.")
            return []

        try:
            # Set up query parameters
            params = {
                "calendarId": calendar_id,
                "singleEvents": True,  # Expand recurring events
                "orderBy": "startTime",
            }

            # Add time filters
            if start_time:
                params["timeMin"] = start_time.isoformat()
            if end_time:
                params["timeMax"] = end_time.isoformat()
            if updated_since:
                params["updatedMin"] = updated_since.isoformat()

            # Add max results
            if max_results:
                params["maxResults"] = max_results

            # Execute query
            events_result = self.service.events().list(**params).execute()
            return events_result.get("items", [])


        except HttpError as e:
            self.logger.exception(f"Error retrieving events: {e}")
            return []

    def get_event_details(self, calendar_id: str, event_id: str) -> dict[str, Any]:
        """Get detailed information about a specific event.

        Args:
            calendar_id: ID of the calendar containing the event
            event_id: ID of the event to retrieve

        Returns:
            Dict[str, Any]: Event details dictionary
        """
        if not self.service:
            self.logger.error("Not authenticated. Call authenticate() first.")
            return {}

        try:
            # Get the event
            return self.service.events().get(calendarId=calendar_id, eventId=event_id).execute()


        except HttpError as e:
            self.logger.exception(f"Error retrieving event details: {e}")
            return {}

    def convert_to_calendar_event(
        self,
        event_data: dict[str, Any],
        calendar_id: str,
    ) -> CalendarEvent:
        """Convert Google Calendar event data to CalendarEvent model.

        Args:
            event_data: Google Calendar event data dictionary
            calendar_id: ID of the calendar containing the event

        Returns:
            CalendarEvent: Converted event model
        """
        try:
            # Get calendar info (if available)
            calendar_info = self._calendars_cache.get(calendar_id, {})
            calendar_info.get("summary", "Unknown Calendar")

            # Extract basic event details
            event_id = event_data.get("id", "")
            subject = event_data.get("summary", "Untitled Event")

            # Get event body
            body = event_data.get("description", "")
            body_type = "html" if "<" in body and ">" in body else "text"

            # Get event times
            start_data = event_data.get("start", {})
            end_data = event_data.get("end", {})

            # Handle all-day events
            is_all_day = "date" in start_data and "date" in end_data

            if is_all_day:
                # All-day event
                start_str = start_data.get("date")
                end_str = end_data.get("date")

                # Parse dates and convert to datetime with timezone
                start_time = datetime.datetime.fromisoformat(start_str)
                start_time = datetime.datetime.combine(
                    start_time.date(),
                    datetime.time(0, 0, 0),
                    tzinfo=datetime.UTC,
                )

                end_time = datetime.datetime.fromisoformat(end_str)
                end_time = datetime.datetime.combine(
                    end_time.date(),
                    datetime.time(23, 59, 59),
                    tzinfo=datetime.UTC,
                )
            else:
                # Regular event with start/end times
                start_str = start_data.get("dateTime")
                end_str = end_data.get("dateTime")

                # Parse datetimes
                start_time = datetime.datetime.fromisoformat(start_str)
                end_time = datetime.datetime.fromisoformat(end_str)

            # Get status
            status_map = {
                "confirmed": EventStatus.CONFIRMED,
                "tentative": EventStatus.TENTATIVE,
                "cancelled": EventStatus.CANCELLED,
            }
            status = status_map.get(
                event_data.get("status", "confirmed"),
                EventStatus.UNKNOWN,
            )

            # Get importance (Google doesn't have direct importance, infer from colorId)
            color_id = event_data.get("colorId")
            importance = "high" if color_id in ["4", "11"] else "normal"  # Red or bold red

            # Get sensitivity
            visibility = event_data.get("visibility", "default")
            sensitivity_map = {
                "default": "normal",
                "public": "normal",
                "private": "private",
                "confidential": "confidential",
            }
            sensitivity = sensitivity_map.get(visibility, "normal")

            # Get recurrence information
            is_recurring = "recurrence" in event_data
            recurrence = None

            if is_recurring:
                recurrence_rules = event_data.get("recurrence", [])
                # Parse RRULE string
                for rule in recurrence_rules:
                    if rule.startswith("RRULE:"):
                        rrule = rule[6:]  # Remove RRULE: prefix
                        rrule_parts = dict(part.split("=") for part in rrule.split(";"))

                        # Determine recurrence type
                        freq = rrule_parts.get("FREQ", "").lower()
                        interval = int(rrule_parts.get("INTERVAL", "1"))

                        recurrence_type_map = {
                            "daily": EventRecurrence.DAILY,
                            "weekly": EventRecurrence.WEEKLY,
                            "monthly": EventRecurrence.MONTHLY,
                            "yearly": EventRecurrence.YEARLY,
                        }

                        recurrence_type = recurrence_type_map.get(
                            freq,
                            EventRecurrence.CUSTOM,
                        )

                        # Get day of week (for weekly recurrence)
                        day_of_week = None
                        if "BYDAY" in rrule_parts:
                            days = rrule_parts["BYDAY"].split(",")
                            day_map = {
                                "SU": 0,
                                "MO": 1,
                                "TU": 2,
                                "WE": 3,
                                "TH": 4,
                                "FR": 5,
                                "SA": 6,
                            }
                            day_of_week = [day_map.get(day[-2:], 0) for day in days]

                        # Get until date
                        until_date = None
                        if "UNTIL" in rrule_parts:
                            until_str = rrule_parts["UNTIL"]
                            # Parse YYYYMMDDTHHMMSSZ format
                            if "T" in until_str:
                                until_date = datetime.datetime.strptime(
                                    until_str,
                                    "%Y%m%dT%H%M%SZ",
                                ).replace(tzinfo=datetime.UTC)
                            else:
                                until_date = datetime.datetime.strptime(
                                    until_str,
                                    "%Y%m%d",
                                ).replace(tzinfo=datetime.UTC)

                        # Get occurrence count
                        occurrence_count = None
                        if "COUNT" in rrule_parts:
                            occurrence_count = int(rrule_parts["COUNT"])

                        # Create recurrence pattern
                        recurrence = RecurrencePattern(
                            type=recurrence_type,
                            interval=interval,
                            day_of_week=day_of_week,
                            first_date=start_time,
                            until_date=until_date,
                            occurrence_count=occurrence_count,
                        )

                        break

            # Get organizer information
            organizer_data = event_data.get("organizer", {})
            organizer_email = organizer_data.get("email", "")
            organizer_name = organizer_data.get("displayName", "")

            organizer = EventAttendee(
                email=organizer_email,
                name=organizer_name,
                response=EventResponse.ORGANIZER,
                required=True,
                organizer=True,
            )

            # Get attendees
            attendees = []
            for attendee_data in event_data.get("attendees", []):
                attendee_email = attendee_data.get("email", "")
                attendee_name = attendee_data.get("displayName", "")

                # Skip organizer (already included)
                if attendee_email == organizer_email:
                    continue

                # Get response status
                response_status = attendee_data.get("responseStatus", "needsAction")
                response_map = {
                    "accepted": EventResponse.ACCEPTED,
                    "tentative": EventResponse.TENTATIVE,
                    "declined": EventResponse.DECLINED,
                    "needsAction": EventResponse.NOT_RESPONDED,
                }
                response = response_map.get(
                    response_status,
                    EventResponse.NOT_RESPONDED,
                )

                # Get attendee type (required or optional)
                required = not attendee_data.get("optional", False)

                attendees.append(
                    EventAttendee(
                        email=attendee_email,
                        name=attendee_name,
                        response=response,
                        required=required,
                        organizer=False,
                    ),
                )

            # Get location
            location_str = event_data.get("location", "")

            # Check if it's an online meeting
            is_online_meeting = False
            online_meeting_provider = None
            join_url = None

            conference_data = event_data.get("conferenceData", {})
            if conference_data:
                is_online_meeting = True

                # Get provider
                provider = conference_data.get("conferenceSolution", {}).get("name", "")
                if "Hangouts" in provider or "Meet" in provider:
                    online_meeting_provider = "meet"
                elif "Zoom" in provider:
                    online_meeting_provider = "zoom"
                else:
                    online_meeting_provider = provider.lower() if provider else None

                # Get join link
                for entry_point in conference_data.get("entryPoints", []):
                    if entry_point.get("entryPointType") == "video":
                        join_url = entry_point.get("uri")
                        break

            # Create location
            location = None
            if location_str or is_online_meeting:
                location = EventLocation(
                    display_name=location_str,
                    is_virtual=is_online_meeting,
                    join_url=join_url,
                )

            # Get attachments
            attachments = []
            for attachment_data in event_data.get("attachments", []):
                file_name = attachment_data.get("title", "Untitled")
                file_url = attachment_data.get("fileUrl", "")
                file_id = attachment_data.get("fileId", "")
                mime_type = attachment_data.get("mimeType", "")

                attachments.append(
                    EventAttachment(
                        name=file_name,
                        content_type=mime_type,
                        uri=file_url,
                        file_id=file_id,
                    ),
                )

            # Get timestamps
            created_time_str = event_data.get("created")
            updated_time_str = event_data.get("updated")

            created_time = datetime.datetime.fromisoformat(created_time_str)
            updated_time = datetime.datetime.fromisoformat(updated_time_str)

            # Determine if the current user is the organizer
            is_organizer = self.user_email == organizer_email

            # Get the current user's response status
            user_response = EventResponse.ORGANIZER if is_organizer else EventResponse.NOT_RESPONDED

            # Check attendees for the current user's response
            if not is_organizer and self.user_email:
                for attendee_data in event_data.get("attendees", []):
                    if attendee_data.get("email") == self.user_email:
                        response_status = attendee_data.get(
                            "responseStatus",
                            "needsAction",
                        )
                        response_map = {
                            "accepted": EventResponse.ACCEPTED,
                            "tentative": EventResponse.TENTATIVE,
                            "declined": EventResponse.DECLINED,
                            "needsAction": EventResponse.NOT_RESPONDED,
                        }
                        user_response = response_map.get(
                            response_status,
                            EventResponse.NOT_RESPONDED,
                        )
                        break

            # Create CalendarEvent
            return CalendarEvent(
                # Event identifiers
                event_id=event_id,
                provider_name="google",
                calendar_id=calendar_id,
                # Event basic details
                subject=subject,
                body=body,
                body_type=body_type,
                start_time=start_time,
                end_time=end_time,
                is_all_day=is_all_day,
                # Status and importance
                status=status,
                sensitivity=sensitivity,
                importance=importance,
                # Recurrence
                is_recurring=is_recurring,
                recurrence=recurrence,
                # People
                organizer=organizer,
                attendees=attendees,
                # Location
                location=location,
                # Categories
                categories=event_data.get("colorId", []),
                # Attachments
                has_attachments=len(attachments) > 0,
                attachments=attachments,
                # Meeting-specific
                is_online_meeting=is_online_meeting,
                online_meeting_provider=online_meeting_provider,
                join_url=join_url,
                # Timestamps
                created_time=created_time,
                last_modified_time=updated_time,
                # User's relationship to this event
                is_organizer=is_organizer,
                response_status=user_response,
                # Activity base data
                provider_id=str(self._provider_id),
                data=json.dumps(event_data),
                occurrence_time=start_time,
            )


        except Exception as e:
            self.logger.exception(f"Error converting event: {e}")
            return None
