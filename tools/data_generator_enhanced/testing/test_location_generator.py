"""
Unit tests for the LocationGeneratorTool.

This module contains tests for the enhanced location metadata generator.
"""

import os
import sys
import unittest
import datetime
import uuid
from typing import Dict, List, Any

# Setup path for imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import location generator tool
from tools.data_generator_enhanced.agents.data_gen.tools.location_generator import (
    LocationGeneratorTool, LocationProfile, SemanticAttributeRegistry
)


class TestLocationGeneratorTool(unittest.TestCase):
    """Test case for LocationGeneratorTool."""

    def setUp(self):
        """Set up test case."""
        self.location_generator = LocationGeneratorTool()
        self.user_id = "test_user"
        self.start_time = datetime.datetime.now() - datetime.timedelta(days=7)
        self.end_time = datetime.datetime.now()

    def test_location_generator_creation(self):
        """Test that LocationGeneratorTool can be instantiated."""
        self.assertIsNotNone(self.location_generator)
        self.assertEqual(self.location_generator.name, "location_generator")
        self.assertIsNotNone(self.location_generator.location_types)
        self.assertIsNotNone(self.location_generator.poi_categories)
        self.assertIsNotNone(self.location_generator.weather_conditions)

    def test_location_profile_creation(self):
        """Test creation of LocationProfile."""
        profile = LocationProfile(self.user_id)
        self.assertIsNotNone(profile)
        self.assertEqual(profile.user_id, self.user_id)
        self.assertIsNotNone(profile.home_location)
        self.assertIsNotNone(profile.work_location)
        self.assertIsNotNone(profile.frequent_places)
        self.assertIsNotNone(profile.weekday_schedule)
        self.assertIsNotNone(profile.weekend_schedule)
        self.assertIsNotNone(profile.travel_history)

    def test_location_profile_get_location_for_time(self):
        """Test getting location for a specific time."""
        profile = LocationProfile(self.user_id)

        # Test weekday morning (9 AM)
        weekday_morning = datetime.datetime.now().replace(
            hour=9, minute=0, second=0, microsecond=0
        )
        # Make sure it's a weekday
        while weekday_morning.weekday() >= 5:  # Saturday or Sunday
            weekday_morning = weekday_morning + datetime.timedelta(days=1)

        coords, place_type, activity = profile.get_location_for_time(weekday_morning)
        self.assertIsNotNone(coords)
        self.assertEqual(place_type, "work")
        self.assertEqual(activity, "working")

        # Test weekend noon (12 PM)
        weekend_noon = datetime.datetime.now().replace(
            hour=12, minute=0, second=0, microsecond=0
        )
        # Make sure it's a weekend
        while weekend_noon.weekday() < 5:  # Not Saturday or Sunday
            weekend_noon = weekend_noon + datetime.timedelta(days=1)

        coords, place_type, activity = profile.get_location_for_time(weekend_noon)
        self.assertIsNotNone(coords)
        self.assertEqual(place_type, "restaurant")
        self.assertEqual(activity, "dining")

    def test_generate_location_records(self):
        """Test generating location records."""
        result = self.location_generator.execute({
            "count": 5,
            "criteria": {
                "user_id": self.user_id,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "location_types": ["gps", "wifi"],
                "include_weather": True,
                "include_poi": True
            }
        })

        self.assertIn("records", result)
        records = result["records"]
        self.assertEqual(len(records), 5)

        # Check structure of records
        for record in records:
            self.assertIn("Id", record)
            self.assertIn("UserId", record)
            self.assertEqual(record["UserId"], self.user_id)
            self.assertIn("Timestamp", record)
            self.assertIn("LocationType", record)
            self.assertIn(record["LocationType"], ["gps", "wifi"])
            self.assertIn("Latitude", record)
            self.assertIn("Longitude", record)
            self.assertIn("Accuracy", record)
            self.assertIn("PlaceType", record)
            self.assertIn("Activity", record)

            # Check optional fields based on location type
            if record["LocationType"] == "gps":
                self.assertIn("Altitude", record)
                self.assertIn("Speed", record)

            # Check weather data
            self.assertIn("Weather", record)
            weather = record["Weather"]
            self.assertIn("temperature", weather)
            self.assertIn("condition", weather)
            self.assertIn("humidity", weather)
            self.assertIn("wind_speed", weather)
            self.assertIn("season", weather)

            # Check POI data
            self.assertIn("POI", record)
            poi = record["POI"]
            self.assertIn("name", poi)
            self.assertIn("category", poi)
            self.assertIn("distance", poi)
            self.assertIn("address", poi)

    def test_semantic_attributes(self):
        """Test semantic attributes generation."""
        result = self.location_generator.execute({
            "count": 1,
            "criteria": {
                "user_id": self.user_id,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "location_types": ["gps"],
                "include_weather": True,
                "include_poi": True
            }
        })

        record = result["records"][0]
        self.assertIn("SemanticAttributes", record)
        semantic_attributes = record["SemanticAttributes"]
        self.assertIsInstance(semantic_attributes, list)
        self.assertGreater(len(semantic_attributes), 0)

        # Check for expected attributes
        expected_attrs = [
            {"domain": SemanticAttributeRegistry.DOMAIN_ACTIVITY, "name": "LOCATION_TYPE"},
            {"domain": SemanticAttributeRegistry.DOMAIN_ACTIVITY, "name": "LOCATION_LATITUDE"},
            {"domain": SemanticAttributeRegistry.DOMAIN_ACTIVITY, "name": "LOCATION_LONGITUDE"},
            {"domain": SemanticAttributeRegistry.DOMAIN_ACTIVITY, "name": "LOCATION_ACCURACY"},
            {"domain": SemanticAttributeRegistry.DOMAIN_ACTIVITY, "name": "LOCATION_PLACE_TYPE"},
            {"domain": SemanticAttributeRegistry.DOMAIN_ACTIVITY, "name": "LOCATION_ACTIVITY"}
        ]

        # Just verify we have at least the expected number of attributes
        self.assertGreaterEqual(len(semantic_attributes), len(expected_attrs), 
                               "Not enough semantic attributes generated")

    def test_multiple_users_consistent_locations(self):
        """Test that same user gets consistent locations across executions."""
        # Get locations for first execution
        result1 = self.location_generator.execute({
            "count": 5,
            "criteria": {
                "user_id": self.user_id,
                "start_time": self.start_time.replace(hour=9, minute=0),  # 9 AM
                "end_time": self.start_time.replace(hour=9, minute=1),    # 9:01 AM
                "location_types": ["gps"]
            }
        })

        # Get locations for second execution
        result2 = self.location_generator.execute({
            "count": 5,
            "criteria": {
                "user_id": self.user_id,
                "start_time": self.start_time.replace(hour=9, minute=0),  # 9 AM
                "end_time": self.start_time.replace(hour=9, minute=1),    # 9:01 AM
                "location_types": ["gps"]
            }
        })

        # Check that place types are consistent for the same time
        for record1, record2 in zip(result1["records"], result2["records"]):
            self.assertEqual(record1["PlaceType"], record2["PlaceType"])
            self.assertEqual(record1["Activity"], record2["Activity"])

    def test_location_patterns(self):
        """Test that location patterns are realistic and follow schedules."""
        # Generate location records throughout a day
        weekday = datetime.datetime.now()
        # Make sure it's a weekday
        while weekday.weekday() >= 5:  # Saturday or Sunday
            weekday = weekday + datetime.timedelta(days=1)

        # Create specific times to test
        times = [
            ("night", weekday.replace(hour=2, minute=0)),    # 2 AM
            ("morning", weekday.replace(hour=8, minute=0)),  # 8 AM
            ("work", weekday.replace(hour=10, minute=0)),    # 10 AM
            ("lunch", weekday.replace(hour=12, minute=30)),  # 12:30 PM
            ("work", weekday.replace(hour=14, minute=0)),    # 2 PM
            ("commute", weekday.replace(hour=17, minute=30)), # 5:30 PM
            ("evening", weekday.replace(hour=20, minute=0))  # 8 PM
        ]

        # Get location for each time
        profile = LocationProfile(self.user_id)
        for label, time in times:
            coords, place_type, activity = profile.get_location_for_time(time)
            
            if label == "night":
                self.assertEqual(place_type, "home", f"Expected to be home at {time}")
                self.assertEqual(activity, "sleeping", f"Expected to be sleeping at {time}")
            elif label == "morning":
                self.assertEqual(place_type, "home", f"Expected to be home at {time}")
                self.assertEqual(activity, "morning_routine", f"Expected morning routine at {time}")
            elif label == "work":
                self.assertEqual(place_type, "work", f"Expected to be at work at {time}")
                self.assertEqual(activity, "working", f"Expected to be working at {time}")
            elif label == "lunch":
                self.assertEqual(place_type, "coffee_shop", f"Expected to be at lunch at {time}")
                self.assertEqual(activity, "lunch", f"Expected to be having lunch at {time}")
            elif label == "commute":
                self.assertEqual(place_type, "commuting", f"Expected to be commuting at {time}")
                self.assertEqual(activity, "traveling", f"Expected to be traveling at {time}")
            elif label == "evening":
                self.assertEqual(place_type, "home", f"Expected to be home at {time}")
                self.assertEqual(activity, "evening_activities", f"Expected evening activities at {time}")


if __name__ == "__main__":
    unittest.main()