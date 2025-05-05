"""
Unit tests for the SemanticAttributeRegistry class.

These tests validate the functionality of the SemanticAttributeRegistry
used in the data generator tools.
"""

import os
import sys
import unittest
import uuid

# Setup path for imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from tools.data_generator_enhanced.agents.data_gen.core.semantic_attributes import SemanticAttributeRegistry
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel


class TestSemanticAttributeRegistry(unittest.TestCase):
    """Tests for SemanticAttributeRegistry class."""

    def test_register_attribute(self):
        """Test registering a new attribute."""
        # Register a new attribute
        attr_id = SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_STORAGE, "TEST_ATTRIBUTE"
        )
        
        # Verify it's a valid UUID
        try:
            uuid_obj = uuid.UUID(attr_id)
            self.assertIsInstance(uuid_obj, uuid.UUID)
        except ValueError:
            self.fail("register_attribute did not return a valid UUID")
            
        # Register with explicit UUID
        explicit_uuid = str(uuid.uuid4())
        attr_id2 = SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_STORAGE, "TEST_ATTRIBUTE2", explicit_uuid
        )
        self.assertEqual(attr_id2, explicit_uuid)
        
    def test_get_attribute_id(self):
        """Test getting an attribute ID."""
        # Register a test attribute
        test_uuid = str(uuid.uuid4())
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_STORAGE, "GET_TEST", test_uuid
        )
        
        # Get the attribute ID
        retrieved_id = SemanticAttributeRegistry.get_attribute_id(
            SemanticAttributeRegistry.DOMAIN_STORAGE, "GET_TEST"
        )
        self.assertEqual(retrieved_id, test_uuid)
        
        # Test auto-creation for unknown attribute
        new_id = SemanticAttributeRegistry.get_attribute_id(
            SemanticAttributeRegistry.DOMAIN_STORAGE, "UNKNOWN_ATTRIBUTE"
        )
        self.assertIsNotNone(new_id)
        try:
            uuid_obj = uuid.UUID(new_id)
            self.assertIsInstance(uuid_obj, uuid.UUID)
        except ValueError:
            self.fail("get_attribute_id did not return a valid UUID")
            
    def test_get_attribute_name(self):
        """Test getting an attribute name."""
        # Register a test attribute
        test_uuid = str(uuid.uuid4())
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_STORAGE, "NAME_TEST", test_uuid
        )
        
        # Get the attribute name
        attr_name = SemanticAttributeRegistry.get_attribute_name(test_uuid)
        self.assertEqual(attr_name, "DATA_GENERATOR_STORAGE_NAME_TEST")
        
        # Test unknown UUID
        unknown_name = SemanticAttributeRegistry.get_attribute_name(str(uuid.uuid4()))
        self.assertIsNone(unknown_name)
        
    def test_create_attribute(self):
        """Test creating a semantic attribute model."""
        # Create a semantic attribute
        attr = SemanticAttributeRegistry.create_attribute(
            SemanticAttributeRegistry.DOMAIN_STORAGE, "CREATE_TEST", "test_value"
        )
        
        # Verify it's the right type
        self.assertIsInstance(attr, IndalekoSemanticAttributeDataModel)
        
        # Verify it has the correct fields (Identifier/Value)
        self.assertIn("Identifier", attr.model_fields_set)
        self.assertIn("Value", attr.model_fields_set)
        
        # Verify the values
        self.assertIsNotNone(attr.Identifier)
        self.assertEqual(attr.Value, "test_value")
        
    def test_get_all_attributes(self):
        """Test getting all registered attributes."""
        # Get all attributes
        all_attrs = SemanticAttributeRegistry.get_all_attributes()
        
        # Verify it's a dictionary
        self.assertIsInstance(all_attrs, dict)
        
        # Verify domains exist
        self.assertIn(SemanticAttributeRegistry.DOMAIN_STORAGE, all_attrs)
        self.assertIn(SemanticAttributeRegistry.DOMAIN_ACTIVITY, all_attrs)
        
        # Verify each domain has attributes
        for domain, attrs in all_attrs.items():
            self.assertIsInstance(attrs, dict)
            self.assertGreater(len(attrs), 0)
            
    def test_get_all_mappings(self):
        """Test getting UUID to name mappings."""
        # Get all mappings
        all_mappings = SemanticAttributeRegistry.get_all_mappings()
        
        # Verify it's a dictionary
        self.assertIsInstance(all_mappings, dict)
        
        # Verify it has entries
        self.assertGreater(len(all_mappings), 0)
        
        # Verify keys are UUIDs and values are names
        for uuid_str, name in all_mappings.items():
            try:
                uuid_obj = uuid.UUID(uuid_str)
            except ValueError:
                self.fail(f"Invalid UUID in mappings: {uuid_str}")
                
            self.assertIsInstance(name, str)
            self.assertGreater(len(name), 0)


if __name__ == "__main__":
    unittest.main()