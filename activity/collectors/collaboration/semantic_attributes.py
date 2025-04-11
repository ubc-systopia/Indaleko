"""
This module defines known semantic attributes for collaboration activity data
providers.

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

# General collaboration activity types
ADP_COLLABORATION_MEETING = "cb44582e-351f-4e79-ac90-f709208ca225"
ADP_COLLABORATION_FILE_SHARE = "a51f65b0-44d0-4902-9b5b-5cb49cae15c3"
ADP_COLLABORATION_CHAT = "78aa8d40-ceec-4031-8865-823a13beb336"
ADP_COLLABORATION_EMAIL = "1258f2f2-53f4-443d-9170-a5dc46b05a4f"

# Calendar activity types
ADP_COLLABORATION_CALENDAR = "df45a3b2-c7e5-4f89-a1d3-6cb908e42a13"
ADP_COLLABORATION_GOOGLE_CALENDAR = "f5f8a1e0-6d1c-4f3a-b7d8-3c3a80a7e1d2"
ADP_COLLABORATION_OUTLOOK_CALENDAR = "d4b2e8c3-5a7f-42e9-9b6d-8f1e2a3b4c5d"
ADP_COLLABORATION_ICAL = "e9a8b7c6-5d4e-3f2a-1b0c-9d8e7f6a5b4c"

# Calendar event attributes
CALENDAR_EVENT_ID = "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6"
CALENDAR_EVENT_SUBJECT = "b2c3d4e5-f6a7-b8c9-d0e1-f2a3b4c5d6e7"
CALENDAR_EVENT_START_TIME = "c3d4e5f6-a7b8-c9d0-e1f2-a3b4c5d6e7f8"
CALENDAR_EVENT_END_TIME = "d4e5f6a7-b8c9-d0e1-f2a3-b4c5d6e7f8a9"
CALENDAR_EVENT_LOCATION = "e5f6a7b8-c9d0-e1f2-a3b4-c5d6e7f8a9b0"
CALENDAR_EVENT_ORGANIZER = "f6a7b8c9-d0e1-f2a3-b4c5-d6e7f8a9b0c1"
CALENDAR_EVENT_STATUS = "a7b8c9d0-e1f2-a3b4-c5d6-e7f8a9b0c1d2"
CALENDAR_EVENT_RECURRENCE = "b8c9d0e1-f2a3-b4c5-d6e7-f8a9b0c1d2e3"

# Calendar event operations
ADT_COLLABORATION_CALENDAR_CREATE = "a7b6c5d4-e3f2-1a0b-9c8d-7e6f5a4b3c2d"
ADT_COLLABORATION_CALENDAR_UPDATE = "b8c7d6e5-f4g3-2h1i-0j9k-8l7m6n5o4p3"
ADT_COLLABORATION_CALENDAR_DELETE = "c9d8e7f6-g5h4-i3j2-k1l0-m9n8o7p6q5r"
ADT_COLLABORATION_CALENDAR_RESPOND = "d0e9f8g7-h6i5-j4k3-l2m1-n0o9p8q7r6"
ADT_COLLABORATION_CALENDAR_ATTEND = "e1f0g9h8-i7j6-k5l4-m3n2-o1p0q9r8s7"

# Meeting-related attributes
CALENDAR_MEETING_TYPE = "c9d0e1f2-a3b4-c5d6-e7f8-a9b0c1d2e3f4"  # In-person, Teams, Zoom, etc.
CALENDAR_MEETING_URL = "d0e1f2a3-b4c5-d6e7-f8a9-b0c1d2e3f4a5"

# Attendee information
CALENDAR_EVENT_ATTENDEES = "e1f2a3b4-c5d6-e7f8-a9b0-c1d2e3f4a5b6"
CALENDAR_EVENT_RESPONSE = "f2a3b4c5-d6e7-f8a9-b0c1-d2e3f4a5b6c7"  # accepted, tentative, declined
