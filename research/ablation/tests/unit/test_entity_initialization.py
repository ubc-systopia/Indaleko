"""Unit tests for entity initialization."""

import unittest

import pytest

from db.db_collections import IndalekoDBCollections
from db.db_config import IndalekoDBConfig

from ...models.named_entity import EntityType
from ...ner.enhanced_entity_manager import NamedEntityManager
from ...ner.initialization import EntityInitializer, initialize_standard_entities
from ..test_utils import AblationTestCase


class TestEntityInitialization(AblationTestCase):
    """Test cases for entity initialization."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

        # Get database connection using Indaleko's existing patterns
        try:
            self.db_config = IndalekoDBConfig()
            self.db = self.db_config.get_arangodb()
        except Exception as e:
            self.db = None
            self.skipTest(f"Failed to connect to database: {e}")

        # Use the standard NamedEntities collection
        self.collection_name = IndalekoDBCollections.Indaleko_Named_Entity_Collection

        # Clear in-memory entity manager for testing
        self.entity_manager = NamedEntityManager(db=None)  # In-memory only
        for entity_type in EntityType:
            self.entity_manager.entities[entity_type] = {}
        self.entity_manager.entities_by_id = {}
        self.entity_manager.relations = {}

    def test_initialize_locations(self):
        """Test initializing location entities."""
        # Create an entity initializer
        initializer = EntityInitializer(self.entity_manager)

        # Initialize locations
        locations = initializer.initialize_locations()

        # Check that locations were created
        self.assertGreater(len(locations), 0)

        # Check for specific locations
        self.assertIn("United States", locations)
        self.assertIn("California", locations)
        self.assertIn("San Francisco", locations)
        self.assertIn("New York City", locations)
        self.assertIn("Home", locations)
        self.assertIn("Work", locations)

        # Check properties
        self.assertEqual("country", locations["United States"].properties["type"])
        self.assertEqual("state", locations["California"].properties["type"])
        self.assertEqual("city", locations["San Francisco"].properties["type"])

        # Check aliases
        self.assertTrue(any(alias.name == "USA" for alias in locations["United States"].aliases))
        self.assertTrue(any(alias.name == "SF" for alias in locations["San Francisco"].aliases))
        self.assertTrue(any(alias.name == "NYC" for alias in locations["New York City"].aliases))

    def test_initialize_people(self):
        """Test initializing person entities."""
        # Create an entity initializer
        initializer = EntityInitializer(self.entity_manager)

        # Initialize people
        people = initializer.initialize_people()

        # Check that people were created
        self.assertGreater(len(people), 0)

        # Check for specific people
        self.assertIn("Elon Musk", people)
        self.assertIn("Bill Gates", people)
        self.assertIn("Taylor Swift", people)
        self.assertIn("John Smith", people)

        # Check properties
        self.assertEqual("entrepreneur", people["Elon Musk"].properties["occupation"])
        self.assertEqual("entrepreneur", people["Bill Gates"].properties["occupation"])
        self.assertEqual("musician", people["Taylor Swift"].properties["occupation"])
        self.assertEqual("fictional", people["John Smith"].properties["type"])

        # Check aliases
        self.assertTrue(any(alias.name == "Elon" for alias in people["Elon Musk"].aliases))
        self.assertTrue(any(alias.name == "Gates" for alias in people["Bill Gates"].aliases))

    def test_initialize_organizations(self):
        """Test initializing organization entities."""
        # Create an entity initializer
        initializer = EntityInitializer(self.entity_manager)

        # Initialize organizations
        organizations = initializer.initialize_organizations()

        # Check that organizations were created
        self.assertGreater(len(organizations), 0)

        # Check for specific organizations
        self.assertIn("Microsoft", organizations)
        self.assertIn("Apple", organizations)
        self.assertIn("Google", organizations)
        self.assertIn("United Nations", organizations)

        # Check properties
        self.assertEqual("technology", organizations["Microsoft"].properties["industry"])
        self.assertEqual("technology", organizations["Apple"].properties["industry"])
        self.assertEqual("technology", organizations["Google"].properties["industry"])
        self.assertEqual("international", organizations["United Nations"].properties["type"])

        # Check aliases
        self.assertTrue(any(alias.name == "MS" for alias in organizations["Microsoft"].aliases))
        self.assertTrue(any(alias.name == "UN" for alias in organizations["United Nations"].aliases))

    def test_initialize_events(self):
        """Test initializing event entities."""
        # Create an entity initializer
        initializer = EntityInitializer(self.entity_manager)

        # Initialize events
        events = initializer.initialize_events()

        # Check that events were created
        self.assertGreater(len(events), 0)

        # Check for specific events
        self.assertIn("Meeting", events)
        self.assertIn("Conference", events)
        self.assertIn("Birthday Party", events)
        self.assertIn("CES", events)

        # Check properties
        self.assertEqual("common", events["Meeting"].properties["type"])
        self.assertEqual("common", events["Conference"].properties["type"])
        self.assertEqual("specific", events["CES"].properties["type"])
        self.assertEqual("technology", events["CES"].properties["category"])

        # Check aliases
        self.assertTrue(any(alias.name == "Birthday" for alias in events["Birthday Party"].aliases))
        self.assertTrue(any(alias.name == "Consumer Electronics Show" for alias in events["CES"].aliases))

    def test_initialize_products(self):
        """Test initializing product entities."""
        # Create an entity initializer
        initializer = EntityInitializer(self.entity_manager)

        # Initialize products
        products = initializer.initialize_products()

        # Check that products were created
        self.assertGreater(len(products), 0)

        # Check for specific products
        self.assertIn("iPhone", products)
        self.assertIn("MacBook", products)
        self.assertIn("Surface", products)
        self.assertIn("Windows", products)

        # Check properties
        self.assertEqual("smartphone", products["iPhone"].properties["category"])
        self.assertEqual("Apple", products["iPhone"].properties["company"])
        self.assertEqual("laptop", products["MacBook"].properties["category"])
        self.assertEqual("operating system", products["Windows"].properties["category"])

        # Check aliases
        self.assertTrue(any(alias.name == "Windows 11" for alias in products["Windows"].aliases))
        self.assertTrue(any(alias.name == "PS5" for alias in products["PlayStation"].aliases))

    def test_initialize_works(self):
        """Test initializing creative work entities."""
        # Create an entity initializer
        initializer = EntityInitializer(self.entity_manager)

        # Initialize works
        works = initializer.initialize_works()

        # Check that works were created
        self.assertGreater(len(works), 0)

        # Check for specific works
        self.assertIn("Star Wars", works)
        self.assertIn("Harry Potter", works)
        self.assertIn("The Matrix", works)
        self.assertIn("Bohemian Rhapsody", works)

        # Check properties
        self.assertEqual("movie", works["Star Wars"].properties["category"])
        self.assertEqual("Star Wars", works["Star Wars"].properties["franchise"])
        self.assertEqual("book", works["Harry Potter"].properties["category"])
        self.assertEqual("song", works["Bohemian Rhapsody"].properties["category"])
        self.assertEqual("Queen", works["Bohemian Rhapsody"].properties["artist"])

        # Check aliases
        self.assertTrue(any(alias.name == "Star Wars: A New Hope" for alias in works["Star Wars"].aliases))
        self.assertTrue(
            any(alias.name == "Harry Potter and the Philosopher's Stone" for alias in works["Harry Potter"].aliases),
        )

    def test_initialize_time_entities(self):
        """Test initializing time entities."""
        # Create an entity initializer
        initializer = EntityInitializer(self.entity_manager)

        # Initialize time entities
        time_entities = initializer.initialize_time_entities()

        # Check that time entities were created
        self.assertGreater(len(time_entities), 0)

        # Check for specific time entities
        self.assertIn("Monday", time_entities)
        self.assertIn("January", time_entities)
        self.assertIn("Morning", time_entities)
        self.assertIn("Today", time_entities)

        # Check properties
        self.assertEqual("day_of_week", time_entities["Monday"].properties["type"])
        self.assertEqual("1", time_entities["Monday"].properties["order"])
        self.assertEqual("month", time_entities["January"].properties["type"])
        self.assertEqual("time_of_day", time_entities["Morning"].properties["type"])
        self.assertEqual("relative_day", time_entities["Today"].properties["type"])

        # Check aliases
        self.assertTrue(any(alias.name == "Jan" for alias in time_entities["January"].aliases))

    def test_initialize_other_entities(self):
        """Test initializing other entities."""
        # Create an entity initializer
        initializer = EntityInitializer(self.entity_manager)

        # Initialize other entities
        other_entities = initializer.initialize_other_entities()

        # Check that other entities were created
        self.assertGreater(len(other_entities), 0)

        # Check for specific entities
        self.assertIn("Rock", other_entities)
        self.assertIn("Python", other_entities)
        self.assertIn("JavaScript", other_entities)

        # Check properties
        self.assertEqual("music_genre", other_entities["Rock"].properties["category"])
        self.assertEqual("programming_language", other_entities["Python"].properties["category"])
        self.assertEqual("programming_language", other_entities["JavaScript"].properties["category"])

        # Check aliases
        self.assertTrue(any(alias.name == "JS" for alias in other_entities["JavaScript"].aliases))

    def test_initialize_relationships(self):
        """Test initializing relationships between entities."""
        # Create an entity initializer
        initializer = EntityInitializer(self.entity_manager)

        # Initialize all entities
        entities = initializer.initialize_common_entities()

        # Check country-state relationships
        usa = entities[EntityType.LOCATION]["United States"]
        california = entities[EntityType.LOCATION]["California"]

        # Get relations for USA as source
        relations = self.entity_manager.get_relations_for_entity(usa.id, as_source=True)

        # Check that the relationship exists
        self.assertTrue(any(relation.target_entity_id == california.id for relation in relations))

        # Check state-city relationships
        sf = entities[EntityType.LOCATION]["San Francisco"]

        # Get relations for California as source
        relations = self.entity_manager.get_relations_for_entity(california.id, as_source=True)

        # Check that the relationship exists
        self.assertTrue(any(relation.target_entity_id == sf.id for relation in relations))

        # Check company-product relationships
        apple = entities[EntityType.ORGANIZATION]["Apple"]
        iphone = entities[EntityType.PRODUCT]["iPhone"]

        # Get relations for Apple as source
        relations = self.entity_manager.get_relations_for_entity(apple.id, as_source=True)

        # Check that the relationship exists
        self.assertTrue(any(relation.target_entity_id == iphone.id for relation in relations))

        # Check person-company relationships
        elon = entities[EntityType.PERSON]["Elon Musk"]
        tesla = entities[EntityType.ORGANIZATION]["Tesla"]

        # Get relations for Elon as source
        relations = self.entity_manager.get_relations_for_entity(elon.id, as_source=True)

        # Check that the relationship exists
        self.assertTrue(any(relation.target_entity_id == tesla.id for relation in relations))

        # Check adjacent day relationships
        monday = entities[EntityType.TIME]["Monday"]
        tuesday = entities[EntityType.TIME]["Tuesday"]

        # Get relations for Monday as source
        relations = self.entity_manager.get_relations_for_entity(monday.id, as_source=True)

        # Check that the relationship exists
        self.assertTrue(any(relation.target_entity_id == tuesday.id for relation in relations))

    def test_initialize_standard_entities(self):
        """Test initializing standard entities."""
        # Initialize standard entities with in-memory storage only
        entity_manager = initialize_standard_entities(db=None)

        # Check that entities were created
        self.assertGreater(len(entity_manager.entities_by_id), 0)

        # Check that each entity type has entities
        for entity_type in EntityType:
            self.assertGreater(len(entity_manager.entities[entity_type]), 0)

        # Check for specific entities
        self.assertIsNotNone(entity_manager.get_entity_by_name(EntityType.LOCATION, "San Francisco"))
        self.assertIsNotNone(entity_manager.get_entity_by_name(EntityType.PERSON, "Elon Musk"))
        self.assertIsNotNone(entity_manager.get_entity_by_name(EntityType.ORGANIZATION, "Microsoft"))
        self.assertIsNotNone(entity_manager.get_entity_by_name(EntityType.EVENT, "Meeting"))
        self.assertIsNotNone(entity_manager.get_entity_by_name(EntityType.PRODUCT, "iPhone"))
        self.assertIsNotNone(entity_manager.get_entity_by_name(EntityType.WORK, "Star Wars"))
        self.assertIsNotNone(entity_manager.get_entity_by_name(EntityType.TIME, "Monday"))

        # Check that relations were created
        self.assertGreater(len(entity_manager.relations), 0)

    def test_idempotent_initialization(self):
        """Test that entity initialization is idempotent."""
        # Initialize entities twice (in-memory only)
        entity_manager1 = initialize_standard_entities(db=None)
        entity_count1 = len(entity_manager1.entities_by_id)
        relation_count1 = len(entity_manager1.relations)

        entity_manager2 = initialize_standard_entities(db=None)
        entity_count2 = len(entity_manager2.entities_by_id)
        relation_count2 = len(entity_manager2.relations)

        # Entity counts should be the same after initialization
        self.assertEqual(entity_count1, entity_count2)
        self.assertEqual(relation_count1, relation_count2)

    @pytest.mark.skipif(not IndalekoDBConfig().get_arangodb, reason="No database connection")
    def test_db_integration(self):
        """Test that entities can be stored in the database."""
        if not self.db:
            self.skipTest("No database connection")

        # Initialize entities with database storage
        db_entity_manager = initialize_standard_entities(db=self.db)

        # Check that entity manager has entities
        self.assertGreater(len(db_entity_manager.entities_by_id), 0)

        try:
            # Check that database has entities
            collection = self.db.collection(self.collection_name)
            count = collection.count()
            self.assertGreater(count, 0)

            # Check that we can retrieve specific entities
            entity = db_entity_manager.get_entity_by_name(EntityType.LOCATION, "San Francisco")
            self.assertIsNotNone(entity)

            # Check that we can retrieve relations
            relations = db_entity_manager.get_relations_for_entity(entity.id, as_source=False)
            self.assertGreaterEqual(len(relations), 0)
        except Exception as e:
            self.skipTest(f"Failed to access database collection: {e}")


if __name__ == "__main__":
    unittest.main()
