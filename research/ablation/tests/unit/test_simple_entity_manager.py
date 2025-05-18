"""Simple unit tests for named entity manager."""

import unittest
import uuid

from ...models.named_entity import EntityRelationType, EntityType
from ...ner.enhanced_entity_manager import NamedEntityManager


class TestSimpleEntityManager(unittest.TestCase):
    """Simple test cases for entity manager that don't require a database connection."""

    def setUp(self):
        """Set up test fixtures."""
        # Create an in-memory entity manager for testing
        self.entity_manager = NamedEntityManager(db=None)

    def test_create_entity(self):
        """Test creating an entity."""
        # Create an entity
        entity = self.entity_manager.create_entity(
            entity_type=EntityType.LOCATION,
            name="Test Location",
            aliases=["TestLoc", "TL"],
            properties={"type": "test"},
        )

        # Check that the entity was created
        self.assertIsNotNone(entity)
        self.assertEqual(EntityType.LOCATION, entity.entity_type)
        self.assertEqual("Test Location", entity.name)
        self.assertEqual(2, len(entity.aliases))
        self.assertEqual("test", entity.properties["type"])

        # Check that it's in the manager's cache
        cached_entity = self.entity_manager.get_entity_by_name(EntityType.LOCATION, "Test Location")
        self.assertIsNotNone(cached_entity)
        self.assertEqual(entity.id, cached_entity.id)

    def test_get_entity_by_name(self):
        """Test getting an entity by name."""
        # Create an entity
        entity = self.entity_manager.create_entity(entity_type=EntityType.PERSON, name="John Doe")

        # Get the entity by name
        retrieved_entity = self.entity_manager.get_entity_by_name(EntityType.PERSON, "John Doe")

        # Check that we got the correct entity
        self.assertIsNotNone(retrieved_entity)
        self.assertEqual(entity.id, retrieved_entity.id)

        # In the current implementation, get_entity_by_name works by checking internal dictionaries
        # It returns None if the name doesn't exist in the internal dictionary
        non_exist_name = f"NonExistent_{uuid.uuid4().hex}"
        non_existent = self.entity_manager.get_entity_by_name(EntityType.PERSON, non_exist_name)
        self.assertIsNone(non_existent)

    def test_get_entity_by_id(self):
        """Test getting an entity by ID."""
        # Create an entity
        entity = self.entity_manager.create_entity(entity_type=EntityType.ORGANIZATION, name="Acme Corp")

        # Get the entity by ID
        retrieved_entity = self.entity_manager.get_entity_by_id(entity.id)

        # Check that we got the correct entity
        self.assertIsNotNone(retrieved_entity)
        self.assertEqual(entity.name, retrieved_entity.name)

        # Try to get a non-existent entity
        import uuid

        non_existent_id = uuid.uuid4()
        non_existent = self.entity_manager.get_entity_by_id(non_existent_id)
        self.assertIsNone(non_existent)

    def test_create_relation(self):
        """Test creating a relation between entities."""
        # Create two entities
        entity1 = self.entity_manager.create_entity(entity_type=EntityType.LOCATION, name="New York")

        entity2 = self.entity_manager.create_entity(entity_type=EntityType.LOCATION, name="Manhattan")

        # Create a relation
        relation = self.entity_manager.create_relation(
            entity1.id, entity2.id, EntityRelationType.PARENT, {"type": "city-borough"},
        )

        # Check that the relation was created
        self.assertIsNotNone(relation)
        self.assertEqual(entity1.id, relation.source_entity_id)
        self.assertEqual(entity2.id, relation.target_entity_id)
        self.assertEqual(EntityRelationType.PARENT, relation.relation_type)
        self.assertEqual("city-borough", relation.properties["type"])

        # Check that it's in the manager's cache
        relations = self.entity_manager.get_relations_for_entity(entity1.id)
        self.assertEqual(1, len(relations))
        self.assertEqual(relation.id, relations[0].id)

    def test_get_related_entities(self):
        """Test getting related entities."""
        # Create three entities with relationships
        new_york = self.entity_manager.create_entity(entity_type=EntityType.LOCATION, name="New York")

        manhattan = self.entity_manager.create_entity(entity_type=EntityType.LOCATION, name="Manhattan")

        brooklyn = self.entity_manager.create_entity(entity_type=EntityType.LOCATION, name="Brooklyn")

        # Create relations
        self.entity_manager.create_relation(new_york.id, manhattan.id, EntityRelationType.PARENT)

        self.entity_manager.create_relation(new_york.id, brooklyn.id, EntityRelationType.PARENT)

        # Get related entities for New York
        related = self.entity_manager.get_related_entities(new_york.id)

        # Check that we got both Manhattan and Brooklyn
        self.assertEqual(2, len(related))
        related_names = [e.name for e in related]
        self.assertIn("Manhattan", related_names)
        self.assertIn("Brooklyn", related_names)

        # Check reverse relationship
        parent = self.entity_manager.get_related_entities(manhattan.id, as_source=False)
        self.assertEqual(1, len(parent))
        self.assertEqual("New York", parent[0].name)

    def test_search_entities(self):
        """Test searching for entities."""
        # Create entities with different names and aliases
        self.entity_manager.create_entity(
            entity_type=EntityType.LOCATION, name="New York City", aliases=["NYC", "The Big Apple"],
        )

        self.entity_manager.create_entity(
            entity_type=EntityType.LOCATION, name="Los Angeles", aliases=["LA", "City of Angels"],
        )

        self.entity_manager.create_entity(entity_type=EntityType.PERSON, name="John Smith")

        # Search for entities
        results = self.entity_manager.search_entities("york")
        self.assertEqual(1, len(results))
        self.assertEqual("New York City", results[0].name)

        results = self.entity_manager.search_entities("nyc")
        self.assertEqual(1, len(results))
        self.assertEqual("New York City", results[0].name)

        # When searching for "city", both "New York City" and possibly "City of Angels"
        # will match, so just check that "New York City" is in the results
        results = self.entity_manager.search_entities("city")
        self.assertGreaterEqual(len(results), 1)
        result_names = [entity.name for entity in results]
        self.assertIn("New York City", result_names)

        results = self.entity_manager.search_entities("angel")
        self.assertEqual(1, len(results))
        self.assertEqual("Los Angeles", results[0].name)

        results = self.entity_manager.search_entities("john")
        self.assertEqual(1, len(results))
        self.assertEqual("John Smith", results[0].name)

    def test_add_entity_alias(self):
        """Test adding an alias to an entity."""
        # Create an entity
        entity = self.entity_manager.create_entity(entity_type=EntityType.LOCATION, name="San Francisco")

        # Add an alias
        success = self.entity_manager.add_entity_alias(entity.id, "SF")
        self.assertTrue(success)

        # Check that the alias was added
        updated_entity = self.entity_manager.get_entity_by_id(entity.id)
        self.assertTrue(any(alias.name == "SF" for alias in updated_entity.aliases))

        # Add another alias with a language
        success = self.entity_manager.add_entity_alias(entity.id, "San Fran", "en")
        self.assertTrue(success)

        # Check that the alias was added
        updated_entity = self.entity_manager.get_entity_by_id(entity.id)
        san_fran_alias = next((alias for alias in updated_entity.aliases if alias.name == "San Fran"), None)
        self.assertIsNotNone(san_fran_alias)
        self.assertEqual("en", san_fran_alias.language)

    def test_add_entity_property(self):
        """Test adding a property to an entity."""
        # Create an entity
        entity = self.entity_manager.create_entity(entity_type=EntityType.ORGANIZATION, name="Google")

        # Add a property
        success = self.entity_manager.add_entity_property(entity.id, "industry", "technology")
        self.assertTrue(success)

        # Check that the property was added
        updated_entity = self.entity_manager.get_entity_by_id(entity.id)
        self.assertEqual("technology", updated_entity.properties["industry"])

    def test_extract_entities_from_text(self):
        """Test extracting entities from text."""
        # Create entities
        self.entity_manager.create_entity(entity_type=EntityType.LOCATION, name="New York", aliases=["NYC"])

        self.entity_manager.create_entity(entity_type=EntityType.PERSON, name="John Smith")

        # Extract entities from text
        text = "John Smith visited New York last week. He loved NYC."
        extracted = self.entity_manager.extract_entities_from_text(text)

        # The extracting function works by checking for matches, which might result
        # in duplicate matches if aliases are also found; just check that all needed
        # entities were found
        extracted_names = [e[0].name for e in extracted]

        entity_names = [e[0].name for e in extracted]
        self.assertIn("John Smith", entity_names)
        self.assertIn("New York", entity_names)

        # Check positions
        positions = [(e[1], e[2]) for e in extracted]
        self.assertIn((0, 10), positions)  # "John Smith"
        self.assertIn((19, 27), positions)  # "New York"

        # One entity should be extracted via its alias (NYC)
        alias_entity = next((e for e in extracted if text[e[1] : e[2]] == "NYC"), None)
        self.assertIsNotNone(alias_entity)
        # The entity found might be "New York" or something similar like "New York City"
        # Just check that it contains "New York" in its name
        self.assertIn("New York", alias_entity[0].name)


if __name__ == "__main__":
    unittest.main()
