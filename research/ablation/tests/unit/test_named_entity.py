"""Unit tests for named entity management."""

import unittest
from uuid import UUID

from ...models.named_entity import EntityRelationType, EntityType, NamedEntity
from ...ner.enhanced_entity_manager import NamedEntityManager
from ..test_utils import AblationTestCase


class TestNamedEntityModel(AblationTestCase):
    """Test cases for the NamedEntity model."""

    def test_named_entity_creation(self):
        """Test creating a NamedEntity."""
        # Create a named entity
        entity = NamedEntity(
            entity_type=EntityType.LOCATION,
            name="San Francisco",
        )

        # Check that the instance was created correctly
        self.assertEqual(EntityType.LOCATION, entity.entity_type)
        self.assertEqual("San Francisco", entity.name)

        # Check that the ID was generated
        self.assertIsNotNone(entity.id)
        self.assertIsInstance(entity.id, UUID)

        # Check that the timestamps were set
        self.assertIsNotNone(entity.created_at)
        self.assertIsNotNone(entity.modified_at)

    def test_named_entity_aliases(self):
        """Test adding aliases to a NamedEntity."""
        # Create a named entity
        entity = NamedEntity(
            entity_type=EntityType.LOCATION,
            name="San Francisco",
        )

        # Add aliases
        entity.add_alias("SF")
        entity.add_alias("Frisco")
        entity.add_alias("San Fran", "en-US")

        # Check that the aliases were added
        self.assertEqual(3, len(entity.aliases))
        self.assertEqual("SF", entity.aliases[0].name)
        self.assertEqual("Frisco", entity.aliases[1].name)
        self.assertEqual("San Fran", entity.aliases[2].name)
        self.assertEqual("en-US", entity.aliases[2].language)

        # Add a duplicate alias
        entity.add_alias("SF")

        # Check that the duplicate was not added
        self.assertEqual(3, len(entity.aliases))

    def test_named_entity_properties(self):
        """Test adding properties to a NamedEntity."""
        # Create a named entity
        entity = NamedEntity(
            entity_type=EntityType.LOCATION,
            name="San Francisco",
        )

        # Add properties
        entity.add_property("country", "USA")
        entity.add_property("state", "California")
        entity.add_property("population", "884,363")

        # Check that the properties were added
        self.assertEqual(3, len(entity.properties))
        self.assertEqual("USA", entity.properties["country"])
        self.assertEqual("California", entity.properties["state"])
        self.assertEqual("884,363", entity.properties["population"])

        # Update a property
        entity.add_property("population", "900,000")

        # Check that the property was updated
        self.assertEqual("900,000", entity.properties["population"])

    def test_named_entity_matches(self):
        """Test the matches method."""
        # Create a named entity
        entity = NamedEntity(
            entity_type=EntityType.LOCATION,
            name="San Francisco",
        )

        # Add aliases
        entity.add_alias("SF")
        entity.add_alias("Frisco")

        # Check matches
        self.assertTrue(entity.matches("I visited San Francisco last week"))
        self.assertTrue(entity.matches("I visited SF last week"))
        self.assertTrue(entity.matches("I visited Frisco last week"))
        self.assertFalse(entity.matches("I visited Los Angeles last week"))

        # Check case-insensitive matching
        self.assertTrue(entity.matches("I visited SAN FRANCISCO last week"))
        self.assertTrue(entity.matches("I visited sf last week"))
        self.assertTrue(entity.matches("I visited FRISCO last week"))


class TestNamedEntityManager(AblationTestCase):
    """Test cases for the NamedEntityManager class."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

        # Create a named entity manager
        self.manager = NamedEntityManager(db=self.db_manager.db)

    def test_create_entity(self):
        """Test creating an entity."""
        # Create an entity
        entity = self.manager.create_entity(
            entity_type=EntityType.LOCATION,
            name="Los Angeles",
            aliases=["LA", "City of Angels"],
            properties={"country": "USA", "state": "California"},
        )

        # Check that the entity was created correctly
        self.assertEqual(EntityType.LOCATION, entity.entity_type)
        self.assertEqual("Los Angeles", entity.name)
        self.assertEqual(2, len(entity.aliases))
        self.assertEqual("LA", entity.aliases[0].name)
        self.assertEqual("City of Angels", entity.aliases[1].name)
        self.assertEqual(2, len(entity.properties))
        self.assertEqual("USA", entity.properties["country"])
        self.assertEqual("California", entity.properties["state"])

        # Check that the entity was added to the manager
        self.assertIs(entity, self.manager.get_entity_by_name(EntityType.LOCATION, "Los Angeles"))
        self.assertIs(entity, self.manager.get_entity_by_id(entity.id))

    def test_create_duplicate_entity(self):
        """Test creating a duplicate entity."""
        # Create an entity
        entity1 = self.manager.create_entity(
            entity_type=EntityType.LOCATION,
            name="Los Angeles",
            aliases=["LA"],
        )

        # Create a duplicate entity
        entity2 = self.manager.create_entity(
            entity_type=EntityType.LOCATION,
            name="Los Angeles",
            aliases=["City of Angels"],
            properties={"country": "USA"},
        )

        # Check that the entities are the same object
        self.assertIs(entity1, entity2)

        # Check that the properties were updated
        self.assertEqual(2, len(entity1.aliases))
        self.assertEqual("LA", entity1.aliases[0].name)
        self.assertEqual("City of Angels", entity1.aliases[1].name)
        self.assertEqual(1, len(entity1.properties))
        self.assertEqual("USA", entity1.properties["country"])

    def test_get_entities_by_type(self):
        """Test getting entities by type."""
        # Create some entities
        self.manager.create_entity(EntityType.LOCATION, "Los Angeles")
        self.manager.create_entity(EntityType.LOCATION, "New York")
        self.manager.create_entity(EntityType.PERSON, "John Smith")
        self.manager.create_entity(EntityType.ORGANIZATION, "Microsoft")

        # Get entities by type
        locations = self.manager.get_entities_by_type(EntityType.LOCATION)
        persons = self.manager.get_entities_by_type(EntityType.PERSON)
        organizations = self.manager.get_entities_by_type(EntityType.ORGANIZATION)

        # Check that the correct entities were returned
        self.assertEqual(2, len(locations))
        self.assertEqual(1, len(persons))
        self.assertEqual(1, len(organizations))
        self.assertIn("Los Angeles", locations)
        self.assertIn("New York", locations)
        self.assertIn("John Smith", persons)
        self.assertIn("Microsoft", organizations)

    def test_search_entities(self):
        """Test searching for entities."""
        # Create some entities
        la = self.manager.create_entity(
            entity_type=EntityType.LOCATION,
            name="Los Angeles",
            aliases=["LA", "City of Angels"],
        )

        ny = self.manager.create_entity(
            entity_type=EntityType.LOCATION,
            name="New York",
            aliases=["NYC", "The Big Apple"],
        )

        # Search for entities
        results1 = self.manager.search_entities("Los")
        results2 = self.manager.search_entities("LA")
        results3 = self.manager.search_entities("NYC")
        results4 = self.manager.search_entities("Chicago")

        # Check that the correct entities were returned
        self.assertEqual(1, len(results1))
        self.assertEqual(1, len(results2))
        self.assertEqual(1, len(results3))
        self.assertEqual(0, len(results4))
        self.assertIn(la, results1)
        self.assertIn(la, results2)
        self.assertIn(ny, results3)

    def test_create_relation(self):
        """Test creating a relation."""
        # Create some entities
        california = self.manager.create_entity(EntityType.LOCATION, "California")
        la = self.manager.create_entity(EntityType.LOCATION, "Los Angeles")

        # Create a relation
        relation = self.manager.create_relation(
            california.id,
            la.id,
            EntityRelationType.PARENT,
            {"type": "state-city"},
        )

        # Check that the relation was created correctly
        self.assertEqual(california.id, relation.source_entity_id)
        self.assertEqual(la.id, relation.target_entity_id)
        self.assertEqual(EntityRelationType.PARENT, relation.relation_type)
        self.assertEqual(1, len(relation.properties))
        self.assertEqual("state-city", relation.properties["type"])

        # Check that the relation was added to the manager
        self.assertIs(relation, self.manager.get_relation(relation.id))

        # Check that the entities were updated
        california_entity = self.manager.get_entity_by_id(california.id)
        self.assertIsNotNone(california_entity)
        self.assertIn(la.id, california_entity.related_entities)

    def test_get_relations_for_entity(self):
        """Test getting relations for an entity."""
        # Create some entities
        california = self.manager.create_entity(EntityType.LOCATION, "California")
        la = self.manager.create_entity(EntityType.LOCATION, "Los Angeles")
        sf = self.manager.create_entity(EntityType.LOCATION, "San Francisco")

        # Create some relations
        relation1 = self.manager.create_relation(
            california.id,
            la.id,
            EntityRelationType.PARENT,
        )

        relation2 = self.manager.create_relation(
            california.id,
            sf.id,
            EntityRelationType.PARENT,
        )

        relation3 = self.manager.create_relation(
            la.id,
            sf.id,
            EntityRelationType.RELATED,
        )

        # Get relations for California as source
        relations1 = self.manager.get_relations_for_entity(california.id, as_source=True)

        # Get parent relations for California as source
        relations2 = self.manager.get_relations_for_entity(
            california.id,
            relation_type=EntityRelationType.PARENT,
            as_source=True,
        )

        # Get relations for LA as target
        relations3 = self.manager.get_relations_for_entity(la.id, as_source=False)

        # Check that the correct relations were returned
        self.assertEqual(2, len(relations1))
        self.assertEqual(2, len(relations2))
        self.assertEqual(1, len(relations3))
        self.assertIn(relation1, relations1)
        self.assertIn(relation2, relations1)
        self.assertIn(relation1, relations2)
        self.assertIn(relation2, relations2)
        self.assertIn(relation1, relations3)

    def test_get_related_entities(self):
        """Test getting related entities."""
        # Create some entities
        california = self.manager.create_entity(EntityType.LOCATION, "California")
        la = self.manager.create_entity(EntityType.LOCATION, "Los Angeles")
        sf = self.manager.create_entity(EntityType.LOCATION, "San Francisco")

        # Create some relations
        self.manager.create_relation(
            california.id,
            la.id,
            EntityRelationType.PARENT,
        )

        self.manager.create_relation(
            california.id,
            sf.id,
            EntityRelationType.PARENT,
        )

        # Get related entities for California as source
        entities = self.manager.get_related_entities(california.id, as_source=True)

        # Check that the correct entities were returned
        self.assertEqual(2, len(entities))
        self.assertIn(la, entities)
        self.assertIn(sf, entities)

        # Get related entities for LA as target
        entities = self.manager.get_related_entities(la.id, as_source=False)

        # Check that the correct entities were returned
        self.assertEqual(1, len(entities))
        self.assertIn(california, entities)

    def test_add_entity_alias(self):
        """Test adding an alias to an entity."""
        # Create an entity
        entity = self.manager.create_entity(EntityType.LOCATION, "San Francisco")

        # Add an alias
        self.manager.add_entity_alias(entity.id, "SF")

        # Check that the alias was added
        updated_entity = self.manager.get_entity_by_id(entity.id)
        self.assertEqual(1, len(updated_entity.aliases))
        self.assertEqual("SF", updated_entity.aliases[0].name)

    def test_add_entity_property(self):
        """Test adding a property to an entity."""
        # Create an entity
        entity = self.manager.create_entity(EntityType.LOCATION, "San Francisco")

        # Add a property
        self.manager.add_entity_property(entity.id, "country", "USA")

        # Check that the property was added
        updated_entity = self.manager.get_entity_by_id(entity.id)
        self.assertEqual(1, len(updated_entity.properties))
        self.assertEqual("USA", updated_entity.properties["country"])

    def test_add_relation_property(self):
        """Test adding a property to a relation."""
        # Create some entities
        california = self.manager.create_entity(EntityType.LOCATION, "California")
        la = self.manager.create_entity(EntityType.LOCATION, "Los Angeles")

        # Create a relation
        relation = self.manager.create_relation(
            california.id,
            la.id,
            EntityRelationType.PARENT,
        )

        # Add a property
        self.manager.add_relation_property(relation.id, "type", "state-city")

        # Check that the property was added
        updated_relation = self.manager.get_relation(relation.id)
        self.assertEqual(1, len(updated_relation.properties))
        self.assertEqual("state-city", updated_relation.properties["type"])

    def test_extract_entities_from_text(self):
        """Test extracting entities from text."""
        # Create some entities
        la = self.manager.create_entity(
            entity_type=EntityType.LOCATION,
            name="Los Angeles",
            aliases=["LA"],
        )

        ny = self.manager.create_entity(
            entity_type=EntityType.LOCATION,
            name="New York",
            aliases=["NYC"],
        )

        # Extract entities from text
        text = "I visited Los Angeles and New York last week. LA was warm, but NYC was cold."
        entities = self.manager.extract_entities_from_text(text)

        # Check that the correct entities were extracted
        self.assertEqual(4, len(entities))
        self.assertEqual(la, entities[0][0])
        self.assertEqual(ny, entities[1][0])
        self.assertEqual(la, entities[2][0])
        self.assertEqual(ny, entities[3][0])
        self.assertEqual(10, entities[0][1])  # "Los Angeles" starts at index 10
        self.assertEqual(26, entities[1][1])  # "New York" starts at index 26
        self.assertEqual(43, entities[2][1])  # "LA" starts at index 43
        self.assertEqual(58, entities[3][1])  # "NYC" starts at index 58


if __name__ == "__main__":
    unittest.main()
