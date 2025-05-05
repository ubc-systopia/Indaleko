#!/usr/bin/env python3
"""
Test case for the UnstructuredMetadataGeneratorTool.

This module provides test cases to verify that the unstructured metadata
generator correctly creates and stores synthetic document elements.
"""

import os
import random
import sys
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
import unittest

# Add the project root to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from db.db_config import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections
from tools.data_generator_enhanced.generators.semantic import UnstructuredMetadataGeneratorImpl


class TestUnstructuredMetadataGenerator(unittest.TestCase):
    """Test cases for the UnstructuredMetadataGenerator implementation."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Set up a database connection for testing
        cls.db_config = IndalekoDBConfig()
        cls.db_config.setup_database(cls.db_config.config["database"]["database"])
        
        # Make sure necessary collections exist
        cls._ensure_collections_exist()
        
        # Create some storage records in the actual database
        cls.storage_keys = cls._create_storage_records()
        
        # Configure the generator
        config = {"seed": 42}
        cls.generator = UnstructuredMetadataGeneratorImpl(
            config=config, 
            db_config=cls.db_config,
            seed=42
        )
        
        # Ensure topics attribute is populated
        if not hasattr(cls.generator, 'topics'):
            cls.generator.topics = [
                "Business", "Technology", "Finance", "Marketing", 
                "Programming", "Data Analysis", "Project Management"
            ]
    
    @classmethod
    def tearDownClass(cls):
        """Tear down test environment."""
        # Clean up test data
        cls._cleanup_test_data()
    
    @classmethod
    def _ensure_collections_exist(cls):
        """Ensure that the necessary collections exist in the database."""
        # List of collections we need
        required_collections = [
            IndalekoDBCollections.Indaleko_Object_Collection,  # Objects
            "SemanticContent"  # For unstructured data
        ]
        
        for collection_name in required_collections:
            if not cls.db_config.db.has_collection(collection_name):
                print(f"Creating collection {collection_name}")
                cls.db_config.db.create_collection(collection_name)
    
    @classmethod
    def _create_storage_records(cls) -> List[str]:
        """Create storage records in the database for testing.
        
        Returns:
            List of storage record keys
        """
        # Sample document types
        test_files = [
            {"name": "test_document1.pdf", "size": 1024567},
            {"name": "test_document2.docx", "size": 2456789},
            {"name": "test_document3.txt", "size": 34567}
        ]
        
        # Get the Objects collection
        objects_collection = cls.db_config.db.collection(IndalekoDBCollections.Indaleko_Object_Collection)
        
        # Add standard fields to all documents and insert them
        storage_keys = []
        for file_info in test_files:
            # Create a unique key and object identifier
            key = str(uuid.uuid4())
            storage_keys.append(key)
            object_id = str(uuid.uuid4())
            
            # Create a minimal valid object record based on the schema requirements
            local_path = f"/test/documents/{file_info['name']}"
            record = {
                "_key": key,
                "LocalPath": local_path,
                "ObjectIdentifier": object_id,
                "Size": file_info['size'],
                "Label": file_info['name'],
                "URI": f"file://{local_path}#{key}"  # Ensure unique URI
            }
            
            # Try to insert the record
            try:
                objects_collection.insert(record)
                print(f"Created storage record with key {key}")
            except Exception as e:
                print(f"Warning: Could not insert storage record: {e}")
                # If it fails, try a more direct query approach
                try:
                    local_path = f"/test/documents/{file_info['name']}"
                    uri = f"file://{local_path}#{key}"
                    
                    insert_query = """
                    INSERT {
                        _key: @key,
                        LocalPath: @local_path,
                        ObjectIdentifier: @object_id,
                        Size: @size,
                        Label: @label,
                        URI: @uri
                    } IN @@collection
                    RETURN NEW
                    """
                    
                    bind_vars = {
                        "@collection": IndalekoDBCollections.Indaleko_Object_Collection,
                        "key": key,
                        "local_path": local_path,
                        "object_id": object_id,
                        "size": file_info['size'],
                        "label": file_info['name'],
                        "uri": uri
                    }
                    cls.db_config.db.aql.execute(insert_query, bind_vars=bind_vars)
                    print(f"Created storage record with key {key} using AQL")
                except Exception as e2:
                    print(f"Error: Could not insert storage record with AQL: {e2}")
        
        return storage_keys
    
    @classmethod
    def _cleanup_test_data(cls):
        """Remove test data from the database."""
        try:
            # Remove test objects
            objects_collection = cls.db_config.db.collection(IndalekoDBCollections.Indaleko_Object_Collection)
            for key in cls.storage_keys:
                try:
                    objects_collection.delete(key)
                except Exception:
                    pass
            
            # Remove semantic content for these objects
            semantic_collection = cls.db_config.db.collection("SemanticContent")
            for key in cls.storage_keys:
                # Find and remove all semantic records for this object
                query = """
                FOR doc IN SemanticContent
                FILTER doc.FileUUID == @key
                REMOVE doc IN SemanticContent
                """
                cls.db_config.db.aql.execute(query, bind_vars={"key": key})
        except Exception as e:
            print(f"Warning: Error cleaning up test data: {e}")
    
    def test_generate(self):
        """Test generating unstructured metadata using real database.
        This will fetch objects from the database and generate unstructured metadata for them.
        """
        # Generate some unstructured metadata
        records = self.generator.generate(5)
        
        # Check that we got some records
        self.assertTrue(len(records) > 0, "Should generate at least one record")
        
        # Check the structure of the records
        for record in records:
            self.assertIsInstance(record, dict)
            self.assertIn("ElementId", record)
            self.assertIn("FileUUID", record)
            self.assertIn("FileType", record)
            self.assertIn("LastModified", record)
            self.assertIn("Languages", record)
            self.assertIn("Text", record)
            self.assertIn("Type", record)
            
            # Check that Languages is a list
            self.assertIsInstance(record["Languages"], list)
            
            # Check that Type is one of the known types
            self.assertIn(record["Type"], self.generator.ELEMENT_TYPES)
        
        # Now check if the records were actually inserted into the database
        semantic_collection = self.db_config.db.collection("SemanticContent")
        query = """
        FOR doc IN SemanticContent
        FILTER doc.FileUUID IN @keys
        RETURN doc
        """
        cursor = self.db_config.db.aql.execute(query, bind_vars={"keys": self.storage_keys})
        db_records = [doc for doc in cursor]
        
        # Should have at least one record in the database
        self.assertTrue(len(db_records) > 0, "Should have inserted records into the database")
    
    def test_generate_for_storage(self):
        """Test generating unstructured metadata for specific storage objects.
        This fetches the test objects we created and generates metadata for them.
        """
        # Get the actual storage records from the database
        query = """
        FOR doc IN @@collection
        FILTER doc._key IN @keys
        RETURN doc
        """
        
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_Object_Collection,
            "keys": self.storage_keys
        }
        
        cursor = self.db_config.db.aql.execute(query, bind_vars=bind_vars)
        storage_records = [doc for doc in cursor]
        
        # Verify we got the storage records
        self.assertTrue(len(storage_records) > 0, "Should have found the test storage records")
        
        # Generate unstructured metadata for these records
        records = self.generator.generate_for_storage(storage_records)
        
        # Check that we got records
        self.assertTrue(len(records) > 0, "Should generate records for storage objects")
        
        # Check that the FileUUID matches one of our storage record keys
        for record in records:
            self.assertIn(record["FileUUID"], self.storage_keys)
        
        # Verify the records were inserted into the database
        semantic_collection = self.db_config.db.collection("SemanticContent")
        query = """
        FOR doc IN SemanticContent
        FILTER doc.FileUUID IN @keys
        RETURN doc
        """
        cursor = self.db_config.db.aql.execute(query, bind_vars={"keys": self.storage_keys})
        db_records = [doc for doc in cursor]
        
        # Should have at least one record in the database
        self.assertTrue(len(db_records) > 0, "Should have inserted records into the database")
    
    def test_generate_truth(self):
        """Test generating truth records with specific criteria.
        This creates a set of "truth" records with specific content for testing search functionality.
        """
        # Define criteria for truth records
        criteria = {
            "storage_keys": self.storage_keys,
            "unstructured_criteria": {
                "required_types": ["Title", "Paragraph"],
                "keywords": ["confidential", "important"],
                "element_criteria": {
                    "Title": {
                        "text": "Test Document: Important Content",
                        "languages": ["en"]
                    }
                }
            }
        }
        
        # Generate truth records
        records = self.generator.generate_truth(3, criteria)
        
        # Check that we got some records
        self.assertTrue(len(records) > 0, "Should generate at least one truth record")
        
        # Check that at least one title has the specified text
        title_found = False
        for record in records:
            if record["Type"] == "Title" and record["Text"] == "Test Document: Important Content":
                title_found = True
                break
        
        self.assertTrue(title_found, "At least one title should have the specified text")


if __name__ == "__main__":
    unittest.main()