"""
Database integration tests for the MusicActivityGeneratorTool.

This module tests the MusicActivityGeneratorTool's ability to:
1. Generate synthetic music activity data
2. Insert it into the ArangoDB database
3. Verify it can be queried and retrieved correctly

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
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from activity.collectors.ambient.semantic_attributes import (
    ADP_AMBIENT_SPOTIFY_ALBUM_NAME,
    ADP_AMBIENT_SPOTIFY_ARTIST_NAME,
    ADP_AMBIENT_SPOTIFY_DEVICE_TYPE,
    ADP_AMBIENT_SPOTIFY_TRACK_DURATION,
    ADP_AMBIENT_SPOTIFY_TRACK_NAME,
)
from db import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections
from tools.data_generator_enhanced.agents.data_gen.tools.music_activity_generator import (
    MusicActivityGeneratorTool,
)


class TestMusicDBIntegration(unittest.TestCase):
    """Test the integration of music activity data with the ArangoDB database."""

    @classmethod
    def setUpClass(cls):
        """Set up the test environment once for all tests."""
        # Initialize the database connection
        try:
            cls.db_config = IndalekoDBConfig()
            cls.db = cls.db_config.db
            
            # Get or create the music activity collection
            collection_name = IndalekoDBCollections.Indaleko_MusicActivityData_Collection
            if not cls.db.has_collection(collection_name):
                cls.db.create_collection(collection_name)
            
            cls.collection = cls.db.collection(collection_name)
            
            # Create a unique test ID to identify our test records
            cls.test_id = str(uuid.uuid4())
            
            # Initialize the generator tool
            cls.generator_tool = MusicActivityGeneratorTool()
            
            # Set up test time period (past 24 hours)
            cls.start_date = datetime.now(timezone.utc) - timedelta(days=1)
            cls.end_date = datetime.now(timezone.utc)
            
            # Generate and insert a batch of test records
            cls.result = cls.generator_tool.generate_music_activities(
                start_date=cls.start_date,
                end_date=cls.end_date,
                count=20,  # Generate a small batch for testing
                insert_to_db=True
            )
            
            # Store the keys of inserted records so we can clean up after tests
            cls.inserted_keys = []
            if cls.result["db_inserts"] > 0:
                # Query for records in our time period
                aql_query = """
                FOR doc IN @@collection
                    FILTER doc.Timestamp >= @start_date AND doc.Timestamp <= @end_date
                    RETURN doc._key
                """
                bind_vars = {
                    "@collection": collection_name,
                    "start_date": cls.start_date.isoformat(),
                    "end_date": cls.end_date.isoformat()
                }
                cursor = cls.db.aql.execute(aql_query, bind_vars=bind_vars)
                cls.inserted_keys = [doc for doc in cursor]
            
        except Exception as e:
            print(f"Error setting up test environment: {str(e)}")
            # Continue with tests even if setup fails - will be skipped if db not available

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests are done."""
        try:
            # Remove test records
            collection_name = IndalekoDBCollections.Indaleko_MusicActivityData_Collection
            if hasattr(cls, 'db') and cls.db and hasattr(cls, 'inserted_keys') and cls.inserted_keys:
                collection = cls.db.collection(collection_name)
                for key in cls.inserted_keys:
                    try:
                        collection.delete(key)
                    except Exception:
                        pass  # Ignore errors during cleanup
        except Exception as e:
            print(f"Error during test cleanup: {str(e)}")

    def setUp(self):
        """Check if database is available and skip tests if not."""
        if not hasattr(self, 'db') or not self.db:
            self.skipTest("Database connection not available")
        if self.result["db_inserts"] == 0:
            self.skipTest("No test records were inserted into the database")

    def test_record_insertion(self):
        """Test that records were successfully inserted into the database."""
        self.assertGreater(self.result["db_inserts"], 0)
        self.assertEqual(self.result["db_inserts"], 20)  # We requested 20 records

    def test_timestamp_search(self):
        """Test querying records by timestamp range."""
        # Query records within our test time period
        aql_query = """
        FOR doc IN @@collection
            FILTER doc.Timestamp >= @start_date AND doc.Timestamp <= @end_date
            RETURN doc
        """
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_MusicActivityData_Collection,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat()
        }
        cursor = self.db.aql.execute(aql_query, bind_vars=bind_vars)
        results = [doc for doc in cursor]
        
        # Log for debugging
        print(f"Found {len(results)} records in timestamp range")
        print(f"Records inserted in test: {self.result['db_inserts']}")
        
        # Verify we can find at least some of our inserted records
        # Our query might also find records from other tests in the same range
        self.assertGreater(len(results), 0, "Should find at least some music activity records")
        
        # Verify record structure
        if results:
            sample = results[0]
            self.assertIn("Record", sample)
            self.assertIn("Timestamp", sample)
            self.assertIn("SemanticAttributes", sample)

    def test_semantic_attribute_search(self):
        """Test querying records by semantic attributes."""
        # Get a sample record to extract real attribute values
        sample_query = """
        FOR doc IN @@collection
            FILTER doc.Timestamp >= @start_date AND doc.Timestamp <= @end_date
            LIMIT 1
            RETURN doc
        """
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_MusicActivityData_Collection,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat()
        }
        cursor = self.db.aql.execute(sample_query, bind_vars=bind_vars)
        sample_records = [doc for doc in cursor]
        
        if not sample_records:
            self.skipTest("No sample records found for semantic attribute testing")
            
        sample = sample_records[0]
        
        # Extract artist name from semantic attributes
        artist_name = None
        for attr in sample.get("SemanticAttributes", []):
            if attr.get("Identifier", {}).get("Identifier") == ADP_AMBIENT_SPOTIFY_ARTIST_NAME:
                artist_name = attr.get("Data")
                break
                
        if not artist_name:
            self.skipTest("No artist name found in sample record")
            
        # Query records by artist name
        artist_query = """
        FOR doc IN @@collection
            FILTER doc.Timestamp >= @start_date AND doc.Timestamp <= @end_date
            FOR attr IN doc.SemanticAttributes
                FILTER attr.Identifier.Identifier == @attr_id AND attr.Data == @attr_value
                RETURN doc
        """
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_MusicActivityData_Collection,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "attr_id": ADP_AMBIENT_SPOTIFY_ARTIST_NAME,
            "attr_value": artist_name
        }
        cursor = self.db.aql.execute(artist_query, bind_vars=bind_vars)
        artist_results = [doc for doc in cursor]
        
        # Verify we found at least one record
        self.assertGreater(len(artist_results), 0)

    def test_complex_query(self):
        """Test a more complex query combining multiple filters."""
        # Get a device type value from a sample record
        sample_query = """
        FOR doc IN @@collection
            FILTER doc.Timestamp >= @start_date AND doc.Timestamp <= @end_date
            FOR attr IN doc.SemanticAttributes
                FILTER attr.Identifier.Identifier == @device_id
                RETURN {doc: doc, device: attr.Data}
        """
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_MusicActivityData_Collection,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "device_id": ADP_AMBIENT_SPOTIFY_DEVICE_TYPE
        }
        cursor = self.db.aql.execute(sample_query, bind_vars=bind_vars)
        sample_results = [doc for doc in cursor]
        
        if not sample_results:
            self.skipTest("No sample records with device type found")
            
        device_type = sample_results[0]["device"]
        
        # Query for records with the device type during morning hours (6-10am)
        complex_query = """
        FOR doc IN @@collection
            FILTER doc.Timestamp >= @start_date AND doc.Timestamp <= @end_date
            LET hour = DATE_HOUR(doc.Timestamp)
            FILTER hour >= 6 AND hour <= 10
            FOR attr IN doc.SemanticAttributes
                FILTER attr.Identifier.Identifier == @device_id AND attr.Data == @device_type
                RETURN doc
        """
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_MusicActivityData_Collection,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "device_id": ADP_AMBIENT_SPOTIFY_DEVICE_TYPE,
            "device_type": device_type
        }
        cursor = self.db.aql.execute(complex_query, bind_vars=bind_vars)
        complex_results = [doc for doc in cursor]
        
        # If no results, this is expected as we might not have morning records
        # Just make sure the query executed without errors
        self.assertIsNotNone(complex_results)

    def test_natural_language_query_capability(self):
        """Test ability to support natural language queries (simulated)."""
        # This test simulates the step before an actual NL query would be processed
        # It verifies that the data model supports the kinds of queries we need
        
        # Test for "songs I listened to yesterday"
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        yesterday_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        time_query = """
        FOR doc IN @@collection
            FILTER doc.Timestamp >= @start_date AND doc.Timestamp <= @end_date
            RETURN doc
        """
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_MusicActivityData_Collection,
            "start_date": yesterday_start.isoformat(),
            "end_date": yesterday_end.isoformat()
        }
        cursor = self.db.aql.execute(time_query, bind_vars=bind_vars)
        time_results = [doc for doc in cursor]
        
        # We might not have data from exactly yesterday, so just verify the query ran
        self.assertIsNotNone(time_results)
        
        # Test for "music I listen to on my Speaker" capability
        device_query = """
        FOR doc IN @@collection
            FILTER doc.Timestamp >= @start_date AND doc.Timestamp <= @end_date
            FOR attr IN doc.SemanticAttributes
                FILTER attr.Identifier.Identifier == @device_id AND attr.Data == @device_type
                RETURN doc
        """
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_MusicActivityData_Collection,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "device_id": ADP_AMBIENT_SPOTIFY_DEVICE_TYPE,
            "device_type": "Speaker"
        }
        cursor = self.db.aql.execute(device_query, bind_vars=bind_vars)
        device_results = [doc for doc in cursor]
        
        # Again, we might not have Speaker data, so just verify the query executed
        self.assertIsNotNone(device_results)


if __name__ == "__main__":
    unittest.main()