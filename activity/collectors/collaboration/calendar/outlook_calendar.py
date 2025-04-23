"""
Microsoft Outlook Calendar activity collector for Indaleko.

This module provides functionality to collect calendar events from Microsoft Outlook Calendar
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

import msal
import requests

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


class OutlookCalendarCollector(CalendarCollectorBase):
    """Microsoft Outlook Calendar activity collector for Indaleko.

    This class collects calendar events from Microsoft Outlook Calendar using
    Microsoft Graph API.
    """

    # Define scopes needed for Microsoft Graph API
    SCOPES = ["Calendars.Read", "User.Read"]

    # Microsoft Graph API endpoint
    GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"

    def __init__(self, **kwargs):
        """Initialize the Outlook Calendar collector.

        Args:
            client_id: Microsoft application (client) ID
            tenant_id: Microsoft tenant ID (use 'common' for multi-tenant apps)
            config_path: Path to the configuration file
            token_path: Path to store/retrieve the authentication token
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)

        # Provider ID for Outlook Calendar
        self._provider_id = uuid.UUID("d4b2e8c3-5a7f-42e9-9b6d-8f1e2a3b4c5d")
        self._name = "Outlook Calendar Collector"

        # Configuration paths
        self.config_path = kwargs.get(
            "config_path",
            os.path.join(
                os.environ.get("INDALEKO_ROOT"),
                "config",
                "outlook_calendar_config.json",
            ),
        )
        self.token_path = kwargs.get(
            "token_path",
            os.path.join(
                os.environ.get("INDALEKO_ROOT"), "config", "outlook_calendar_token.json",
            ),
        )

        # Make sure directories exist
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.token_path), exist_ok=True)

        # Load config or use provided values
        self.config = self._load_config()

        # Client configuration
        self.client_id = kwargs.get("client_id", self.config.get("client_id"))
        self.client_secret = kwargs.get(
            "client_secret", self.config.get("client_secret"),
        )
        self.tenant_id = kwargs.get("tenant_id", self.config.get("tenant_id", "common"))
        self.redirect_uri = kwargs.get(
            "redirect_uri", self.config.get("redirect_uri", "http://localhost:8000"),
        )

        # MSAL app and authentication state
        self.app = None
        self.token_cache = msal.SerializableTokenCache()
        self._load_token_cache()

        # Current user information
        self.user_info = None

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from file.

        Returns:
            Dict[str, Any]: Configuration dictionary
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path) as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading config: {e}")

        return {}

    def _save_config(self, config: dict[str, Any]) -> None:
        """Save configuration to file.

        Args:
            config: Configuration dictionary
        """
        try:
            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")

    def _load_token_cache(self) -> None:
        """Load token cache from file."""
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path) as f:
                    self.token_cache.deserialize(f.read())
            except Exception as e:
                self.logger.error(f"Error loading token cache: {e}")

    def _save_token_cache(self) -> None:
        """Save token cache to file."""
        if self.token_cache.has_state_changed:
            try:
                with open(self.token_path, "w") as f:
                    f.write(self.token_cache.serialize())
            except Exception as e:
                self.logger.error(f"Error saving token cache: {e}")

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

    def authenticate(self) -> bool:
        """Authenticate with Microsoft Graph API.

        Returns:
            bool: True if authentication was successful, False otherwise
        """
        try:
            # Check if required configuration is available
            if not self.client_id or not self.client_secret:
                self.logger.error("Microsoft Graph API credentials not found")
                self.logger.error(
                    "Please provide client_id and client_secret or configure outlook_calendar_config.json",
                )
                return False

            # Create MSAL app
            self.app = msal.ConfidentialClientApplication(
                client_id=self.client_id,
                client_credential=self.client_secret,
                authority=f"https://login.microsoftonline.com/{self.tenant_id}",
                token_cache=self.token_cache,
            )

            # Try to get token silently first
            accounts = self.app.get_accounts()
            result = None

            if accounts:
                result = self.app.acquire_token_silent(self.SCOPES, account=accounts[0])

            # If silent acquisition fails, do interactive authentication
            if not result:
                # Generate auth URL
                auth_url = self.app.get_authorization_request_url(
                    scopes=self.SCOPES, redirect_uri=self.redirect_uri,
                )

                print("\nPlease open the following URL in your browser:")
                print(auth_url)
                print(
                    "\nAfter authenticating, copy the redirect URL containing the code parameter.",
                )

                auth_code = input("\nPaste the full redirect URL: ")

                # Extract code from URL
                if "code=" in auth_code:
                    code = auth_code.split("code=")[1].split("&")[0]
                else:
                    code = auth_code  # Assume they just pasted the code

                # Get token with code
                result = self.app.acquire_token_by_authorization_code(
                    code=code, scopes=self.SCOPES, redirect_uri=self.redirect_uri,
                )

            # Save token cache
            self._save_token_cache()

            # Check if token was obtained
            if not result or "access_token" not in result:
                error = result.get("error", "unknown error")
                error_desc = result.get("error_description", "No error description")
                self.logger.error(f"Authentication failed: {error} - {error_desc}")
                return False

            # Get user info
            self.user_info = self._get_user_info(result["access_token"])

            return True

        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False

    def _get_user_info(self, token: str) -> dict[str, Any]:
        """Get user information from Microsoft Graph API.

        Args:
            token: Access token

        Returns:
            Dict[str, Any]: User information
        """
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            response = requests.get(f"{self.GRAPH_API_ENDPOINT}/me", headers=headers)

            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(
                    f"Error getting user info: {response.status_code} - {response.text}",
                )
                return {}

        except Exception as e:
            self.logger.error(f"Error getting user info: {e}")
            return {}

    def _get_access_token(self) -> str | None:
        """Get a valid access token for Microsoft Graph API.

        Returns:
            Optional[str]: Access token or None if authentication fails
        """
        try:
            # Try to get token silently
            accounts = self.app.get_accounts()
            if accounts:
                result = self.app.acquire_token_silent(self.SCOPES, account=accounts[0])
                if result and "access_token" in result:
                    return result["access_token"]

            # If token acquisition fails, try to refresh
            self.logger.info("Token expired or not available. Re-authenticating...")
            if self.authenticate():
                accounts = self.app.get_accounts()
                if accounts:
                    result = self.app.acquire_token_silent(
                        self.SCOPES, account=accounts[0],
                    )
                    if result and "access_token" in result:
                        return result["access_token"]

            return None

        except Exception as e:
            self.logger.error(f"Error getting access token: {e}")
            return None

    def get_calendars(self) -> list[dict[str, Any]]:
        """Get a list of available calendars.

        Returns:
            List[Dict[str, Any]]: List of calendar information dictionaries
        """
        try:
            # Get access token
            token = self._get_access_token()
            if not token:
                self.logger.error("Failed to get access token")
                return []

            # Set up headers
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            # Get calendars
            response = requests.get(
                f"{self.GRAPH_API_ENDPOINT}/me/calendars", headers=headers,
            )

            if response.status_code != 200:
                self.logger.error(
                    f"Error retrieving calendars: {response.status_code} - {response.text}",
                )
                return []

            # Process response
            calendars_data = response.json().get("value", [])

            # Clear the cache
            self._calendars_cache = {}

            # Process calendars
            result = []
            for calendar in calendars_data:
                calendar_id = calendar.get("id")
                self._calendars_cache[calendar_id] = calendar

                result.append(
                    {
                        "id": calendar_id,
                        "name": calendar.get("name", "Unknown"),
                        "color": calendar.get("color", "auto"),
                        "can_edit": calendar.get("canEdit", False),
                        "can_share": calendar.get("canShare", False),
                        "is_default": calendar.get("isDefaultCalendar", False),
                        "owner": calendar.get("owner", {}).get("name", ""),
                    },
                )

            return result

        except Exception as e:
            self.logger.error(f"Error retrieving calendars: {e}")
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
        try:
            # Get access token
            token = self._get_access_token()
            if not token:
                self.logger.error("Failed to get access token")
                return []

            # Set up headers
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Prefer": 'outlook.timezone="UTC"',
            }

            # Build query parameters
            params = {}
            filter_parts = []

            # Add time filters
            if start_time:
                start_time_str = start_time.isoformat()
                filter_parts.append(f"start/dateTime ge '{start_time_str}'")

            if end_time:
                end_time_str = end_time.isoformat()
                filter_parts.append(f"end/dateTime le '{end_time_str}'")

            if updated_since:
                updated_since_str = updated_since.isoformat()
                filter_parts.append(f"lastModifiedDateTime ge '{updated_since_str}'")

            # Combine filter parts
            if filter_parts:
                params["$filter"] = " and ".join(filter_parts)

            # Add expansion for recurring events
            params["$expand"] = "extensions"

            # Add select fields
            params["$select"] = (
                "id,subject,bodyPreview,body,importance,sensitivity,start,end,location,"
                "locations,attendees,organizer,recurrence,isAllDay,isCancelled,isOnlineMeeting,"
                "onlineMeetingProvider,onlineMeeting,categories,hasAttachments,attachments,"
                "createdDateTime,lastModifiedDateTime,changeKey,showAs"
            )

            # Add order
            params["$orderby"] = "start/dateTime asc"

            # Add top (max results)
            if max_results:
                params["$top"] = min(max_results, 100)  # Graph API limits to 100

            # Get events
            response = requests.get(
                f"{self.GRAPH_API_ENDPOINT}/me/calendars/{calendar_id}/events",
                headers=headers,
                params=params,
            )

            if response.status_code != 200:
                self.logger.error(
                    f"Error retrieving events: {response.status_code} - {response.text}",
                )
                return []

            # Get events from response
            events_data = response.json().get("value", [])

            # Get attachments for each event
            for event in events_data:
                if event.get("hasAttachments", False):
                    event_id = event.get("id")

                    # Get attachments
                    attachments_response = requests.get(
                        f"{self.GRAPH_API_ENDPOINT}/me/calendars/{calendar_id}/events/{event_id}/attachments",
                        headers=headers,
                    )

                    if attachments_response.status_code == 200:
                        event["attachments"] = attachments_response.json().get(
                            "value", [],
                        )
                    else:
                        self.logger.warning(
                            f"Failed to get attachments for event {event_id}",
                        )
                        event["attachments"] = []
                else:
                    event["attachments"] = []

            return events_data

        except Exception as e:
            self.logger.error(f"Error retrieving events: {e}")
            return []

    def get_event_details(self, calendar_id: str, event_id: str) -> dict[str, Any]:
        """Get detailed information about a specific event.

        Args:
            calendar_id: ID of the calendar containing the event
            event_id: ID of the event to retrieve

        Returns:
            Dict[str, Any]: Event details dictionary
        """
        try:
            # Get access token
            token = self._get_access_token()
            if not token:
                self.logger.error("Failed to get access token")
                return {}

            # Set up headers
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Prefer": 'outlook.timezone="UTC"',
            }

            # Get event details
            response = requests.get(
                f"{self.GRAPH_API_ENDPOINT}/me/calendars/{calendar_id}/events/{event_id}",
                headers=headers,
                params={
                    "$expand": "extensions",
                    "$select": "id,subject,bodyPreview,body,importance,sensitivity,start,end,location,"
                    "locations,attendees,organizer,recurrence,isAllDay,isCancelled,isOnlineMeeting,"
                    "onlineMeetingProvider,onlineMeeting,categories,hasAttachments,attachments,"
                    "createdDateTime,lastModifiedDateTime,changeKey,showAs",
                },
            )

            if response.status_code != 200:
                self.logger.error(
                    f"Error retrieving event details: {response.status_code} - {response.text}",
                )
                return {}

            # Get event data
            event_data = response.json()

            # Get attachments
            if event_data.get("hasAttachments", False):
                # Get attachments
                attachments_response = requests.get(
                    f"{self.GRAPH_API_ENDPOINT}/me/calendars/{calendar_id}/events/{event_id}/attachments",
                    headers=headers,
                )

                if attachments_response.status_code == 200:
                    event_data["attachments"] = attachments_response.json().get(
                        "value", [],
                    )
                else:
                    self.logger.warning(
                        f"Failed to get attachments for event {event_id}",
                    )
                    event_data["attachments"] = []
            else:
                event_data["attachments"] = []

            return event_data

        except Exception as e:
            self.logger.error(f"Error retrieving event details: {e}")
            return {}

    def convert_to_calendar_event(
        self, event_data: dict[str, Any], calendar_id: str,
    ) -> CalendarEvent:
        """Convert Outlook Calendar event data to CalendarEvent model.

        Args:
            event_data: Outlook Calendar event data dictionary
            calendar_id: ID of the calendar containing the event

        Returns:
            CalendarEvent: Converted event model
        """
        try:
            # Get calendar info (if available)
            calendar_info = self._calendars_cache.get(calendar_id, {})
            calendar_name = calendar_info.get("name", "Unknown Calendar")

            # Extract basic event details
            event_id = event_data.get("id", "")
            subject = event_data.get("subject", "Untitled Event")

            # Get event body
            body_data = event_data.get("body", {})
            body = body_data.get("content", "")
            body_type = body_data.get("contentType", "text").lower()

            # Get event times
            start_data = event_data.get("start", {})
            end_data = event_data.get("end", {})

            # Parse times
            start_time_str = start_data.get("dateTime", "")
            start_timezone = start_data.get("timeZone", "UTC")

            end_time_str = end_data.get("dateTime", "")
            end_timezone = end_data.get("timeZone", "UTC")

            # Convert to datetime objects
            start_time = datetime.datetime.fromisoformat(start_time_str)
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=datetime.UTC)

            end_time = datetime.datetime.fromisoformat(end_time_str)
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=datetime.UTC)

            # Check if all-day event
            is_all_day = event_data.get("isAllDay", False)

            # Get status (cancelled or not)
            is_cancelled = event_data.get("isCancelled", False)
            status = EventStatus.CANCELLED if is_cancelled else EventStatus.CONFIRMED

            # Get sensitivity
            sensitivity = event_data.get("sensitivity", "normal").lower()

            # Get importance
            importance = event_data.get("importance", "normal").lower()

            # Get recurrence information
            recurrence_data = event_data.get("recurrence")
            is_recurring = recurrence_data is not None
            recurrence = None

            if is_recurring:
                # Get pattern data
                pattern = recurrence_data.get("pattern", {})
                range_data = recurrence_data.get("range", {})

                # Get recurrence type
                type_str = pattern.get("type", "").lower()
                recurrence_type_map = {
                    "daily": EventRecurrence.DAILY,
                    "weekly": EventRecurrence.WEEKLY,
                    "absolutemonthly": EventRecurrence.MONTHLY,
                    "relativeMonthly": EventRecurrence.MONTHLY,
                    "absoluteyearly": EventRecurrence.YEARLY,
                    "relativeyearly": EventRecurrence.YEARLY,
                }
                recurrence_type = recurrence_type_map.get(
                    type_str, EventRecurrence.CUSTOM,
                )

                # Get interval
                interval = pattern.get("interval", 1)

                # Get days of week (for weekly recurrence)
                day_of_week = None
                if "daysOfWeek" in pattern:
                    days = pattern.get("daysOfWeek", [])
                    day_map = {
                        "sunday": 0,
                        "monday": 1,
                        "tuesday": 2,
                        "wednesday": 3,
                        "thursday": 4,
                        "friday": 5,
                        "saturday": 6,
                    }
                    day_of_week = [day_map.get(day.lower(), 0) for day in days]

                # Get day of month (for monthly recurrence)
                day_of_month = pattern.get("dayOfMonth")

                # Get range information
                range_type = range_data.get("type", "").lower()
                range_start_date = range_data.get("startDate", "")
                range_end_date = range_data.get("endDate", "")

                # Parse range dates
                if range_start_date:
                    first_date = datetime.datetime.fromisoformat(range_start_date)
                    if first_date.tzinfo is None:
                        first_date = first_date.replace(tzinfo=datetime.UTC)
                else:
                    first_date = start_time

                # Parse end date if available
                until_date = None
                if range_end_date:
                    until_date = datetime.datetime.fromisoformat(range_end_date)
                    if until_date.tzinfo is None:
                        until_date = until_date.replace(tzinfo=datetime.UTC)

                # Get occurrence count
                occurrence_count = range_data.get("numberOfOccurrences")
                if range_type != "numbered" or not occurrence_count:
                    occurrence_count = None

                # Create recurrence pattern
                recurrence = RecurrencePattern(
                    type=recurrence_type,
                    interval=interval,
                    day_of_week=day_of_week,
                    day_of_month=day_of_month,
                    first_date=first_date,
                    until_date=until_date,
                    occurrence_count=occurrence_count,
                )

            # Get organizer information
            organizer_data = event_data.get("organizer", {}).get("emailAddress", {})
            organizer_email = organizer_data.get("address", "")
            organizer_name = organizer_data.get("name", "")

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
                email_data = attendee_data.get("emailAddress", {})
                attendee_email = email_data.get("address", "")
                attendee_name = email_data.get("name", "")

                # Skip organizer (already included)
                if attendee_email == organizer_email:
                    continue

                # Get response status
                status_str = (
                    attendee_data.get("status", {})
                    .get("response", "notResponded")
                    .lower()
                )
                response_map = {
                    "accepted": EventResponse.ACCEPTED,
                    "tentativelyaccepted": EventResponse.TENTATIVE,
                    "declined": EventResponse.DECLINED,
                    "notresponded": EventResponse.NOT_RESPONDED,
                }
                response = response_map.get(status_str, EventResponse.NOT_RESPONDED)

                # Get attendee type
                type_str = attendee_data.get("type", "required").lower()
                required = type_str == "required"

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
            location_data = event_data.get("location", {})
            location_str = location_data.get("displayName", "")

            # Check if this is an online meeting
            is_online_meeting = event_data.get("isOnlineMeeting", False)
            online_meeting_provider = None
            join_url = None

            if is_online_meeting:
                # Get provider
                provider_str = event_data.get("onlineMeetingProvider", "").lower()
                if provider_str:
                    online_meeting_provider = provider_str

                # Get join URL
                online_meeting_data = event_data.get("onlineMeeting", {})
                join_url = online_meeting_data.get("joinUrl", "")

            # Create location
            location = None
            if location_str or is_online_meeting:
                # Get physical address if available
                address = None
                if "address" in location_data:
                    address_data = location_data.get("address", {})
                    address_parts = [
                        address_data.get("street", ""),
                        address_data.get("city", ""),
                        address_data.get("state", ""),
                        address_data.get("postalCode", ""),
                        address_data.get("countryOrRegion", ""),
                    ]
                    address = ", ".join(filter(None, address_parts))

                # Get coordinates if available
                coordinates = None
                if "coordinates" in location_data:
                    coord_data = location_data.get("coordinates", {})
                    latitude = coord_data.get("latitude")
                    longitude = coord_data.get("longitude")
                    if latitude is not None and longitude is not None:
                        coordinates = {"latitude": latitude, "longitude": longitude}

                location = EventLocation(
                    display_name=location_str,
                    address=address,
                    coordinates=coordinates,
                    is_virtual=is_online_meeting,
                    join_url=join_url,
                )

            # Get attachments
            attachments = []
            for attachment_data in event_data.get("attachments", []):
                name = attachment_data.get("name", "Untitled")
                content_type = attachment_data.get("contentType", "")
                size = attachment_data.get("size", 0)

                # Get file ID and URI
                file_id = attachment_data.get("id", "")
                uri = None
                if (
                    attachment_data.get("@odata.type", "")
                    == "#microsoft.graph.referenceAttachment"
                ):
                    uri = attachment_data.get(
                        "referenceAttachmentLastModifiedDateTime", "",
                    )

                attachments.append(
                    EventAttachment(
                        name=name,
                        content_type=content_type,
                        uri=uri,
                        size=size,
                        file_id=file_id,
                    ),
                )

            # Get timestamps
            created_time_str = event_data.get("createdDateTime", "")
            updated_time_str = event_data.get("lastModifiedDateTime", "")

            created_time = datetime.datetime.fromisoformat(created_time_str)
            if created_time.tzinfo is None:
                created_time = created_time.replace(tzinfo=datetime.UTC)

            updated_time = datetime.datetime.fromisoformat(updated_time_str)
            if updated_time.tzinfo is None:
                updated_time = updated_time.replace(tzinfo=datetime.UTC)

            # Determine if the current user is the organizer
            is_organizer = False
            if self.user_info:
                user_email = self.user_info.get("mail") or self.user_info.get(
                    "userPrincipalName",
                )
                is_organizer = user_email == organizer_email

            # Get the current user's response status
            user_response = (
                EventResponse.ORGANIZER if is_organizer else EventResponse.NOT_RESPONDED
            )

            # Check attendees for the current user's response
            if not is_organizer and self.user_info:
                user_email = self.user_info.get("mail") or self.user_info.get(
                    "userPrincipalName",
                )
                for attendee_data in event_data.get("attendees", []):
                    email_data = attendee_data.get("emailAddress", {})
                    if email_data.get("address") == user_email:
                        status_str = (
                            attendee_data.get("status", {})
                            .get("response", "notResponded")
                            .lower()
                        )
                        response_map = {
                            "accepted": EventResponse.ACCEPTED,
                            "tentativelyaccepted": EventResponse.TENTATIVE,
                            "declined": EventResponse.DECLINED,
                            "notresponded": EventResponse.NOT_RESPONDED,
                        }
                        user_response = response_map.get(
                            status_str, EventResponse.NOT_RESPONDED,
                        )
                        break

            # Get categories
            categories = event_data.get("categories", [])

            # Create CalendarEvent
            calendar_event = CalendarEvent(
                # Event identifiers
                event_id=event_id,
                provider_name="outlook",
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
                categories=categories,
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

            return calendar_event

        except Exception as e:
            self.logger.error(f"Error converting event: {e}")
            return None
