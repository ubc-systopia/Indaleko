"""
Enhanced calendar event generator for Indaleko.

This module provides comprehensive calendar event generation capabilities,
including meetings, appointments, and recurring events with attendees, 
locations, and realistic metadata.
"""

import os
import sys
import random
import uuid
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timezone, timedelta
import json
from enum import Enum

# Setup path for imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import tool interface
from tools.data_generator_enhanced.agents.data_gen.core.tools import Tool

# Import generators
from tools.data_generator_enhanced.agents.data_gen.tools.named_entity_generator import (
    EntityNameGenerator, IndalekoNamedEntityType
)

# Import semantic attribute registry and data models
try:
    # Try to import real registry and data models
    from tools.data_generator_enhanced.agents.data_gen.core.semantic_attributes import SemanticAttributeRegistry
    from data_models.base import IndalekoBaseModel
    from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
    from data_models.i_uuid import IndalekoUUIDDataModel
    from activity.collectors.collaboration.data_models.calendar_event import (
        EventRecurrence, EventStatus, EventResponse, EventAttendee, EventLocation,
        RecurrencePattern, EventAttachment, CalendarEvent
    )
    from activity.collectors.collaboration.semantic_attributes import (
        CALENDAR_EVENT_ID, CALENDAR_EVENT_SUBJECT, CALENDAR_EVENT_START_TIME,
        CALENDAR_EVENT_END_TIME, CALENDAR_EVENT_LOCATION, CALENDAR_EVENT_ORGANIZER,
        CALENDAR_EVENT_STATUS, CALENDAR_EVENT_RECURRENCE, CALENDAR_MEETING_TYPE,
        CALENDAR_MEETING_URL, CALENDAR_EVENT_ATTENDEES, CALENDAR_EVENT_RESPONSE,
        ADP_COLLABORATION_CALENDAR, ADP_COLLABORATION_GOOGLE_CALENDAR,
        ADP_COLLABORATION_OUTLOOK_CALENDAR, ADP_COLLABORATION_ICAL
    )
    from db.db_collections import IndalekoDBCollections
    from db.db_config import IndalekoDBConfig
    HAS_DB = True
except ImportError:
    # Create mock classes for testing
    HAS_DB = False
    
    class SemanticAttributeRegistry:
        """Mock registry for semantic attributes."""
        
        # Common domains for attributes
        DOMAIN_STORAGE = "storage"
        DOMAIN_ACTIVITY = "activity"
        DOMAIN_SEMANTIC = "semantic"
        DOMAIN_RELATIONSHIP = "relationship"
        DOMAIN_MACHINE = "machine"
        DOMAIN_ENTITY = "entity"
        DOMAIN_CALENDAR = "calendar"
        
        @classmethod
        def get_attribute_id(cls, domain: str, name: str) -> str:
            """Get an attribute ID for a registered attribute."""
            return f"{domain}_{name}_id"
        
        @classmethod
        def get_attribute_name(cls, attribute_id: str) -> str:
            """Get the human-readable name for an attribute ID."""
            return attribute_id.replace("_id", "")
        
        @classmethod
        def register_attribute(cls, domain: str, name: str, attribute_id: Optional[str] = None) -> str:
            """Register an attribute."""
            return cls.get_attribute_id(domain, name)
    
    # Calendar event semantic attributes (mock constants)
    CALENDAR_EVENT_ID = "a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6"
    CALENDAR_EVENT_SUBJECT = "b2c3d4e5-f6a7-b8c9-d0e1-f2a3b4c5d6e7"
    CALENDAR_EVENT_START_TIME = "c3d4e5f6-a7b8-c9d0-e1f2-a3b4c5d6e7f8"
    CALENDAR_EVENT_END_TIME = "d4e5f6a7-b8c9-d0e1-f2a3-b4c5d6e7f8a9"
    CALENDAR_EVENT_LOCATION = "e5f6a7b8-c9d0-e1f2-a3b4-c5d6e7f8a9b0"
    CALENDAR_EVENT_ORGANIZER = "f6a7b8c9-d0e1-f2a3-b4c5-d6e7f8a9b0c1"
    CALENDAR_EVENT_STATUS = "a7b8c9d0-e1f2-a3b4-c5d6-e7f8a9b0c1d2"
    CALENDAR_EVENT_RECURRENCE = "b8c9d0e1-f2a3-b4c5-d6e7-f8a9b0c1d2e3"
    CALENDAR_MEETING_TYPE = "c9d0e1f2-a3b4-c5d6-e7f8-a9b0c1d2e3f4"
    CALENDAR_MEETING_URL = "d0e1f2a3-b4c5-d6e7-f8a9-b0c1d2e3f4a5"
    CALENDAR_EVENT_ATTENDEES = "e1f2a3b4-c5d6-e7f8-a9b0-c1d2e3f4a5b6"
    CALENDAR_EVENT_RESPONSE = "f2a3b4c5-d6e7-f8a9-b0c1-d2e3f4a5b6c7"
    
    # Platform types
    ADP_COLLABORATION_CALENDAR = "df45a3b2-c7e5-4f89-a1d3-6cb908e42a13"
    ADP_COLLABORATION_GOOGLE_CALENDAR = "f5f8a1e0-6d1c-4f3a-b7d8-3c3a80a7e1d2"
    ADP_COLLABORATION_OUTLOOK_CALENDAR = "d4b2e8c3-5a7f-42e9-9b6d-8f1e2a3b4c5d"
    ADP_COLLABORATION_ICAL = "e9a8b7c6-5d4e-3f2a-1b0c-9d8e7f6a5b4c"
    
    class IndalekoBaseModel:
        """Mock base model for testing."""
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        
        def model_dump(self):
            """Convert model to dictionary."""
            return self.__dict__
    
    class IndalekoSemanticAttributeDataModel(IndalekoBaseModel):
        """Mock semantic attribute data model for testing."""
        pass
    
    class IndalekoUUIDDataModel(IndalekoBaseModel):
        """Mock UUID data model for testing."""
        pass
    
    # Enum classes for calendar events
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
        required: bool = True
        organizer: bool = False
    
    class EventLocation(IndalekoBaseModel):
        """Model representing a calendar event location"""
        
        display_name: str
        address: str | None = None
        coordinates: dict[str, float] | None = None
        is_virtual: bool = False
        join_url: str | None = None
    
    class RecurrencePattern(IndalekoBaseModel):
        """Model representing a calendar event recurrence pattern"""
        
        type: EventRecurrence
        interval: int = 1
        day_of_week: list[int] | None = None
        day_of_month: int | None = None
        month_of_year: int | None = None
        first_date: datetime
        until_date: datetime | None = None
        occurrence_count: int | None = None
    
    class EventAttachment(IndalekoBaseModel):
        """Model representing an attachment to a calendar event"""
        
        name: str
        content_type: str
        uri: str | None = None
        size: int | None = None
        last_modified: datetime | None = None
        file_id: str | None = None
    
    class CalendarEvent(IndalekoBaseModel):
        """Model representing a calendar event"""
        
        event_id: str
        provider_name: str
        calendar_id: str
        subject: str
        body: str | None = None
        body_type: str | None = None
        start_time: datetime
        end_time: datetime
        is_all_day: bool = False
        status: EventStatus = EventStatus.CONFIRMED
        sensitivity: str | None = None
        importance: str | None = None
        is_recurring: bool = False
        recurrence: RecurrencePattern | None = None
        series_master_id: str | None = None
        instance_index: int | None = None
        organizer: EventAttendee
        attendees: list[EventAttendee] = []
        location: EventLocation | None = None
        categories: list[str] = []
        has_attachments: bool = False
        attachments: list[EventAttachment] = []
        related_files: list[Dict[str, Any]] = []
        is_online_meeting: bool = False
        online_meeting_provider: str | None = None
        join_url: str | None = None
        created_time: datetime
        last_modified_time: datetime
        is_organizer: bool = False
        response_status: EventResponse = EventResponse.NOT_RESPONDED
        event_uuid: str = None

# Removed duplicate import


class CalendarEventGenerator:
    """Generator for realistic calendar events."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize the generator.
        
        Args:
            seed: Random seed for reproducibility
        """
        self.random = random.Random(seed)
        self.name_generator = EntityNameGenerator(seed)
        
        # Calendar providers
        self.providers = {
            "outlook": ADP_COLLABORATION_OUTLOOK_CALENDAR,
            "google": ADP_COLLABORATION_GOOGLE_CALENDAR,
            "ical": ADP_COLLABORATION_ICAL,
            "generic": ADP_COLLABORATION_CALENDAR
        }
        
        # Calendar IDs for different providers
        self.calendar_ids = {
            "outlook": "AQMkADE1YjU3YjE0LWRkOWMtNDMyNS04NWRlLWNlNzBkY2VkZDdkZAAuAAADIWMO0YPXekqX8i9C2hopjAEA0aPWZAC05kC6_A-y9yX-JQAAAgENAAAA",
            "google": "primary",
            "ical": "personal",
            "generic": "default"
        }
        
        # Event templates for generating realistic events
        self.event_templates = [
            {
                "subject": "Team Meeting",
                "body": "Weekly team sync to discuss ongoing projects and priorities.",
                "duration_minutes": 60,
                "categories": ["Work", "Team"],
                "importance": "normal",
                "is_recurring": True,
                "recurrence_type": EventRecurrence.WEEKLY,
                "is_online_meeting": True,
                "online_meeting_provider": "teams"
            },
            {
                "subject": "1:1 with {person}",
                "body": "Regular check-in to discuss progress, blockers, and career development.",
                "duration_minutes": 30,
                "categories": ["Work", "1:1"],
                "importance": "high",
                "is_recurring": True,
                "recurrence_type": EventRecurrence.BI_WEEKLY,
                "is_online_meeting": True,
                "online_meeting_provider": "teams"
            },
            {
                "subject": "Project Kickoff: {project}",
                "body": "Initial meeting to discuss project goals, timeline, and responsibilities.",
                "duration_minutes": 90,
                "categories": ["Work", "Project"],
                "importance": "high",
                "is_recurring": False,
                "is_online_meeting": True,
                "online_meeting_provider": "zoom"
            },
            {
                "subject": "Lunch with {person}",
                "body": "Catch up over lunch at {restaurant}.",
                "duration_minutes": 60,
                "categories": ["Personal", "Social"],
                "importance": "normal",
                "is_recurring": False,
                "is_online_meeting": False
            },
            {
                "subject": "Doctor Appointment",
                "body": "Regular check-up with Dr. {person}.",
                "duration_minutes": 45,
                "categories": ["Personal", "Health"],
                "importance": "high",
                "is_recurring": False,
                "is_online_meeting": False
            },
            {
                "subject": "Gym",
                "body": "Regular workout session.",
                "duration_minutes": 90,
                "categories": ["Personal", "Health"],
                "importance": "normal",
                "is_recurring": True,
                "recurrence_type": EventRecurrence.WEEKLY,
                "is_online_meeting": False
            },
            {
                "subject": "{project} Planning Session",
                "body": "Session to plan upcoming work on the {project} project.",
                "duration_minutes": 120,
                "categories": ["Work", "Planning"],
                "importance": "high",
                "is_recurring": False,
                "is_online_meeting": True,
                "online_meeting_provider": "teams"
            },
            {
                "subject": "Review Meeting: {project}",
                "body": "Review progress and discuss next steps for {project}.",
                "duration_minutes": 60,
                "categories": ["Work", "Review"],
                "importance": "normal",
                "is_recurring": False,
                "is_online_meeting": True,
                "online_meeting_provider": "zoom"
            },
            {
                "subject": "Birthday Party: {person}",
                "body": "Celebration for {person}'s birthday at {location}.",
                "duration_minutes": 180,
                "categories": ["Personal", "Social"],
                "importance": "normal",
                "is_recurring": False,
                "is_online_meeting": False
            },
            {
                "subject": "Conference: {topic}",
                "body": "Attending the {topic} conference at {location}.",
                "duration_minutes": 480,
                "categories": ["Work", "Conference"],
                "importance": "high",
                "is_recurring": False,
                "is_online_meeting": False
            },
            {
                "subject": "Vacation",
                "body": "Time off for vacation in {location}.",
                "duration_minutes": 480,
                "categories": ["Personal", "Vacation"],
                "importance": "normal",
                "is_recurring": False,
                "is_all_day": True,
                "is_online_meeting": False
            },
            {
                "subject": "Training: {topic}",
                "body": "Training session on {topic}.",
                "duration_minutes": 120,
                "categories": ["Work", "Training"],
                "importance": "normal",
                "is_recurring": False,
                "is_online_meeting": True,
                "online_meeting_provider": "zoom"
            }
        ]
        
        # Topics for events
        self.topics = [
            "Machine Learning", "Data Science", "Project Management", "Leadership", 
            "Communication Skills", "Cloud Computing", "DevOps", "Cybersecurity",
            "Digital Marketing", "UX Design", "Blockchain", "AI Ethics",
            "Mobile Development", "Web Development", "Big Data", "IoT"
        ]
        
        # Project names
        self.projects = [
            "Atlas", "Phoenix", "Voyager", "Horizon", "Nexus", "Odyssey", "Polaris",
            "Quantum", "Sentinel", "Titan", "Aurora", "Cascade", "Ember", "Fusion",
            "Genesis", "Helix", "Impulse", "Javelin", "Kinetic", "Lumina"
        ]
        
        # Restaurant names
        self.restaurants = [
            "The Rustic Table", "Olive & Ivy", "Copper Kitchen", "Harvest Moon", 
            "Salt & Pepper", "The Silver Spoon", "Blue Water Grill", "Maple & Ash",
            "The Garden Gate", "Fireside Bistro", "Wild Sage", "The Copper Pot",
            "Seaside Terrace", "Urban Plate", "Fresh Fields", "The Hungry Bear"
        ]
        
        # Common locations
        self.locations = [
            "Conference Room A", "Conference Room B", "Main Office", "Downtown Office",
            "Home Office", "Client Site", "Coffee Shop", "Restaurant", "Hotel Lobby",
            "Training Center", "Innovation Lab", "Executive Boardroom"
        ]
        
        # Meeting URLs
        self.meeting_urls = [
            "https://teams.microsoft.com/l/meetup-join/19%3ameeting_{uuid}%40thread.v2/0",
            "https://zoom.us/j/{digits}",
            "https://meet.google.com/{code}"
        ]
        
        # File attachments
        self.attachments = [
            {
                "name": "Agenda.docx",
                "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "size": 25600
            },
            {
                "name": "Presentation.pptx",
                "content_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                "size": 1024000
            },
            {
                "name": "Budget.xlsx",
                "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "size": 51200
            },
            {
                "name": "ProjectPlan.pdf",
                "content_type": "application/pdf",
                "size": 102400
            },
            {
                "name": "Requirements.docx",
                "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "size": 30720
            },
            {
                "name": "Notes.txt",
                "content_type": "text/plain",
                "size": 5120
            }
        ]
        
    def generate_events(self, 
                       count: int, 
                       user_email: str,
                       user_name: str,
                       start_time: datetime,
                       end_time: datetime,
                       provider: str = "outlook",
                       entities: Optional[Dict[str, List[Dict[str, Any]]]] = None,
                       location_data: Optional[List[Dict[str, Any]]] = None) -> List[CalendarEvent]:
        """Generate calendar events.
        
        Args:
            count: Number of events to generate
            user_email: User email (organizer)
            user_name: User name (organizer)
            start_time: Start time range for events
            end_time: End time range for events
            provider: Calendar provider (outlook, google, ical, generic)
            entities: Optional dict of entity lists by type
            location_data: Optional location data to use
            
        Returns:
            List of generated calendar events
        """
        if provider not in self.providers:
            provider = "outlook"  # Default to outlook
            
        if not entities:
            entities = {}
            
        # Select the calendar ID
        calendar_id = self.calendar_ids.get(provider, self.calendar_ids["outlook"])
        
        events = []
        
        # Generate non-recurring events first
        non_recurring_count = int(count * 0.6)  # 60% non-recurring
        recurring_count = count - non_recurring_count
        
        # Spread events throughout the time range
        time_range = (end_time - start_time).total_seconds()
        time_step = time_range / (non_recurring_count + 1)
        
        # Generate non-recurring events
        for i in range(non_recurring_count):
            # Calculate start time for this event
            event_time = start_time + timedelta(seconds=(i + 1) * time_step)
            
            # Round to nearest 15 minutes
            event_time = event_time.replace(
                minute=(event_time.minute // 15) * 15,
                second=0, 
                microsecond=0
            )
            
            # Use one of the non-recurring templates, or one that can be made non-recurring
            template = self.random.choice([t for t in self.event_templates 
                                          if not t.get("is_recurring", False) or not self.random.randint(0, 1)])
            template = dict(template)  # Create a copy to modify
            template["is_recurring"] = False  # Ensure it's not recurring
            
            # Generate and add the event
            event = self._generate_event(
                template=template,
                user_email=user_email,
                user_name=user_name,
                start_time=event_time,
                provider=provider,
                calendar_id=calendar_id,
                entities=entities,
                location_data=location_data
            )
            events.append(event)
        
        # Generate recurring events
        for i in range(recurring_count):
            # Spread recurring events over the first 2/3 of the time range
            # This ensures there are instances within our time window
            event_time = start_time + timedelta(seconds=self.random.uniform(0, time_range * 2/3))
            
            # Round to nearest 15 minutes
            event_time = event_time.replace(
                minute=(event_time.minute // 15) * 15,
                second=0, 
                microsecond=0
            )
            
            # Use one of the recurring templates
            template = self.random.choice([t for t in self.event_templates 
                                          if t.get("is_recurring", False)])
            
            # Generate and add the event
            event = self._generate_event(
                template=template,
                user_email=user_email,
                user_name=user_name,
                start_time=event_time,
                provider=provider,
                calendar_id=calendar_id,
                entities=entities,
                location_data=location_data
            )
            events.append(event)
            
            # For recurring events, add some individual instances
            if event.get("is_recurring", False) and event.get("recurrence"):
                # Add 1-3 instances of this recurring event
                instances = self._generate_recurring_instances(event, 
                                                             self.random.randint(1, 3), 
                                                             start_time, 
                                                             end_time)
                events.extend(instances)
        
        # Sort events by start time
        events.sort(key=lambda e: e["start_time"] if isinstance(e["start_time"], str) else e["start_time"].isoformat())
        
        return events
    
    def _generate_event(self, 
                       template: Dict[str, Any],
                       user_email: str,
                       user_name: str,
                       start_time: datetime,
                       provider: str,
                       calendar_id: str,
                       entities: Dict[str, List[Dict[str, Any]]],
                       location_data: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Generate a single calendar event.
        
        Args:
            template: Event template to use
            user_email: User email (organizer)
            user_name: User name (organizer)
            start_time: Start time for the event
            provider: Calendar provider
            calendar_id: Calendar ID
            entities: Dict of entity lists by type
            location_data: Optional location data to use
            
        Returns:
            Generated calendar event as a dictionary
        """
        # Generate a unique event ID
        event_id = str(uuid.uuid4())
        
        # Calculate end time based on duration
        duration_minutes = template.get("duration_minutes", 60)
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # Format subject with placeholders
        subject = template["subject"]
        if "{person}" in subject:
            if "person" in entities and entities["person"] and self.random.random() < 0.7:
                # 70% chance to use a known person entity
                person = self.random.choice(entities["person"])
                subject = subject.replace("{person}", person["name"])
            else:
                # Otherwise generate a random name
                subject = subject.replace("{person}", self.name_generator.generate_person_name())
        
        if "{project}" in subject:
            subject = subject.replace("{project}", self.random.choice(self.projects))
        
        if "{topic}" in subject:
            subject = subject.replace("{topic}", self.random.choice(self.topics))
        
        # Format body with placeholders
        body = template.get("body", "")
        if "{person}" in body:
            if "person" in entities and entities["person"] and self.random.random() < 0.7:
                # 70% chance to use a known person entity
                person = self.random.choice(entities["person"])
                body = body.replace("{person}", person["name"])
            else:
                # Otherwise generate a random name
                body = body.replace("{person}", self.name_generator.generate_person_name())
        
        if "{project}" in body:
            body = body.replace("{project}", self.random.choice(self.projects))
        
        if "{topic}" in body:
            body = body.replace("{topic}", self.random.choice(self.topics))
            
        if "{restaurant}" in body:
            body = body.replace("{restaurant}", self.random.choice(self.restaurants))
            
        if "{location}" in body:
            if location_data and self.random.random() < 0.6:
                # 60% chance to use a known location
                location = self.random.choice(location_data)
                body = body.replace("{location}", location.get("name", "Unknown Location"))
            else:
                # Otherwise use a random location
                body = body.replace("{location}", self.random.choice(self.locations))
        
        # Create the organizer
        organizer = {
            "email": user_email,
            "name": user_name,
            "response": "organizer",
            "required": True,
            "organizer": True
        }
        
        # Determine if this is an all-day event
        is_all_day = template.get("is_all_day", False)
        
        # Determine event status
        status = "confirmed"
        if self.random.random() < 0.1:  # 10% chance of tentative
            status = "tentative"
        elif self.random.random() < 0.05:  # 5% chance of cancelled
            status = "cancelled"
        
        # Determine importance
        importance = template.get("importance", "normal")
        
        # Generate the location
        location = None
        if not template.get("is_online_meeting", False) or self.random.random() < 0.3:
            # Physical location or hybrid meeting
            location_name = self.random.choice(self.locations)
            coordinates = None
            
            # Use coordinates from location_data if available
            if location_data and self.random.random() < 0.6:
                loc_data = self.random.choice(location_data)
                location_name = loc_data.get("name", location_name)
                if "latitude" in loc_data and "longitude" in loc_data:
                    coordinates = {
                        "latitude": loc_data["latitude"],
                        "longitude": loc_data["longitude"]
                    }
            
            location = {
                "display_name": location_name,
                "address": f"{self.random.randint(100, 999)} Main St, City, State 12345" if self.random.random() < 0.3 else None,
                "coordinates": coordinates,
                "is_virtual": template.get("is_online_meeting", False),
                "join_url": self._generate_meeting_url(template.get("online_meeting_provider")) if template.get("is_online_meeting", False) else None
            }
        elif template.get("is_online_meeting", False):
            # Online only meeting
            location = {
                "display_name": f"Online - {template.get('online_meeting_provider', 'teams').capitalize()}",
                "address": None,
                "coordinates": None,
                "is_virtual": True,
                "join_url": self._generate_meeting_url(template.get("online_meeting_provider"))
            }
        
        # Generate attendees (1-5 attendees besides organizer)
        attendee_count = self.random.randint(1, 5)
        attendees = [organizer]
        
        # Add known entities as attendees if available
        if "person" in entities and entities["person"]:
            for _ in range(min(attendee_count, len(entities["person"]))):
                if self.random.random() < 0.7:  # 70% chance to use a known person
                    person = self.random.choice(entities["person"])
                    # Create an email from the person's name
                    name_parts = person["name"].split()
                    if len(name_parts) > 1:
                        email = f"{name_parts[0].lower()}.{name_parts[-1].lower()}@example.com"
                    else:
                        email = f"{name_parts[0].lower()}@example.com"
                    
                    # Create attendee
                    response_types = ["accepted", "tentative", "declined", "notResponded"]
                    response = self.random.choice(response_types)
                    if response == "organizer":
                        response = "accepted"  # Avoid duplicate organizers
                        
                    attendee = {
                        "email": email,
                        "name": person["name"],
                        "response": response,
                        "required": self.random.random() < 0.8,  # 80% required
                        "organizer": False
                    }
                    attendees.append(attendee)
        
        # Fill remaining attendees with random names
        while len(attendees) < attendee_count + 1:
            name = self.name_generator.generate_person_name()
            name_parts = name.split()
            if len(name_parts) > 1:
                email = f"{name_parts[0].lower()}.{name_parts[-1].lower()}@example.com"
            else:
                email = f"{name_parts[0].lower()}@example.com"
            
            response_types = ["accepted", "tentative", "declined", "notResponded"]
            response = self.random.choice(response_types)
            
            attendee = {
                "email": email,
                "name": name,
                "response": response,
                "required": self.random.random() < 0.8,  # 80% required
                "organizer": False
            }
            attendees.append(attendee)
        
        # Generate recurrence pattern if recurring
        recurrence = None
        if template.get("is_recurring", False):
            recurrence_type = template.get("recurrence_type", "weekly")
            if isinstance(recurrence_type, EventRecurrence):
                recurrence_type = recurrence_type.value
            
            # Default weekly recurrence on same day of week
            day_of_week = [start_time.weekday()]
            day_of_month = None
            month_of_year = None
            
            # Monthly recurrence
            if recurrence_type == "monthly":
                day_of_month = start_time.day
                day_of_week = None
            
            # Yearly recurrence
            elif recurrence_type == "yearly":
                day_of_month = start_time.day
                month_of_year = start_time.month
                day_of_week = None
            
            # Biweekly recurrence
            elif recurrence_type == "biweekly":
                interval = 2  # Every 2 weeks
            else:
                interval = 1
            
            # End date is 6 months in the future
            until_date = start_time + timedelta(days=180)
            
            recurrence = {
                "type": recurrence_type,
                "interval": interval if 'interval' in locals() else 1,
                "day_of_week": day_of_week,
                "day_of_month": day_of_month,
                "month_of_year": month_of_year,
                "first_date": start_time.isoformat(),
                "until_date": until_date.isoformat()
            }
        
        # Determine if we add attachments
        has_attachments = self.random.random() < 0.3  # 30% chance of attachments
        attachments = []
        if has_attachments:
            attachment_count = self.random.randint(1, 3)
            for _ in range(attachment_count):
                attachment_data = self.random.choice(self.attachments)
                # Create a unique ID and modify slightly
                file_id = str(uuid.uuid4())
                attachment = {
                    "name": attachment_data["name"],
                    "content_type": attachment_data["content_type"],
                    "uri": f"https://example.com/files/{file_id}",
                    "size": attachment_data["size"] + self.random.randint(-5000, 5000),
                    "last_modified": (datetime.now(timezone.utc) - timedelta(days=self.random.randint(1, 30))).isoformat(),
                    "file_id": file_id
                }
                attachments.append(attachment)
        
        # Check if we have related files
        related_files = []
        if self.random.random() < 0.2:  # 20% chance of related files
            # We'd implement this with real files if we had a file database
            related_file_count = self.random.randint(1, 2)
            for _ in range(related_file_count):
                related_files.append({
                    "id": str(uuid.uuid4()),
                    "name": self.random.choice(self.attachments)["name"],
                    "url": f"https://example.com/files/{str(uuid.uuid4())}"
                })
        
        # Create the semantic attributes
        semantic_attributes = self._generate_event_semantic_attributes({
            "event_id": event_id,
            "subject": subject,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "status": status,
            "organizer": organizer,
            "is_recurring": template.get("is_recurring", False),
            "location": location,
            "is_online_meeting": template.get("is_online_meeting", False),
            "online_meeting_provider": template.get("online_meeting_provider"),
            "join_url": location.get("join_url") if location and template.get("is_online_meeting", False) else None
        })
        
        # Create source identifier for record
        source_identifier = {
            "Identifier": str(uuid.uuid4()),
            "Version": "1.0"
        }
        
        # Create the record
        record = {
            "SourceIdentifier": source_identifier,
            "Timestamp": datetime.now(timezone.utc).isoformat(),
            "Data": ""  # Empty for now, as we're not generating actual raw data
        }
        
        # Create the event as a dictionary that matches the expected model fields
        event = {
            "event_id": event_id,
            "provider_name": provider,
            "calendar_id": calendar_id,
            "subject": subject,
            "body": body,
            "body_type": "text",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "is_all_day": is_all_day,
            "status": status,
            "sensitivity": "normal",
            "importance": importance,
            "is_recurring": template.get("is_recurring", False),
            "recurrence": recurrence,
            "series_master_id": None,
            "instance_index": None,
            "organizer": organizer,
            "attendees": attendees,
            "location": location,
            "categories": template.get("categories", []),
            "has_attachments": has_attachments,
            "attachments": attachments,
            "related_files": related_files,
            "is_online_meeting": template.get("is_online_meeting", False),
            "online_meeting_provider": template.get("online_meeting_provider"),
            "join_url": location.get("join_url") if location and template.get("is_online_meeting", False) else None,
            "created_time": (start_time - timedelta(days=self.random.randint(1, 14))).isoformat(),
            "last_modified_time": (start_time - timedelta(days=self.random.randint(0, 7))).isoformat(),
            "is_organizer": True,
            "response_status": "organizer",
            "event_uuid": str(uuid.uuid4()),
            # Required base model fields
            "Record": record,
            "Timestamp": start_time.isoformat(),
            "SemanticAttributes": semantic_attributes,
            "CollaborationType": "calendar"
        }
        
        return event
    
    def _generate_event_semantic_attributes(self, event_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate semantic attributes for an event.
        
        Args:
            event_data: Event data
            
        Returns:
            List of semantic attributes
        """
        semantic_attributes = []
        
        # Event ID attribute
        id_attr = {
            "Identifier": {
                "Identifier": CALENDAR_EVENT_ID,
                "Label": "EVENT_ID"
            },
            "Value": event_data["event_id"]
        }
        semantic_attributes.append(id_attr)
        
        # Subject attribute
        subject_attr = {
            "Identifier": {
                "Identifier": CALENDAR_EVENT_SUBJECT,
                "Label": "EVENT_SUBJECT"
            },
            "Value": event_data["subject"]
        }
        semantic_attributes.append(subject_attr)
        
        # Start time attribute
        start_time_attr = {
            "Identifier": {
                "Identifier": CALENDAR_EVENT_START_TIME,
                "Label": "EVENT_START_TIME"
            },
            "Value": event_data["start_time"]
        }
        semantic_attributes.append(start_time_attr)
        
        # End time attribute
        end_time_attr = {
            "Identifier": {
                "Identifier": CALENDAR_EVENT_END_TIME,
                "Label": "EVENT_END_TIME"
            },
            "Value": event_data["end_time"]
        }
        semantic_attributes.append(end_time_attr)
        
        # Location attribute
        if event_data["location"]:
            location_attr = {
                "Identifier": {
                    "Identifier": CALENDAR_EVENT_LOCATION,
                    "Label": "EVENT_LOCATION"
                },
                "Value": event_data["location"]["display_name"]
            }
            semantic_attributes.append(location_attr)
        
        # Organizer attribute
        if event_data["organizer"]:
            organizer_attr = {
                "Identifier": {
                    "Identifier": CALENDAR_EVENT_ORGANIZER,
                    "Label": "EVENT_ORGANIZER"
                },
                "Value": event_data["organizer"]["name"] if event_data["organizer"]["name"] else event_data["organizer"]["email"]
            }
            semantic_attributes.append(organizer_attr)
        
        # Status attribute
        status_attr = {
            "Identifier": {
                "Identifier": CALENDAR_EVENT_STATUS,
                "Label": "EVENT_STATUS"
            },
            "Value": event_data["status"]
        }
        semantic_attributes.append(status_attr)
        
        # Recurrence attribute
        if event_data.get("is_recurring", False):
            recurrence_type = "series-instance"
            if event_data.get("recurrence") and "type" in event_data["recurrence"]:
                recurrence_type = event_data["recurrence"]["type"]
            
            recurrence_attr = {
                "Identifier": {
                    "Identifier": CALENDAR_EVENT_RECURRENCE,
                    "Label": "EVENT_RECURRENCE"
                },
                "Value": recurrence_type
            }
            semantic_attributes.append(recurrence_attr)
        
        # Meeting type attribute
        if event_data["is_online_meeting"] and event_data["online_meeting_provider"]:
            meeting_type_attr = {
                "Identifier": {
                    "Identifier": CALENDAR_MEETING_TYPE,
                    "Label": "MEETING_TYPE"
                },
                "Value": event_data["online_meeting_provider"]
            }
            semantic_attributes.append(meeting_type_attr)
        
        # Meeting URL attribute
        if event_data["is_online_meeting"] and event_data["join_url"]:
            meeting_url_attr = {
                "Identifier": {
                    "Identifier": CALENDAR_MEETING_URL,
                    "Label": "MEETING_URL"
                },
                "Value": event_data["join_url"]
            }
            semantic_attributes.append(meeting_url_attr)
        
        return semantic_attributes
    
    def _generate_recurring_instances(self, 
                                    master_event: Dict[str, Any], 
                                    count: int,
                                    start_time: datetime,
                                    end_time: datetime) -> List[Dict[str, Any]]:
        """Generate instances of a recurring event.
        
        Args:
            master_event: Master recurring event
            count: Number of instances to generate
            start_time: Minimum start time for instances
            end_time: Maximum end time for instances
            
        Returns:
            List of event instances
        """
        if not master_event.get("is_recurring", False) or not master_event.get("recurrence"):
            return []
        
        instances = []
        recurrence = master_event["recurrence"]
        
        # Calculate the next occurrences based on recurrence pattern
        occurrences = []
        current = datetime.fromisoformat(recurrence["first_date"])
        recurrence_until_date = datetime.fromisoformat(recurrence["until_date"])
        
        # Maximum number of occurrences to check to avoid infinite loops
        max_iterations = 50
        iterations = 0
        
        while iterations < max_iterations:
            iterations += 1
            
            if recurrence_until_date and current > recurrence_until_date:
                break
                
            if current > end_time:
                break
                
            if current >= start_time:
                occurrences.append(current)
                
            # Calculate the next occurrence
            if recurrence["type"] == "daily":
                current = current + timedelta(days=recurrence["interval"])
            elif recurrence["type"] == "weekly":
                current = current + timedelta(weeks=recurrence["interval"])
            elif recurrence["type"] == "biweekly":
                current = current + timedelta(weeks=2)
            elif recurrence["type"] == "monthly":
                # Get the same day in the next month
                month = current.month + recurrence["interval"]
                year = current.year + (month - 1) // 12
                month = ((month - 1) % 12) + 1
                
                # Handle potential invalid day (e.g., Feb 30)
                try:
                    current = current.replace(year=year, month=month)
                except ValueError:
                    # If the day doesn't exist in the month, use the last day
                    if month == 2:
                        # February special case
                        last_day = 29 if year % 4 == 0 else 28
                    else:
                        # General case for months with 30/31 days
                        last_day = 30 if month in [4, 6, 9, 11] else 31
                    current = current.replace(year=year, month=month, day=min(current.day, last_day))
            elif recurrence["type"] == "yearly":
                current = current.replace(year=current.year + recurrence["interval"])
            else:
                # Unknown recurrence type
                break
        
        # Select random occurrences
        if occurrences:
            selected_occurrences = self.random.sample(
                occurrences, 
                min(count, len(occurrences))
            )
            
            # Create instances for each selected occurrence
            for i, occurrence_time in enumerate(selected_occurrences):
                # Calculate duration
                master_start_time = datetime.fromisoformat(master_event["start_time"])
                master_end_time = datetime.fromisoformat(master_event["end_time"])
                duration = master_end_time - master_start_time
                
                # Create a clone of the master event
                instance = master_event.copy()
                
                # Update instance-specific fields
                instance["event_id"] = str(uuid.uuid4())
                instance["start_time"] = occurrence_time.isoformat()
                instance["end_time"] = (occurrence_time + duration).isoformat()
                instance["is_recurring"] = True  # It's still part of a series
                instance["recurrence"] = None  # Individual instance doesn't have recurrence
                instance["series_master_id"] = master_event["event_id"]
                instance["instance_index"] = i + 1
                instance["event_uuid"] = str(uuid.uuid4())
                instance["Timestamp"] = occurrence_time.isoformat()
                
                # Make some realistic changes to this instance
                if self.random.random() < 0.2:  # 20% chance to change status
                    status_options = ["confirmed", "tentative", "cancelled"]
                    instance["status"] = self.random.choice(status_options)
                
                if self.random.random() < 0.1:  # 10% chance to change location
                    location_name = self.random.choice(self.locations)
                    instance["location"] = {
                        "display_name": location_name,
                        "address": f"{self.random.randint(100, 999)} Main St, City, State 12345" if self.random.random() < 0.3 else None,
                        "coordinates": None,
                        "is_virtual": instance["is_online_meeting"],
                        "join_url": self._generate_meeting_url(instance["online_meeting_provider"]) if instance["is_online_meeting"] else None
                    }
                    
                    if instance["is_online_meeting"]:
                        instance["join_url"] = instance["location"]["join_url"]
                
                # Modified responses for attendees
                for attendee in instance["attendees"]:
                    if not attendee.get("organizer", False) and self.random.random() < 0.3:  # 30% chance to change response
                        response_types = ["accepted", "tentative", "declined", "notResponded"]
                        attendee["response"] = self.random.choice(response_types)
                
                # Update semantic attributes for this instance
                instance["SemanticAttributes"] = self._generate_event_semantic_attributes({
                    "event_id": instance["event_id"],
                    "subject": instance["subject"],
                    "start_time": instance["start_time"],
                    "end_time": instance["end_time"],
                    "status": instance["status"],
                    "organizer": instance["organizer"],
                    "is_recurring": instance["is_recurring"],
                    "location": instance["location"],
                    "is_online_meeting": instance["is_online_meeting"],
                    "online_meeting_provider": instance["online_meeting_provider"],
                    "join_url": instance["join_url"]
                })
                
                instances.append(instance)
        
        return instances
    
    def _generate_meeting_url(self, provider: Optional[str] = None) -> str:
        """Generate a meeting URL for online meetings.
        
        Args:
            provider: Meeting provider (teams, zoom, meet)
            
        Returns:
            Meeting URL
        """
        if not provider:
            provider = self.random.choice(["teams", "zoom", "meet"])
            
        if provider == "teams":
            meeting_id = str(uuid.uuid4())
            return f"https://teams.microsoft.com/l/meetup-join/19%3ameeting_{meeting_id}%40thread.v2/0"
        elif provider == "zoom":
            digits = ''.join([str(self.random.randint(0, 9)) for _ in range(10)])
            return f"https://zoom.us/j/{digits}"
        elif provider == "meet":
            letters = 'abcdefghijklmnopqrstuvwxyz'
            code = ''.join([self.random.choice(letters) for _ in range(3)]) + '-' + \
                  ''.join([self.random.choice(letters) for _ in range(4)]) + '-' + \
                  ''.join([self.random.choice(letters) for _ in range(3)])
            return f"https://meet.google.com/{code}"
        else:
            # Default to teams
            meeting_id = str(uuid.uuid4())
            return f"https://teams.microsoft.com/l/meetup-join/19%3ameeting_{meeting_id}%40thread.v2/0"


class CalendarEventGeneratorTool(Tool):
    """Tool to generate realistic calendar events."""
    
    def __init__(self):
        """Initialize the calendar event generator tool."""
        super().__init__(name="calendar_event_generator", description="Generates realistic calendar events")
        
        # Create the event generator
        self.generator = CalendarEventGenerator()
        
        # Set up logger
        self.logger = logging.getLogger(__name__)
        
        # Initialize database connection if available
        self.db_config = None
        self.db = None
        if HAS_DB:
            try:
                self.db_config = IndalekoDBConfig()
                self.db = self.db_config.db
                self.logger.info("Database connection initialized")
            except Exception as e:
                self.logger.error(f"Error initializing database connection: {e}")
        
        # Register calendar semantic attributes
        self._register_calendar_attributes()
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the calendar event generator tool.
        
        Args:
            params: Parameters for execution
                count: Number of events to generate
                criteria: Criteria for generation
                    user_email: User email
                    user_name: User name
                    provider: Calendar provider (outlook, google, ical, generic)
                    start_time: Optional start time for events
                    end_time: Optional end time for events
                    entities: Optional dict of entity lists by type
                    location_data: Optional list of location data
                    
        Returns:
            Dictionary with generated events
        """
        count = params.get("count", 10)
        criteria = params.get("criteria", {})
        
        user_email = criteria.get("user_email", "user@example.com")
        user_name = criteria.get("user_name", "Test User")
        provider = criteria.get("provider", "outlook")
        
        # Default time range: last 90 days to next 90 days
        now = datetime.now(timezone.utc)
        start_time = criteria.get("start_time", now - timedelta(days=90))
        end_time = criteria.get("end_time", now + timedelta(days=90))
        
        # Convert timestamps to datetime if needed
        if isinstance(start_time, (int, float)):
            start_time = datetime.fromtimestamp(start_time, timezone.utc)
        if isinstance(end_time, (int, float)):
            end_time = datetime.fromtimestamp(end_time, timezone.utc)
            
        # Get named entities if provided
        entities = criteria.get("entities", {})
        
        # Get location data
        location_data = criteria.get("location_data", [])
        
        # Generate events
        events = self.generator.generate_events(
            count=count,
            user_email=user_email,
            user_name=user_name,
            start_time=start_time,
            end_time=end_time,
            provider=provider,
            entities=entities,
            location_data=location_data
        )
        
        # Process events for database usage
        event_records = []
        for event in events:
            # The events are already dictionaries from generate_events
            event_dict = event
            
            # Make sure semantic attributes are added if they're not already
            if "SemanticAttributes" not in event_dict:
                event_dict["SemanticAttributes"] = self._generate_semantic_attributes(event_dict)
                
            event_records.append(event_dict)
            
            # Store in database if available
            if HAS_DB and self.db:
                self._store_calendar_event(event_dict)
        
        return {
            "events": event_records
        }
    
    def _register_calendar_attributes(self) -> None:
        """Register calendar semantic attributes."""
        # These are already registered in the real implementation
        # For mock implementation, we would register them here
        pass
    
    def _generate_semantic_attributes(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate semantic attributes for a calendar event.
        
        Args:
            event: Event to generate attributes for (dictionary)
            
        Returns:
            List of semantic attributes
        """
        semantic_attributes = []
        
        # Event ID attribute (create as a dictionary directly)
        id_attr = {
            "Identifier": {
                "Identifier": CALENDAR_EVENT_ID,
                "Label": "EVENT_ID"
            },
            "Value": event.get("event_id", "")
        }
        semantic_attributes.append(id_attr)
        
        # Subject attribute
        subject_attr = {
            "Identifier": {
                "Identifier": CALENDAR_EVENT_SUBJECT,
                "Label": "EVENT_SUBJECT"
            },
            "Value": event.get("subject", "")
        }
        semantic_attributes.append(subject_attr)
        
        # Start time attribute
        start_time = event.get("start_time", "")
        if isinstance(start_time, datetime):
            start_time = start_time.isoformat()
        
        start_time_attr = {
            "Identifier": {
                "Identifier": CALENDAR_EVENT_START_TIME,
                "Label": "EVENT_START_TIME"
            },
            "Value": start_time
        }
        semantic_attributes.append(start_time_attr)
        
        # End time attribute
        end_time = event.get("end_time", "")
        if isinstance(end_time, datetime):
            end_time = end_time.isoformat()
            
        end_time_attr = {
            "Identifier": {
                "Identifier": CALENDAR_EVENT_END_TIME,
                "Label": "EVENT_END_TIME"
            },
            "Value": end_time
        }
        semantic_attributes.append(end_time_attr)
        
        # Location attribute
        location = event.get("location", None)
        if location:
            location_attr = {
                "Identifier": {
                    "Identifier": CALENDAR_EVENT_LOCATION,
                    "Label": "EVENT_LOCATION"
                },
                "Value": location.get("display_name", "") if isinstance(location, dict) else ""
            }
            semantic_attributes.append(location_attr)
        
        # Organizer attribute
        organizer = event.get("organizer", None)
        if organizer:
            name = organizer.get("name", "") if isinstance(organizer, dict) else ""
            email = organizer.get("email", "") if isinstance(organizer, dict) else ""
            
            organizer_attr = {
                "Identifier": {
                    "Identifier": CALENDAR_EVENT_ORGANIZER,
                    "Label": "EVENT_ORGANIZER"
                },
                "Value": name if name else email
            }
            semantic_attributes.append(organizer_attr)
        
        # Status attribute
        status_attr = {
            "Identifier": {
                "Identifier": CALENDAR_EVENT_STATUS,
                "Label": "EVENT_STATUS"
            },
            "Value": event.get("status", "unknown")
        }
        semantic_attributes.append(status_attr)
        
        # Recurrence attribute
        if event.get("is_recurring", False):
            recurrence = event.get("recurrence", None)
            recurrence_type = "series-instance"
            
            if recurrence and isinstance(recurrence, dict) and "type" in recurrence:
                recurrence_type = recurrence["type"]
                
            recurrence_attr = {
                "Identifier": {
                    "Identifier": CALENDAR_EVENT_RECURRENCE,
                    "Label": "EVENT_RECURRENCE"
                },
                "Value": recurrence_type
            }
            semantic_attributes.append(recurrence_attr)
        
        # Meeting type attribute
        if event.get("is_online_meeting", False) and event.get("online_meeting_provider"):
            meeting_type_attr = {
                "Identifier": {
                    "Identifier": CALENDAR_MEETING_TYPE,
                    "Label": "MEETING_TYPE"
                },
                "Value": event.get("online_meeting_provider", "")
            }
            semantic_attributes.append(meeting_type_attr)
        
        # Meeting URL attribute
        if event.get("is_online_meeting", False) and event.get("join_url"):
            meeting_url_attr = {
                "Identifier": {
                    "Identifier": CALENDAR_MEETING_URL,
                    "Label": "MEETING_URL"
                },
                "Value": event.get("join_url", "")
            }
            semantic_attributes.append(meeting_url_attr)
        
        # Attendees attribute
        attendees = event.get("attendees", [])
        for attendee in attendees:
            # Skip organizer (already added)
            if isinstance(attendee, dict) and not attendee.get("organizer", False):
                name = attendee.get("name", "")
                email = attendee.get("email", "")
                
                attendee_attr = {
                    "Identifier": {
                        "Identifier": CALENDAR_EVENT_ATTENDEES,
                        "Label": "EVENT_ATTENDEE"
                    },
                    "Value": name if name else email
                }
                semantic_attributes.append(attendee_attr)
        
        # Response attribute
        response_attr = {
            "Identifier": {
                "Identifier": CALENDAR_EVENT_RESPONSE,
                "Label": "EVENT_RESPONSE"
            },
            "Value": event.get("response_status", "unknown")
        }
        semantic_attributes.append(response_attr)
        
        return semantic_attributes
    
    def _store_calendar_event(self, event: Dict[str, Any]) -> bool:
        """Store a calendar event in the database.
        
        Args:
            event: Calendar event to store
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db:
            return False
            
        try:
            # Define collection name for calendar events
            collection_name = "CalendarEvents"
            
            # Check if collection exists, create if not
            if not self.db.has_collection(collection_name):
                self.logger.info(f"Creating CalendarEvents collection")
                self.db.create_collection(collection_name)
            
            # Get the collection
            collection = self.db.collection(collection_name)
            
            # Insert the event
            collection.insert(event)
            
            return True
        except Exception as e:
            self.logger.error(f"Error storing calendar event: {e}")
            return False


if __name__ == "__main__":
    # Set up logging
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Simple test
    tool = CalendarEventGeneratorTool()
    
    # Create a test entity
    test_person = {
        "Id": str(uuid.uuid4()),
        "name": "John Smith",
        "category": IndalekoNamedEntityType.person
    }
    
    test_location = {
        "latitude": 37.7749,
        "longitude": -122.4194,
        "name": "San Francisco"
    }
    
    result = tool.execute({
        "count": 5,
        "criteria": {
            "user_email": "test.user@example.com",
            "user_name": "Test User",
            "provider": "outlook",
            "entities": {
                "person": [test_person]
            },
            "location_data": [test_location]
        }
    })
    
    # Print sample event
    if result["events"]:
        sample = result["events"][0].copy()
        
        if "SemanticAttributes" in sample:
            sample["SemanticAttributes"] = f"[{len(sample['SemanticAttributes'])} attributes]"
        
        print(json.dumps(sample, indent=2))