"""Unit tests for entity validation utilities."""

import unittest
from uuid import uuid4

from ...models.named_entity import (
    EntityAlias,
    EntityRelation,
    EntityRelationType,
    EntityType,
    NamedEntity,
)
from ...ner.validation import (
    validate_entity_alias,
    validate_entity_name,
    validate_entity_relation,
    validate_entity_type,
    validate_named_entity,
    validate_properties,
    validate_property_key,
    validate_property_value,
    validate_relation_type,
)
from ..test_utils import AblationTestCase


class TestEntityValidation(AblationTestCase):
    """Test cases for entity validation utilities."""

    def test_validate_entity_name(self):
        """Test validating an entity name."""
        # Test valid names
        self.assertIsNone(validate_entity_name("San Francisco"))
        self.assertIsNone(validate_entity_name("John Smith"))
        self.assertIsNone(validate_entity_name("Microsoft"))

        # Test invalid names
        self.assertIsNotNone(validate_entity_name(""))
        self.assertIsNotNone(validate_entity_name("   "))
        self.assertIsNotNone(validate_entity_name("a" * 101))

    def test_validate_entity_alias(self):
        """Test validating an entity alias."""
        # Test valid aliases
        self.assertIsNone(validate_entity_alias("SF"))
        self.assertIsNone(validate_entity_alias("NYC"))
        self.assertIsNone(validate_entity_alias("The Big Apple"))

        # Test invalid aliases
        self.assertIsNotNone(validate_entity_alias(""))
        self.assertIsNotNone(validate_entity_alias("   "))
        self.assertIsNotNone(validate_entity_alias("a" * 51))

    def test_validate_entity_type(self):
        """Test validating an entity type."""
        # Test valid entity types
        self.assertIsNone(validate_entity_type("location"))
        self.assertIsNone(validate_entity_type("person"))
        self.assertIsNone(validate_entity_type("organization"))

        # Test invalid entity types
        self.assertIsNotNone(validate_entity_type("invalid_type"))
        self.assertIsNotNone(validate_entity_type(""))
        self.assertIsNotNone(validate_entity_type("123"))

    def test_validate_relation_type(self):
        """Test validating a relation type."""
        # Test valid relation types
        self.assertIsNone(validate_relation_type("parent"))
        self.assertIsNone(validate_relation_type("part-of"))
        self.assertIsNone(validate_relation_type("related"))

        # Test invalid relation types
        self.assertIsNotNone(validate_relation_type("invalid_type"))
        self.assertIsNotNone(validate_relation_type(""))
        self.assertIsNotNone(validate_relation_type("123"))

    def test_validate_property_key(self):
        """Test validating a property key."""
        # Test valid property keys
        self.assertIsNone(validate_property_key("country"))
        self.assertIsNone(validate_property_key("state_name"))
        self.assertIsNone(validate_property_key("entity.type"))
        self.assertIsNone(validate_property_key("test-key"))

        # Test invalid property keys
        self.assertIsNotNone(validate_property_key(""))
        self.assertIsNotNone(validate_property_key("   "))
        self.assertIsNotNone(validate_property_key("a" * 51))
        self.assertIsNotNone(validate_property_key("invalid key"))
        self.assertIsNotNone(validate_property_key("invalid@key"))

    def test_validate_property_value(self):
        """Test validating a property value."""
        # Test valid property values
        self.assertIsNone(validate_property_value("USA"))
        self.assertIsNone(validate_property_value("California"))
        self.assertIsNone(validate_property_value(""))
        self.assertIsNone(validate_property_value("   "))
        self.assertIsNone(validate_property_value("a" * 1000))

        # Test invalid property values
        self.assertIsNotNone(validate_property_value("a" * 1001))
        self.assertIsNotNone(validate_property_value(123))
        self.assertIsNotNone(validate_property_value(True))
        self.assertIsNotNone(validate_property_value(None))

    def test_validate_properties(self):
        """Test validating a dictionary of properties."""
        # Test valid properties
        self.assertEqual(0, len(validate_properties({})))
        self.assertEqual(0, len(validate_properties({"country": "USA"})))
        self.assertEqual(0, len(validate_properties({"country": "USA", "state": "California"})))

        # Test invalid properties
        self.assertEqual(1, len(validate_properties({"": "USA"})))
        self.assertEqual(1, len(validate_properties({"country": 123})))
        self.assertEqual(2, len(validate_properties({"": "USA", "country": 123})))

    def test_validate_named_entity(self):
        """Test validating a named entity."""
        # Create a valid entity
        entity = NamedEntity(
            entity_type=EntityType.LOCATION,
            name="San Francisco",
            aliases=[EntityAlias(name="SF"), EntityAlias(name="Frisco")],
            properties={"country": "USA", "state": "California"},
        )

        # Validate the entity
        errors = validate_named_entity(entity)
        self.assertEqual(0, len(errors))

        # Create an invalid entity
        entity = NamedEntity(
            entity_type=EntityType.LOCATION,
            name="",
            aliases=[EntityAlias(name=""), EntityAlias(name="a" * 51)],
            properties={"": "USA", "country": "USA"},
        )

        # Validate the entity
        errors = validate_named_entity(entity)
        self.assertEqual(3, len(errors))

        # Validate using a dictionary
        entity_dict = {
            "entity_type": "location",
            "name": "San Francisco",
            "aliases": [{"name": "SF"}, {"name": "Frisco"}],
            "properties": {"country": "USA", "state": "California"},
        }

        errors = validate_named_entity(entity_dict)
        self.assertEqual(0, len(errors))

        # Validate an invalid dictionary
        entity_dict = {
            "entity_type": "invalid_type",
            "name": "",
            "aliases": [{"name": ""}, {"name": "a" * 51}],
            "properties": {"": "USA", "country": "USA"},
        }

        errors = validate_named_entity(entity_dict)
        self.assertGreater(len(errors), 0)

    def test_validate_entity_relation(self):
        """Test validating an entity relation."""
        # Create a valid relation
        relation = EntityRelation(
            source_entity_id=uuid4(),
            target_entity_id=uuid4(),
            relation_type=EntityRelationType.PARENT,
            properties={"type": "state-city"},
        )

        # Validate the relation
        errors = validate_entity_relation(relation)
        self.assertEqual(0, len(errors))

        # Create an invalid relation
        relation = EntityRelation(
            source_entity_id=uuid4(),
            target_entity_id=uuid4(),
            relation_type="invalid_type",  # type: ignore
            properties={"": "test", "invalid key": "test"},
        )

        # Validate the relation
        errors = validate_entity_relation(relation)
        self.assertEqual(3, len(errors))

        # Validate using a dictionary
        relation_dict = {
            "source_entity_id": str(uuid4()),
            "target_entity_id": str(uuid4()),
            "relation_type": "parent",
            "properties": {"type": "state-city"},
        }

        errors = validate_entity_relation(relation_dict)
        self.assertEqual(0, len(errors))

        # Validate an invalid dictionary
        relation_dict = {
            "source_entity_id": str(uuid4()),
            "target_entity_id": str(uuid4()),
            "relation_type": "invalid_type",
            "properties": {"": "test", "invalid key": "test"},
        }

        errors = validate_entity_relation(relation_dict)
        self.assertGreater(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
