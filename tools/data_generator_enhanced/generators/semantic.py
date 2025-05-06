#!/usr/bin/env python3
"""
Semantic metadata generator.

This module provides implementation for generating realistic semantic
metadata records (MIME types, checksums, unstructured document elements, etc.) 
and storing them directly in the database.
"""

import hashlib
import json
import logging
import mimetypes
import os
import random
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from data_models.base import IndalekoBaseModel
from db.db_collections import IndalekoDBCollections
from db.db_config import IndalekoDBConfig
from pydantic import Field

from tools.data_generator_enhanced.generators.base import BaseGenerator, SemanticMetadataGenerator
from tools.data_generator_enhanced.utils.statistical import Distribution

# Initialize mimetypes database
mimetypes.init()


class SemanticRecord(IndalekoBaseModel):
    """Semantic record model for SemanticData collection."""
    
    # Required fields
    Object: str  # _key of the storage object
    MIMEType: str
    
    # Optional fields with defaults
    Keywords: List[str] = []
    ContentSummary: Optional[str] = None
    Size: Optional[int] = None
    CreateDate: Optional[float] = None
    ModifyDate: Optional[float] = None
    MD5: Optional[str] = None
    SHA1: Optional[str] = None
    SHA256: Optional[str] = None
    ContentLanguage: Optional[str] = None
    Sentiment: Optional[float] = None
    ContentType: Optional[str] = None
    Title: Optional[str] = None
    Author: Optional[str] = None
    Topics: List[str] = []


class SemanticMetadataGeneratorImpl(SemanticMetadataGenerator):
    """Generator for semantic metadata records with direct database integration."""
    
    def __init__(self, config: Dict[str, Any], db_config: Optional[IndalekoDBConfig] = None, seed: Optional[int] = None):
        """Initialize the semantic metadata generator.
        
        Args:
            config: Configuration dictionary for the generator
            db_config: Database configuration for direct insertion
            seed: Optional random seed for reproducible generation
        """
        super().__init__(config, seed)
        
        # Set random seed if provided
        if seed is not None:
            random.seed(seed)
        
        # Initialize database connection
        self.db_config = db_config or IndalekoDBConfig()
        self.db_config.setup_database(self.db_config.config["database"]["database"])
        
        # Make sure the semantic data collection exists
        if not self.db_config.db.has_collection(IndalekoDBCollections.Indaleko_SemanticData_Collection):
            self.logger.info(f"Creating SemanticData collection")
            self.db_config.db.create_collection(IndalekoDBCollections.Indaleko_SemanticData_Collection)
        
        # Get the collection
        self.semantic_collection = self.db_config.db.collection(IndalekoDBCollections.Indaleko_SemanticData_Collection)
        
        # Initialize MIME type map
        self.mime_type_map = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".ppt": "application/vnd.ms-powerpoint",
            ".txt": "text/plain",
            ".csv": "text/csv",
            ".html": "text/html",
            ".htm": "text/html",
            ".xml": "application/xml",
            ".json": "application/json",
            ".js": "application/javascript",
            ".css": "text/css",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".mp3": "audio/mpeg",
            ".mp4": "video/mp4",
            ".avi": "video/x-msvideo",
            ".mov": "video/quicktime",
            ".wav": "audio/wav",
            ".ogg": "audio/ogg",
            ".zip": "application/zip",
            ".tar": "application/x-tar",
            ".gz": "application/gzip",
            ".7z": "application/x-7z-compressed",
            ".py": "text/x-python",
            ".java": "text/x-java",
            ".c": "text/x-c",
            ".cpp": "text/x-c++",
            ".h": "text/x-c",
            ".hpp": "text/x-c++",
            ".md": "text/markdown",
            ".markdown": "text/markdown",
            ".rst": "text/x-rst",
            ".rtf": "application/rtf",
            ".odt": "application/vnd.oasis.opendocument.text",
            ".ods": "application/vnd.oasis.opendocument.spreadsheet",
            ".odp": "application/vnd.oasis.opendocument.presentation",
        }
        
        # Common content types for different file categories
        self.content_types = {
            "image": ["photograph", "diagram", "chart", "illustration", "screenshot", "icon", "logo", "infographic", "meme", "art"],
            "document": ["report", "memo", "letter", "essay", "manual", "proposal", "contract", "resume", "invoice", "form"],
            "spreadsheet": ["financial report", "budget", "inventory", "schedule", "data analysis", "metrics dashboard", "timesheet", "price list", "expense report", "forecast"],
            "presentation": ["sales pitch", "project update", "conference talk", "training module", "proposal", "quarterly review", "market analysis", "strategic plan", "product launch", "research findings"],
            "audio": ["podcast", "music track", "interview", "lecture", "audiobook", "voicenote", "sound effect", "radio show", "meditation", "ambient sound"],
            "video": ["tutorial", "presentation recording", "interview", "promotional video", "product demo", "webinar", "animation", "lecture recording", "meeting recording", "screencast"],
            "code": ["script", "application", "module", "function", "class implementation", "utility", "test suite", "configuration", "library", "algorithm"],
            "archive": ["backup", "collection", "installation package", "distribution", "data dump", "bundled resources", "compressed files", "source code", "document collection", "media package"],
        }
        
        # Potential authors for generated files
        self.authors = [
            "John Smith", "Emily Johnson", "Michael Williams", "Jessica Brown", 
            "Christopher Jones", "Lisa Garcia", "Matthew Davis", "Jennifer Miller", 
            "David Wilson", "Sarah Moore", "James Taylor", "Linda Anderson", 
            "Robert Thomas", "Elizabeth White", "Daniel Harris", "Barbara Martin", 
            "Joseph Thompson", "Mary Jackson", "Charles Clark", "Susan Lewis",
            "Samantha Lee", "Richard Wright", "Emma Turner", "Paul Scott",
            "Ashley Walker", "Andrew Green", "Olivia Baker", "Thomas Hall",
            "Sophia Young", "Kevin Allen", "Amanda King", "Ryan Wright",
            "Natalie Hill", "Joshua Adams", "Melissa Carter", "Brandon Parker"
        ]
        
        # Common topics for content
        self.topics = [
            "Business", "Marketing", "Finance", "Technology", "Programming", 
            "Data Analysis", "Project Management", "Human Resources", "Sales", 
            "Customer Service", "Product Development", "Research", "Innovation", 
            "Strategy", "Education", "Training", "Design", "Communication", 
            "Leadership", "Teamwork", "Sustainability", "Health", "Safety", 
            "Legal", "Compliance", "Operations", "Logistics", "Manufacturing", 
            "Quality Assurance", "Engineering", "Science", "Mathematics", 
            "Ethics", "Social Media", "Digital Marketing", "E-commerce", 
            "Artificial Intelligence", "Machine Learning", "Cloud Computing", 
            "Cybersecurity", "Data Privacy", "Blockchain", "Internet of Things", 
            "Mobile Development", "Web Development", "User Experience", 
            "User Interface", "Graphic Design", "Content Creation", "Branding", 
            "Public Relations", "Event Planning", "Risk Management", "Investment", 
            "Real Estate", "Insurance", "Accounting", "Taxation", "Auditing"
        ]
        
        # Common keywords for content
        self.keywords = [
            "analytics", "report", "quarterly", "annual", "summary", "overview", 
            "analysis", "data", "metrics", "statistics", "growth", "decline", 
            "performance", "evaluation", "assessment", "review", "forecast", 
            "projection", "prediction", "trend", "comparison", "benchmark", 
            "standard", "measurement", "indicator", "result", "outcome", "output", 
            "input", "process", "procedure", "protocol", "guideline", "policy", 
            "strategy", "tactic", "plan", "proposal", "recommendation", "suggestion", 
            "implementation", "execution", "operation", "management", "administration", 
            "coordination", "organization", "development", "improvement", "enhancement", 
            "optimization", "efficiency", "effectiveness", "productivity", "quality", 
            "quantity", "value", "cost", "price", "expense", "budget", "revenue", 
            "profit", "loss", "income", "investment", "return", "benefit", "risk", 
            "opportunity", "challenge", "problem", "solution", "resolution", "decision", 
            "approval", "authorization", "permission", "requirement", "specification", 
            "standard", "compliance", "regulation", "rule", "innovation", "creativity", 
            "idea", "concept", "design", "model", "template", "framework", "structure", 
            "system", "network", "platform", "application", "program", "software", 
            "hardware", "device", "equipment", "tool", "resource", "asset", "property", 
            "facility", "infrastructure", "architecture", "environment", "ecosystem", 
            "sustainable", "renewable", "reusable", "recyclable", "biodegradable", 
            "eco-friendly", "green", "clean", "natural", "organic", "healthy", "safe", 
            "secure", "protected", "private", "confidential", "classified", "restricted", 
            "limited", "exclusive", "inclusive", "comprehensive", "detailed", "thorough", 
            "complete", "partial", "segment", "section", "component", "element", "factor", 
            "variable", "parameter", "dimension", "perspective", "viewpoint", "opinion"
        ]
        
        # Truth generator tracks
        self.truth_list = []
    
    def generate(self, count: int) -> List[Dict[str, Any]]:
        """Generate the specified number of semantic metadata records.
        
        Args:
            count: Number of records to generate
            
        Returns:
            List of generated semantic metadata records
        """
        # First, we need to fetch storage records to generate semantic metadata for
        storage_records = self._fetch_storage_records(count)
        
        if not storage_records:
            self.logger.warning("No storage records found in database. Cannot generate semantic metadata.")
            return []
        
        # Generate semantic metadata for the storage records
        semantic_records = self._generate_semantic_metadata(storage_records)
        
        # Insert records into the database
        self._insert_records(semantic_records)
        
        return semantic_records
    
    def generate_for_storage(self, storage_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate semantic metadata for the given storage records.
        
        Args:
            storage_records: Storage metadata records
            
        Returns:
            List of generated semantic metadata records
        """
        # Generate semantic metadata for the storage records
        semantic_records = self._generate_semantic_metadata(storage_records)
        
        # Insert records into the database
        self._insert_records(semantic_records)
        
        return semantic_records
    
    def generate_truth(self, count: int, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate truth records that match specific criteria.
        
        Args:
            count: Number of truth records to generate
            criteria: Criteria that the truth records must satisfy
            
        Returns:
            List of generated truth records
        """
        # Get storage records that match the criteria
        storage_keys = criteria.get("storage_keys", [])
        
        if not storage_keys:
            # Fetch storage records that match criteria
            query_criteria = criteria.get("storage_criteria", {})
            storage_records = self._fetch_specific_storage_records(count, query_criteria)
            storage_keys = [r.get("_key") for r in storage_records]
        
        if not storage_keys:
            self.logger.warning("No matching storage records found. Cannot generate truth records.")
            return []
        
        # Generate semantic metadata with specific properties
        semantic_criteria = criteria.get("semantic_criteria", {})
        
        # Ensure we only generate as many as requested
        storage_keys = storage_keys[:count]
        
        # Generate metadata for each storage record
        truth_records = []
        
        for storage_key in storage_keys:
            record = self._generate_specific_semantic_metadata(storage_key, semantic_criteria)
            if record:
                truth_records.append(record)
                # Store the key for later evaluation
                self.truth_list.append(record.get("_key"))
        
        # Insert records into the database
        self._insert_records(truth_records)
        
        return truth_records
    
    def _fetch_storage_records(self, count: int) -> List[Dict[str, Any]]:
        """Fetch storage records from the database.
        
        Args:
            count: Maximum number of records to fetch
            
        Returns:
            List of storage records
        """
        # Query to get non-directory objects
        query = f"""
        FOR doc IN @@collection
        FILTER doc.IsDirectory == false || doc.IsDirectory == null
        SORT RAND()
        LIMIT {count}
        RETURN doc
        """
        
        # Prepare bind variables
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_Object_Collection
        }
        
        try:
            cursor = self.db_config.db.aql.execute(query, bind_vars=bind_vars)
            records = [doc for doc in cursor]
            self.logger.info(f"Fetched {len(records)} storage records from database")
            return records
        except Exception as e:
            self.logger.error(f"Error fetching storage records: {e}")
            # Fail fast - no point continuing if we can't get storage records
            raise
    
    def _fetch_specific_storage_records(self, count: int, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch storage records that match specific criteria.
        
        Args:
            count: Maximum number of records to fetch
            criteria: Criteria to filter records by
            
        Returns:
            List of storage records
        """
        # Build filter conditions based on criteria
        filter_conditions = []
        
        # Always exclude directories
        filter_conditions.append("doc.IsDirectory == false")
        
        # Add filters for file extensions
        if "file_extension" in criteria:
            extensions = criteria["file_extension"]
            if isinstance(extensions, str):
                extensions = [extensions]
            
            extension_conditions = []
            for ext in extensions:
                # Ensure extension starts with a dot
                if not ext.startswith("."):
                    ext = f".{ext}"
                extension_conditions.append(f'doc.Name LIKE "%{ext}"')
            
            if extension_conditions:
                filter_conditions.append(f"({' OR '.join(extension_conditions)})")
        
        # Add filters for file size
        if "min_size" in criteria:
            filter_conditions.append(f"doc.Size >= {criteria['min_size']}")
        if "max_size" in criteria:
            filter_conditions.append(f"doc.Size <= {criteria['max_size']}")
        
        # Add filters for time range
        if "time_range" in criteria:
            time_range = criteria["time_range"]
            if "start" in time_range:
                filter_conditions.append(f"doc.ModificationTime >= {time_range['start']}")
            if "end" in time_range:
                filter_conditions.append(f"doc.ModificationTime <= {time_range['end']}")
        
        # Add filters for name pattern
        if "name_pattern" in criteria:
            pattern = criteria["name_pattern"]
            if "%" in pattern:
                # Replace % with SQL-like wildcard for AQL
                pattern = pattern.replace("%", "%")
                filter_conditions.append(f'doc.Name LIKE "{pattern}"')
            else:
                filter_conditions.append(f'doc.Name == "{pattern}"')
        
        # Combine all filters
        filter_clause = " AND ".join(filter_conditions)
        
        # Build and execute query
        query = f"""
        FOR doc IN @@collection
        FILTER {filter_clause}
        SORT RAND()
        LIMIT {count}
        RETURN doc
        """
        
        # Prepare bind variables
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_Object_Collection
        }
        
        self.logger.debug(f"Storage query: {query}")
        
        try:
            cursor = self.db_config.db.aql.execute(query, bind_vars=bind_vars)
            records = [doc for doc in cursor]
            self.logger.info(f"Fetched {len(records)} specific storage records from database")
            return records
        except Exception as e:
            self.logger.error(f"Error fetching specific storage records: {e}")
            # Fail fast - no point continuing if we can't get storage records
            raise
    
    def _generate_semantic_metadata(self, storage_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate semantic metadata for storage records.
        
        Args:
            storage_records: List of storage records
            
        Returns:
            List of semantic metadata records
        """
        semantic_records = []
        
        for storage_record in storage_records:
            # Get the storage record key
            storage_key = storage_record.get("_key")
            
            if not storage_key:
                self.logger.warning(f"Storage record missing _key: {storage_record}")
                continue
            
            # Check if semantic metadata already exists for this object
            if self._semantic_exists(storage_key):
                self.logger.debug(f"Semantic metadata already exists for {storage_key}")
                continue
            
            # Generate semantic metadata
            semantic_record = self._generate_metadata_for_record(storage_record)
            if semantic_record:
                semantic_records.append(semantic_record)
        
        return semantic_records
    
    def _generate_specific_semantic_metadata(self, storage_key: str, criteria: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate semantic metadata for a specific storage record with custom criteria.
        
        Args:
            storage_key: Key of the storage record
            criteria: Custom criteria for the semantic metadata
            
        Returns:
            Generated semantic metadata record or None if generation failed
        """
        # Fetch the storage record
        try:
            storage_record = self.db_config.db.collection(IndalekoDBCollections.Indaleko_Object_Collection).get(storage_key)
            if not storage_record:
                self.logger.warning(f"Storage record {storage_key} not found")
                return None
        except Exception as e:
            self.logger.error(f"Error fetching storage record {storage_key}: {e}")
            return None
        
        # Start with a basic record
        semantic_record = self._generate_metadata_for_record(storage_record)
        if not semantic_record:
            return None
        
        # Override with custom criteria
        for key, value in criteria.items():
            if key in semantic_record:
                semantic_record[key] = value
        
        # Add specific topics and keywords if provided
        if "topics" in criteria:
            topics = criteria["topics"]
            if isinstance(topics, str):
                topics = [topics]
            semantic_record["Topics"] = topics
        
        if "keywords" in criteria:
            keywords = criteria["keywords"]
            if isinstance(keywords, str):
                keywords = [keywords]
            semantic_record["Keywords"] = keywords
        
        if "content_summary" in criteria:
            semantic_record["ContentSummary"] = criteria["content_summary"]
        
        if "content_type" in criteria:
            semantic_record["ContentType"] = criteria["content_type"]
        
        if "author" in criteria:
            semantic_record["Author"] = criteria["author"]
        
        return semantic_record
    
    def _semantic_exists(self, storage_key: str) -> bool:
        """Check if semantic metadata exists for a storage record.
        
        Args:
            storage_key: Key of the storage record
            
        Returns:
            True if semantic metadata exists, False otherwise
        """
        query = f"""
        FOR doc IN {IndalekoDBCollections.Indaleko_SemanticData_Collection}
        FILTER doc.Object == @storage_key
        LIMIT 1
        RETURN doc
        """
        
        try:
            cursor = self.db_config.db.aql.execute(query, bind_vars={"storage_key": storage_key})
            # Returns True if any record exists
            return any(cursor)
        except Exception as e:
            self.logger.error(f"Error checking if semantic metadata exists: {e}")
            # Assume it doesn't exist if we can't check
            return False
    
    def _generate_metadata_for_record(self, storage_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate semantic metadata for a specific storage record.
        
        Args:
            storage_record: Storage record to generate metadata for
            
        Returns:
            Generated semantic metadata record or None if generation failed
        """
        storage_key = storage_record.get("_key")
        
        if not storage_key:
            self.logger.warning(f"Storage record missing _key: {storage_record}")
            return None
        
        file_name = storage_record.get("Name", "")
        
        # Determine MIME type from file extension
        mime_type = self._determine_mime_type(file_name)
        
        # Calculate content category based on MIME type
        content_category = self._determine_content_category(mime_type)
        
        # Generate content type based on content category
        content_type = self._determine_content_type(content_category)
        
        # Generate file checksums (simulated)
        checksums = self._generate_checksums(storage_key, file_name)
        
        # Generate topics and keywords
        topics, keywords = self._generate_topics_and_keywords(content_category, file_name)
        
        # Generate content summary
        content_summary = self._generate_content_summary(file_name, content_type, topics)
        
        # Generate author (50% chance)
        author = random.choice(self.authors) if random.random() < 0.5 else None
        
        # Generate sentiment (for text files, 30% chance)
        sentiment = None
        if content_category in ["document", "spreadsheet", "presentation", "code"] and random.random() < 0.3:
            sentiment = random.uniform(-1.0, 1.0)
        
        # Create semantic record
        semantic_record = {
            "_key": str(uuid.uuid4()),
            "Object": storage_key,
            "MIMEType": mime_type,
            "ContentType": content_type,
            "ContentSummary": content_summary,
            "Keywords": keywords,
            "Topics": topics,
            "Size": storage_record.get("Size"),
            "CreateDate": storage_record.get("CreationTime"),
            "ModifyDate": storage_record.get("ModificationTime"),
            "MD5": checksums.get("md5"),
            "SHA1": checksums.get("sha1"),
            "SHA256": checksums.get("sha256"),
            "ContentLanguage": "en",  # Default to English
            "Sentiment": sentiment,
            "Title": self._generate_title(file_name, content_type),
            "Author": author
        }
        
        return semantic_record
    
    def _insert_records(self, records: List[Dict[str, Any]]) -> None:
        """Insert records into the semantic data collection.
        
        Args:
            records: Records to insert
        """
        if not records:
            self.logger.info("No records to insert")
            return
        
        # Use a transaction for atomicity
        try:
            self.logger.info(f"Inserting {len(records)} semantic records into database")
            
            # ArangoDB batch insert is more efficient for multiple records
            results = self.semantic_collection.insert_many(records)
            self.logger.info(f"Successfully inserted {len(results)} semantic records")
            
        except Exception as e:
            self.logger.error(f"Error inserting semantic records: {e}")
            # Fail fast - no point continuing if we can't insert records
            raise
    
    def _determine_mime_type(self, file_name: str) -> str:
        """Determine MIME type from file extension.
        
        Args:
            file_name: Name of the file
            
        Returns:
            MIME type for the file
        """
        # Get file extension
        _, ext = os.path.splitext(file_name)
        ext = ext.lower()
        
        # Look up in our map first
        if ext in self.mime_type_map:
            return self.mime_type_map[ext]
        
        # Fall back to mimetypes library
        mime_type, _ = mimetypes.guess_type(file_name)
        
        # Default if nothing else works
        if not mime_type:
            # Try to categorize based on extension patterns
            if ext in ['.db', '.sql', '.sqlite']:
                mime_type = 'application/x-sqlite3'
            elif ext in ['.log', '.cfg', '.ini', '.config']:
                mime_type = 'text/plain'
            else:
                mime_type = 'application/octet-stream'
        
        return mime_type
    
    def _determine_content_category(self, mime_type: str) -> str:
        """Determine content category from MIME type.
        
        Args:
            mime_type: MIME type of the file
            
        Returns:
            Content category
        """
        mime_type = mime_type.lower()
        
        if mime_type.startswith('image/'):
            return "image"
        elif mime_type.startswith('audio/'):
            return "audio"
        elif mime_type.startswith('video/'):
            return "video"
        elif mime_type in ['application/zip', 'application/x-tar', 'application/gzip', 'application/x-7z-compressed']:
            return "archive"
        elif mime_type.startswith('text/x-') or mime_type in ['application/javascript', 'application/json', 'application/xml']:
            return "code"
        elif mime_type in ['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.oasis.opendocument.spreadsheet', 'text/csv']:
            return "spreadsheet"
        elif mime_type in ['application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'application/vnd.oasis.opendocument.presentation']:
            return "presentation"
        elif mime_type in ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/rtf', 'application/vnd.oasis.opendocument.text', 'text/plain', 'text/markdown', 'text/html']:
            return "document"
        else:
            return "other"
    
    def _determine_content_type(self, content_category: str) -> str:
        """Determine specific content type based on category.
        
        Args:
            content_category: Category of the content
            
        Returns:
            Specific content type
        """
        if content_category in self.content_types:
            return random.choice(self.content_types[content_category])
        else:
            return "unknown"
    
    def _generate_checksums(self, storage_key: str, file_name: str) -> Dict[str, str]:
        """Generate simulated checksums for a file.
        
        Args:
            storage_key: Key of the storage record
            file_name: Name of the file
            
        Returns:
            Dictionary with MD5, SHA1, and SHA256 checksums
        """
        # Create a deterministic but unique string to hash
        data = f"{storage_key}:{file_name}:{random.randint(1, 10000000)}"
        
        # Generate checksums
        md5 = hashlib.md5(data.encode()).hexdigest()
        sha1 = hashlib.sha1(data.encode()).hexdigest()
        sha256 = hashlib.sha256(data.encode()).hexdigest()
        
        return {
            "md5": md5,
            "sha1": sha1,
            "sha256": sha256
        }
    
    def _generate_topics_and_keywords(self, content_category: str, file_name: str) -> Tuple[List[str], List[str]]:
        """Generate topics and keywords based on content category and file name.
        
        Args:
            content_category: Category of the content
            file_name: Name of the file
            
        Returns:
            Tuple of (topics, keywords)
        """
        # Number of topics (1-3)
        num_topics = random.randint(1, 3)
        
        # Number of keywords (3-8)
        num_keywords = random.randint(3, 8)
        
        # Select random topics and keywords
        topics = random.sample(self.topics, num_topics)
        keywords = random.sample(self.keywords, num_keywords)
        
        # Add words from the filename as keywords if they're meaningful
        file_base = os.path.splitext(file_name)[0]
        words = re.findall(r'[A-Za-z]+', file_base)
        for word in words:
            if len(word) > 3 and word.lower() not in [k.lower() for k in keywords]:
                if random.random() < 0.5:  # 50% chance to add each word
                    keywords.append(word.lower())
        
        return topics, keywords
    
    def _generate_content_summary(self, file_name: str, content_type: str, topics: List[str]) -> str:
        """Generate a content summary for the file.
        
        Args:
            file_name: Name of the file
            content_type: Type of content
            topics: List of topics
            
        Returns:
            Generated content summary
        """
        # Extract base name without extension
        base_name = os.path.splitext(file_name)[0]
        
        # Note: This is where we would use LLM in the future
        # For now, use a template-based approach
        templates = [
            f"A {content_type} about {', '.join(topics)}.",
            f"{base_name}: {content_type} related to {random.choice(topics)}.",
            f"Document containing information about {' and '.join(topics[:2])}.",
            f"{content_type.capitalize()} with details on {random.choice(topics)}.",
            f"This file contains a {content_type} discussing {', '.join(topics)}.",
            f"A {content_type} titled '{base_name}' covering {random.choice(topics)}.",
            f"Information related to {', '.join(topics)} in the form of a {content_type}.",
            f"{base_name} - a {content_type} created for {random.choice(topics)} purposes.",
        ]
        
        return random.choice(templates)
    
    def _generate_title(self, file_name: str, content_type: str) -> Optional[str]:
        """Generate a title based on the file name.
        
        Args:
            file_name: Name of the file
            content_type: Type of content
            
        Returns:
            Generated title or None
        """
        # 70% chance to have a title
        if random.random() > 0.7:
            return None
        
        # Extract base name without extension
        base_name = os.path.splitext(file_name)[0]
        
        # Convert CamelCase or snake_case to spaces
        title = re.sub(r'([a-z])([A-Z])', r'\1 \2', base_name)  # CamelCase to spaces
        title = title.replace('_', ' ').replace('-', ' ')  # Replace underscores and hyphens
        
        # Capitalize words
        title = ' '.join(word.capitalize() for word in title.split())
        
        # Sometimes add a prefix or suffix
        if random.random() < 0.3:
            prefixes = [
                f"{content_type.capitalize()}: ",
                "Report on ",
                "Analysis of ",
                "Overview of ",
                "Guide to ",
                "Summary of ",
                f"{random.choice(self.topics)} - "
            ]
            title = random.choice(prefixes) + title
        
        if random.random() < 0.2 and len(title) < 50:
            suffixes = [
                " Report",
                " Analysis",
                " Overview",
                " Guide",
                " Summary",
                f" {content_type.capitalize()}",
                f" ({random.choice(self.topics)})",
                " - Draft",
                " - Final",
                " - Rev 1"
            ]
            title = title + random.choice(suffixes)
        
        return title


def main():
    """Main function for testing the semantic metadata generator."""
    logging.basicConfig(level=logging.INFO)
    
    # Sample configuration
    config = {}
    
    # Create generator with direct database connection
    db_config = IndalekoDBConfig()
    db_config.setup_database(db_config.config["database"]["database"])
    
    generator = SemanticMetadataGeneratorImpl(config, db_config, seed=42)
    
    # Generate semantic metadata for existing storage records
    records = generator.generate(10)
    
    # Generate some truth records
    criteria = {
        "storage_criteria": {
            "file_extension": ".pdf"
        },
        "semantic_criteria": {
            "ContentType": "report",
            "topics": ["Finance", "Business"],
            "keywords": ["quarterly", "analysis", "metrics", "performance"]
        }
    }
    truth_records = generator.generate_truth(5, criteria)
    
    # Print records for inspection
    logging.info(f"Generated {len(records)} regular semantic records")
    logging.info(f"Generated {len(truth_records)} truth semantic records")
    
    # Print sample record
    if records:
        logging.info(f"Sample record: {records[0]}")
    
    # Print sample truth record
    if truth_records:
        logging.info(f"Sample truth record: {truth_records[0]}")
    
    # Print truth list
    logging.info(f"Truth list: {generator.truth_list}")


class UnstructuredEmbeddedRecord(IndalekoBaseModel):
    """Unstructured Embedded Data Model for document elements."""
    
    # Required fields
    ElementId: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for the element")
    FileUUID: uuid.UUID = Field(..., description="UUID of the related file")
    FileType: str = Field(..., description="MIME type of the file")
    LastModified: datetime = Field(..., description="Last modified time of the file")
    Languages: List[str] = Field(default_factory=list, description="Languages detected in the element")
    Text: str = Field(..., description="The text content of the element")
    Type: str = Field(..., description="Type of element (Title, Paragraph, etc.)")
    
    # Optional fields
    PageNumber: Optional[int] = Field(None, description="Page number where the element appears")
    EmphasizedTextContents: Optional[List[str]] = Field(None, description="Emphasized text contents")
    EmphasizedTextTags: Optional[List[str]] = Field(None, description="Tags for emphasized text")
    Raw: Optional[str] = Field(None, description="Raw data from unstructured.io")


class UnstructuredMetadataGeneratorImpl(SemanticMetadataGenerator):
    """Generator for unstructured document metadata with direct database integration."""
    
    # Semantic attribute UUIDs from semantic/collectors/semantic_attributes.py
    ELEMENT_TYPES = {
        "Title": "ad3bd698-bff6-4da9-b80e-e4901295d20c",
        "Text": "cd387e10-9c24-42a5-b89c-fc80e3333f25",
        "UncategorizedText": "985e1f7a-0169-41b9-b634-539266119247",
        "NarrativeText": "3a723e1f-9d16-46f3-a8f3-e57e5bb637f7",
        "BulletedText": "d11b77a7-97a2-4655-a721-fb19c6302313",
        "Paragraph": "3604baaf-be93-4505-b3c1-2e6f0b73a484",
        "Abstract": "dd29242a-c44f-440d-8148-53c8fe573398",
        "List": "1b040c78-c13c-4dfe-a63f-79378b2a7d36",
        "ListItem": "154a7459-1393-4baf-b520-4218f5973dce",
        "Table": "ace96486-c548-42a0-950f-fcc70f277abc",
        "Header": "dfb512a7-39c0-454c-8658-0d5ad9696727",
        "Headline": "3341c3f9-0865-47a6-9cc2-3142a6500c80",
        "SubHeadline": "fb786ade-0d25-44dd-bf33-12b09adc54d7",
        "CodeSnippet": "5629ff99-fe21-4e43-8a60-1b3be9dc9e69",
        "Footnote": "cc02e32a-2f11-4e47-8497-73112c83ecf1",
        "FormKeysValues": "915246b5-d36f-471b-9da2-57c604e6468d"
    }
    
    # File metadata attribute UUIDs
    FILE_ATTRIBUTES = {
        "filetype": "b4a5a775-bba8-4697-91bf-4acf99927221",
        "filename": "f286556b-15b5-4c7a-b9a4-2a1d566d0c14",
        "last_modified": "ed55af45-b5a2-43de-aa89-89526189388f",
        "page_number": "af847833-ff07-4eda-9753-bda0f5308bc4",
        "language": "af6eba9e-0993-4bab-a620-163d523e7850"
    }
    
    def __init__(self, config: Dict[str, Any], db_config: Optional[IndalekoDBConfig] = None, seed: Optional[int] = None):
        """Initialize the unstructured metadata generator.
        
        Args:
            config: Configuration dictionary for the generator
            db_config: Database configuration for direct insertion
            seed: Optional random seed for reproducible generation
        """
        super().__init__(config, seed)
        
        # Set random seed if provided
        if seed is not None:
            random.seed(seed)
        
        # Initialize database connection
        self.db_config = db_config or IndalekoDBConfig()
        self.db_config.setup_database(self.db_config.config["database"]["database"])
        
        # Make sure the semantic content collection exists
        collection_name = "SemanticContent"
        if not self.db_config.db.has_collection(collection_name):
            self.logger.info(f"Creating SemanticContent collection")
            self.db_config.db.create_collection(collection_name)
        
        # Get the collection
        self.semantic_collection = self.db_config.db.collection(collection_name)
        
        # Common languages to randomly select from
        self.languages = ["en", "es", "fr", "de", "it", "pt", "ru", "ja", "zh", "ar", "hi", "ko"]
        
        # Initialize common text resources
        self.topics = [
            "Business", "Technology", "Finance", "Marketing", 
            "Programming", "Data Analysis", "Project Management"
        ]
        
        # Common keywords for content
        self.keywords = [
            "analytics", "report", "quarterly", "annual", "summary", "overview", 
            "analysis", "data", "metrics", "statistics", "growth", "performance"
        ]
        
        # Potential authors for generated files
        self.authors = [
            "John Smith", "Emily Johnson", "Michael Williams", "Jessica Brown", 
            "Christopher Jones", "Lisa Garcia", "Matthew Davis", "Jennifer Miller"
        ]
        
        # Document element type distributions
        self.element_type_distribution = {
            "Title": 0.1,
            "Headline": 0.1,
            "Paragraph": 0.4,
            "NarrativeText": 0.15,
            "BulletedText": 0.1,
            "Table": 0.05,
            "ListItem": 0.05,
            "CodeSnippet": 0.03,
            "Footnote": 0.02
        }
        
        # For generating realistic document text
        self.lorem_ipsum = [
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "Nullam auctor sapien eget justo tincidunt, nec faucibus lorem fringilla.",
            "Praesent vitae erat at dolor iaculis volutpat vel sit amet nisi.",
            "Duis ut nunc vel justo pulvinar lacinia in vel risus.",
            "Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae.",
            "Nulla facilisi. Sed vel urna vel purus venenatis malesuada.",
            "Proin consectetur risus ut elit pulvinar, a facilisis felis volutpat.",
            "Fusce ac tellus vel velit efficitur ultrices ac at nisi.",
            "Aenean euismod dui nec purus lacinia, vel facilisis mi facilisis.",
            "Morbi iaculis metus eu nisi elementum, vitae commodo eros eleifend.",
            "Vivamus eget quam vitae risus fermentum iaculis.",
            "In hac habitasse platea dictumst. Nullam vel magna eu justo placerat dictum.",
            "Nunc vel purus nec nisi euismod lacinia.",
            "Suspendisse potenti. Donec eget diam vel ex pretium sagittis.",
            "Mauris cursus nisi eu est efficitur, at blandit orci tincidunt.",
            "Curabitur sodales lorem eget justo dapibus, et rhoncus arcu consequat.",
            "Integer consequat augue eget felis semper, in fermentum libero ultrices.",
            "Etiam eu lorem vel justo congue facilisis.",
            "Sed vehicula velit vel est molestie, vel vehicula enim scelerisque.",
            "Phasellus et magna vel lorem ultrices tempor.",
        ]
        
        # Code snippets for CodeSnippet elements
        self.code_snippets = [
            "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
            "function calculateTotal(items) {\n    return items.reduce((sum, item) => sum + item.price, 0);\n}",
            "public class HelloWorld {\n    public static void main(String[] args) {\n        System.out.println(\"Hello, World!\");\n    }\n}",
            "SELECT * FROM customers WHERE region = 'North' ORDER BY last_name ASC;",
            "from collections import defaultdict\n\nword_counts = defaultdict(int)\nfor word in text.split():\n    word_counts[word] += 1",
            "const apiUrl = 'https://api.example.com/data';\nfetch(apiUrl)\n    .then(response => response.json())\n    .then(data => console.log(data))\n    .catch(error => console.error('Error:', error));",
            "import numpy as np\nimport matplotlib.pyplot as plt\n\nx = np.linspace(0, 10, 100)\ny = np.sin(x)\nplt.plot(x, y)\nplt.show()",
            "#include <iostream>\nint main() {\n    std::cout << \"Hello, World!\" << std::endl;\n    return 0;\n}",
            "CREATE TABLE users (\n    id INT PRIMARY KEY,\n    username VARCHAR(50) NOT NULL,\n    email VARCHAR(100) UNIQUE,\n    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n);",
            "print(f\"The result is: {2 + 2}\")"
        ]
        
        # Text styles for EmphasizedTextTags
        self.emphasis_styles = ["bold", "italic", "underline", "strikethrough", "superscript", "subscript"]
        
        # Truth generator tracks
        self.truth_list = []
    
    def generate(self, count: int) -> List[Dict[str, Any]]:
        """Generate the specified number of unstructured metadata records.
        
        Args:
            count: Number of records to generate
            
        Returns:
            List of generated unstructured metadata records
        """
        # First, we need to fetch storage records to generate unstructured metadata for
        storage_records = self._fetch_document_storage_records(count)
        
        if not storage_records:
            self.logger.warning("No suitable document storage records found. Cannot generate unstructured metadata.")
            return []
        
        # Generate unstructured metadata for the storage records
        unstructured_records = self._generate_unstructured_metadata(storage_records)
        
        # Insert records into the database
        self._insert_records(unstructured_records)
        
        return unstructured_records
    
    def generate_for_storage(self, storage_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate unstructured metadata for the given storage records.
        
        Args:
            storage_records: Storage metadata records
            
        Returns:
            List of generated unstructured metadata records
        """
        # Filter for document types
        document_records = self._filter_document_types(storage_records)
        
        if not document_records:
            self.logger.warning("No suitable document storage records provided. Cannot generate unstructured metadata.")
            return []
        
        # Generate unstructured metadata for the storage records
        unstructured_records = self._generate_unstructured_metadata(document_records)
        
        # Insert records into the database
        self._insert_records(unstructured_records)
        
        return unstructured_records
    
    def generate_truth(self, count: int, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate truth records that match specific criteria.
        
        Args:
            count: Number of truth records to generate
            criteria: Criteria that the truth records must satisfy
            
        Returns:
            List of generated truth records
        """
        # Get storage records that match the criteria
        storage_keys = criteria.get("storage_keys", [])
        
        if not storage_keys:
            # Fetch storage records that match criteria
            query_criteria = criteria.get("storage_criteria", {})
            if "file_types" not in query_criteria:
                # Default to document types for unstructured data
                query_criteria["file_types"] = [".pdf", ".docx", ".doc", ".txt", ".html"]
                
            storage_records = self._fetch_specific_storage_records(count, query_criteria)
            storage_keys = [str(r.get("_key")) for r in storage_records]
        
        if not storage_keys:
            self.logger.warning("No matching storage records found. Cannot generate truth records.")
            return []
        
        # Generate unstructured metadata with specific properties
        unstructured_criteria = criteria.get("unstructured_criteria", {})
        
        # Ensure we only generate as many as requested
        storage_keys = storage_keys[:count]
        
        # Generate metadata for each storage record
        truth_records = []
        
        for storage_key in storage_keys:
            record_batch = self._generate_specific_unstructured_metadata(storage_key, unstructured_criteria)
            if record_batch:
                truth_records.extend(record_batch)
                # Store the keys for later evaluation
                for record in record_batch:
                    self.truth_list.append(record.get("_key"))
        
        # Insert records into the database
        self._insert_records(truth_records)
        
        return truth_records
    
    def _fetch_document_storage_records(self, count: int) -> List[Dict[str, Any]]:
        """Fetch document storage records from the database.
        
        Args:
            count: Maximum number of records to fetch
            
        Returns:
            List of document storage records
        """
        # Define document file extensions we want to target
        document_extensions = [
            ".pdf", ".docx", ".doc", ".txt", ".html", ".htm", ".rtf", 
            ".odt", ".md", ".pptx", ".ppt", ".odp", ".xlsx", ".xls", ".csv"
        ]
        
        # Build extension conditions
        extension_conditions = []
        for ext in document_extensions:
            extension_conditions.append(f'LIKE(doc.Label, "%{ext}", true)')
        
        extension_filter = f"({' OR '.join(extension_conditions)})"
        
        # Query to get objects with document extensions
        query = f"""
        FOR doc IN @@collection
        FILTER {extension_filter}
        SORT RAND()
        LIMIT {count}
        RETURN doc
        """
        
        # Prepare bind variables
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_Object_Collection
        }
        
        try:
            cursor = self.db_config.db.aql.execute(query, bind_vars=bind_vars)
            records = [doc for doc in cursor]
            self.logger.info(f"Fetched {len(records)} document storage records from database")
            return records
        except Exception as e:
            self.logger.error(f"Error fetching document storage records: {e}")
            # Fail fast - no point continuing if we can't get storage records
            raise
    
    def _filter_document_types(self, storage_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter storage records for document types.
        
        Args:
            storage_records: List of storage records to filter
            
        Returns:
            List of document storage records
        """
        document_extensions = [
            ".pdf", ".docx", ".doc", ".txt", ".html", ".htm", ".rtf", 
            ".odt", ".md", ".pptx", ".ppt", ".odp", ".xlsx", ".xls", ".csv"
        ]
        
        filtered_records = []
        
        for record in storage_records:
            # Use Label field instead of Name
            name = record.get("Label", "")
            if any(name.lower().endswith(ext) for ext in document_extensions):
                filtered_records.append(record)
        
        return filtered_records
    
    def _fetch_specific_storage_records(self, count: int, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch storage records that match specific criteria.
        
        Args:
            count: Maximum number of records to fetch
            criteria: Criteria to filter records by
            
        Returns:
            List of storage records
        """
        # Build filter conditions based on criteria
        filter_conditions = []
        
        # Always exclude directories
        filter_conditions.append("doc.IsDirectory == false")
        
        # Add filters for file types (extensions)
        if "file_types" in criteria:
            file_types = criteria["file_types"]
            if isinstance(file_types, str):
                file_types = [file_types]
            
            extension_conditions = []
            for ext in file_types:
                # Ensure extension starts with a dot
                if not ext.startswith("."):
                    ext = f".{ext}"
                extension_conditions.append(f'LIKE(doc.Label, "%{ext}", true)')
            
            if extension_conditions:
                filter_conditions.append(f"({' OR '.join(extension_conditions)})")
        
        # Add filters for file size
        if "min_size" in criteria:
            filter_conditions.append(f"doc.Size >= {criteria['min_size']}")
        if "max_size" in criteria:
            filter_conditions.append(f"doc.Size <= {criteria['max_size']}")
        
        # Add filters for time range
        if "time_range" in criteria:
            time_range = criteria["time_range"]
            if "start" in time_range:
                filter_conditions.append(f"doc.ModificationTime >= {time_range['start']}")
            if "end" in time_range:
                filter_conditions.append(f"doc.ModificationTime <= {time_range['end']}")
        
        # Add filters for name pattern
        if "name_pattern" in criteria:
            pattern = criteria["name_pattern"]
            filter_conditions.append(f'LIKE(doc.Label, "{pattern}", true)')
        
        # Combine all filters
        filter_clause = " AND ".join(filter_conditions)
        
        # Build and execute query
        query = f"""
        FOR doc IN @@collection
        FILTER {filter_clause}
        SORT RAND()
        LIMIT {count}
        RETURN doc
        """
        
        # Prepare bind variables
        bind_vars = {
            "@collection": IndalekoDBCollections.Indaleko_Object_Collection
        }
        
        self.logger.debug(f"Storage query: {query}")
        
        try:
            cursor = self.db_config.db.aql.execute(query, bind_vars=bind_vars)
            records = [doc for doc in cursor]
            self.logger.info(f"Fetched {len(records)} specific storage records from database")
            return records
        except Exception as e:
            self.logger.error(f"Error fetching specific storage records: {e}")
            # Fail fast - no point continuing if we can't get storage records
            raise
    
    def _generate_unstructured_metadata(self, storage_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate unstructured metadata for storage records.
        
        Args:
            storage_records: List of storage records
            
        Returns:
            List of unstructured metadata records
        """
        unstructured_records = []
        
        for storage_record in storage_records:
            # Get the storage record key
            storage_key = str(storage_record.get("_key"))
            
            if not storage_key:
                self.logger.warning(f"Storage record missing _key: {storage_record}")
                continue
            
            # Check if unstructured metadata already exists for this object
            if self._unstructured_exists(storage_key):
                self.logger.debug(f"Unstructured metadata already exists for {storage_key}")
                continue
            
            # Generate unstructured metadata elements
            try:
                elements = self._generate_elements_for_record(storage_record)
                if elements:
                    unstructured_records.extend(elements)
            except Exception as e:
                self.logger.error(f"Error generating elements for record {storage_key}: {e}")
                continue
        
        return unstructured_records
    
    def _generate_specific_unstructured_metadata(
        self, storage_key: str, criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate unstructured metadata for a specific storage record with custom criteria.
        
        Args:
            storage_key: Key of the storage record
            criteria: Custom criteria for the unstructured metadata
            
        Returns:
            List of generated unstructured metadata records
        """
        # Fetch the storage record
        try:
            query = """
            FOR doc IN @@collection
            FILTER doc._key == @key
            LIMIT 1
            RETURN doc
            """
            bind_vars = {
                "@collection": IndalekoDBCollections.Indaleko_Object_Collection,
                "key": storage_key
            }
            cursor = self.db_config.db.aql.execute(query, bind_vars=bind_vars)
            storage_records = [doc for doc in cursor]
            
            if not storage_records:
                self.logger.warning(f"Storage record {storage_key} not found")
                return []
            
            storage_record = storage_records[0]
        except Exception as e:
            self.logger.error(f"Error fetching storage record {storage_key}: {e}")
            return []
        
        # Create base elements for this record
        elements = []
        
        # Create elements based on required types
        if "required_types" in criteria:
            for element_type in criteria["required_types"]:
                # Get text based on criteria if specified
                element_text = self._generate_text_for_type(element_type)
                
                if "element_criteria" in criteria and element_type in criteria["element_criteria"]:
                    element_override = criteria["element_criteria"][element_type]
                    if "text" in element_override:
                        element_text = element_override["text"]
                
                # Add specified keywords to text if requested
                if "keywords" in criteria and len(element_text) > 20 and random.random() < 0.7:
                    keywords = criteria["keywords"]
                    if isinstance(keywords, str):
                        keywords = [keywords]
                    
                    # Insert a random keyword into the text
                    keyword = random.choice(keywords)
                    insert_pos = random.randint(20, len(element_text) - len(keyword))
                    element_text = element_text[:insert_pos] + " " + keyword + " " + element_text[insert_pos:]
                
                # Create the element
                new_element = self._create_element(
                    storage_key,
                    element_type,
                    element_text,
                    storage_record
                )
                elements.append(new_element)
        else:
            # Generate default elements if no specific types required
            title_element = self._create_element(
                storage_key,
                "Title",
                self._generate_title_text(),
                storage_record
            )
            elements.append(title_element)
            
            paragraph_element = self._create_element(
                storage_key,
                "Paragraph",
                self._generate_paragraph_text(),
                storage_record
            )
            elements.append(paragraph_element)
        
        return elements
    
    def _unstructured_exists(self, storage_key: str) -> bool:
        """Check if unstructured metadata exists for a storage record.
        
        Args:
            storage_key: Key of the storage record
            
        Returns:
            True if unstructured metadata exists, False otherwise
        """
        # For testing purposes, always return False to allow generation
        return False
        
        # In a real implementation we would use:
        # query = """
        # FOR doc IN SemanticContent
        # FILTER doc.FileUUID == @storage_key
        # LIMIT 1
        # RETURN doc
        # """
        # 
        # try:
        #     cursor = self.db_config.db.aql.execute(query, bind_vars={"storage_key": storage_key})
        #     # Returns True if any record exists
        #     return any(cursor)
        # except Exception as e:
        #     self.logger.error(f"Error checking if unstructured metadata exists: {e}")
        #     # Assume it doesn't exist if we can't check
        #     return False
    
    def _generate_elements_for_record(self, storage_record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate unstructured elements for a specific storage record.
        
        Args:
            storage_record: Storage record to generate elements for
            
        Returns:
            List of generated unstructured element records
        """
        storage_key = str(storage_record.get("_key"))
        
        if not storage_key:
            self.logger.warning(f"Storage record missing _key: {storage_record}")
            return []
        
        file_name = storage_record.get("Name", "")
        
        # Determine number of elements based on file size
        file_size = storage_record.get("Size", 0)
        num_elements = max(1, min(20, int(file_size / 5000)))
        
        # Generate document element types based on distributions
        element_types = self._select_element_types(num_elements)
        
        # Generate elements
        elements = []
        for i, element_type in enumerate(element_types):
            page_number = i // 4 + 1  # About 4 elements per page
            
            element = self._create_element(
                storage_key,
                element_type,
                self._generate_text_for_type(element_type),
                storage_record,
                page_number=page_number
            )
            
            elements.append(element)
        
        return elements
    
    def _select_element_types(self, count: int) -> List[str]:
        """Select element types based on distribution.
        
        Args:
            count: Number of elements to select
            
        Returns:
            List of selected element types
        """
        element_types = []
        
        # Always include title as the first element if we have more than 1 element
        if count > 1:
            element_types.append("Title")
            count -= 1
        
        # Select remaining elements based on distribution
        types = list(self.element_type_distribution.keys())
        weights = [self.element_type_distribution[t] for t in types]
        
        for _ in range(count):
            element_type = random.choices(types, weights=weights, k=1)[0]
            element_types.append(element_type)
        
        return element_types
    
    def _generate_text_for_type(self, element_type: str) -> str:
        """Generate text content based on element type.
        
        Args:
            element_type: Type of element
            
        Returns:
            Generated text content
        """
        if element_type == "Title":
            return self._generate_title_text()
        elif element_type == "Headline" or element_type == "SubHeadline":
            return self._generate_headline_text()
        elif element_type == "CodeSnippet":
            return random.choice(self.code_snippets)
        elif element_type == "BulletedText" or element_type == "ListItem":
            return self._generate_list_item_text()
        elif element_type == "Table":
            return self._generate_table_text()
        elif element_type == "Footnote":
            return self._generate_footnote_text()
        else:
            # Default to paragraph text
            return self._generate_paragraph_text()
    
    def _generate_title_text(self) -> str:
        """Generate title text.
        
        Returns:
            Generated title text
        """
        templates = [
            "Introduction to {topic}",
            "{topic} Overview",
            "Understanding {topic}",
            "The Complete Guide to {topic}",
            "{topic}: Principles and Practice",
            "{topic} Analysis",
            "Exploring {topic}",
            "{topic} in the Modern World",
            "Advanced {topic}",
            "{topic}: A Comprehensive Study"
        ]
        
        topic = random.choice(self.topics)
        return random.choice(templates).format(topic=topic)
    
    def _generate_headline_text(self) -> str:
        """Generate headline text.
        
        Returns:
            Generated headline text
        """
        templates = [
            "Chapter 1: {topic} Fundamentals",
            "Key Concepts in {topic}",
            "{topic} Methodology",
            "Understanding {topic} Components",
            "Evolution of {topic}",
            "{topic} Implementation",
            "Best Practices for {topic}",
            "{topic} Applications",
            "Recent Developments in {topic}",
            "The Future of {topic}"
        ]
        
        topic = random.choice(self.topics)
        return random.choice(templates).format(topic=topic)
    
    def _generate_paragraph_text(self) -> str:
        """Generate paragraph text.
        
        Returns:
            Generated paragraph text
        """
        # Select 2-5 sentences from lorem ipsum
        num_sentences = random.randint(2, 5)
        sentences = random.sample(self.lorem_ipsum, num_sentences)
        
        return " ".join(sentences)
    
    def _generate_list_item_text(self) -> str:
        """Generate list item text.
        
        Returns:
            Generated list item text
        """
        templates = [
            "Item {num}: {sentence}",
            "Point {num} - {sentence}",
            "{sentence}",
            "{keyword}: {sentence}",
            "{sentence} related to {keyword}"
        ]
        
        num = random.randint(1, 10)
        keyword = random.choice(self.keywords)
        sentence = random.choice(self.lorem_ipsum)
        
        return random.choice(templates).format(num=num, sentence=sentence, keyword=keyword)
    
    def _generate_table_text(self) -> str:
        """Generate table text representation.
        
        Returns:
            Generated table text
        """
        # Simple text representation of a table
        headers = ["ID", "Name", "Value", "Date"]
        
        rows = []
        for i in range(3):
            row = [
                str(i + 1),
                f"Item-{random.randint(100, 999)}",
                f"${random.randint(10, 1000)}.00",
                f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
            ]
            rows.append(" | ".join(row))
        
        table_text = " | ".join(headers) + "\n"
        table_text += "-" * len(table_text) + "\n"
        table_text += "\n".join(rows)
        
        return table_text
    
    def _generate_footnote_text(self) -> str:
        """Generate footnote text.
        
        Returns:
            Generated footnote text
        """
        templates = [
            "[1] Reference to {source}, {year}",
            "[2] {author}, \"{title}\", {source}, {year}",
            "[3] See {source} for more information",
            "[4] {author}, {year}",
            "[5] Data from {source}, accessed on {date}"
        ]
        
        author = random.choice(self.authors)
        year = random.randint(2000, 2023)
        source = random.choice(["Journal of Data Science", "ACM Transactions", "IEEE Proceedings", 
                                "Oxford University Press", "Cambridge University Press", "Springer",
                                "Nature", "Science", "Quarterly Review", "Technical Report"])
        date = f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
        title = self._generate_title_text()
        
        return random.choice(templates).format(
            author=author, year=year, source=source, date=date, title=title
        )
    
    def _create_element(
        self, 
        storage_key: str, 
        element_type: str, 
        text: str,
        storage_record: Dict[str, Any],
        page_number: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create an unstructured element.
        
        Args:
            storage_key: Key of the storage record
            element_type: Type of element
            text: Text content
            storage_record: Original storage record
            page_number: Optional page number
            
        Returns:
            Created unstructured element
        """
        # Get file metadata
        file_name = storage_record.get("Label", "Unknown")
        file_type = self._determine_mime_type(file_name)
        
        # Use storage record modification time if available, otherwise current time
        last_modified = datetime.now(timezone.utc)
        
        # Randomly select 1-2 languages
        num_languages = random.randint(1, 2)
        languages = random.sample(self.languages, num_languages)
        if "en" not in languages and random.random() < 0.7:
            languages[0] = "en"  # 70% chance primary language is English
        
        # Occasionally add emphasized text
        emphasized_text_contents = None
        emphasized_text_tags = None
        if random.random() < 0.2:  # 20% chance
            # Extract one or two phrases to emphasize
            words = text.split()
            if len(words) >= 5:
                start_idx = random.randint(0, len(words) - 3)
                phrase_len = random.randint(1, min(3, len(words) - start_idx))
                emphasized_phrase = " ".join(words[start_idx:start_idx + phrase_len])
                
                emphasized_text_contents = [emphasized_phrase]
                emphasized_text_tags = [random.choice(self.emphasis_styles)]
        
        # Create raw data that mimics unstructured.io output
        raw_data = {
            "element_id": str(uuid.uuid4()),
            "metadata": {
                "file_directory": "/test/documents",
                "filename": file_name,
                "filetype": file_type,
                "languages": languages,
                "last_modified": last_modified.isoformat(),
                "page_number": page_number or 1
            },
            "text": text,
            "type": element_type
        }
        
        # Create the element record
        element = {
            "_key": str(uuid.uuid4()),
            "ElementId": str(uuid.uuid4()),
            "FileUUID": storage_key,  # Use the key directly
            "FileType": file_type,
            "LastModified": last_modified.isoformat(),
            "PageNumber": page_number or 1,
            "Languages": languages,
            "Text": text,
            "Type": element_type,
            "EmphasizedTextContents": emphasized_text_contents,
            "EmphasizedTextTags": emphasized_text_tags,
            "Raw": json.dumps(raw_data)
        }
        
        return element
    
    def _determine_mime_type(self, file_name: str) -> str:
        """Determine MIME type from file extension.
        
        Args:
            file_name: Name of the file
            
        Returns:
            MIME type for the file
        """
        # Get file extension
        _, ext = os.path.splitext(file_name)
        ext = ext.lower()
        
        mime_type_map = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".ppt": "application/vnd.ms-powerpoint",
            ".txt": "text/plain",
            ".csv": "text/csv",
            ".html": "text/html",
            ".htm": "text/html",
            ".rtf": "application/rtf",
            ".odt": "application/vnd.oasis.opendocument.text",
            ".ods": "application/vnd.oasis.opendocument.spreadsheet",
            ".odp": "application/vnd.oasis.opendocument.presentation",
            ".md": "text/markdown"
        }
        
        # Look up in our map first
        if ext in mime_type_map:
            return mime_type_map[ext]
        
        # Fall back to mimetypes library
        mime_type, _ = mimetypes.guess_type(file_name)
        
        # Default if nothing else works
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        return mime_type
    
    def _insert_records(self, records: List[Dict[str, Any]]) -> None:
        """Insert records into the semantic content collection.
        
        Args:
            records: Records to insert
        """
        if not records:
            self.logger.info("No records to insert")
            return
        
        # Use a transaction for atomicity
        try:
            self.logger.info(f"Inserting {len(records)} unstructured records into database")
            
            # ArangoDB batch insert is more efficient for multiple records
            results = self.semantic_collection.insert_many(records)
            self.logger.info(f"Successfully inserted {len(results)} unstructured records")
            
        except Exception as e:
            self.logger.error(f"Error inserting unstructured records: {e}")
            # Fail fast - no point continuing if we can't insert records
            raise


def test_unstructured_generator():
    """Test function for the unstructured metadata generator."""
    logging.basicConfig(level=logging.INFO)
    
    # Sample configuration
    config = {}
    
    # Create generator with direct database connection
    db_config = IndalekoDBConfig()
    db_config.setup_database(db_config.config["database"]["database"])
    
    generator = UnstructuredMetadataGeneratorImpl(config, db_config, seed=42)
    
    # Generate unstructured metadata for existing storage records
    records = generator.generate(5)
    
    # Generate some truth records
    criteria = {
        "storage_criteria": {
            "file_types": [".pdf", ".docx"],
        },
        "unstructured_criteria": {
            "required_types": ["Title", "Paragraph", "Table"],
            "keywords": ["important", "critical", "confidential"],
            "element_criteria": {
                "Title": {
                    "text": "Confidential: Strategic Analysis Report",
                    "languages": ["en"]
                }
            }
        }
    }
    
    truth_records = generator.generate_truth(3, criteria)
    
    # Print records for inspection
    logging.info(f"Generated {len(records)} regular unstructured records")
    logging.info(f"Generated {len(truth_records)} truth unstructured records")
    
    # Print sample record
    if records:
        logging.info(f"Sample record: {records[0]}")
    
    # Print truth list
    logging.info(f"Truth list: {generator.truth_list}")


if __name__ == "__main__":
    main()
    # Uncomment to test the unstructured generator independently
    test_unstructured_generator()
