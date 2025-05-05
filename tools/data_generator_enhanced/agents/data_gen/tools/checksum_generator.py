"""
Checksum generator tool for Indaleko.

This module provides a tool for generating file checksums including MD5, SHA1, SHA256, 
SHA512, and Dropbox checksums. It supports creating synthetic checksums for files
that don't exist, simulating duplicates, and integrating with ArangoDB.
"""

import os
import sys
import uuid
import random
import hashlib
import logging
from typing import Dict, List, Any, Optional, Union, Set
from datetime import datetime, timezone, timedelta

# Setup path for imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import tool interface
from tools.data_generator_enhanced.agents.data_gen.core.tools import Tool

# Import semantic attribute registry and data models
try:
    # Try to import real registry and data models
    from tools.data_generator_enhanced.agents.data_gen.core.semantic_attributes import SemanticAttributeRegistry
    from data_models.base import IndalekoBaseModel
    from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
    from data_models.i_uuid import IndalekoUUIDDataModel
    from semantic.collectors.checksum.data_model import SemanticChecksumDataModel
    from semantic.recorders.checksum.characteristics import (
        SEMANTIC_CHECKSUM_MD5,
        SEMANTIC_CHECKSUM_SHA1,
        SEMANTIC_CHECKSUM_SHA256,
        SEMANTIC_CHECKSUM_SHA512,
        SEMANTIC_CHECKSUM_DROPBOX_SHA2,
    )
    from db.db_collections import IndalekoDBCollections
    from db.db_config import IndalekoDBConfig
    HAS_DB = True
except ImportError:
    # Create mock classes for testing
    HAS_DB = False
    
    class SemanticAttributeRegistry:
        """Mock registry for semantic attributes."""
        
        # Common domains for attributes
        DOMAIN_STORAGE = "storage"
        DOMAIN_ACTIVITY = "activity"
        DOMAIN_SEMANTIC = "semantic"
        DOMAIN_RELATIONSHIP = "relationship"
        DOMAIN_MACHINE = "machine"
        DOMAIN_ENTITY = "entity"
        DOMAIN_CHECKSUM = "checksum"
        
        @classmethod
        def get_attribute_id(cls, domain: str, name: str) -> str:
            """Get an attribute ID for a registered attribute."""
            return f"{domain}_{name}_id"
        
        @classmethod
        def get_attribute_name(cls, attribute_id: str) -> str:
            """Get the human-readable name for an attribute ID."""
            return attribute_id.replace("_id", "")
        
        @classmethod
        def register_attribute(cls, domain: str, name: str, attribute_id: Optional[str] = None) -> str:
            """Register an attribute."""
            return cls.get_attribute_id(domain, name)
    
    # Checksum semantic attributes (mock constants)
    SEMANTIC_CHECKSUM_MD5 = "de41cd6f-5468-4eba-8493-428c5791c23e"
    SEMANTIC_CHECKSUM_SHA1 = "e2c803f8-a362-4d9b-b026-757e3af9c3d8"
    SEMANTIC_CHECKSUM_SHA256 = "0e7123a1-b87b-4eb5-afb7-cebc38c8848d"
    SEMANTIC_CHECKSUM_SHA512 = "f9a1bd2a-1b94-4a7a-8a3d-fb9e8cadfb17"
    SEMANTIC_CHECKSUM_DROPBOX_SHA2 = "0349dc34-ec36-4d50-b861-9de5ffb20fbf"
    
    class IndalekoBaseModel:
        """Mock base model for testing."""
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        
        def model_dump(self):
            """Convert model to dictionary."""
            return self.__dict__
    
    class IndalekoSemanticAttributeDataModel(IndalekoBaseModel):
        """Mock semantic attribute data model for testing."""
        pass
    
    class IndalekoUUIDDataModel(IndalekoBaseModel):
        """Mock UUID data model for testing."""
        pass
    
    class SemanticChecksumDataModel(IndalekoBaseModel):
        """Mock checksum data model for testing."""
        checksum_data_id: uuid.UUID
        md5_checksum: str
        sha1_checksum: str
        sha256_checksum: str
        sha512_checksum: str
        dropbox_checksum: str
    
        def __init__(self, **kwargs):
            super().__init__(**kwargs)


class ChecksumGenerator:
    """Generator for synthetic file checksums."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize the generator.
        
        Args:
            seed: Random seed for reproducibility
        """
        self.random = random.Random(seed)
        
        # Existing checksums for duplication
        self.existing_checksums = {}
        self.duplicate_probability = 0.15  # 15% chance of generating a duplicate
        
        # Known file sizes for different types (in bytes)
        self.file_size_ranges = {
            "document": (1_000, 5_000_000),       # 1KB to 5MB
            "image": (50_000, 15_000_000),        # 50KB to 15MB
            "video": (1_000_000, 1_000_000_000),  # 1MB to 1GB
            "audio": (500_000, 50_000_000),       # 500KB to 50MB
            "executable": (100_000, 200_000_000), # 100KB to 200MB
            "archive": (1_000_000, 500_000_000),  # 1MB to 500MB
        }
    
    def _generate_random_hex(self, length: int) -> str:
        """Generate a random hex string of the specified length.
        
        Args:
            length: Length of the hex string
            
        Returns:
            Random hex string
        """
        return ''.join(self.random.choice('0123456789abcdef') for _ in range(length))
    
    def _generate_random_checksums(self) -> Dict[str, str]:
        """Generate random checksums for a file.
        
        Returns:
            Dictionary of checksums with algorithm as key
        """
        return {
            "MD5": self._generate_random_hex(32),
            "SHA1": self._generate_random_hex(40),
            "SHA256": self._generate_random_hex(64),
            "SHA512": self._generate_random_hex(128),
            "Dropbox": self._generate_random_hex(64)
        }
    
    def _generate_deterministic_checksums(self, file_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate deterministic checksums based on file data.
        
        Args:
            file_data: Dictionary containing file information
            
        Returns:
            Dictionary of checksums with algorithm as key
        """
        # Create a deterministic string from file data
        seed_string = (
            f"{file_data.get('path', '')}"
            f"{file_data.get('name', '')}"
            f"{file_data.get('size', 0)}"
            f"{file_data.get('created', '')}"
            f"{file_data.get('modified', '')}"
        )
        
        # Generate checksums based on this seed
        md5 = hashlib.md5(seed_string.encode()).hexdigest()
        sha1 = hashlib.sha1(seed_string.encode()).hexdigest()
        sha256 = hashlib.sha256(seed_string.encode()).hexdigest()
        sha512 = hashlib.sha512(seed_string.encode()).hexdigest()
        
        # For Dropbox checksum, use the SHA256 (normally it's more complex but this is synthetic)
        dropbox = sha256
        
        return {
            "MD5": md5,
            "SHA1": sha1,
            "SHA256": sha256,
            "SHA512": sha512,
            "Dropbox": dropbox
        }
    
    def generate_checksum(self, 
                          file_data: Dict[str, Any], 
                          allow_duplicates: bool = True) -> Dict[str, Any]:
        """Generate checksums for a file.
        
        Args:
            file_data: Dictionary containing file information
            allow_duplicates: Whether to allow duplicate checksums
            
        Returns:
            Dictionary containing checksums and metadata
        """
        # Check if we should create a duplicate
        create_duplicate = allow_duplicates and len(self.existing_checksums) > 0 and self.random.random() < self.duplicate_probability
        
        if create_duplicate:
            # Pick a random existing checksum set
            original_path = self.random.choice(list(self.existing_checksums.keys()))
            checksums = self.existing_checksums[original_path].copy()
            is_duplicate = True
            duplicate_of = original_path
        else:
            # Generate new checksums
            if file_data.get('size') is not None:
                # Use deterministic generation if we have file data
                checksums = self._generate_deterministic_checksums(file_data)
            else:
                # Generate random checksums if no file data
                checksums = self._generate_random_checksums()
            
            # Store for potential future duplicates
            file_path = file_data.get('path', f"file_{len(self.existing_checksums)}")
            self.existing_checksums[file_path] = checksums
            is_duplicate = False
            duplicate_of = None
        
        # Create the result
        result = {
            "checksums": checksums,
            "is_duplicate": is_duplicate
        }
        
        if duplicate_of:
            result["duplicate_of"] = duplicate_of
            
        return result
    
    def generate_checksums_batch(self, 
                                files: List[Dict[str, Any]], 
                                duplicate_groups: Optional[List[List[int]]] = None) -> List[Dict[str, Any]]:
        """Generate checksums for multiple files with controlled duplication.
        
        Args:
            files: List of file dictionaries
            duplicate_groups: Optional list of index groups to make duplicates
            
        Returns:
            List of checksum dictionaries
        """
        results = [None] * len(files)  # Pre-allocate results list
        processed_indices = set()
        
        # Process duplicate groups first
        if duplicate_groups:
            for group in duplicate_groups:
                if not group or len(group) < 2:
                    continue
                    
                # Process the first file in the group normally
                first_idx = group[0]
                if first_idx < len(files):
                    first_file = files[first_idx]
                    # Generate deterministic checksums for the first file
                    checksum_data = self._generate_deterministic_checksums(first_file)
                    
                    # Create result for first file (not a duplicate)
                    first_result = {
                        "checksums": checksum_data,
                        "is_duplicate": False
                    }
                    results[first_idx] = first_result
                    processed_indices.add(first_idx)
                    
                    # Store the checksums
                    file_path = first_file.get('path', f"file_{first_idx}")
                    self.existing_checksums[file_path] = checksum_data
                    
                    # Process the rest as duplicates
                    for dup_idx in group[1:]:
                        if dup_idx < len(files):
                            # Create duplicate result
                            dup_result = {
                                "checksums": checksum_data.copy(),
                                "is_duplicate": True,
                                "duplicate_of": file_path
                            }
                            results[dup_idx] = dup_result
                            processed_indices.add(dup_idx)
        
        # Process remaining files
        for idx, file_data in enumerate(files):
            if idx not in processed_indices:
                checksum_data = self.generate_checksum(file_data)
                results[idx] = checksum_data
        
        # Ensure no None values in the results
        for idx, result in enumerate(results):
            if result is None and idx < len(files):
                results[idx] = self.generate_checksum(files[idx])
                
        return results


class ChecksumGeneratorTool(Tool):
    """Tool to generate file checksums with duplication support."""
    
    def __init__(self):
        """Initialize the checksum generator tool."""
        super().__init__(name="checksum_generator", description="Generates file checksums with duplication detection support")
        
        # Create the checksum generator
        self.generator = ChecksumGenerator()
        
        # Set up logger
        self.logger = logging.getLogger(__name__)
        
        # Initialize database connection if available
        self.db_config = None
        self.db = None
        if HAS_DB:
            try:
                self.db_config = IndalekoDBConfig()
                self.db = self.db_config.db
                self.logger.info("Database connection initialized")
            except Exception as e:
                self.logger.error(f"Error initializing database connection: {e}")
        
        # Register checksum semantic attributes
        self._register_checksum_attributes()
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the checksum generator tool.
        
        Args:
            params: Parameters for execution
                files: List of file dictionaries
                duplicate_groups: Optional list of index groups to make duplicates
                duplication_rate: Optional probability of creating duplicates
                
        Returns:
            Dictionary with generated checksums
        """
        files = params.get("files", [])
        duplicate_groups = params.get("duplicate_groups", [])
        duplication_rate = params.get("duplication_rate")
        
        # Update duplication rate if specified
        if duplication_rate is not None:
            self.generator.duplicate_probability = max(0.0, min(1.0, duplication_rate))
        
        # Generate checksums
        checksum_results = self.generator.generate_checksums_batch(files, duplicate_groups)
        
        # Add semantic attributes to each result
        for i, result in enumerate(checksum_results):
            file_data = files[i] if i < len(files) else {}
            semantic_attributes = self._generate_semantic_attributes(result["checksums"])
            result["SemanticAttributes"] = semantic_attributes
            
            # Store in database if available
            if HAS_DB and self.db and file_data.get("object_id"):
                self._store_checksum_data(result, file_data.get("object_id"))
        
        # Compute stats
        duplicate_count = sum(1 for result in checksum_results if result.get("is_duplicate", False))
        unique_count = len(checksum_results) - duplicate_count
        
        return {
            "checksums": checksum_results,
            "stats": {
                "total": len(checksum_results),
                "unique": unique_count,
                "duplicates": duplicate_count,
                "duplication_rate": duplicate_count / max(1, len(checksum_results))
            }
        }
    
    def _register_checksum_attributes(self) -> None:
        """Register checksum semantic attributes."""
        # These are already registered in the real implementation
        # For mock implementation, we would register them here
        pass
    
    def _generate_semantic_attributes(self, checksums: Dict[str, str]) -> List[Dict[str, Any]]:
        """Generate semantic attributes for checksums.
        
        Args:
            checksums: Dictionary of checksums
            
        Returns:
            List of semantic attributes
        """
        semantic_attributes = []
        
        # MD5 attribute
        if "MD5" in checksums:
            md5_attr = {
                "Identifier": {
                    "Identifier": SEMANTIC_CHECKSUM_MD5,
                    "Label": "MD5 Checksum" 
                },
                "Value": checksums["MD5"]
            }
            semantic_attributes.append(md5_attr)
        
        # SHA1 attribute
        if "SHA1" in checksums:
            sha1_attr = {
                "Identifier": {
                    "Identifier": SEMANTIC_CHECKSUM_SHA1,
                    "Label": "SHA1 Checksum"
                },
                "Value": checksums["SHA1"]
            }
            semantic_attributes.append(sha1_attr)
        
        # SHA256 attribute
        if "SHA256" in checksums:
            sha256_attr = {
                "Identifier": {
                    "Identifier": SEMANTIC_CHECKSUM_SHA256,
                    "Label": "SHA256 Checksum"
                },
                "Value": checksums["SHA256"]
            }
            semantic_attributes.append(sha256_attr)
        
        # SHA512 attribute
        if "SHA512" in checksums:
            sha512_attr = {
                "Identifier": {
                    "Identifier": SEMANTIC_CHECKSUM_SHA512,
                    "Label": "SHA512 Checksum"
                },
                "Value": checksums["SHA512"]
            }
            semantic_attributes.append(sha512_attr)
        
        # Dropbox attribute
        if "Dropbox" in checksums:
            dropbox_attr = {
                "Identifier": {
                    "Identifier": SEMANTIC_CHECKSUM_DROPBOX_SHA2,
                    "Label": "Dropbox Checksum"
                },
                "Value": checksums["Dropbox"]
            }
            semantic_attributes.append(dropbox_attr)
        
        return semantic_attributes
    
    def _store_checksum_data(self, checksum_data: Dict[str, Any], object_id: str) -> bool:
        """Store checksum data in the database.
        
        Args:
            checksum_data: Checksum data to store
            object_id: Object ID to associate with the checksums
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db:
            return False
            
        try:
            # Define collection name for checksums
            collection_name = "FileChecksums"
            
            # Check if collection exists, create if not
            if not self.db.has_collection(collection_name):
                self.logger.info(f"Creating {collection_name} collection")
                self.db.create_collection(collection_name)
            
            # Get the collection
            collection = self.db.collection(collection_name)
            
            # Create a proper document
            checksums = checksum_data["checksums"]
            document = {
                "ObjectIdentifier": object_id,
                "Timestamp": datetime.now(timezone.utc).isoformat(),
                "MD5": checksums.get("MD5", ""),
                "SHA1": checksums.get("SHA1", ""),
                "SHA256": checksums.get("SHA256", ""),
                "SHA512": checksums.get("SHA512", ""),
                "Dropbox": checksums.get("Dropbox", ""),
                "is_duplicate": checksum_data.get("is_duplicate", False),
                "duplicate_of": checksum_data.get("duplicate_of", None),
                "SemanticAttributes": checksum_data.get("SemanticAttributes", [])
            }
            
            # Insert the document
            collection.insert(document)
            
            return True
        except Exception as e:
            self.logger.error(f"Error storing checksum data: {e}")
            return False


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Simple test
    tool = ChecksumGeneratorTool()
    
    # Create test files
    test_files = [
        {
            "path": "/files/document1.docx",
            "name": "document1.docx",
            "size": 25000,
            "created": datetime.now(timezone.utc).isoformat(),
            "modified": datetime.now(timezone.utc).isoformat(),
            "object_id": str(uuid.uuid4())
        },
        {
            "path": "/files/image1.jpg",
            "name": "image1.jpg",
            "size": 500000,
            "created": datetime.now(timezone.utc).isoformat(),
            "modified": datetime.now(timezone.utc).isoformat(),
            "object_id": str(uuid.uuid4())
        },
        {
            "path": "/files/document2.docx",
            "name": "document2.docx",
            "size": 30000,
            "created": datetime.now(timezone.utc).isoformat(),
            "modified": datetime.now(timezone.utc).isoformat(),
            "object_id": str(uuid.uuid4())
        }
    ]
    
    # Set up duplicate groups (make document1 and document2 duplicates)
    duplicate_groups = [[0, 2]]
    
    result = tool.execute({
        "files": test_files,
        "duplicate_groups": duplicate_groups
    })
    
    # Print results
    for i, checksum in enumerate(result["checksums"]):
        print(f"File {i+1}:")
        print(f"  MD5: {checksum['checksums']['MD5']}")
        print(f"  SHA1: {checksum['checksums']['SHA1']}")
        print(f"  SHA256: {checksum['checksums']['SHA256']}")
        print(f"  Is duplicate: {checksum.get('is_duplicate', False)}")
        if checksum.get('duplicate_of'):
            print(f"  Duplicate of: {checksum['duplicate_of']}")
        print()
    
    print(f"Stats: {result['stats']}")