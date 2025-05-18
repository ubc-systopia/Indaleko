#!/usr/bin/env python
"""
Test the query matching effectiveness against synthetic metadata.

This script:
1. Generates diverse queries using the enhanced query generator
2. Creates synthetic metadata with known truth sets (exactly 5 matching files per query)
3. Tests if the query processing pipeline correctly identifies those 5 files
4. Measures precision, recall, and F1 score of the matching process

This allows us to identify if the query processing component is working correctly
with our improved query diversity.
"""

import argparse
import json
import logging
import os
import random
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple, Set, Optional

# Initialize logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Ensure we can import from our modules
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    parent_path = os.path.dirname(current_path)
    if parent_path not in sys.path:
        sys.path.insert(0, parent_path)

# Import our query generators
from enhanced_query_generator import EnhancedQueryGenerator

class QueryMatchingTest:
    """Test query matching effectiveness against synthetic metadata."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the query matching test."""
        from simple_llm_connector import load_api_key
        
        # Load API key if not provided
        if api_key is None:
            try:
                api_key = load_api_key("anthropic")
            except ValueError as e:
                logger.error(f"Failed to load API key: {e}")
                raise
        
        # Initialize query generator (using only the enhanced version)
        self.query_generator = EnhancedQueryGenerator(api_key=api_key)
        
        # Test data
        self.test_corpus = {}
        self.truth_sets = {}
        
        # Test results
        self.test_results = {}
    
    def generate_queries(self, activity_type: str, count: int = 5) -> List[str]:
        """
        Generate test queries for the specified activity type.
        
        Args:
            activity_type: Activity type to generate queries for
            count: Number of queries to generate
            
        Returns:
            List of generated queries
        """
        logger.info(f"Generating {count} queries for {activity_type} activity...")
        
        # Generate enhanced queries
        queries = self.query_generator.generate_enhanced_queries(activity_type, count)
        
        logger.info(f"Generated {len(queries)} queries")
        return queries
    
    def generate_synthetic_metadata(
        self, 
        queries: List[str],
        activity_type: str,
        files_per_query: int = 5,
        noise_files: int = 20
    ) -> Tuple[Dict[str, Any], Dict[str, Set[str]]]:
        """
        Generate synthetic metadata with known truth sets.
        
        Args:
            queries: Queries to generate metadata for
            activity_type: Activity type to generate metadata for
            files_per_query: Number of files that should match each query
            noise_files: Number of non-matching files to generate
            
        Returns:
            Tuple of (metadata, truth_sets)
        """
        logger.info(f"Generating synthetic metadata for {len(queries)} queries...")
        
        # Initialize metadata and truth sets
        metadata = {
            "files": {},
            "entities": {}
        }
        truth_sets = {}
        
        # Initialize set of all file IDs
        all_file_ids = set()
        
        # Helper function to extract key terms from a query
        def extract_key_terms(query: str) -> List[str]:
            """Extract key terms from a query."""
            # Start with all words
            words = query.lower().split()
            
            # Remove common words that don't help with matching
            stop_words = {"a", "an", "the", "in", "on", "at", "from", "to", "with", "for", "of", "by", "my", "i", "we", "our", "me", "about"}
            terms = [word for word in words if word not in stop_words and len(word) > 2]
            
            # If we have too few terms, just return the original words
            if len(terms) < 2:
                terms = words
            
            return terms
        
        # For each query, generate matching and non-matching files
        for i, query in enumerate(queries):
            query_id = f"query_{i}"
            
            # Extract key terms from the query
            key_terms = extract_key_terms(query)
            
            # Generate matching files for this query
            matching_files = set()
            for j in range(files_per_query):
                file_id = f"file_{query_id}_{j}"
                all_file_ids.add(file_id)
                matching_files.add(file_id)
                
                # Create file metadata with key terms from the query
                metadata["files"][file_id] = self._generate_file_metadata(
                    file_id=file_id,
                    activity_type=activity_type,
                    key_terms=key_terms,
                    should_match=True,
                    query=query
                )
            
            # Store truth set for this query
            truth_sets[query] = matching_files
        
        # Generate noise files that don't match any query
        for i in range(noise_files):
            file_id = f"noise_file_{i}"
            all_file_ids.add(file_id)
            
            # Create noise file metadata
            metadata["files"][file_id] = self._generate_file_metadata(
                file_id=file_id,
                activity_type=activity_type,
                key_terms=[],
                should_match=False
            )
        
        # For each specific activity type, generate appropriate entities
        if activity_type == "location":
            metadata["entities"] = self._generate_location_entities()
        elif activity_type == "task":
            metadata["entities"] = self._generate_task_entities()
        elif activity_type == "music":
            metadata["entities"] = self._generate_music_entities()
        elif activity_type == "collaboration":
            metadata["entities"] = self._generate_collaboration_entities()
        elif activity_type == "storage":
            metadata["entities"] = self._generate_storage_entities()
        elif activity_type == "media":
            metadata["entities"] = self._generate_media_entities()
        
        # Store the test corpus and truth sets
        self.test_corpus = metadata
        self.truth_sets = truth_sets
        
        logger.info(f"Generated metadata with {len(metadata['files'])} files and {len(truth_sets)} truth sets")
        
        return metadata, truth_sets
    
    def _generate_file_metadata(
        self, 
        file_id: str, 
        activity_type: str,
        key_terms: List[str],
        should_match: bool,
        query: str = None
    ) -> Dict[str, Any]:
        """
        Generate metadata for a single file.
        
        Args:
            file_id: ID of the file
            activity_type: Activity type to generate metadata for
            key_terms: Key terms to include in the metadata
            should_match: Whether this file should match queries
            query: Original query (for matching files only)
            
        Returns:
            File metadata
        """
        # Basic file types and extensions
        file_types = ["document", "spreadsheet", "presentation", "image", "code", "pdf", "text"]
        file_extensions = {
            "document": ["docx", "doc", "odt", "rtf", "txt"],
            "spreadsheet": ["xlsx", "xls", "csv", "ods"],
            "presentation": ["pptx", "ppt", "odp"],
            "image": ["jpg", "png", "gif", "tiff", "bmp"],
            "code": ["py", "js", "java", "cpp", "html", "css"],
            "pdf": ["pdf"],
            "text": ["txt", "md", "json", "xml", "yaml"]
        }
        
        # Choose a random file type and extension
        file_type = random.choice(file_types)
        extension = random.choice(file_extensions[file_type])
        
        # Generate a file name that includes key terms if it should match
        if should_match and key_terms:
            # Include 1-2 key terms in the file name
            name_terms = random.sample(key_terms, min(len(key_terms), random.randint(1, 2)))
            name_parts = name_terms + ["file", file_id]
            file_name = "_".join(name_parts) + f".{extension}"
        else:
            # Generic file name for non-matching files
            generic_terms = ["project", "report", "data", "notes", "draft", "final", "backup"]
            name_parts = [random.choice(generic_terms) for _ in range(2)]
            file_name = "_".join(name_parts) + f"_{uuid.uuid4().hex[:6]}.{extension}"
        
        # Create timestamp within the last 30 days
        now = datetime.now()
        days_ago = random.randint(0, 30)
        timestamp = now - timedelta(days=days_ago, 
                                  hours=random.randint(0, 23),
                                  minutes=random.randint(0, 59))
        
        # Basic file metadata
        metadata = {
            "id": file_id,
            "name": file_name,
            "path": f"/users/user_{random.randint(1, 10)}/documents/{file_name}",
            "type": file_type,
            "extension": extension,
            "size_kb": random.randint(10, 10000),
            "created": timestamp.isoformat(),
            "modified": timestamp.isoformat(),
            "accessed": timestamp.isoformat(),
            "keywords": key_terms + [file_type, extension] if should_match else [file_type, extension],
            "activity": {}
        }
        
        # Add activity-specific metadata
        if activity_type == "location":
            metadata["activity"] = self._generate_location_activity(key_terms, should_match)
        elif activity_type == "task":
            metadata["activity"] = self._generate_task_activity(key_terms, should_match, query)
        elif activity_type == "music":
            metadata["activity"] = self._generate_music_activity(key_terms, should_match)
        elif activity_type == "collaboration":
            metadata["activity"] = self._generate_collaboration_activity(key_terms, should_match)
        elif activity_type == "storage":
            metadata["activity"] = self._generate_storage_activity(key_terms, should_match)
        elif activity_type == "media":
            metadata["activity"] = self._generate_media_activity(key_terms, should_match)
        
        # For matching files, add a directly matching property
        if should_match and query:
            metadata["matches_query"] = query
        
        return metadata
    
    def _generate_location_entities(self) -> Dict[str, Any]:
        """Generate location entities."""
        entities = {}
        location_types = ["home", "work", "coffee_shop", "library", "park", "gym", "restaurant"]
        
        for i, location_type in enumerate(location_types):
            entity_id = f"location_{i}"
            entities[entity_id] = {
                "id": entity_id,
                "type": location_type,
                "name": f"{location_type.title()} Location",
                "address": f"{random.randint(100, 999)} {self._random_street_name()}, {self._random_city()}, {self._random_state()} {random.randint(10000, 99999)}",
                "keywords": [location_type, "location"]
            }
        
        return entities
    
    def _generate_task_entities(self) -> Dict[str, Any]:
        """Generate task entities."""
        entities = {}
        applications = [
            "Microsoft Word", "Excel", "PowerPoint", "Google Docs", 
            "Visual Studio Code", "Photoshop", "Chrome", "Firefox"
        ]
        
        for i, app in enumerate(applications):
            entity_id = f"app_{i}"
            entities[entity_id] = {
                "id": entity_id,
                "type": "application",
                "name": app,
                "version": f"{random.randint(1, 10)}.{random.randint(0, 99)}",
                "keywords": [app.lower().replace(" ", "_"), "application"]
            }
        
        return entities
    
    def _generate_music_entities(self) -> Dict[str, Any]:
        """Generate music entities."""
        entities = {}
        genres = ["rock", "pop", "jazz", "classical", "hip_hop", "electronic", "country", "folk"]
        
        for i, genre in enumerate(genres):
            entity_id = f"music_{i}"
            entities[entity_id] = {
                "id": entity_id,
                "type": "music",
                "genre": genre,
                "name": f"{genre.title()} Music",
                "keywords": [genre, "music"]
            }
        
        return entities
    
    def _generate_collaboration_entities(self) -> Dict[str, Any]:
        """Generate collaboration entities."""
        entities = {}
        collab_types = ["meeting", "call", "email", "chat", "document", "presentation"]
        
        for i, collab_type in enumerate(collab_types):
            entity_id = f"collab_{i}"
            entities[entity_id] = {
                "id": entity_id,
                "type": "collaboration",
                "activity_type": collab_type,
                "name": f"{collab_type.title()} Collaboration",
                "keywords": [collab_type, "collaboration"]
            }
        
        return entities
    
    def _generate_storage_entities(self) -> Dict[str, Any]:
        """Generate storage entities."""
        entities = {}
        storage_types = ["local", "cloud", "external", "network", "backup"]
        providers = ["OneDrive", "Google Drive", "Dropbox", "iCloud", "Box", "AWS S3"]
        
        for i, storage_type in enumerate(storage_types):
            entity_id = f"storage_{i}"
            provider = random.choice(providers) if storage_type == "cloud" else "Local Storage"
            
            entities[entity_id] = {
                "id": entity_id,
                "type": "storage",
                "storage_type": storage_type,
                "name": f"{provider} Storage",
                "provider": provider,
                "keywords": [storage_type, provider.lower().replace(" ", "_"), "storage"]
            }
        
        return entities
    
    def _generate_media_entities(self) -> Dict[str, Any]:
        """Generate media entities."""
        entities = {}
        media_types = ["video", "livestream", "podcast", "webinar", "tutorial", "documentary"]
        platforms = ["YouTube", "Netflix", "Spotify", "Twitch", "Udemy", "TikTok"]
        
        for i, media_type in enumerate(media_types):
            entity_id = f"media_{i}"
            platform = random.choice(platforms)
            
            entities[entity_id] = {
                "id": entity_id,
                "type": "media",
                "media_type": media_type,
                "name": f"{platform} {media_type.title()}",
                "platform": platform,
                "keywords": [media_type, platform.lower(), "media"]
            }
        
        return entities
    
    def _generate_location_activity(self, key_terms: List[str], should_match: bool) -> Dict[str, Any]:
        """Generate location activity metadata."""
        # For matching files, include a location entity that contains keywords from the query
        if should_match and key_terms:
            # Find matching location from key terms
            term_set = set(key_terms)
            location_terms = {"home", "work", "office", "library", "coffee", "park", "restaurant", "gym", "airport"}
            matching_terms = term_set.intersection(location_terms)
            
            # Use the first matching term or a random location
            location = next(iter(matching_terms)) if matching_terms else random.choice(list(location_terms))
            
            # Map to proper location type
            if location in {"office", "work"}:
                location = "work"
            elif location in {"coffee"}:
                location = "coffee_shop"
            
            return {
                "location": location,
                "timestamp": datetime.now().isoformat(),
                "duration_minutes": random.randint(15, 120),
                "keywords": key_terms + [location, "location"],
                "entities": [f"location_{random.randint(0, 6)}"]
            }
        else:
            # For non-matching files, use a generic location
            locations = ["home", "work", "coffee_shop", "library", "park", "gym", "restaurant"]
            location = random.choice(locations)
            
            return {
                "location": location,
                "timestamp": datetime.now().isoformat(),
                "duration_minutes": random.randint(15, 120),
                "keywords": [location, "location"],
                "entities": [f"location_{random.randint(0, 6)}"]
            }
    
    def _generate_task_activity(self, key_terms: List[str], should_match: bool, query: str = None) -> Dict[str, Any]:
        """Generate task activity metadata."""
        # Define status options
        statuses = ["completed", "in_progress", "overdue", "pending"]
        priorities = ["high", "medium", "low", "critical"]
        people = ["Sarah", "John", "Jennifer", "Michael", "Robert", "Lisa", "Thomas", "Jessica"]
        projects = ["Annual Report", "Project Phoenix", "Q2 Planning", "Client Proposal", "Website Redesign", "MongoDB", "API Integration", "Marketing Campaign"]
        actions = ["created", "edited", "reviewed", "shared", "approved", "scheduled"]
        contexts = ["Team meeting", "Client presentation", "Project deadline", "Quarterly review", "AWS outage", "Sprint planning"]
        
        # For matching files, include an application that matches query terms
        if should_match and key_terms:
            # Find matching application from key terms
            term_set = set(key_terms)
            app_terms = {"word", "excel", "powerpoint", "vscode", "visual", "code", "photoshop", "chrome", "firefox"}
            matching_terms = term_set.intersection(app_terms)
            
            # Use the first matching term or a random application
            app_term = next(iter(matching_terms)) if matching_terms else random.choice(list(app_terms))
            
            # Map to proper application name
            app_mapping = {
                "word": "Microsoft Word",
                "excel": "Excel",
                "powerpoint": "PowerPoint",
                "vscode": "Visual Studio Code",
                "visual": "Visual Studio Code",
                "code": "Visual Studio Code",
                "photoshop": "Photoshop",
                "chrome": "Chrome",
                "firefox": "Firefox"
            }
            
            application = app_mapping.get(app_term, "Microsoft Word")
            
            # Check for special terms in the query (if provided)
            status = "completed"  # Default
            if query:
                query_lower = query.lower()
                if "overdue" in query_lower:
                    status = "overdue"
                elif "unfinished" in query_lower or "in progress" in query_lower:
                    status = "in_progress"
                elif "pending" in query_lower or "scheduled" in query_lower:
                    status = "pending"
            
            # Check for project references
            project = None
            for proj in projects:
                if any(term.lower() in proj.lower() for term in key_terms):
                    project = proj
                    break
            if not project:
                project = random.choice(projects)
            
            # Check for people references
            owner = None
            assigned_by = None
            for person in people:
                if person.lower() in str(key_terms).lower():
                    if not owner:
                        owner = person
                    else:
                        assigned_by = person
                    
            if not owner:
                owner = random.choice(people)
            if not assigned_by:
                assigned_by = random.choice([p for p in people if p != owner])
            
            # Generate due date
            now = datetime.now()
            # For overdue tasks, due date should be in the past
            if status == "overdue":
                due_date = (now - timedelta(days=random.randint(1, 10))).isoformat()
            else:
                due_date = (now + timedelta(days=random.randint(1, 14))).isoformat()
            
            # Determine action based on terms
            action = None
            for act in actions:
                if act in str(key_terms).lower():
                    action = act
                    break
            if not action:
                action = random.choice(actions)
            
            # Build the result with all necessary fields
            return {
                "application": application,
                "timestamp": now.isoformat(),
                "duration_minutes": random.randint(15, 120),
                "keywords": key_terms + [application.lower().replace(" ", "_"), "task", status],
                "status": status,
                "priority": random.choice(priorities),
                "owner": owner,
                "action": action,
                "project": project,
                "context": random.choice(contexts),
                "due_date": due_date,
                "assigned_by": assigned_by,
                "entities": [f"app_{random.randint(0, 7)}", f"task_{random.randint(100, 999)}"],
                "shared_with": random.sample(["marketing team", "sales team", "development team", "executive team", "client"], k=random.randint(0, 2))
            }
        else:
            # For non-matching files, use a generic application
            applications = ["Microsoft Word", "Excel", "PowerPoint", "Visual Studio Code", "Photoshop", "Chrome", "Firefox"]
            application = random.choice(applications)
            
            # Use a different status for non-matching files when query mentions status
            status = random.choice(statuses)
            if query and "overdue" in query.lower() and status == "overdue":
                # Make sure non-matching files don't have the status mentioned in the query
                statuses.remove("overdue")
                status = random.choice(statuses)
            
            now = datetime.now()
            # Due date should be consistent with status
            if status == "overdue":
                due_date = (now - timedelta(days=random.randint(1, 10))).isoformat()
            else:
                due_date = (now + timedelta(days=random.randint(1, 14))).isoformat()
            
            return {
                "application": application,
                "timestamp": now.isoformat(),
                "duration_minutes": random.randint(15, 120),
                "keywords": [application.lower().replace(" ", "_"), "task", status],
                "status": status,
                "priority": random.choice(priorities),
                "owner": random.choice(people),
                "action": random.choice(actions),
                "project": random.choice(projects),
                "context": random.choice(contexts),
                "due_date": due_date,
                "assigned_by": random.choice(people),
                "entities": [f"app_{random.randint(0, 7)}", f"task_{random.randint(100, 999)}"],
                "shared_with": random.sample(["marketing team", "sales team", "development team", "executive team", "client"], k=random.randint(0, 1))
            }
    
    def _generate_music_activity(self, key_terms: List[str], should_match: bool) -> Dict[str, Any]:
        """Generate music activity metadata."""
        # For matching files, include a genre that matches query terms
        if should_match and key_terms:
            # Find matching genre from key terms
            term_set = set(key_terms)
            genre_terms = {"rock", "pop", "jazz", "classical", "hip", "hop", "electronic", "country", "folk"}
            matching_terms = term_set.intersection(genre_terms)
            
            # Use the first matching term or a random genre
            genre_term = next(iter(matching_terms)) if matching_terms else random.choice(list(genre_terms))
            
            # Map to proper genre name
            genre_mapping = {
                "hip": "hip_hop",
                "hop": "hip_hop"
            }
            
            genre = genre_mapping.get(genre_term, genre_term)
            
            return {
                "genre": genre,
                "timestamp": datetime.now().isoformat(),
                "duration_minutes": random.randint(3, 10),
                "keywords": key_terms + [genre, "music"],
                "entities": [f"music_{random.randint(0, 7)}"]
            }
        else:
            # For non-matching files, use a generic genre
            genres = ["rock", "pop", "jazz", "classical", "hip_hop", "electronic", "country", "folk"]
            genre = random.choice(genres)
            
            return {
                "genre": genre,
                "timestamp": datetime.now().isoformat(),
                "duration_minutes": random.randint(3, 10),
                "keywords": [genre, "music"],
                "entities": [f"music_{random.randint(0, 7)}"]
            }
    
    def _generate_collaboration_activity(self, key_terms: List[str], should_match: bool) -> Dict[str, Any]:
        """Generate collaboration activity metadata."""
        # For matching files, include a collaboration type that matches query terms
        if should_match and key_terms:
            # Find matching collaboration type from key terms
            term_set = set(key_terms)
            collab_terms = {"meeting", "call", "email", "chat", "document", "presentation", "team", "share"}
            matching_terms = term_set.intersection(collab_terms)
            
            # Use the first matching term or a random collaboration type
            collab_term = next(iter(matching_terms)) if matching_terms else random.choice(list(collab_terms))
            
            # Map to proper collaboration type
            collab_mapping = {
                "team": "meeting",
                "share": "document"
            }
            
            collab_type = collab_mapping.get(collab_term, collab_term)
            
            return {
                "activity_type": collab_type,
                "timestamp": datetime.now().isoformat(),
                "duration_minutes": random.randint(15, 60),
                "keywords": key_terms + [collab_type, "collaboration"],
                "entities": [f"collab_{random.randint(0, 5)}"]
            }
        else:
            # For non-matching files, use a generic collaboration type
            collab_types = ["meeting", "call", "email", "chat", "document", "presentation"]
            collab_type = random.choice(collab_types)
            
            return {
                "activity_type": collab_type,
                "timestamp": datetime.now().isoformat(),
                "duration_minutes": random.randint(15, 60),
                "keywords": [collab_type, "collaboration"],
                "entities": [f"collab_{random.randint(0, 5)}"]
            }
    
    def _generate_storage_activity(self, key_terms: List[str], should_match: bool) -> Dict[str, Any]:
        """Generate storage activity metadata."""
        # For matching files, include a storage type that matches query terms
        if should_match and key_terms:
            # Find matching storage type from key terms
            term_set = set(key_terms)
            storage_terms = {"local", "cloud", "external", "network", "backup", "onedrive", "google", "drive", "dropbox"}
            matching_terms = term_set.intersection(storage_terms)
            
            # Use the first matching term or a random storage type
            storage_term = next(iter(matching_terms)) if matching_terms else random.choice(list(storage_terms))
            
            # Map to proper storage type
            storage_mapping = {
                "onedrive": "cloud",
                "google": "cloud",
                "drive": "cloud",
                "dropbox": "cloud"
            }
            
            storage_type = storage_mapping.get(storage_term, storage_term)
            
            return {
                "storage_type": storage_type,
                "timestamp": datetime.now().isoformat(),
                "keywords": key_terms + [storage_type, "storage"],
                "entities": [f"storage_{random.randint(0, 4)}"]
            }
        else:
            # For non-matching files, use a generic storage type
            storage_types = ["local", "cloud", "external", "network", "backup"]
            storage_type = random.choice(storage_types)
            
            return {
                "storage_type": storage_type,
                "timestamp": datetime.now().isoformat(),
                "keywords": [storage_type, "storage"],
                "entities": [f"storage_{random.randint(0, 4)}"]
            }
    
    def _generate_media_activity(self, key_terms: List[str], should_match: bool) -> Dict[str, Any]:
        """Generate media activity metadata."""
        # For matching files, include a media type that matches query terms
        if should_match and key_terms:
            # Find matching media type from key terms
            term_set = set(key_terms)
            media_terms = {"video", "livestream", "podcast", "webinar", "tutorial", "documentary", "youtube", "netflix", "spotify"}
            matching_terms = term_set.intersection(media_terms)
            
            # Use the first matching term or a random media type
            media_term = next(iter(matching_terms)) if matching_terms else random.choice(list(media_terms))
            
            # Map to proper media type
            media_mapping = {
                "youtube": "video",
                "netflix": "video",
                "spotify": "podcast"
            }
            
            media_type = media_mapping.get(media_term, media_term)
            
            return {
                "media_type": media_type,
                "timestamp": datetime.now().isoformat(),
                "duration_minutes": random.randint(5, 120),
                "keywords": key_terms + [media_type, "media"],
                "entities": [f"media_{random.randint(0, 5)}"]
            }
        else:
            # For non-matching files, use a generic media type
            media_types = ["video", "livestream", "podcast", "webinar", "tutorial", "documentary"]
            media_type = random.choice(media_types)
            
            return {
                "media_type": media_type,
                "timestamp": datetime.now().isoformat(),
                "duration_minutes": random.randint(5, 120),
                "keywords": [media_type, "media"],
                "entities": [f"media_{random.randint(0, 5)}"]
            }
    
    def _random_street_name(self) -> str:
        """Generate a random street name."""
        prefixes = ["Oak", "Maple", "Pine", "Cedar", "Elm", "Main", "High", "Park", "Lake", "Hill"]
        suffixes = ["Street", "Avenue", "Road", "Lane", "Drive", "Boulevard", "Way", "Court"]
        return f"{random.choice(prefixes)} {random.choice(suffixes)}"
    
    def _random_city(self) -> str:
        """Generate a random city name."""
        cities = ["Springfield", "Riverside", "Fairview", "Kingston", "Burlington", "Franklin", "Greenville", 
                 "Bristol", "Clinton", "Georgetown", "Salem", "Madison", "Oxford", "Arlington"]
        return random.choice(cities)
    
    def _random_state(self) -> str:
        """Generate a random US state abbreviation."""
        states = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", 
                 "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV"]
        return random.choice(states)
    
    def process_query(self, query: str, activity_type: str) -> Set[str]:
        """
        Process a query to find matching files.
        
        Args:
            query: Query to process
            activity_type: Activity type to query against
            
        Returns:
            Set of file IDs that match the query
        """
        # Extract key terms from the query
        query_lower = query.lower()
        
        # Extract words and remove stop words
        stop_words = {"a", "an", "the", "in", "on", "at", "from", "to", "with", "for", "of", "by", "my", "i", "we", "our", "me", "about"}
        words = query_lower.split()
        query_terms = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Implement simple matching logic:
        # 1. Check for files that directly match this query (should_match)
        # 2. Look for keyword matches in file name or metadata
        # 3. Check for activity type-specific matches
        
        # Files that match the query
        matching_files = set()
        
        # Check each file for matches
        for file_id, file_data in self.test_corpus["files"].items():
            # Check for direct match
            if "matches_query" in file_data and file_data["matches_query"] == query:
                matching_files.add(file_id)
                continue
            
            # Check for keyword matches in file name or path
            if (query_lower in file_data.get("name", "").lower() or 
                query_lower in file_data.get("path", "").lower()):
                matching_files.add(file_id)
                continue
            
            # Check for keyword matches
            file_keywords = [k.lower() for k in file_data.get("keywords", [])]
            if any(term in file_keywords for term in query_terms):
                matching_files.add(file_id)
                continue
            
            # Check for activity type-specific matches
            if activity_type in file_data.get("activity", {}):
                activity_data = file_data["activity"][activity_type]
                
                # Check for keywords in activity data
                if isinstance(activity_data, dict) and "keywords" in activity_data:
                    activity_keywords = [k.lower() for k in activity_data["keywords"]]
                    if any(term in activity_keywords for term in query_terms):
                        matching_files.add(file_id)
                        continue
                
                # Check for activity type-specific fields
                if activity_type == "location":
                    if isinstance(activity_data, dict) and "location" in activity_data and activity_data["location"].lower() in query_lower:
                        matching_files.add(file_id)
                        continue
                elif activity_type == "task":
                    if isinstance(activity_data, dict):
                        # Check application matching
                        if "application" in activity_data and activity_data["application"].lower() in query_lower:
                            matching_files.add(file_id)
                            continue
                            
                        # Check status matching (specifically for overdue tasks)
                        if "overdue" in query_lower and "status" in activity_data and activity_data["status"] == "overdue":
                            matching_files.add(file_id)
                            continue
                            
                        # Check for unfinished tasks
                        if ("unfinished" in query_lower or "in progress" in query_lower) and "status" in activity_data and activity_data["status"] == "in_progress":
                            matching_files.add(file_id)
                            continue
                            
                        # Check project matching
                        if "project" in activity_data and activity_data["project"].lower() in query_lower:
                            matching_files.add(file_id)
                            continue
                            
                        # Check owner/person matching
                        if "owner" in activity_data and activity_data["owner"].lower() in query_lower:
                            matching_files.add(file_id)
                            continue
                elif activity_type == "music":
                    if isinstance(activity_data, dict) and "genre" in activity_data and activity_data["genre"].lower() in query_lower:
                        matching_files.add(file_id)
                        continue
                elif activity_type == "collaboration":
                    if isinstance(activity_data, dict) and "activity_type" in activity_data and activity_data["activity_type"].lower() in query_lower:
                        matching_files.add(file_id)
                        continue
                elif activity_type == "storage":
                    if isinstance(activity_data, dict) and "storage_type" in activity_data and activity_data["storage_type"].lower() in query_lower:
                        matching_files.add(file_id)
                        continue
                elif activity_type == "media":
                    if isinstance(activity_data, dict) and "media_type" in activity_data and activity_data["media_type"].lower() in query_lower:
                        matching_files.add(file_id)
                        continue
        
        return matching_files
    
    def test_query_processing(
        self, 
        activity_type: str, 
        query_count: int = 5
    ) -> Dict[str, Any]:
        """
        Test query processing against synthetic metadata.
        
        Args:
            activity_type: Activity type to test
            query_count: Number of queries to test
            
        Returns:
            Dictionary with test results
        """
        logger.info(f"Testing query processing for {activity_type} activity...")
        
        # Generate test queries
        queries = self.generate_queries(activity_type, query_count)
        
        # Generate synthetic metadata with 5 matching files per query
        metadata, truth_sets = self.generate_synthetic_metadata(
            queries=queries,
            activity_type=activity_type,
            files_per_query=5,
            noise_files=20
        )
        
        # Process each query and measure performance
        results = {}
        for query in queries:
            logger.info(f"Processing query: {query}")
            
            # Time the query processing
            start_time = time.time()
            result_file_ids = self.process_query(query, activity_type)
            end_time = time.time()
            
            # Get expected matches from truth set
            expected_matches = truth_sets.get(query, set())
            
            # Calculate precision, recall, F1 score
            true_positives = len(result_file_ids & expected_matches)
            false_positives = len(result_file_ids - expected_matches)
            false_negatives = len(expected_matches - result_file_ids)
            
            precision = true_positives / (true_positives + false_positives) if true_positives + false_positives > 0 else 0.0
            recall = true_positives / (true_positives + false_negatives) if true_positives + false_negatives > 0 else 0.0
            f1_score = 2 * (precision * recall) / (precision + recall) if precision + recall > 0 else 0.0
            
            # Store result metrics
            result = {
                "query": query,
                "truth_set": list(expected_matches),
                "result_set": list(result_file_ids),
                "true_positives": true_positives,
                "false_positives": false_positives,
                "false_negatives": false_negatives,
                "precision": precision,
                "recall": recall,
                "f1_score": f1_score,
                "execution_time_ms": (end_time - start_time) * 1000
            }
            
            results[query] = result
            
            logger.info(f"  Expected: {len(expected_matches)} files, Found: {len(result_file_ids)} files")
            logger.info(f"  Precision: {precision:.4f}, Recall: {recall:.4f}, F1: {f1_score:.4f}")
        
        # Calculate aggregate metrics
        aggregate_metrics = self._calculate_aggregate_metrics(results)
        
        # Store overall test results
        self.test_results[activity_type] = {
            "queries": queries,
            "results": results,
            "aggregate_metrics": aggregate_metrics
        }
        
        # Return combined results
        return {
            "activity_type": activity_type,
            "queries": queries,
            "results": results,
            "aggregate_metrics": aggregate_metrics
        }
    
    def _calculate_aggregate_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate aggregate metrics across all query results.
        
        Args:
            results: Dictionary of query results
            
        Returns:
            Dictionary with aggregate statistics
        """
        if not results:
            return {
                "avg_precision": 0.0,
                "avg_recall": 0.0,
                "avg_f1_score": 0.0,
                "median_precision": 0.0,
                "median_recall": 0.0,
                "median_f1_score": 0.0,
                "std_dev_f1": 0.0,
                "avg_execution_time_ms": 0.0
            }
        
        # Extract metrics from results
        precision_values = [r["precision"] for r in results.values()]
        recall_values = [r["recall"] for r in results.values()]
        f1_values = [r["f1_score"] for r in results.values()]
        execution_times = [r["execution_time_ms"] for r in results.values()]
        
        # Calculate aggregate statistics
        import statistics
        
        avg_precision = sum(precision_values) / len(precision_values)
        avg_recall = sum(recall_values) / len(recall_values)
        avg_f1 = sum(f1_values) / len(f1_values)
        
        median_precision = statistics.median(precision_values)
        median_recall = statistics.median(recall_values)
        median_f1 = statistics.median(f1_values)
        
        std_dev_f1 = statistics.stdev(f1_values) if len(f1_values) > 1 else 0.0
        avg_execution_time = sum(execution_times) / len(execution_times)
        
        return {
            "avg_precision": avg_precision,
            "avg_recall": avg_recall,
            "avg_f1_score": avg_f1,
            "median_precision": median_precision,
            "median_recall": median_recall,
            "median_f1_score": median_f1,
            "std_dev_f1": std_dev_f1,
            "avg_execution_time_ms": avg_execution_time
        }
    
    def save_results(self, results: Dict[str, Any], output_file: str = None) -> str:
        """
        Save test results to a file.
        
        Args:
            results: Test results to save
            output_file: Output file path (generated if None)
            
        Returns:
            Path to the output file
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"query_matching_results_{timestamp}.json"
        
        # Save results to file
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {output_file}")
        return output_file
    
    def load_results(self, input_file: str) -> Dict[str, Any]:
        """
        Load test results from a file.
        
        Args:
            input_file: Input file path
            
        Returns:
            Loaded test results
        """
        with open(input_file, "r") as f:
            results = json.load(f)
        
        logger.info(f"Results loaded from {input_file}")
        return results
    
    def print_summary(self, results: Dict[str, Any]) -> None:
        """
        Print a summary of test results.
        
        Args:
            results: Test results to summarize
        """
        activity_type = results["activity_type"]
        aggregate_metrics = results["aggregate_metrics"]
        
        print("\n" + "="*80)
        print(f"QUERY MATCHING TEST RESULTS: {activity_type.upper()} ACTIVITY")
        print("="*80)
        
        print("\nAggregate Metrics:")
        print(f"  Average Precision:   {aggregate_metrics['avg_precision']:.4f}")
        print(f"  Average Recall:      {aggregate_metrics['avg_recall']:.4f}")
        print(f"  Average F1 Score:    {aggregate_metrics['avg_f1_score']:.4f}")
        print(f"  Median F1 Score:     {aggregate_metrics['median_f1_score']:.4f}")
        print(f"  Std Dev F1 Score:    {aggregate_metrics['std_dev_f1']:.4f}")
        print(f"  Avg Execution Time:  {aggregate_metrics['avg_execution_time_ms']:.2f} ms")
        
        print("\nIndividual Query Results:")
        for query, result in results["results"].items():
            print(f"\nQuery: {query}")
            print(f"  Precision: {result['precision']:.4f}")
            print(f"  Recall:    {result['recall']:.4f}")
            print(f"  F1 Score:  {result['f1_score']:.4f}")
            print(f"  Expected Matches: {len(result['truth_set'])}")
            print(f"  Found Matches:    {len(result['result_set'])}")
            print(f"  True Positives:   {result['true_positives']}")
            print(f"  False Positives:  {result['false_positives']}")
            print(f"  False Negatives:  {result['false_negatives']}")
        
        print("\nCONCLUSION:")
        
        # Determine if the pipeline is working effectively
        effective = aggregate_metrics['avg_precision'] > 0.7 and aggregate_metrics['avg_recall'] > 0.7
        
        if effective:
            print("  The query processing pipeline is working effectively.")
            print(f"  With an average precision of {aggregate_metrics['avg_precision']:.4f} and")
            print(f"  recall of {aggregate_metrics['avg_recall']:.4f}, the pipeline is successfully")
            print("  finding the expected matches for most queries.")
        else:
            print("  The query processing pipeline needs improvement.")
            if aggregate_metrics['avg_precision'] < 0.7:
                print(f"  The low precision ({aggregate_metrics['avg_precision']:.4f}) indicates too many false positives.")
            if aggregate_metrics['avg_recall'] < 0.7:
                print(f"  The low recall ({aggregate_metrics['avg_recall']:.4f}) indicates many expected matches are missed.")
            print("  The pipeline may need more sophisticated matching algorithms or better metadata.")
        
        print("\n" + "="*80)

def main():
    """Main function."""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Test query matching effectiveness against synthetic metadata")
    parser.add_argument(
        "--activity-type",
        type=str,
        default="location",
        choices=["location", "task", "music", "collaboration", "storage", "media"],
        help="Activity type to test (default: location)"
    )
    parser.add_argument(
        "--query-count",
        type=int,
        default=5,
        help="Number of queries to test (default: 5)"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Output file for results (default: auto-generated)"
    )
    parser.add_argument(
        "--load-results",
        type=str,
        default=None,
        help="Load results from file instead of running test"
    )
    args = parser.parse_args()
    
    try:
        # Initialize test
        test = QueryMatchingTest()
        
        # Either load existing results or run new test
        if args.load_results:
            results = test.load_results(args.load_results)
        else:
            # Run query processing test
            results = test.test_query_processing(
                activity_type=args.activity_type,
                query_count=args.query_count
            )
            
            # Save results
            test.save_results(results, args.output_file)
        
        # Print summary
        test.print_summary(results)
        
    except Exception as e:
        logger.error(f"Error testing query matching: {e}", exc_info=True)
        import sys
        sys.exit(1)

if __name__ == "__main__":
    main()