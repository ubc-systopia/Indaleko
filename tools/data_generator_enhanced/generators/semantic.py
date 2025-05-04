#!/usr/bin/env python3
"""
Semantic metadata generator.

This module provides implementation for generating realistic semantic
metadata records (MIME types, checksums, etc.) and storing them directly
in the database.
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


if __name__ == "__main__":
    main()
