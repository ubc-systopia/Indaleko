"""
Tests for the entity manager module.

This module contains unit tests for the named entity management functionality
in the ablation study framework.
"""

import json
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from typing import Dict, List, Any

from tools.ablation.ner.entity_manager import EntityManager


class TestEntityManager(unittest.TestCase):
    """Test case for the EntityManager class."""

    def setUp(self):
        """Set up test fixtures."""
        # Use a test-specific collection name to avoid interfering with real data
        self.manager = EntityManager(collection_name="TestAblationNamedEntities")
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Clear any existing test data
        self.manager.clear_entities()

    def tearDown(self):
        """Tear down test fixtures."""
        # Clear test data
        self.manager.clear_entities()
        self.temp_dir.cleanup()

    def test_add_and_get_entity(self):
        """Test adding and retrieving entities."""
        # Add a test entity
        name = "Seattle"
        entity_type = "location"
        attributes = {
            "country": "USA",
            "state": "Washington",
            "coordinates": {
                "latitude": 47.6062,
                "longitude": -122.3321
            }
        }

        entity_id = self.manager.add_entity(name, entity_type, attributes)

        # Check that the entity ID is a string
        self.assertIsInstance(entity_id, str)

        # Get the entity
        entity = self.manager.get_entity(name, entity_type)

        # Check that we got an entity back
        self.assertIsNotNone(entity)

        # Check that the entity has the expected fields
        self.assertEqual(entity["name"], name)
        self.assertEqual(entity["entity_type"], entity_type)
        self.assertEqual(entity["attributes"], attributes)

    def test_update_entity(self):
        """Test updating an entity."""
        # Add a test entity
        name = "Taylor Swift"
        entity_type = "artist"
        attributes = {
            "genres": ["pop", "country"],
            "active_since": 2006
        }

        entity_id = self.manager.add_entity(name, entity_type, attributes)

        # Update the entity
        updated_attributes = {
            "genres": ["pop", "country", "alternative"],
            "albums": ["1989", "Reputation", "Folklore"]
        }

        success = self.manager.update_entity(entity_id, updated_attributes)

        # Check that the update succeeded
        self.assertTrue(success)

        # Get the updated entity
        entity = self.manager.get_entity(name, entity_type)

        # Check that the entity was updated correctly
        self.assertIsNotNone(entity)
        self.assertEqual(entity["attributes"]["genres"], ["pop", "country", "alternative"])
        self.assertEqual(entity["attributes"]["albums"], ["1989", "Reputation", "Folklore"])
        self.assertEqual(entity["attributes"]["active_since"], 2006)  # Should keep existing attributes

    def test_get_entities_by_type(self):
        """Test getting entities by type."""
        # Add some test entities
        locations = [
            ("Seattle", {"country": "USA", "state": "Washington"}),
            ("London", {"country": "UK", "city": "London"}),
            ("Tokyo", {"country": "Japan", "city": "Tokyo"})
        ]

        for name, attributes in locations:
            self.manager.add_entity(name, "location", attributes)

        # Add entities of a different type
        artists = [
            ("Taylor Swift", {"genres": ["pop", "country"]}),
            ("The Beatles", {"genres": ["rock"]})
        ]

        for name, attributes in artists:
            self.manager.add_entity(name, "artist", attributes)

        # Get all location entities
        location_entities = self.manager.get_entities_by_type("location")

        # Check that we got the right number of entities
        self.assertEqual(len(location_entities), 3)

        # Check that all entities are of the right type
        for entity in location_entities:
            self.assertEqual(entity["entity_type"], "location")

        # Get all artist entities
        artist_entities = self.manager.get_entities_by_type("artist")

        # Check that we got the right number of entities
        self.assertEqual(len(artist_entities), 2)

        # Check that all entities are of the right type
        for entity in artist_entities:
            self.assertEqual(entity["entity_type"], "artist")

    def test_get_or_create_entity(self):
        """Test getting or creating an entity."""
        # Try to get a non-existent entity
        name = "Seattle"
        entity_type = "location"
        attributes = {
            "country": "USA",
            "state": "Washington"
        }

        # This should create the entity
        entity_id = self.manager.get_or_create_entity(name, entity_type, attributes)

        # Check that we got an entity ID
        self.assertIsNotNone(entity_id)

        # Get the entity
        entity = self.manager.get_entity(name, entity_type)

        # Check that the entity was created correctly
        self.assertIsNotNone(entity)
        self.assertEqual(entity["name"], name)
        self.assertEqual(entity["entity_type"], entity_type)
        self.assertEqual(entity["attributes"], attributes)

        # Try to get the same entity again, with updated attributes
        updated_attributes = {
            "country": "USA",
            "state": "Washington",
            "coordinates": {
                "latitude": 47.6062,
                "longitude": -122.3321
            }
        }

        # This should return the same entity
        second_id = self.manager.get_or_create_entity(name, entity_type, updated_attributes)

        # Check that we got the same entity ID
        self.assertEqual(second_id, entity_id)

        # Get the entity again
        updated_entity = self.manager.get_entity(name, entity_type)

        # Check that the entity was updated correctly
        self.assertIsNotNone(updated_entity)
        self.assertEqual(updated_entity["attributes"], updated_attributes)

    def test_add_reference(self):
        """Test adding a reference to an entity."""
        # Add a test entity
        name = "Seattle"
        entity_type = "location"
        attributes = {"country": "USA"}

        entity_id = self.manager.add_entity(name, entity_type, attributes)

        # Add a reference
        reference_id = str(uuid.uuid4())
        success = self.manager.add_reference(entity_id, reference_id)

        # Check that the reference was added successfully
        self.assertTrue(success)

        # Get the entity
        entity = self.manager.get_entity(name, entity_type)

        # Check that the reference was added correctly
        self.assertIsNotNone(entity)
        self.assertIn(reference_id, entity["references"])

    def test_save_and_load_entities(self):
        """Test saving and loading entities."""
        # Add some test entities
        entities = [
            ("Seattle", "location", {"country": "USA"}),
            ("London", "location", {"country": "UK"}),
            ("Taylor Swift", "artist", {"genres": ["pop"]})
        ]

        for name, entity_type, attributes in entities:
            self.manager.add_entity(name, entity_type, attributes)

        # Save the entities
        output_path = self.temp_path / "entities.json"
        self.manager.save_entities(output_path)

        # Check that the file exists
        self.assertTrue(output_path.exists())

        # Clear the existing data
        self.manager.clear_entities()

        # Check that the data was cleared
        self.assertEqual(self.manager.get_entity_count(), 0)

        # Load the entities
        self.manager.load_entities(output_path)

        # Check that we got the entities back
        self.assertEqual(self.manager.get_entity_count(), 3)

        # Check that specific entities were loaded correctly
        seattle = self.manager.get_entity("Seattle", "location")
        taylor = self.manager.get_entity("Taylor Swift", "artist")

        self.assertIsNotNone(seattle)
        self.assertIsNotNone(taylor)
        self.assertEqual(seattle["attributes"]["country"], "USA")
        self.assertEqual(taylor["attributes"]["genres"], ["pop"])


if __name__ == "__main__":
    unittest.main()
