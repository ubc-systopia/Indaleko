#!/usr/bin/env python3
"""
Synthetic metadata generator for ablation testing.

This module provides tools for generating synthetic metadata that targets
specific categories for use in ablation testing.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import os
import sys
import logging
import random
import json
import datetime
import uuid
from typing import Dict, List, Any, Optional, Set, Union, Tuple
from pathlib import Path

# Add the Indaleko root to the path
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import Indaleko modules
from db.db_collections import IndalekoDBCollections
from db.db_config import IndalekoDBConfig
from tools.data_generator_enhanced.testing.query_generator_enhanced import EnhancedQueryGenerator


class MetadataCategory:
    """Represents a metadata category for generation."""

    def __init__(
        self,
        name: str,
        fields: List[str],
        value_generators: Dict[str, callable],
        group: str = "ablation"
    ):
        """Initialize a metadata category.

        Args:
            name: Category name (e.g., "temporal", "activity")
            fields: List of fields in this category
            value_generators: Functions to generate values for each field
            group: Whether this is an ablation or control category
        """
        self.name = name
        self.fields = fields
        self.value_generators = value_generators
        self.group = group


class SyntheticMetadataGenerator:
    """Generator for synthetic metadata for ablation testing."""

    def __init__(self, seed: int = 42):
        """Initialize the metadata generator.

        Args:
            seed: Random seed for reproducible results
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.random = random.Random(seed)
        self.logger.info(f"Initialized with random seed {seed}")

        # Define metadata categories
        self._initialize_metadata_categories()

    def _initialize_metadata_categories(self):
        """Initialize metadata categories with generators."""
        # Define common generation parameters
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Define all metadata categories
        self.metadata_categories = {
            "temporal": MetadataCategory(
                name="temporal",
                group="ablation",
                fields=["created_at", "modified_at", "session_duration"],
                value_generators={
                    "created_at": lambda: (now - datetime.timedelta(
                        days=self.random.randint(1, 30)
                    )).isoformat(),
                    "modified_at": lambda: (now - datetime.timedelta(
                        days=self.random.randint(0, 7),
                        hours=self.random.randint(0, 23),
                        minutes=self.random.randint(0, 59)
                    )).isoformat(),
                    "session_duration": lambda: self.random.randint(30, 3600)  # 30s to 1h
                }
            ),
            "activity": MetadataCategory(
                name="activity",
                group="ablation",
                fields=["action", "collaborator"],
                value_generators={
                    "action": lambda: self.random.choice([
                        "created", "edited", "viewed", "shared", "commented",
                        "downloaded", "uploaded", "deleted", "printed", "renamed"
                    ]),
                    "collaborator": lambda: self.random.choice([
                        "John Smith", "Sarah Johnson", "Michael Lee", "Emma Davis",
                        "James Wilson", "Marketing Team", "Engineering Department",
                        "Project X Team", "Client ABC", "Executive Leadership",
                        None  # Sometimes there is no collaborator
                    ])
                }
            ),
            "spatial": MetadataCategory(
                name="spatial",
                group="control",
                fields=["geolocation", "device_location"],
                value_generators={
                    "geolocation": lambda: self.random.choice([
                        "Seattle, WA", "San Francisco, CA", "New York, NY", 
                        "Boston, MA", "Chicago, IL", "Austin, TX", "Denver, CO",
                        "Portland, OR", "Los Angeles, CA", "Miami, FL",
                        None  # Sometimes location data is not available
                    ]),
                    "device_location": lambda: self.random.choice([
                        "Home Office", "Work Desk", "Coffee Shop", "Conference Room",
                        "Client Site", "Coworking Space", "Remote Office",
                        "Living Room", "Airport Lounge", "Hotel Room",
                        None  # Sometimes device location is not known
                    ])
                }
            ),
            "content": MetadataCategory(
                name="content",
                group="control",
                fields=["file_type", "keywords", "tags"],
                value_generators={
                    "file_type": lambda: self.random.choice([
                        "PDF", "DOCX", "XLSX", "PPTX", "JPG", "PNG", "TXT",
                        "HTML", "CSS", "JS", "PY", "MD", "JSON", "CSV"
                    ]),
                    "keywords": lambda: self.random.sample([
                        "budget", "report", "quarterly", "annual", "project", 
                        "plan", "strategy", "proposal", "analysis", "research",
                        "meeting", "notes", "presentation", "summary", "draft",
                        "final", "review", "feedback", "update", "agenda"
                    ], k=self.random.randint(0, 5)),
                    "tags": lambda: self.random.sample([
                        "important", "urgent", "review", "approved", "draft",
                        "confidential", "public", "archived", "work", "personal",
                        "team", "client", "project", "reference", "completed"
                    ], k=self.random.randint(0, 3))
                }
            )
        }

    def generate_metadata(
        self,
        query_obj: Dict[str, Any],
        matching: bool = True,
        document_base: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate metadata for a document that either matches or doesn't match a query.

        Args:
            query_obj: Query object containing the query text and metadata
            matching: Whether the metadata should match the query
            document_base: Base document to extend with metadata (optional)

        Returns:
            Generated metadata document
        """
        # Create a base document if none is provided
        if document_base is None:
            document_base = {
                "_id": f"Objects/{uuid.uuid4().hex}",
                "ObjectIdentifier": uuid.uuid4().hex,
                "Label": f"Document_{uuid.uuid4().hex[:8]}.pdf"
            }

        # Determine which categories are relevant for this query
        query_categories = query_obj.get("categories", [])
        
        # Generate metadata for all categories
        metadata = document_base.copy()
        
        # Add basic record structure
        if "Record" not in metadata:
            metadata["Record"] = {
                "Attributes": {}
            }
        
        if "Attributes" not in metadata["Record"]:
            metadata["Record"]["Attributes"] = {}
            
        # Add semantic attributes array if needed
        if "SemanticAttributes" not in metadata:
            metadata["SemanticAttributes"] = []
            
        # Add timestamps array if needed
        if "Timestamps" not in metadata:
            metadata["Timestamps"] = []
            
        # If matching, generate metadata that matches the query
        if matching:
            # Fill in metadata fields for all relevant categories
            for category_name in query_categories:
                if category_name in self.metadata_categories:
                    category = self.metadata_categories[category_name]
                    self._add_category_metadata(metadata, category, query_obj)
        else:
            # Generate metadata that explicitly doesn't match the query
            # Find categories not in the query
            non_matching_categories = [
                name for name in self.metadata_categories
                if name not in query_categories
            ]
            
            # If no non-matching categories, use a random one
            if not non_matching_categories:
                non_matching_categories = list(self.metadata_categories.keys())
                self.random.shuffle(non_matching_categories)
                non_matching_categories = non_matching_categories[:1]
                
            # Add metadata from non-matching categories
            for category_name in non_matching_categories:
                category = self.metadata_categories[category_name]
                self._add_category_metadata(metadata, category, query_obj)
                
            # Ensure data from query categories is NOT matching
            for category_name in query_categories:
                if category_name in self.metadata_categories:
                    category = self.metadata_categories[category_name]
                    self._add_non_matching_metadata(metadata, category, query_obj)
        
        return metadata
    
    def _add_category_metadata(
        self,
        metadata: Dict[str, Any],
        category: MetadataCategory,
        query_obj: Dict[str, Any]
    ) -> None:
        """Add metadata for a specific category to a document.

        Args:
            metadata: Document metadata to modify
            category: Metadata category to add
            query_obj: Query object for context
        """
        # Extract the query text and analyze it for specific values
        query_text = query_obj.get("query", "").lower()
        
        # Handle each category differently
        if category.name == "temporal":
            # Add timestamps
            created_at = self._get_temporal_value(query_text, "created", category.value_generators["created_at"])
            modified_at = self._get_temporal_value(query_text, "modified", category.value_generators["modified_at"])
            
            # Add to timestamps array
            metadata["Timestamps"].append({
                "Label": "Created",
                "Value": created_at
            })
            
            metadata["Timestamps"].append({
                "Label": "Modified",
                "Value": modified_at
            })
            
            # Add session duration as a semantic attribute
            session_duration = category.value_generators["session_duration"]()
            self._add_semantic_attribute(metadata, "SessionDuration", session_duration)
            
        elif category.name == "activity":
            # Extract action from query if possible
            action = self._extract_action_from_query(query_text) or category.value_generators["action"]()
            
            # Extract collaborator from query if possible
            collaborator = self._extract_collaborator_from_query(query_text) or category.value_generators["collaborator"]()
            
            # Add to semantic attributes
            self._add_semantic_attribute(metadata, "Action", action)
            
            if collaborator:
                self._add_semantic_attribute(metadata, "Collaborator", collaborator)
                
            # Add activity record
            if "ActivityRecords" not in metadata:
                metadata["ActivityRecords"] = []
                
            activity_record = {
                "Type": action,
                "Timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "User": collaborator or "Current User"
            }
            
            metadata["ActivityRecords"].append(activity_record)
            
        elif category.name == "spatial":
            # Extract location from query if possible
            geolocation = self._extract_location_from_query(query_text) or category.value_generators["geolocation"]()
            
            # Use default generator for device location
            device_location = category.value_generators["device_location"]()
            
            # Add to semantic attributes
            if geolocation:
                self._add_semantic_attribute(metadata, "Geolocation", geolocation)
                
            if device_location:
                self._add_semantic_attribute(metadata, "DeviceLocation", device_location)
                
        elif category.name == "content":
            # Extract file type from query if possible
            file_type = self._extract_file_type_from_query(query_text) or category.value_generators["file_type"]()
            
            # Extract keywords and tags
            keywords = self._extract_keywords_from_query(query_text) or category.value_generators["keywords"]()
            tags = category.value_generators["tags"]()
            
            # Add to metadata
            metadata["Record"]["Attributes"]["FileType"] = file_type
            
            # Set extension based on file type
            extension = self._file_type_to_extension(file_type)
            metadata["Record"]["Attributes"]["Extension"] = extension
            
            # Update the document label to have the correct extension
            if "Label" in metadata and not metadata["Label"].lower().endswith(extension.lower()):
                base_name = Path(metadata["Label"]).stem
                metadata["Label"] = f"{base_name}.{extension}"
                
            # Add keywords and tags as semantic attributes
            if keywords:
                self._add_semantic_attribute(metadata, "Keywords", keywords)
                
            if tags:
                self._add_semantic_attribute(metadata, "Tags", tags)
    
    def _add_non_matching_metadata(
        self,
        metadata: Dict[str, Any],
        category: MetadataCategory,
        query_obj: Dict[str, Any]
    ) -> None:
        """Add metadata that explicitly doesn't match the query.

        Args:
            metadata: Document metadata to modify
            category: Metadata category to add
            query_obj: Query object for context
        """
        query_text = query_obj.get("query", "").lower()
        
        if category.name == "temporal":
            # Make timestamps be outside the range mentioned in the query
            if "yesterday" in query_text or "last week" in query_text or "recent" in query_text:
                # Use an old date (more than 30 days ago)
                old_date = (datetime.datetime.now(datetime.timezone.utc) - 
                           datetime.timedelta(days=self.random.randint(60, 365))).isoformat()
                
                # Replace any existing timestamps
                metadata["Timestamps"] = [
                    {"Label": "Created", "Value": old_date},
                    {"Label": "Modified", "Value": old_date}
                ]
                
        elif category.name == "activity":
            # Use different action than mentioned in query
            mentioned_actions = self._extract_action_words(query_text)
            all_actions = [
                "created", "edited", "viewed", "shared", "commented",
                "downloaded", "uploaded", "deleted", "printed", "renamed"
            ]
            available_actions = [action for action in all_actions if action not in mentioned_actions]
            
            if available_actions:
                action = self.random.choice(available_actions)
                # Replace semantic attribute
                self._replace_semantic_attribute(metadata, "Action", action)
                
                # Update activity records
                if "ActivityRecords" in metadata and metadata["ActivityRecords"]:
                    for record in metadata["ActivityRecords"]:
                        record["Type"] = action
                        
        elif category.name == "spatial":
            # Use different locations than mentioned in query
            mentioned_locations = self._extract_location_words(query_text)
            all_locations = [
                "Seattle, WA", "San Francisco, CA", "New York, NY", 
                "Boston, MA", "Chicago, IL", "Austin, TX", "Denver, CO",
                "Portland, OR", "Los Angeles, CA", "Miami, FL"
            ]
            available_locations = [loc for loc in all_locations if not any(word in loc.lower() for word in mentioned_locations)]
            
            if available_locations:
                geolocation = self.random.choice(available_locations)
                self._replace_semantic_attribute(metadata, "Geolocation", geolocation)
                
        elif category.name == "content":
            # Use different file type than mentioned in query
            mentioned_file_types = self._extract_file_type_words(query_text)
            all_file_types = [
                "PDF", "DOCX", "XLSX", "PPTX", "JPG", "PNG", "TXT",
                "HTML", "CSS", "JS", "PY", "MD", "JSON", "CSV"
            ]
            available_file_types = [ft for ft in all_file_types if ft.lower() not in mentioned_file_types]
            
            if available_file_types:
                file_type = self.random.choice(available_file_types)
                
                # Update file type
                metadata["Record"]["Attributes"]["FileType"] = file_type
                
                # Update extension
                extension = self._file_type_to_extension(file_type)
                metadata["Record"]["Attributes"]["Extension"] = extension
                
                # Update document label
                if "Label" in metadata:
                    base_name = Path(metadata["Label"]).stem
                    metadata["Label"] = f"{base_name}.{extension}"
                    
            # Use different keywords than mentioned in query
            mentioned_keywords = self._extract_keyword_words(query_text)
            all_keywords = [
                "budget", "report", "quarterly", "annual", "project", 
                "plan", "strategy", "proposal", "analysis", "research",
                "meeting", "notes", "presentation", "summary", "draft",
                "final", "review", "feedback", "update", "agenda"
            ]
            available_keywords = [kw for kw in all_keywords if kw not in mentioned_keywords]
            
            if available_keywords:
                new_keywords = self.random.sample(available_keywords, 
                                               k=min(3, len(available_keywords)))
                self._replace_semantic_attribute(metadata, "Keywords", new_keywords)
    
    def _add_semantic_attribute(
        self,
        metadata: Dict[str, Any],
        name: str,
        value: Any
    ) -> None:
        """Add a semantic attribute to a document.

        Args:
            metadata: Document metadata to modify
            name: Name of the attribute
            value: Value of the attribute
        """
        # Ensure there's a semantic attributes array
        if "SemanticAttributes" not in metadata:
            metadata["SemanticAttributes"] = []
            
        # Create semantic attribute
        attribute = {
            "Identifier": {
                "Identifier": f"sem_{uuid.uuid4().hex}",
                "Label": name
            },
            "Value": value
        }
        
        # Add to semantic attributes array
        metadata["SemanticAttributes"].append(attribute)
        
    def _replace_semantic_attribute(
        self,
        metadata: Dict[str, Any],
        name: str,
        value: Any
    ) -> None:
        """Replace a semantic attribute if it exists, or add if it doesn't.

        Args:
            metadata: Document metadata to modify
            name: Name of the attribute
            value: Value of the attribute
        """
        # Find existing attribute
        if "SemanticAttributes" in metadata:
            for i, attr in enumerate(metadata["SemanticAttributes"]):
                if attr.get("Identifier", {}).get("Label") == name:
                    metadata["SemanticAttributes"][i]["Value"] = value
                    return
                    
        # If not found, add it
        self._add_semantic_attribute(metadata, name, value)
        
    def _get_temporal_value(
        self,
        query_text: str,
        field_type: str,
        default_generator: callable
    ) -> str:
        """Get a temporal value that matches the query or use default generator.

        Args:
            query_text: Query text to analyze
            field_type: Type of field ("created" or "modified")
            default_generator: Default value generator function

        Returns:
            Temporal value as ISO format string
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Check for specific time references in the query
        if "yesterday" in query_text:
            if field_type in query_text or "modified" not in query_text:
                return (now - datetime.timedelta(days=1)).isoformat()
                
        elif "last week" in query_text:
            if field_type in query_text or "modified" not in query_text:
                days_ago = self.random.randint(1, 7)
                return (now - datetime.timedelta(days=days_ago)).isoformat()
                
        elif "this month" in query_text or "this year" in query_text:
            if field_type in query_text or "modified" not in query_text:
                days_ago = self.random.randint(1, 30)
                return (now - datetime.timedelta(days=days_ago)).isoformat()
                
        # If no match or not specific to this field type, use default
        return default_generator()
    
    def _extract_action_from_query(self, query_text: str) -> Optional[str]:
        """Extract an action from the query text.

        Args:
            query_text: Query text to analyze

        Returns:
            Extracted action or None
        """
        action_mapping = {
            "create": "created",
            "created": "created",
            "edit": "edited",
            "edited": "edited",
            "view": "viewed",
            "viewed": "viewed",
            "share": "shared",
            "shared": "shared",
            "comment": "commented",
            "commented": "commented",
            "download": "downloaded",
            "downloaded": "downloaded",
            "upload": "uploaded",
            "uploaded": "uploaded",
            "delete": "deleted",
            "deleted": "deleted",
            "print": "printed",
            "printed": "printed",
            "rename": "renamed",
            "renamed": "renamed",
            "work": "edited",
            "worked": "edited"
        }
        
        # Look for action words in the query
        for word, action in action_mapping.items():
            if word in query_text:
                return action
                
        return None
    
    def _extract_collaborator_from_query(self, query_text: str) -> Optional[str]:
        """Extract a collaborator from the query text.

        Args:
            query_text: Query text to analyze

        Returns:
            Extracted collaborator or None
        """
        # Look for common collaborator patterns
        if "with john" in query_text:
            return "John Smith"
        elif "with sarah" in query_text:
            return "Sarah Johnson"
        elif "with michael" in query_text:
            return "Michael Lee"
        elif "with emma" in query_text:
            return "Emma Davis"
        elif "with james" in query_text:
            return "James Wilson"
        elif "with marketing" in query_text or "marketing team" in query_text:
            return "Marketing Team"
        elif "with engineering" in query_text or "engineering department" in query_text:
            return "Engineering Department"
        elif "with client" in query_text:
            return "Client ABC"
            
        return None
    
    def _extract_location_from_query(self, query_text: str) -> Optional[str]:
        """Extract a location from the query text.

        Args:
            query_text: Query text to analyze

        Returns:
            Extracted location or None
        """
        # Look for location references
        location_mapping = {
            "seattle": "Seattle, WA",
            "san francisco": "San Francisco, CA",
            "new york": "New York, NY",
            "boston": "Boston, MA",
            "chicago": "Chicago, IL",
            "austin": "Austin, TX",
            "denver": "Denver, CO",
            "portland": "Portland, OR",
            "los angeles": "Los Angeles, CA",
            "miami": "Miami, FL",
            "home": "Home Office",
            "work": "Work Desk",
            "coffee shop": "Coffee Shop",
            "conference room": "Conference Room",
            "client site": "Client Site",
            "coworking": "Coworking Space",
            "hotel": "Hotel Room",
            "airport": "Airport Lounge"
        }
        
        for location_text, location_value in location_mapping.items():
            if location_text in query_text:
                return location_value
                
        return None
    
    def _extract_file_type_from_query(self, query_text: str) -> Optional[str]:
        """Extract a file type from the query text.

        Args:
            query_text: Query text to analyze

        Returns:
            Extracted file type or None
        """
        file_type_mapping = {
            "pdf": "PDF",
            "word": "DOCX",
            "excel": "XLSX",
            "spreadsheet": "XLSX",
            "powerpoint": "PPTX",
            "presentation": "PPTX",
            "document": "DOCX",  # Default document type
            "image": "JPG",
            "picture": "JPG",
            "photo": "JPG",
            "text": "TXT",
            "code": "PY",
            "html": "HTML",
            "css": "CSS",
            "js": "JS",
            "javascript": "JS",
            "python": "PY",
            "markdown": "MD",
            "json": "JSON",
            "csv": "CSV"
        }
        
        for type_text, type_value in file_type_mapping.items():
            if type_text in query_text:
                return type_value
                
        return None
    
    def _extract_keywords_from_query(self, query_text: str) -> Optional[List[str]]:
        """Extract keywords from the query text.

        Args:
            query_text: Query text to analyze

        Returns:
            List of extracted keywords or None
        """
        # Common content keyword patterns
        keyword_patterns = [
            "budget", "report", "quarterly", "annual", "project", 
            "plan", "strategy", "proposal", "analysis", "research",
            "meeting", "notes", "presentation", "summary", "draft",
            "final", "review", "feedback", "update", "agenda"
        ]
        
        # Extract matching keywords
        extracted = []
        for keyword in keyword_patterns:
            if keyword in query_text:
                extracted.append(keyword)
                
        return extracted if extracted else None
    
    def _extract_action_words(self, query_text: str) -> List[str]:
        """Extract all action-related words from query text.

        Args:
            query_text: Query text to analyze

        Returns:
            List of action words
        """
        action_words = [
            "create", "created", "edit", "edited", "view", "viewed",
            "share", "shared", "comment", "commented", "download", "downloaded",
            "upload", "uploaded", "delete", "deleted", "print", "printed",
            "rename", "renamed", "work", "worked"
        ]
        
        return [word for word in action_words if word in query_text]
    
    def _extract_location_words(self, query_text: str) -> List[str]:
        """Extract all location-related words from query text.

        Args:
            query_text: Query text to analyze

        Returns:
            List of location words
        """
        location_words = [
            "seattle", "san francisco", "new york", "boston", "chicago",
            "austin", "denver", "portland", "los angeles", "miami",
            "home", "work", "coffee shop", "conference room", "client site",
            "coworking", "hotel", "airport"
        ]
        
        return [word for word in location_words if word in query_text]
    
    def _extract_file_type_words(self, query_text: str) -> List[str]:
        """Extract all file type related words from query text.

        Args:
            query_text: Query text to analyze

        Returns:
            List of file type words
        """
        file_type_words = [
            "pdf", "word", "excel", "spreadsheet", "powerpoint", "presentation",
            "document", "image", "picture", "photo", "text", "code", "html",
            "css", "js", "javascript", "python", "markdown", "json", "csv"
        ]
        
        return [word for word in file_type_words if word in query_text]
    
    def _extract_keyword_words(self, query_text: str) -> List[str]:
        """Extract all content keyword related words from query text.

        Args:
            query_text: Query text to analyze

        Returns:
            List of keyword words
        """
        keyword_words = [
            "budget", "report", "quarterly", "annual", "project", 
            "plan", "strategy", "proposal", "analysis", "research",
            "meeting", "notes", "presentation", "summary", "draft",
            "final", "review", "feedback", "update", "agenda"
        ]
        
        return [word for word in keyword_words if word in query_text]
    
    def _file_type_to_extension(self, file_type: str) -> str:
        """Convert a file type to a file extension.

        Args:
            file_type: File type (e.g., "PDF", "DOCX")

        Returns:
            File extension (e.g., "pdf", "docx")
        """
        file_type_mapping = {
            "PDF": "pdf",
            "DOCX": "docx",
            "XLSX": "xlsx",
            "PPTX": "pptx",
            "JPG": "jpg",
            "PNG": "png",
            "TXT": "txt",
            "HTML": "html",
            "CSS": "css",
            "JS": "js",
            "PY": "py",
            "MD": "md",
            "JSON": "json",
            "CSV": "csv"
        }
        
        return file_type_mapping.get(file_type, "txt")
    
    def generate_truth_set(
        self,
        query_obj: Dict[str, Any],
        matching_count: int = 5,
        non_matching_count: int = 45
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Generate a truth set of documents for a query.

        Args:
            query_obj: Query object containing the query text and metadata
            matching_count: Number of matching documents to generate
            non_matching_count: Number of non-matching documents to generate

        Returns:
            Tuple of (matching_documents, non_matching_documents)
        """
        matching_documents = []
        non_matching_documents = []
        
        # Generate matching documents
        for _ in range(matching_count):
            document = self.generate_metadata(query_obj, matching=True)
            matching_documents.append(document)
            
        # Generate non-matching documents
        for _ in range(non_matching_count):
            document = self.generate_metadata(query_obj, matching=False)
            non_matching_documents.append(document)
            
        return matching_documents, non_matching_documents
    
    def upload_truth_data(
        self,
        db_config: IndalekoDBConfig,
        matching_documents: List[Dict[str, Any]],
        non_matching_documents: List[Dict[str, Any]]
    ) -> bool:
        """Upload truth data to the database.

        Args:
            db_config: Database configuration
            matching_documents: List of matching documents
            non_matching_documents: List of non-matching documents

        Returns:
            True if successful, False otherwise
        """
        try:
            db = db_config.get_arangodb()
            
            # Get the Objects collection
            objects_collection = db_config.get_collection(IndalekoDBCollections.Indaleko_Object_Collection)
            
            # Upload matching documents
            for doc in matching_documents:
                # Clean up document to ensure it's compatible with ArangoDB
                if "_id" in doc and not doc["_id"].startswith(IndalekoDBCollections.Indaleko_Object_Collection):
                    doc["_id"] = f"{IndalekoDBCollections.Indaleko_Object_Collection}/{doc['_id'].split('/')[-1]}"
                
                try:
                    objects_collection.insert(doc, overwrite=True)
                except Exception as e:
                    self.logger.warning(f"Error inserting matching document: {e}")
                    
            # Upload non-matching documents
            for doc in non_matching_documents:
                # Clean up document for ArangoDB
                if "_id" in doc and not doc["_id"].startswith(IndalekoDBCollections.Indaleko_Object_Collection):
                    doc["_id"] = f"{IndalekoDBCollections.Indaleko_Object_Collection}/{doc['_id'].split('/')[-1]}"
                
                try:
                    objects_collection.insert(doc, overwrite=True)
                except Exception as e:
                    self.logger.warning(f"Error inserting non-matching document: {e}")
                    
            self.logger.info(f"Uploaded {len(matching_documents)} matching and {len(non_matching_documents)} non-matching documents")
            return True
            
        except Exception as e:
            self.logger.error(f"Error uploading truth data: {e}")
            return False


def main():
    """Test the synthetic metadata generator."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger = logging.getLogger("MetadataGeneratorTest")
    logger.info("Testing synthetic metadata generator...")
    
    # Create generator with fixed seed
    generator = SyntheticMetadataGenerator(seed=42)
    
    # Create a query to test with
    query_obj = {
        "query": "Find PDF documents I edited yesterday",
        "categories": ["temporal", "activity", "content"]
    }
    
    # Generate a sample matching document
    matching_doc = generator.generate_metadata(query_obj, matching=True)
    logger.info("\nMatching document example:")
    print(json.dumps(matching_doc, indent=2))
    
    # Generate a sample non-matching document
    non_matching_doc = generator.generate_metadata(query_obj, matching=False)
    logger.info("\nNon-matching document example:")
    print(json.dumps(non_matching_doc, indent=2))
    
    # Generate a small truth set
    matching_docs, non_matching_docs = generator.generate_truth_set(
        query_obj, matching_count=3, non_matching_count=7
    )
    logger.info(f"\nGenerated truth set: {len(matching_docs)} matching, {len(non_matching_docs)} non-matching")
    

if __name__ == "__main__":
    main()