"""
Unit tests for the checksum generator tool.

These tests verify the basic functionality of the checksum generator without
requiring a database connection.
"""

import os
import sys
import uuid
import unittest
import datetime
from typing import Dict, List, Any

# Setup path for imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import the checksum generator
from tools.data_generator_enhanced.agents.data_gen.tools.checksum_generator import (
    ChecksumGenerator, ChecksumGeneratorTool
)


class TestChecksumGenerator(unittest.TestCase):
    """Test cases for the ChecksumGenerator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.generator = ChecksumGenerator(seed=42)
        self.test_files = [
            {
                "path": "/test/files/document1.docx",
                "name": "document1.docx",
                "size": 25000,
                "created": "2023-01-01T00:00:00Z",
                "modified": "2023-01-02T00:00:00Z"
            },
            {
                "path": "/test/files/image1.jpg",
                "name": "image1.jpg",
                "size": 500000,
                "created": "2023-01-01T00:00:00Z",
                "modified": "2023-01-02T00:00:00Z"
            },
            {
                "path": "/test/files/document2.docx",
                "name": "document2.docx",
                "size": 30000,
                "created": "2023-01-01T00:00:00Z",
                "modified": "2023-01-02T00:00:00Z"
            }
        ]
    
    def test_generate_random_hex(self):
        """Test generation of random hex strings."""
        hex_string = self.generator._generate_random_hex(32)
        self.assertEqual(len(hex_string), 32)
        self.assertTrue(all(c in "0123456789abcdef" for c in hex_string))
    
    def test_generate_random_checksums(self):
        """Test generation of random checksums."""
        checksums = self.generator._generate_random_checksums()
        
        # Check that all expected checksums are present
        self.assertIn("MD5", checksums)
        self.assertIn("SHA1", checksums)
        self.assertIn("SHA256", checksums)
        self.assertIn("SHA512", checksums)
        self.assertIn("Dropbox", checksums)
        
        # Check the length of each checksum
        self.assertEqual(len(checksums["MD5"]), 32)
        self.assertEqual(len(checksums["SHA1"]), 40)
        self.assertEqual(len(checksums["SHA256"]), 64)
        self.assertEqual(len(checksums["SHA512"]), 128)
        self.assertEqual(len(checksums["Dropbox"]), 64)
    
    def test_generate_deterministic_checksums(self):
        """Test generation of deterministic checksums based on file data."""
        checksums1 = self.generator._generate_deterministic_checksums(self.test_files[0])
        checksums2 = self.generator._generate_deterministic_checksums(self.test_files[0])
        checksums3 = self.generator._generate_deterministic_checksums(self.test_files[1])
        
        # Same file should produce same checksums
        self.assertEqual(checksums1, checksums2)
        
        # Different files should produce different checksums
        self.assertNotEqual(checksums1, checksums3)
    
    def test_generate_checksum(self):
        """Test generation of a single checksum."""
        result = self.generator.generate_checksum(self.test_files[0], allow_duplicates=False)
        
        # Check that the result has expected keys
        self.assertIn("checksums", result)
        self.assertIn("is_duplicate", result)
        
        # Check that checksums have expected format
        checksums = result["checksums"]
        self.assertEqual(len(checksums["MD5"]), 32)
        self.assertEqual(len(checksums["SHA1"]), 40)
        self.assertEqual(len(checksums["SHA256"]), 64)
        self.assertEqual(len(checksums["SHA512"]), 128)
    
    def test_generate_checksums_batch(self):
        """Test generation of checksums for multiple files."""
        results = self.generator.generate_checksums_batch(self.test_files)
        
        # Check that we got the right number of results
        self.assertEqual(len(results), len(self.test_files))
        
        # Check that each result has expected keys
        for result in results:
            self.assertIn("checksums", result)
            self.assertIn("is_duplicate", result)
    
    def test_duplicates(self):
        """Test generation of duplicate checksums."""
        # Force no random duplicates by setting probability to 0
        self.generator.duplicate_probability = 0.0
        
        # Set up duplicate groups
        duplicate_groups = [[0, 2]]  # Make file 0 and 2 duplicates
        
        results = self.generator.generate_checksums_batch(
            self.test_files, duplicate_groups=duplicate_groups
        )
        
        # Check that we got the right number of results
        self.assertEqual(len(results), len(self.test_files))
        
        # File 0 should not be marked as duplicate
        self.assertFalse(results[0]["is_duplicate"])
        
        # File 2 should be marked as duplicate
        self.assertTrue(results[2]["is_duplicate"])
        
        # Files 0 and 2 should have matching checksums for all checksum types
        for checksum_type in ["MD5", "SHA1", "SHA256", "SHA512", "Dropbox"]:
            self.assertEqual(
                results[0]["checksums"][checksum_type], 
                results[2]["checksums"][checksum_type]
            )
        
        # File 2 should reference file 0 as its duplicate source
        self.assertEqual(results[2].get("duplicate_of"), self.test_files[0]["path"])


class TestChecksumGeneratorTool(unittest.TestCase):
    """Test cases for the ChecksumGeneratorTool class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tool = ChecksumGeneratorTool()
        
        # Create test files with object IDs
        self.test_files = [
            {
                "path": "/test/files/document1.docx",
                "name": "document1.docx",
                "size": 25000,
                "created": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "modified": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "object_id": str(uuid.uuid4())
            },
            {
                "path": "/test/files/image1.jpg",
                "name": "image1.jpg",
                "size": 500000,
                "created": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "modified": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "object_id": str(uuid.uuid4())
            },
            {
                "path": "/test/files/document2.docx",
                "name": "document2.docx",
                "size": 30000,
                "created": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "modified": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "object_id": str(uuid.uuid4())
            }
        ]
    
    def test_execute(self):
        """Test execution of the tool."""
        # Run with default parameters
        result = self.tool.execute({"files": self.test_files})
        
        # Check that the result has expected keys
        self.assertIn("checksums", result)
        self.assertIn("stats", result)
        
        # Check that we got the right number of checksums
        self.assertEqual(len(result["checksums"]), len(self.test_files))
        
        # Check stats
        stats = result["stats"]
        self.assertEqual(stats["total"], len(self.test_files))
        self.assertGreaterEqual(stats["unique"], 0)
        self.assertGreaterEqual(stats["duplicates"], 0)
        self.assertEqual(stats["unique"] + stats["duplicates"], len(self.test_files))
    
    def test_duplicate_control(self):
        """Test controlling duplication rate."""
        # Set up duplicate groups and force no random duplicates
        duplicate_groups = [[0, 2]]  # Make file 0 and 2 duplicates
        
        result = self.tool.execute({
            "files": self.test_files,
            "duplicate_groups": duplicate_groups,
            "duplication_rate": 0.0  # Force no random duplicates
        })
        
        # Check duplicates exist (at least 1)
        self.assertGreater(result["stats"]["duplicates"], 0)
        
        # File 0 should not be a duplicate since it's the source
        self.assertFalse(result["checksums"][0]["is_duplicate"])
        
        # File 2 should be a duplicate
        self.assertTrue(result["checksums"][2]["is_duplicate"])
        
        # Checksums for files 0 and 2 should be identical for each checksum type
        for checksum_type in ["MD5", "SHA1", "SHA256", "SHA512", "Dropbox"]:
            self.assertEqual(
                result["checksums"][0]["checksums"][checksum_type],
                result["checksums"][2]["checksums"][checksum_type]
            )
    
    def test_semantic_attributes(self):
        """Test generation of semantic attributes."""
        result = self.tool.execute({"files": self.test_files})
        
        # Check that each checksum has semantic attributes
        for checksum in result["checksums"]:
            self.assertIn("SemanticAttributes", checksum)
            self.assertGreaterEqual(len(checksum["SemanticAttributes"]), 5)  # At least 5 attributes (one for each hash type)
            
            # Check the first attribute
            first_attr = checksum["SemanticAttributes"][0]
            self.assertIn("Identifier", first_attr)
            self.assertIn("Value", first_attr)
            
            # Identifier should have Identifier and Label
            self.assertIn("Identifier", first_attr["Identifier"])
            self.assertIn("Label", first_attr["Identifier"])
            
            # Value should be a string
            self.assertIsInstance(first_attr["Value"], str)


if __name__ == "__main__":
    unittest.main()