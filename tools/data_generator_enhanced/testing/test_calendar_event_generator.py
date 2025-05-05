"""Test suite for the CalendarEventGeneratorTool.

This module tests the functionality of the CalendarEventGeneratorTool,
ensuring it generates valid calendar events and relationships
that can be properly stored in the ArangoDB database.
"""

import os
import sys
import unittest
import uuid
import random
from typing import Dict, Any
from datetime import datetime, timezone, timedelta

# Setup path for imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import the generator tools
from tools.data_generator_enhanced.agents.data_gen.tools.calendar_event_generator import (
    CalendarEventGeneratorTool,
    CalendarEventGenerator,
    EventStatus,
    EventResponse
)
from tools.data_generator_enhanced.agents.data_gen.tools.named_entity_generator import (
    IndalekoNamedEntityType
)

# Import database-related modules
try:
    from db.db_config import IndalekoDBConfig
    from db.db_collections import IndalekoDBCollections
    HAS_DB = True
except ImportError:
    HAS_DB = False


class TestCalendarEventGenerator(unittest.TestCase):
    """Test cases for the CalendarEventGeneratorTool."""

    def setUp(self):
        """Set up the test environment."""
        # Initialize the generator with a fixed seed for reproducibility
        self.generator = CalendarEventGeneratorTool()
        self.seed = 42
        random.seed(self.seed)
        
        # Create test data
        self.user_email = "test.user@example.com"
        self.user_name = "Test User"
        self.test_entities = {
            "person": [
                {
                    "Id": str(uuid.uuid4()),
                    "name": "John Smith",
                    "category": IndalekoNamedEntityType.person
                },
                {
                    "Id": str(uuid.uuid4()),
                    "name": "Jane Doe",
                    "category": IndalekoNamedEntityType.person
                }
            ],
            "organization": [
                {
                    "Id": str(uuid.uuid4()),
                    "name": "Acme Corp",
                    "category": IndalekoNamedEntityType.organization
                }
            ],
            "location": [
                {
                    "Id": str(uuid.uuid4()),
                    "name": "San Francisco",
                    "category": IndalekoNamedEntityType.location,
                    "gis_location": {
                        "latitude": 37.7749,
                        "longitude": -122.4194
                    }
                }
            ]
        }
        
        self.test_location_data = [
            {
                "latitude": 37.7749,
                "longitude": -122.4194,
                "name": "San Francisco"
            },
            {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "name": "New York"
            }
        ]
        
        # Time range for events (90 days in the past to 90 days in the future)
        self.now = datetime.now(timezone.utc)
        self.start_time = self.now - timedelta(days=90)
        self.end_time = self.now + timedelta(days=90)
        
        # Generate sample data
        self.result = self.generator.execute({
            "count": 10,
            "criteria": {
                "user_email": self.user_email,
                "user_name": self.user_name,
                "provider": "outlook",
                "entities": self.test_entities,
                "location_data": self.test_location_data,
                "start_time": self.start_time,
                "end_time": self.end_time
            }
        })
        
        # Set up database connection if available
        if HAS_DB:
            try:
                self.db_config = IndalekoDBConfig()
                self.db = self.db_config.db
                self.HAS_ACTIVE_DB = self.db_config.db is not None
            except Exception as e:
                print(f"Database connection failed: {e}")
                self.HAS_ACTIVE_DB = False
        else:
            self.HAS_ACTIVE_DB = False
    
    def test_generator_initialization(self):
        """Test that the generator initializes correctly."""
        self.assertIsNotNone(self.generator)
        self.assertIsInstance(self.generator, CalendarEventGeneratorTool)
        self.assertIsInstance(self.generator.generator, CalendarEventGenerator)
    
    def test_event_generation(self):
        """Test that events are generated with the correct structure."""
        # Check that events were generated
        self.assertIn("events", self.result)
        events = self.result["events"]
        self.assertEqual(len(events), 10)
        
        # Check that events have a mix of recurring and non-recurring
        recurring_events = [e for e in events if e.get("is_recurring")]
        non_recurring_events = [e for e in events if not e.get("is_recurring")]
        
        # Should have both types
        self.assertTrue(len(recurring_events) > 0, "No recurring events generated")
        self.assertTrue(len(non_recurring_events) > 0, "No non-recurring events generated")
        
        # Check the structure of each event
        for event in events:
            # Basic fields
            self.assertIn("event_id", event)
            self.assertIn("provider_name", event)
            self.assertIn("calendar_id", event)
            self.assertIn("subject", event)
            self.assertIn("start_time", event)
            self.assertIn("end_time", event)
            self.assertIn("status", event)
            self.assertIn("organizer", event)
            self.assertIn("attendees", event)
            self.assertIn("SemanticAttributes", event)
            
            # Verify event time range
            event_start = datetime.fromisoformat(event["start_time"]) if isinstance(event["start_time"], str) else event["start_time"]
            event_end = datetime.fromisoformat(event["end_time"]) if isinstance(event["end_time"], str) else event["end_time"]
            
            # Event should be within the time range (or for recurring events, the master)
            if not event.get("series_master_id"):  # Only check master events, not instances
                self.assertTrue(self.start_time <= event_start <= self.end_time, 
                            f"Event start time {event_start} not within range {self.start_time} - {self.end_time}")
            
            # End time should be after start time
            self.assertTrue(event_end > event_start, "Event end time is not after start time")
            
            # Check organizer
            organizer = event["organizer"]
            self.assertIn("email", organizer)
            self.assertIn("name", organizer)
            self.assertEqual(organizer["email"], self.user_email)
            self.assertEqual(organizer["name"], self.user_name)
            
            # Check attendees
            self.assertIsInstance(event["attendees"], list)
            self.assertTrue(len(event["attendees"]) > 0, "Event has no attendees")
            
            # Verify that the organizer is in the attendee list
            organizer_in_attendees = False
            for attendee in event["attendees"]:
                self.assertIn("email", attendee)
                self.assertIn("name", attendee)
                self.assertIn("response", attendee)
                
                if attendee.get("organizer"):
                    organizer_in_attendees = True
                    self.assertEqual(attendee["email"], self.user_email)
                    self.assertEqual(attendee["response"], "organizer")
            
            self.assertTrue(organizer_in_attendees, "Organizer not in attendee list")
            
            # Check recurrence if present
            if event.get("is_recurring") and event.get("recurrence"):
                recurrence = event["recurrence"]
                self.assertIn("type", recurrence)
                self.assertIn("interval", recurrence)
                self.assertIn("first_date", recurrence)
                
                # Recurrence first date should match event start time
                first_date = datetime.fromisoformat(recurrence["first_date"]) if isinstance(recurrence["first_date"], str) else recurrence["first_date"]
                self.assertEqual(first_date, event_start)
            
            # If it's an instance of a recurring event, check the series master ID
            if event.get("series_master_id"):
                self.assertIsNotNone(event.get("instance_index"))
                self.assertTrue(event.get("is_recurring"))
                self.assertIsNone(event.get("recurrence"))  # Instances don't have recurrence patterns
    
    def test_location_integration(self):
        """Test that events properly integrate location data."""
        events_with_location = [e for e in self.result["events"] if e.get("location")]
        
        # Should have some events with location
        self.assertTrue(len(events_with_location) > 0, "No events with location data")
        
        # Check that some location data comes from our test locations
        test_location_names = [loc["name"] for loc in self.test_location_data]
        events_with_test_locations = 0
        
        for event in events_with_location:
            location = event["location"]
            self.assertIn("display_name", location)
            
            if location["display_name"] in test_location_names:
                events_with_test_locations += 1
                
                # Check coordinates if available
                if location.get("coordinates"):
                    self.assertIn("latitude", location["coordinates"])
                    self.assertIn("longitude", location["coordinates"])
        
        # At least some events should use our test locations
        self.assertTrue(events_with_test_locations > 0, "No events using test locations")
    
    def test_entity_integration(self):
        """Test that events properly integrate named entities."""
        # Get test person names
        test_person_names = [person["name"] for person in self.test_entities["person"]]
        
        # Check for events that reference our test persons
        events_with_test_persons = 0
        
        for event in self.result["events"]:
            # Check subject for person names
            if any(person_name in event["subject"] for person_name in test_person_names):
                events_with_test_persons += 1
                continue
                
            # Check body for person names
            if event.get("body") and any(person_name in event["body"] for person_name in test_person_names):
                events_with_test_persons += 1
                continue
                
            # Check attendees for person names
            for attendee in event["attendees"]:
                if attendee.get("name") in test_person_names:
                    events_with_test_persons += 1
                    break
        
        # At least some events should reference our test persons
        self.assertTrue(events_with_test_persons > 0, "No events reference test persons")
    
    def test_online_meetings(self):
        """Test that online meetings are properly configured."""
        online_meetings = [e for e in self.result["events"] if e.get("is_online_meeting")]
        
        # Should have some online meetings
        self.assertTrue(len(online_meetings) > 0, "No online meeting events generated")
        
        for event in online_meetings:
            # Online meetings should have a provider
            self.assertIsNotNone(event.get("online_meeting_provider"), 
                              "Online meeting missing provider")
            
            # Should have a join URL
            self.assertIsNotNone(event.get("join_url"), 
                              "Online meeting missing join URL")
            
            # Location should be virtual
            self.assertTrue(event["location"]["is_virtual"], 
                         "Online meeting location not marked as virtual")
            
            # URL in location should match join URL
            self.assertEqual(event["location"]["join_url"], event["join_url"],
                          "Location join URL doesn't match event join URL")
            
            # Check URL format based on provider
            if event["online_meeting_provider"] == "teams":
                self.assertTrue(event["join_url"].startswith("https://teams.microsoft.com/"))
            elif event["online_meeting_provider"] == "zoom":
                self.assertTrue(event["join_url"].startswith("https://zoom.us/"))
            elif event["online_meeting_provider"] == "meet":
                self.assertTrue(event["join_url"].startswith("https://meet.google.com/"))
    
    def test_semantic_attributes(self):
        """Test that semantic attributes are generated correctly."""
        for event in self.result["events"]:
            semantic_attrs = event["SemanticAttributes"]
            self.assertTrue(len(semantic_attrs) > 0, "No semantic attributes generated")
            
            # Basic checks for structure
            for attr in semantic_attrs:
                self.assertIn("Identifier", attr)
                self.assertIn("Value", attr)
                
                # Identifier should have proper structure
                self.assertIn("Identifier", attr["Identifier"])
                self.assertIn("Label", attr["Identifier"])
                
                # Check specific attributes we expect to see
                label = attr["Identifier"]["Label"]
                if label == "EVENT_SUBJECT":
                    self.assertEqual(attr["Value"], event["subject"])
                elif label == "EVENT_STATUS":
                    self.assertEqual(attr["Value"], event["status"])
                elif label == "EVENT_ORGANIZER" and event.get("organizer", {}).get("name"):
                    self.assertEqual(attr["Value"], event["organizer"]["name"])
    
    def test_time_sorting(self):
        """Test that events are sorted by start time."""
        events = self.result["events"]
        
        # Convert times to datetime if needed
        start_times = []
        for event in events:
            if isinstance(event["start_time"], str):
                start_times.append(datetime.fromisoformat(event["start_time"]))
            else:
                start_times.append(event["start_time"])
        
        # Check that start times are in order
        self.assertEqual(start_times, sorted(start_times), 
                      "Events are not sorted by start time")
    
    def test_recurring_instances(self):
        """Test that recurring events have proper instances."""
        events = self.result["events"]
        
        # Group events by series
        series_events = {}
        for event in events:
            if event.get("series_master_id"):
                # It's an instance
                master_id = event["series_master_id"]
                if master_id not in series_events:
                    series_events[master_id] = []
                series_events[master_id].append(event)
            elif event.get("is_recurring") and not event.get("series_master_id"):
                # It's a master
                series_events[event["event_id"]] = [event]
        
        # Check that we have some recurring series
        self.assertTrue(len(series_events) > 0, "No recurring series found")
        
        # Check each series and its instances
        for master_id, events_in_series in series_events.items():
            # Should have master + instances
            master_events = [e for e in events_in_series if not e.get("series_master_id")]
            instance_events = [e for e in events_in_series if e.get("series_master_id")]
            
            # Verify structure
            if master_events:  # We have the master
                self.assertEqual(len(master_events), 1, "Multiple masters for same series")
                master = master_events[0]
                
                if instance_events:  # We have instances
                    # Check instances have correct master ID
                    for instance in instance_events:
                        self.assertEqual(instance["series_master_id"], master["event_id"])
                        
                        # Instances should have the same subject as master
                        self.assertEqual(instance["subject"], master["subject"])
                        
                        # Should have instance index
                        self.assertIsNotNone(instance["instance_index"])
    
    @unittest.skipIf(not HAS_DB, "Database modules not available")
    def test_db_integration(self):
        """Test that generated events can be stored in the database."""
        if not hasattr(self, 'db') or not self.HAS_ACTIVE_DB:
            self.skipTest("No active database connection available")
        
        print("Database connection verified. Running database integration test...")
        
        # Check if collection exists
        collection_name = "CalendarEvents"
        if not self.db.has_collection(collection_name):
            self.db.create_collection(collection_name)
        
        collection = self.db.collection(collection_name)
        
        # Get the first event
        event = self.result["events"][0]
        
        # Make a copy with only the essential fields for database testing
        db_event = {
            "event_id": event["event_id"],
            "subject": event["subject"],
            "start_time": event["start_time"] if isinstance(event["start_time"], str) else event["start_time"].isoformat(),
            "end_time": event["end_time"] if isinstance(event["end_time"], str) else event["end_time"].isoformat(),
            "status": event["status"]
        }
        
        try:
            # Try to insert the event into the database
            document = collection.insert(db_event)
            self.assertIsNotNone(document)
            print(f"Successfully inserted event into database: {document}")
            
            # Clean up after test
            collection.delete(document)
            print("Successfully deleted test event from database")
        except Exception as e:
            self.fail(f"Database integration test failed: {e}")


if __name__ == "__main__":
    unittest.main()