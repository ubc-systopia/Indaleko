"""Test suite for the NamedEntityGeneratorTool.

This module tests the functionality of the NamedEntityGeneratorTool,
ensuring it generates valid named entities and relationships
that can be properly stored in the ArangoDB database.
"""

import os
import sys
import unittest
import uuid
import random
from typing import Dict, Any
from datetime import datetime, timezone

# Setup path for imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import the generator tool
from tools.data_generator_enhanced.agents.data_gen.tools.named_entity_generator import (
    NamedEntityGeneratorTool,
    EntityGenerator,
    EntityNameGenerator,
    RelationshipManager,
    IndalekoNamedEntityType
)

# Import database-related modules
try:
    from db.db_config import IndalekoDBConfig
    from db.db_collections import IndalekoDBCollections
    HAS_DB = True
except ImportError:
    HAS_DB = False


class TestNamedEntityGenerator(unittest.TestCase):
    """Test cases for the NamedEntityGeneratorTool."""

    def setUp(self):
        """Set up the test environment."""
        # Initialize the generator with a fixed seed for reproducibility
        self.generator = NamedEntityGeneratorTool()
        self.seed = 42
        random.seed(self.seed)
        
        # Parameters for testing
        self.entity_counts = {
            "person": 3,
            "organization": 2,
            "location": 2,
            "item": 2
        }
        
        # Generate sample data
        self.result = self.generator.execute({
            "entity_counts": self.entity_counts,
            "relationship_density": 0.5,
            "seed": self.seed
        })
        
        # Set up database connection if available
        self.HAS_ACTIVE_DB = False
        if HAS_DB:
            try:
                self.db_config = IndalekoDBConfig()
                # Try to access database
                self.db = self.db_config.db
                if self.db:
                    self.named_entity_collection = self.db.collection(
                        IndalekoDBCollections.Indaleko_Named_Entity_Collection
                    )
                    self.HAS_ACTIVE_DB = True
            except Exception as e:
                print(f"Database connection failed: {e}")
                self.HAS_ACTIVE_DB = False
        else:
            self.HAS_ACTIVE_DB = False

    def test_generator_initialization(self):
        """Test that the generator initializes correctly."""
        self.assertIsNotNone(self.generator)
        self.assertIsInstance(self.generator, NamedEntityGeneratorTool)
        self.assertIsInstance(self.generator.entity_generator, EntityGenerator)
        self.assertIsInstance(self.generator.relationship_manager, RelationshipManager)

    def test_entity_generation(self):
        """Test that entities are generated with the correct types and counts."""
        # Check that all entity types were generated
        self.assertIn("entities", self.result)
        self.assertIn("relationships", self.result)
        
        # Check entity counts
        for entity_type, count in self.entity_counts.items():
            self.assertIn(entity_type, self.result["entities"])
            self.assertEqual(len(self.result["entities"][entity_type]), count)
            
        # Check entity structure
        for entity_type, entities in self.result["entities"].items():
            for entity in entities:
                self.assertIn("Id", entity)
                self.assertIn("name", entity)
                self.assertIn("category", entity)
                self.assertIn("description", entity)
                self.assertIn("attributes", entity)
                self.assertIn("semantic_attributes", entity)
                self.assertIn("created_at", entity)
                
                # UUID validation
                try:
                    uuid.UUID(entity["Id"])
                except ValueError:
                    self.fail(f"Invalid UUID format: {entity['Id']}")
                
                # Check entity-specific fields
                if entity_type == "person":
                    self.assertEqual(entity["category"], IndalekoNamedEntityType.person)
                    self.assertIn("profession", entity["attributes"])
                elif entity_type == "organization":
                    self.assertEqual(entity["category"], IndalekoNamedEntityType.organization)
                    self.assertIn("industry", entity["attributes"])
                elif entity_type == "location":
                    self.assertEqual(entity["category"], IndalekoNamedEntityType.location)
                    self.assertIn("gis_location", entity)
                    self.assertIn("latitude", entity["gis_location"])
                    self.assertIn("longitude", entity["gis_location"])
                elif entity_type == "item":
                    self.assertEqual(entity["category"], IndalekoNamedEntityType.item)
                    self.assertIn("device_id", entity)

    def test_relationship_generation(self):
        """Test that relationships are generated correctly."""
        self.assertIn("relationships", self.result)
        relationships = self.result["relationships"]
        
        # Check we have some relationships
        self.assertGreater(len(relationships), 0)
        
        # Check relationship structure
        for relationship in relationships:
            self.assertIn("Id", relationship)
            self.assertIn("entity1_id", relationship)
            self.assertIn("entity1_name", relationship)
            self.assertIn("entity1_type", relationship)
            self.assertIn("relationship_type", relationship)
            self.assertIn("entity2_id", relationship)
            self.assertIn("entity2_name", relationship)
            self.assertIn("entity2_type", relationship)
            self.assertIn("confidence", relationship)
            self.assertIn("created_at", relationship)
            
            # Check confidence is in range
            self.assertGreaterEqual(relationship["confidence"], 0.0)
            self.assertLessEqual(relationship["confidence"], 1.0)
            
            # Verify entities exist in the generated data
            found_entity1 = False
            found_entity2 = False
            
            for entity_list in self.result["entities"].values():
                for entity in entity_list:
                    if entity["Id"] == relationship["entity1_id"]:
                        found_entity1 = True
                    if entity["Id"] == relationship["entity2_id"]:
                        found_entity2 = True
            
            self.assertTrue(found_entity1, f"Entity1 {relationship['entity1_id']} not found in generated entities")
            self.assertTrue(found_entity2, f"Entity2 {relationship['entity2_id']} not found in generated entities")

    def test_common_locations(self):
        """Test that common locations are generated and shared."""
        self.assertIn("common_locations", self.result)
        common_locations = self.result["common_locations"]
        
        # Check that common locations are defined
        self.assertIn("home", common_locations)
        self.assertIn("work", common_locations)
        
        # Check that home and work locations are strings
        self.assertIsInstance(common_locations["home"], str)
        self.assertIsInstance(common_locations["work"], str)
        
        # Check that person entities reference common locations
        for person in self.result["entities"]["person"]:
            self.assertIn("references", person)
            self.assertIn("home", person["references"])
            self.assertIn("work", person["references"])
            self.assertEqual(person["references"]["home"], common_locations["home"])
            self.assertEqual(person["references"]["work"], common_locations["work"])

    def test_semantic_attributes(self):
        """Test that semantic attributes are generated correctly."""
        # Check each entity type has semantic attributes
        for entity_type, entities in self.result["entities"].items():
            for entity in entities:
                self.assertIn("semantic_attributes", entity)
                semantic_attrs = entity["semantic_attributes"]
                self.assertGreater(len(semantic_attrs), 0)
                
                # Check structure of semantic attributes
                for attr in semantic_attrs:
                    self.assertIn("Identifier", attr)
                    self.assertIn("Value", attr)
                    
                    # Check that identifier is a string that includes the domain
                    self.assertIsInstance(attr["Identifier"], str)
                    self.assertIn("_id", attr["Identifier"])
                    
                    # Value can be various types (string, int, float)
                    self.assertIsNotNone(attr["Value"])

    def test_name_generation(self):
        """Test that names are generated correctly for different entity types."""
        name_generator = EntityNameGenerator(seed=self.seed)
        
        # Test person name generation
        person_name = name_generator.generate_person_name()
        self.assertIsInstance(person_name, str)
        self.assertGreater(len(person_name.split()), 1)  # Should have first and last name
        
        # Test organization name generation
        org_name = name_generator.generate_organization_name()
        self.assertIsInstance(org_name, str)
        self.assertGreater(len(org_name), 0)
        
        # Test location name generation
        location_name = name_generator.generate_location_name()
        self.assertIsInstance(location_name, str)
        self.assertGreater(len(location_name), 0)
        
        # Test item name generation
        item_name = name_generator.generate_item_name()
        self.assertIsInstance(item_name, str)
        self.assertGreater(len(item_name), 0)

    @unittest.skipIf(not HAS_DB, "Database modules not available")
    def test_db_integration(self):
        """Test that generated entities can be stored in the database."""
        if not hasattr(self, 'db') or not self.HAS_ACTIVE_DB:
            self.skipTest("No active database connection available")
            
        print("Database connection verified. Running database integration test...")
        
        # Get a person entity from the generated data
        person = self.result["entities"]["person"][0]
        
        # Convert to database format (following the schema requirements)
        db_entity = {
            "name": person["name"],
            "uuid": person["Id"],
            "category": person["category"],
            "description": person["description"]
        }
        
        # If the entity has a gis_location, include it
        if "gis_location" in person:
            db_entity["gis_location"] = person["gis_location"]
        
        # If the entity has a device_id, include it
        if "device_id" in person:
            db_entity["device_id"] = person["device_id"]
        
        try:
            # Try to insert the entity into the database
            document = self.named_entity_collection.insert(db_entity)
            self.assertIsNotNone(document)
            print(f"Successfully inserted document into database: {document}")
            
            # Clean up after test
            self.named_entity_collection.delete(document)
            print("Successfully deleted test document from database")
        except Exception as e:
            self.fail(f"Database integration test failed: {e}")

    def test_truth_criteria(self):
        """Test that truth entities can be generated with specific criteria."""
        # Generate data with truth criteria
        truth_criteria = {
            "person": {
                "name": "Tony Mason",
                "attributes": {
                    "profession": "researcher",
                    "expertise": "machine learning"
                }
            },
            "location": {
                "name": "Redmond",
                "gis_location": {
                    "latitude": 47.6739,
                    "longitude": -122.1215
                }
            }
        }
        
        result = self.generator.execute({
            "entity_counts": self.entity_counts,
            "relationship_density": 0.5,
            "seed": self.seed,
            "truth_criteria": truth_criteria
        })
        
        # Verify truth entities were generated
        self.assertIn("truth_entities", result)
        self.assertIn("person", result["truth_entities"])
        self.assertIn("location", result["truth_entities"])
        
        # Verify criteria were applied
        person = result["truth_entities"]["person"]
        self.assertEqual(person["name"], "Tony Mason")
        self.assertEqual(person["attributes"]["profession"], "researcher")
        self.assertEqual(person["attributes"]["expertise"], "machine learning")
        
        location = result["truth_entities"]["location"]
        self.assertEqual(location["name"], "Redmond")
        self.assertEqual(location["gis_location"]["latitude"], 47.6739)
        self.assertEqual(location["gis_location"]["longitude"], -122.1215)


if __name__ == "__main__":
    unittest.main()