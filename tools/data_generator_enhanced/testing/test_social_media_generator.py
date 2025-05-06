"""Test suite for the SocialMediaActivityGeneratorTool.

This module tests the functionality of the SocialMediaActivityGeneratorTool,
ensuring it generates valid social media activities and relationships
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
from tools.data_generator_enhanced.agents.data_gen.tools.social_media_generator import (
    SocialMediaActivityGeneratorTool,
    SocialMediaActivityGenerator,
    Post
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


class TestSocialMediaGenerator(unittest.TestCase):
    """Test cases for the SocialMediaActivityGeneratorTool."""

    def setUp(self):
        """Set up the test environment."""
        # Initialize the generator with a fixed seed for reproducibility
        self.generator = SocialMediaActivityGeneratorTool()
        self.seed = 42
        random.seed(self.seed)
        
        # Create test data
        self.user_id = "test_user"
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
        
        # Generate sample data
        self.result = self.generator.execute({
            "count": 5,
            "criteria": {
                "user_id": self.user_id,
                "platforms": ["Instagram", "Twitter", "Facebook"],
                "entities": self.test_entities,
                "location_data": self.test_location_data,
                "start_time": datetime.now(timezone.utc) - timedelta(days=30),
                "end_time": datetime.now(timezone.utc)
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
        self.assertIsInstance(self.generator, SocialMediaActivityGeneratorTool)
        self.assertIsInstance(self.generator.generator, SocialMediaActivityGenerator)
    
    def test_post_generation(self):
        """Test that posts are generated with the correct structure."""
        # Check that posts were generated
        self.assertIn("records", self.result)
        records = self.result["records"]
        self.assertEqual(len(records), 5)
        
        # Check the structure of each post
        for post in records:
            # Basic fields
            self.assertIn("Id", post)
            self.assertIn("UserId", post)
            self.assertIn("Platform", post)
            self.assertIn("Text", post)
            self.assertIn("Hashtags", post)
            self.assertIn("CreationTime", post)
            self.assertIn("Comments", post)
            self.assertIn("Likes", post)
            self.assertIn("Shares", post)
            self.assertIn("Engagement", post)
            self.assertIn("SemanticAttributes", post)
            
            # User ID should match
            self.assertEqual(post["UserId"], self.user_id)
            
            # Platform should be one of the specified ones
            self.assertIn(post["Platform"], ["Instagram", "Twitter", "Facebook"])
            
            # Text should not be empty
            self.assertTrue(len(post["Text"]) > 0)
            
            # Hashtags should be a list
            self.assertIsInstance(post["Hashtags"], list)
            
            # Creation time should be a valid ISO timestamp
            try:
                dt = datetime.fromisoformat(post["CreationTime"])
                self.assertTrue(isinstance(dt, datetime))
            except ValueError:
                self.fail("CreationTime is not a valid ISO timestamp")
            
            # Engagement should have count fields
            self.assertIn("CommentCount", post["Engagement"])
            self.assertIn("LikeCount", post["Engagement"])
            self.assertIn("ShareCount", post["Engagement"])
            
            # Comment counts should match actual comments
            self.assertEqual(post["Engagement"]["CommentCount"], len(post["Comments"]))
            self.assertEqual(post["Engagement"]["LikeCount"], len(post["Likes"]))
            self.assertEqual(post["Engagement"]["ShareCount"], len(post["Shares"]))
            
            # If there are comments, check their structure
            for comment in post["Comments"]:
                self.assertIn("id", comment)
                self.assertIn("user_id", comment)
                self.assertIn("text", comment)
                self.assertIn("timestamp", comment)
    
    def test_entity_mentions(self):
        """Test that entities are mentioned in posts."""
        # Find posts with entity mentions
        posts_with_mentions = [
            post for post in self.result["records"] 
            if "MentionedEntities" in post and post["MentionedEntities"]
        ]
        
        # We should have at least some posts with mentions
        self.assertTrue(len(posts_with_mentions) > 0, "No posts with entity mentions found")
        
        # Check that mentions are properly formatted
        for post in posts_with_mentions:
            for entity in post["MentionedEntities"]:
                self.assertIn("id", entity)
                self.assertIn("name", entity)
                self.assertIn("type", entity)
                
                # Entity should be a person
                self.assertEqual(entity["type"], "person")
    
    def test_location_tagging(self):
        """Test that locations are tagged in posts."""
        # Find posts with location data
        posts_with_location = [
            post for post in self.result["records"] 
            if "LocationData" in post and post["LocationData"]
        ]
        
        # We should have at least some posts with location data
        self.assertTrue(
            len(posts_with_location) > 0, 
            "No posts with location data found"
        )
        
        # Check that location data is properly formatted
        for post in posts_with_location:
            location = post["LocationData"]
            self.assertIn("latitude", location)
            self.assertIn("longitude", location)
            self.assertIn("name", location)
            self.assertIn("timestamp", location)
            
            # Name should be one of our test locations
            self.assertIn(
                location["name"], 
                [loc["name"] for loc in self.test_location_data]
            )
    
    def test_semantic_attributes(self):
        """Test that semantic attributes are generated correctly."""
        # All posts should have semantic attributes
        for post in self.result["records"]:
            self.assertIn("SemanticAttributes", post)
            semantic_attrs = post["SemanticAttributes"]
            self.assertTrue(len(semantic_attrs) > 0)
            
            # Check the structure of semantic attributes
            for attr in semantic_attrs:
                self.assertIn("Identifier", attr)
                self.assertIn("Value", attr)
                
                # Identifier should have proper structure
                self.assertIn("Identifier", attr["Identifier"])
                self.assertIn("Label", attr["Identifier"])
                
                # Value should not be None
                self.assertIsNotNone(attr["Value"])
                
                # Check specific attribute types
                if attr["Identifier"]["Label"] == "PLATFORM":
                    self.assertIn(attr["Value"], ["Instagram", "Twitter", "Facebook"])
                elif attr["Identifier"]["Label"] == "POST_TYPE":
                    self.assertIn(attr["Value"], ["text", "media"])
                elif attr["Identifier"]["Label"] == "ENGAGEMENT":
                    self.assertIn(attr["Value"], ["low", "medium", "high"])
    
    def test_time_range_compliance(self):
        """Test that posts are created within the specified time range."""
        start_time = datetime.now(timezone.utc) - timedelta(days=30)
        end_time = datetime.now(timezone.utc)
        
        for post in self.result["records"]:
            creation_time = datetime.fromisoformat(post["CreationTime"])
            self.assertTrue(start_time <= creation_time <= end_time)
    
    def test_post_sorting(self):
        """Test that posts are sorted by creation time."""
        times = [datetime.fromisoformat(post["CreationTime"]) for post in self.result["records"]]
        
        # Check that times are in ascending order
        self.assertEqual(times, sorted(times))
    
    @unittest.skipIf(not HAS_DB, "Database modules not available")
    def test_db_integration(self):
        """Test that generated posts can be stored in the database."""
        if not hasattr(self, 'db') or not self.HAS_ACTIVE_DB:
            self.skipTest("No active database connection available")
        
        print("Database connection verified. Running database integration test...")
        
        # Check if collection exists
        collection_name = "SocialMediaActivity"
        if not self.db.has_collection(collection_name):
            self.db.create_collection(collection_name)
        
        collection = self.db.collection(collection_name)
        
        # Get the first post
        post = self.result["records"][0]
        
        try:
            # Try to insert the post into the database
            document = collection.insert(post)
            self.assertIsNotNone(document)
            print(f"Successfully inserted post into database: {document}")
            
            # Clean up after test
            collection.delete(document)
            print("Successfully deleted test post from database")
        except Exception as e:
            self.fail(f"Database integration test failed: {e}")


if __name__ == "__main__":
    unittest.main()