#!/usr/bin/env python3
"""
Enhanced test data generator for ablation testing with stronger dependencies.

This script creates synthetic data specifically designed to demonstrate 
the impact of activity data ablation on query results by creating stronger
dependencies between activity collections and object matching.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import os
import sys
import uuid
import random
import logging
import datetime
import argparse
import json
import base64
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

# Set up path
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import Indaleko modules
from db.db_config import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from utils.misc.data_management import encode_binary_data


class TruthDataTracker:
    """Tracks ground truth for ablation testing."""

    def __init__(self, output_dir: str = "./ablation_results"):
        """Initialize the truth data tracker.
        
        Args:
            output_dir: Directory to save truth data
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        self.truth_data = {
            "positive_examples": {},  # Query -> list of document IDs that should match
            "negative_examples": {},  # Query -> list of document IDs that should not match
            "activity_dependency": {},  # Document ID -> {collection: bool} - whether this doc depends on activity data
            "metadata": {
                "timestamp": datetime.datetime.now().isoformat(),
                "total_positive": 0,
                "total_negative": 0
            }
        }
    
    def add_positive_example(self, query: str, doc_id: str):
        """Add a positive example (document that should match the query).
        
        Args:
            query: The query this document should match
            doc_id: The document ID
        """
        if query not in self.truth_data["positive_examples"]:
            self.truth_data["positive_examples"][query] = []
        
        self.truth_data["positive_examples"][query].append(doc_id)
        self.truth_data["metadata"]["total_positive"] += 1
    
    def add_negative_example(self, query: str, doc_id: str):
        """Add a negative example (document that should not match the query).
        
        Args:
            query: The query this document should not match
            doc_id: The document ID
        """
        if query not in self.truth_data["negative_examples"]:
            self.truth_data["negative_examples"][query] = []
        
        self.truth_data["negative_examples"][query].append(doc_id)
        self.truth_data["metadata"]["total_negative"] += 1
    
    def set_activity_dependency(self, doc_id: str, collection: str, depends: bool):
        """Mark whether a document depends on activity data from a specific collection.
        
        Args:
            doc_id: The document ID
            collection: The collection name
            depends: Whether the document depends on this collection to match
        """
        if doc_id not in self.truth_data["activity_dependency"]:
            self.truth_data["activity_dependency"][doc_id] = {}
        
        self.truth_data["activity_dependency"][doc_id][collection] = depends
    
    def save(self):
        """Save the truth data to a file."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(self.output_dir, f"truth_data_{timestamp}.json")
        
        with open(output_path, 'w') as f:
            json.dump(self.truth_data, f, indent=2, default=str)
        
        logging.info(f"Truth data saved to {output_path}")
        
        # Also save a readable summary
        summary_path = os.path.join(self.output_dir, f"truth_summary_{timestamp}.txt")
        
        with open(summary_path, 'w') as f:
            f.write("Ablation Test Truth Data Summary\n")
            f.write("==============================\n\n")
            f.write(f"Generated: {timestamp}\n")
            f.write(f"Total positive examples: {self.truth_data['metadata']['total_positive']}\n")
            f.write(f"Total negative examples: {self.truth_data['metadata']['total_negative']}\n\n")
            
            f.write("Query Distribution:\n")
            for query in self.truth_data["positive_examples"]:
                positive_count = len(self.truth_data["positive_examples"].get(query, []))
                negative_count = len(self.truth_data["negative_examples"].get(query, []))
                f.write(f"  '{query}':\n")
                f.write(f"    Positive examples: {positive_count}\n")
                f.write(f"    Negative examples: {negative_count}\n")
                
                # Count activity dependencies
                music_deps = 0
                geo_deps = 0
                for doc_id in self.truth_data["positive_examples"].get(query, []):
                    if doc_id in self.truth_data["activity_dependency"]:
                        deps = self.truth_data["activity_dependency"][doc_id]
                        if deps.get(IndalekoDBCollections.Indaleko_MusicActivityData_Collection, False):
                            music_deps += 1
                        if deps.get(IndalekoDBCollections.Indaleko_GeoActivityData_Collection, False):
                            geo_deps += 1
                
                f.write(f"    Music dependencies: {music_deps}/{positive_count}\n")
                f.write(f"    Geo dependencies: {geo_deps}/{positive_count}\n")
        
        logging.info(f"Truth summary saved to {summary_path}")
        return output_path


def generate_file_metadata(
    query: str, 
    is_positive: bool,
    file_index: int,
    activity_dependent: bool = False,
    activity_type: str = None
) -> Dict[str, Any]:
    """Generate file metadata for ablation testing.
    
    Args:
        query: The query to generate examples for
        is_positive: Whether this is a positive or negative example
        file_index: Index for file naming
        activity_dependent: Whether this file's matching depends on activity data
        activity_type: Type of activity dependency ("music", "geo", or None)
        
    Returns:
        A dictionary with the file metadata
    """
    # Extract keywords from query to determine what types of files to generate
    query_lower = query.lower()
    object_id = str(uuid.uuid4())
    
    # Default file types - we'll update based on query
    file_types = ["pdf", "docx", "txt", "xlsx", "pptx", "jpg", "png", "html"]
    file_activities = ["opened", "created", "modified", "shared", "deleted"]
    applications = ["Microsoft Word", "Microsoft Excel", "Microsoft PowerPoint", 
                   "Adobe Reader", "VSCode", "Chrome", "Firefox", "Safari"]
    locations = ["home", "office", "Seattle", "Portland", "San Francisco", "New York"]
    
    # Adjust file types based on query
    if "pdf" in query_lower:
        file_types = ["pdf"]
    elif "excel" in query_lower:
        file_types = ["xlsx"]
    elif "word" in query_lower:
        file_types = ["docx"]
    elif "presentation" in query_lower:
        file_types = ["pptx"]
    
    # Determine time frame based on query
    now = datetime.datetime.now(datetime.timezone.utc)
    if "yesterday" in query_lower:
        time_range = (now - datetime.timedelta(days=1), now)
    elif "last week" in query_lower:
        time_range = (now - datetime.timedelta(days=7), now)
    elif "last month" in query_lower:
        time_range = (now - datetime.timedelta(days=30), now)
    else:
        time_range = (now - datetime.timedelta(days=14), now)
    
    # Determine location if specified
    location = None
    for loc in locations:
        if loc.lower() in query_lower:
            location = loc
    
    # Determine activity if specified
    activity = None
    for act in file_activities:
        if act in query_lower:
            activity = act
    
    # Determine application if specified
    application = None
    for app in applications:
        if app.lower() in query_lower:
            application = app
    
    # Generate file type and object identifier
    file_type = random.choice(file_types)
    
    # Determine whether to use matching criteria
    # For activity-dependent files, we deliberately withhold the direct matching criteria
    # so they only match when activity data is present
    use_direct_match = is_positive and not activity_dependent
    
    # For positive examples: use dates within the time range
    # For negative examples: use dates outside the time range
    if use_direct_match:
        # This will directly match without activity data
        created_at = random.uniform(time_range[0].timestamp(), time_range[1].timestamp())
        created_date = datetime.datetime.fromtimestamp(created_at, datetime.timezone.utc)
        
        modified_at = random.uniform(created_date.timestamp(), time_range[1].timestamp())
        modified_date = datetime.datetime.fromtimestamp(modified_at, datetime.timezone.utc)
        
        accessed_at = random.uniform(modified_date.timestamp(), time_range[1].timestamp())
        accessed_date = datetime.datetime.fromtimestamp(accessed_at, datetime.timezone.utc)
        
        file_path = f"/Test/DirectMatch"
        file_name = f"direct_match_{file_index}.{file_type}"
    elif is_positive:
        # This is a positive example that depends on activity data
        # Use dates within range but don't add other matching criteria
        created_at = random.uniform(time_range[0].timestamp(), time_range[1].timestamp())
        created_date = datetime.datetime.fromtimestamp(created_at, datetime.timezone.utc)
        
        modified_at = random.uniform(created_date.timestamp(), time_range[1].timestamp())
        modified_date = datetime.datetime.fromtimestamp(modified_at, datetime.timezone.utc)
        
        accessed_at = random.uniform(modified_date.timestamp(), time_range[1].timestamp())
        accessed_date = datetime.datetime.fromtimestamp(accessed_at, datetime.timezone.utc)
        
        file_path = f"/Test/ActivityDependent"
        file_name = f"activity_dependent_{file_index}.{file_type}"
    else:
        # Use dates outside the query's time range for negative examples
        outside_range_date = time_range[0] - datetime.timedelta(days=random.randint(15, 30))
        created_date = outside_range_date
        modified_date = outside_range_date
        accessed_date = outside_range_date
        
        file_path = f"/Test/Negatives"
        file_name = f"neg_file_{file_index}.{file_type}"
    
    # Semantic attributes mapping to standard UUIDs
    file_size = random.randint(1000, 10000000)
    
    # Standard semantic attribute UUIDs
    filename_uuid = "701af169-b044-4877-8bcf-0cd21ed3172f"  # File name
    filepath_uuid = "1ef8c7e3-2527-4435-b485-22f549dafaf3"  # File path
    filesize_uuid = "966d0b9b-90a9-4781-95b8-cbf141399511"  # File size
    filetype_uuid = "f93c9f59-0cc7-4628-89dc-9f0c686d81e7"  # File type
    mimetype_uuid = "f71ee08f-a5ae-4d75-9794-fb30330b3ce7"  # MIME type
    
    # Create MIME type based on file extension
    mime_type = {
        "pdf": "application/pdf", 
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "jpg": "image/jpeg",
        "png": "image/png",
        "html": "text/html",
        "txt": "text/plain"
    }.get(file_type, "application/octet-stream")
    
    # Create timestamps
    timestamps = [
        {
            "Label": str(uuid.uuid4()),
            "Value": created_date.isoformat(),
            "Description": "Created"
        },
        {
            "Label": str(uuid.uuid4()),
            "Value": modified_date.isoformat(),
            "Description": "Modified"
        },
        {
            "Label": str(uuid.uuid4()),
            "Value": accessed_date.isoformat(),
            "Description": "Accessed"
        }
    ]
    
    # Create basic semantic attributes
    semantic_attributes = [
        {"Identifier": filename_uuid, "Value": file_name},
        {"Identifier": filepath_uuid, "Value": file_path},
        {"Identifier": filesize_uuid, "Value": file_size},
        {"Identifier": filetype_uuid, "Value": file_type},
        {"Identifier": mimetype_uuid, "Value": mime_type}
    ]
    
    # Only add direct matching criteria for non-activity-dependent files
    if use_direct_match:
        # Add location if relevant (with made-up but consistent UUID)
        location_uuid = "6bcb0a8b-28c8-47d2-a7e6-d910f717694a"
        if location and "location" in query_lower:
            semantic_attributes.append({"Identifier": location_uuid, "Value": location})
        
        # Add application if relevant (with made-up but consistent UUID)
        application_uuid = "7a32a229-54b1-460e-86be-5ea421f1fcad"
        if application:
            semantic_attributes.append({"Identifier": application_uuid, "Value": application})
        
        # Add activity-specific attributes (with made-up but consistent UUID)
        activity_uuid = "2f8e3d10-49e7-4c7f-bd15-5fc8e85d8039"
        if activity:
            semantic_attributes.append({"Identifier": activity_uuid, "Value": activity})
        
        # Add meeting-related attributes if in query (with made-up but consistent UUID)
        meeting_uuid = "3e88a0d5-b642-4cb1-a818-7fcd5e9e7b1c"
        if "meeting" in query_lower:
            meeting_type = "COVID" if "covid" in query_lower else "quarterly"
            semantic_attributes.append({"Identifier": meeting_uuid, "Value": meeting_type})
        
        # Add sharing-related attributes if in query (with made-up but consistent UUID)
        sharing_uuid = "4f99b0e2-c357-4d82-b91c-8d9e7a6a192d"
        if "shared" in query_lower or "share" in query_lower:
            semantic_attributes.append({"Identifier": sharing_uuid, "Value": True})
    
    # For negative examples, add opposite criteria
    if not is_positive:
        # If query asks for a specific location, add a different one
        location_uuid = "6bcb0a8b-28c8-47d2-a7e6-d910f717694a"
        if location and "location" in query_lower:
            wrong_locations = [loc for loc in locations if loc != location]
            semantic_attributes.append({"Identifier": location_uuid, "Value": random.choice(wrong_locations)})
        
        # If query asks for a specific application, add a different one
        application_uuid = "7a32a229-54b1-460e-86be-5ea421f1fcad"
        if application:
            wrong_apps = [app for app in applications if app != application]
            semantic_attributes.append({"Identifier": application_uuid, "Value": random.choice(wrong_apps)})
    
    # Create the record with source identifier
    record = {
        "SourceIdentifier": {
            "Identifier": str(uuid.uuid4()),
            "Version": "1.0",
            "Description": "Generated by enhanced ablation test data generator"
        },
        "Timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "Data": encode_binary_data(b"x")
    }
    
    # Create the file metadata object in dictionary form
    file_obj = {
        "_key": object_id,
        "Record": record,
        "URI": f"file://{file_path}/{file_name}_{object_id}",  # Make URI unique
        "ObjectIdentifier": object_id,
        "Timestamps": timestamps,
        "Size": file_size,
        "SemanticAttributes": semantic_attributes,
        "Label": file_name,
        "LocalPath": file_path,
        "LocalIdentifier": str(random.randint(1000000000, 9999999999)),
        "PosixFileAttributes": "S_IFREG",
        "WindowsFileAttributes": None,
        # Add debug fields to help with analysis
        "_debug": {
            "is_positive": is_positive,
            "activity_dependent": activity_dependent,
            "activity_type": activity_type,
            "query": query
        }
    }
    
    return file_obj


def generate_enhanced_test_data(
    query: str, 
    positive_count: int = 10, 
    negative_count: int = 40,
    direct_match_pct: float = 0.5,  # Percentage of positive examples that directly match (no activity dependency)
    music_pct: float = 0.25,        # Percentage of activity-dependent examples that depend on music
    geo_pct: float = 0.25           # Percentage of activity-dependent examples that depend on geo
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Generate enhanced test data with activity dependencies.
    
    Args:
        query: The query to generate data for
        positive_count: Number of positive examples
        negative_count: Number of negative examples
        direct_match_pct: Percentage of positive examples that match without activity data
        music_pct: Percentage of activity-dependent examples that depend on music
        geo_pct: Percentage of activity-dependent examples that depend on geo
        
    Returns:
        Tuple of (direct_match_files, music_dependent_files, geo_dependent_files, negative_files)
    """
    direct_match_files = []
    music_dependent_files = []
    geo_dependent_files = []
    negative_files = []
    
    # Calculate counts based on percentages
    direct_match_count = int(positive_count * direct_match_pct)
    activity_dependent_count = positive_count - direct_match_count
    
    music_dependent_count = int(activity_dependent_count * music_pct / (music_pct + geo_pct))
    geo_dependent_count = activity_dependent_count - music_dependent_count
    
    # Generate direct match files (match without activity data)
    for i in range(direct_match_count):
        file_obj = generate_file_metadata(
            query=query,
            is_positive=True,
            file_index=i,
            activity_dependent=False,
            activity_type=None
        )
        direct_match_files.append(file_obj)
    
    # Generate music-dependent files
    for i in range(music_dependent_count):
        file_obj = generate_file_metadata(
            query=query,
            is_positive=True,
            file_index=i,
            activity_dependent=True,
            activity_type="music"
        )
        music_dependent_files.append(file_obj)
    
    # Generate geo-dependent files
    for i in range(geo_dependent_count):
        file_obj = generate_file_metadata(
            query=query,
            is_positive=True,
            file_index=i,
            activity_dependent=True,
            activity_type="geo"
        )
        geo_dependent_files.append(file_obj)
    
    # Generate negative files
    for i in range(negative_count):
        file_obj = generate_file_metadata(
            query=query,
            is_positive=False,
            file_index=i,
            activity_dependent=False
        )
        negative_files.append(file_obj)
    
    return direct_match_files, music_dependent_files, geo_dependent_files, negative_files


def generate_music_activity_data(
    files: List[Dict[str, Any]], 
    query: str
) -> List[Dict[str, Any]]:
    """Generate music activity data linked to files.
    
    Args:
        files: List of files to link activity data to
        query: The query being tested
        
    Returns:
        List of music activity records
    """
    music_activities = []
    query_lower = query.lower()
    
    # Define some music metadata for generation
    artists = ["The Beatles", "Taylor Swift", "Beyoncé", "BTS", "Drake", "Adele"]
    songs = ["Bohemian Rhapsody", "Shake It Off", "Single Ladies", "Dynamite", "God's Plan", "Hello"]
    albums = ["Abbey Road", "1989", "Lemonade", "Map of the Soul", "Scorpion", "25"]
    
    # Music query keywords
    music_keywords = ["music", "spotify", "song", "artist", "album", "playlist"]
    is_music_query = any(keyword in query_lower for keyword in music_keywords)
    
    # Create one activity record per file
    for file in files:
        activity_id = str(uuid.uuid4())
        file_id = file["_key"]
        
        # Base activity timestamp around file modification time
        file_modified = None
        for ts in file["Timestamps"]:
            if ts["Description"] == "Modified":
                file_modified = ts["Value"]
                break
        
        if file_modified is None:
            file_modified = datetime.datetime.now(datetime.timezone.utc).isoformat()
        else:
            # Convert string to datetime if needed
            if isinstance(file_modified, str):
                file_modified = datetime.datetime.fromisoformat(file_modified)
                
        # If it's a datetime, add time delta
        if isinstance(file_modified, datetime.datetime):
            activity_time = file_modified + datetime.timedelta(minutes=random.randint(-30, 30))
        else:
            # Fallback
            activity_time = datetime.datetime.now(datetime.timezone.utc)
            
        # Generate app name based on query
        app_name = "Spotify" if "spotify" in query_lower else random.choice(["Spotify", "Apple Music", "YouTube Music"])
        
        # Create music-specific semantic attributes
        semantic_attributes = []
        
        # Activity type
        activity_type_uuid = "b4a2a6b8-1c7d-42d9-8f8e-6d9e48a5b3c7"
        semantic_attributes.append({"Identifier": activity_type_uuid, "Value": "MUSIC"})
        
        # Application
        app_uuid = "7a32a229-54b1-460e-86be-5ea421f1fcad"
        semantic_attributes.append({"Identifier": app_uuid, "Value": app_name})
        
        # Timestamp
        timestamp_uuid = "a8c3d4e5-f6g7-h8i9-j0k1-l2m3n4o5p6q7"
        semantic_attributes.append({"Identifier": timestamp_uuid, "Value": activity_time.isoformat()})
        
        # Artist
        artist_uuid = "r8s9t0u1-v2w3-x4y5-z6a7-b8c9d0e1f2g3"
        artist = random.choice(artists)
        semantic_attributes.append({"Identifier": artist_uuid, "Value": artist})
        
        # Song
        song_uuid = "h3i4j5k6-l7m8-n9o0-p1q2-r3s4t5u6v7w8"
        song = random.choice(songs)
        semantic_attributes.append({"Identifier": song_uuid, "Value": song})
        
        # Album
        album_uuid = "x8y9z0a1-b2c3-d4e5-f6g7-h8i9j0k1l2m3"
        album = random.choice(albums)
        semantic_attributes.append({"Identifier": album_uuid, "Value": album})
        
        # If this is a music query, add the exact matching criteria from the query
        # This creates the dependency - without this record, the file won't match
        if is_music_query:
            # Add specific attribute for music
            music_match_uuid = "m4n5o6p7-q8r9-s0t1-u2v3-w4x5y6z7a8b9"
            semantic_attributes.append({"Identifier": music_match_uuid, "Value": True})
            
            # If the query mentions Spotify specifically
            if "spotify" in query_lower:
                spotify_uuid = "c4d5e6f7-g8h9-i0j1-k2l3-m4n5o6p7q8r9"
                semantic_attributes.append({"Identifier": spotify_uuid, "Value": "Spotify"})
                
                # Ensure app name is Spotify
                for attr in semantic_attributes:
                    if attr["Identifier"] == app_uuid:
                        attr["Value"] = "Spotify"
                        break
            
            # If the query mentions sharing
            if "shared" in query_lower or "share" in query_lower:
                sharing_uuid = "4f99b0e2-c357-4d82-b91c-8d9e7a6a192d"
                semantic_attributes.append({"Identifier": sharing_uuid, "Value": True})
        
        # Create the record
        record = {
            "SourceIdentifier": {
                "Identifier": str(uuid.uuid4()),
                "Version": "1.0",
                "Description": "Generated by ablation test data generator"
            },
            "Timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "Data": encode_binary_data(b"x")
        }
        
        # Create the activity data in dictionary form
        activity = {
            "_key": activity_id,
            "ObjectId": file_id,
            "Record": record,
            "Timestamp": activity_time.isoformat(),
            "SemanticAttributes": semantic_attributes,
            # Add debug info
            "_debug": {
                "is_music_query": is_music_query,
                "query": query
            }
        }
        
        # Add to the list
        music_activities.append(activity)
    
    return music_activities


def generate_geo_activity_data(
    files: List[Dict[str, Any]], 
    query: str
) -> List[Dict[str, Any]]:
    """Generate geo activity data linked to files.
    
    Args:
        files: List of files to link activity data to
        query: The query being tested
        
    Returns:
        List of geo activity records
    """
    geo_activities = []
    query_lower = query.lower()
    
    # Location data
    locations = {
        "home": {"lat": 47.6062, "long": -122.3321, "address": "123 Home St, Seattle, WA"},
        "office": {"lat": 47.6149, "long": -122.1941, "address": "456 Office Ave, Redmond, WA"},
        "seattle": {"lat": 47.6062, "long": -122.3321, "address": "Downtown Seattle, WA"},
        "portland": {"lat": 45.5152, "long": -122.6784, "address": "Portland, OR"},
        "san francisco": {"lat": 37.7749, "long": -122.4194, "address": "San Francisco, CA"},
        "new york": {"lat": 40.7128, "long": -74.0060, "address": "New York, NY"}
    }
    
    # Geo query keywords
    geo_keywords = ["location", "home", "office", "seattle", "portland", "san francisco", "new york"]
    is_geo_query = any(keyword in query_lower for keyword in geo_keywords)
    
    # Find target location from query
    target_location = None
    for loc in locations.keys():
        if loc in query_lower:
            target_location = loc
            break
    
    # Default to home if no location specified in a geo query
    if target_location is None and is_geo_query:
        target_location = "home"
    
    # Create one activity record per file
    for file in files:
        activity_id = str(uuid.uuid4())
        file_id = file["_key"]
        
        # Base activity timestamp around file modification time
        file_modified = None
        for ts in file["Timestamps"]:
            if ts["Description"] == "Modified":
                file_modified = ts["Value"]
                break
        
        if file_modified is None:
            file_modified = datetime.datetime.now(datetime.timezone.utc).isoformat()
        else:
            # Convert string to datetime if needed
            if isinstance(file_modified, str):
                file_modified = datetime.datetime.fromisoformat(file_modified)
                
        # If it's a datetime, add time delta
        if isinstance(file_modified, datetime.datetime):
            activity_time = file_modified + datetime.timedelta(minutes=random.randint(-30, 30))
        else:
            # Fallback
            activity_time = datetime.datetime.now(datetime.timezone.utc)
            
        # For geo query, use target location
        # For non-geo query, use random location
        if is_geo_query and target_location:
            location_key = target_location
        else:
            location_key = random.choice(list(locations.keys()))
            
        location_data = locations[location_key]
        
        # Add some randomness to location coordinates
        lat = location_data["lat"] + random.uniform(-0.01, 0.01)
        long = location_data["long"] + random.uniform(-0.01, 0.01)
        
        # Create location-specific semantic attributes
        semantic_attributes = []
        
        # Activity type
        activity_type_uuid = "b4a2a6b8-1c7d-42d9-8f8e-6d9e48a5b3c7"
        semantic_attributes.append({"Identifier": activity_type_uuid, "Value": "LOCATION"})
        
        # Timestamp
        timestamp_uuid = "a8c3d4e5-f6g7-h8i9-j0k1-l2m3n4o5p6q7"
        semantic_attributes.append({"Identifier": timestamp_uuid, "Value": activity_time.isoformat()})
        
        # Location name
        location_uuid = "6bcb0a8b-28c8-47d2-a7e6-d910f717694a"
        semantic_attributes.append({"Identifier": location_uuid, "Value": location_key})
        
        # Latitude
        lat_uuid = "n3o4p5q6-r7s8-t9u0-v1w2-x3y4z5a6b7c8"
        semantic_attributes.append({"Identifier": lat_uuid, "Value": lat})
        
        # Longitude
        long_uuid = "d8e9f0g1-h2i3-j4k5-l6m7-n8o9p0q1r2s3"
        semantic_attributes.append({"Identifier": long_uuid, "Value": long})
        
        # Address
        address_uuid = "t3u4v5w6-x7y8-z9a0-b1c2-d3e4f5g6h7i8"
        semantic_attributes.append({"Identifier": address_uuid, "Value": location_data["address"]})
        
        # If this is a geo query, add the exact matching criteria from the query
        # This creates the dependency - without this record, the file won't match
        if is_geo_query:
            # Add specific attribute for location match
            location_match_uuid = "g4h5i6j7-k8l9-m0n1-o2p3-q4r5s6t7u8v9"
            semantic_attributes.append({"Identifier": location_match_uuid, "Value": True})
            
            # If query mentions a specific location, make sure it matches
            if target_location:
                # Ensure location name matches target
                for attr in semantic_attributes:
                    if attr["Identifier"] == location_uuid:
                        attr["Value"] = target_location
                        break
        
        # Create the record
        record = {
            "SourceIdentifier": {
                "Identifier": str(uuid.uuid4()),
                "Version": "1.0",
                "Description": "Generated by ablation test data generator"
            },
            "Timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "Data": encode_binary_data(b"x")
        }
        
        # Create the activity data in dictionary form
        activity = {
            "_key": activity_id,
            "ObjectId": file_id,
            "Record": record,
            "Timestamp": activity_time.isoformat(),
            "SemanticAttributes": semantic_attributes,
            # Add debug info
            "_debug": {
                "is_geo_query": is_geo_query,
                "target_location": target_location,
                "query": query
            }
        }
        
        # Add to the list
        geo_activities.append(activity)
    
    return geo_activities


def generate_test_data_for_all_queries(
    db_config: IndalekoDBConfig, 
    test_queries: List[str], 
    dataset_params: Dict[str, Any], 
    tracker: TruthDataTracker
) -> bool:
    """Generate test data for all queries.
    
    Args:
        db_config: Database configuration
        test_queries: List of test queries
        dataset_params: Parameters for data generation
        tracker: Truth data tracker
        
    Returns:
        True if successful, False otherwise
    """
    try:
        db = db_config.get_arangodb()
        
        # Get collection handles
        object_collection_name = IndalekoDBCollections.Indaleko_Object_Collection
        music_collection_name = IndalekoDBCollections.Indaleko_MusicActivityData_Collection
        geo_collection_name = IndalekoDBCollections.Indaleko_GeoActivityData_Collection
        
        object_collection = db.collection(object_collection_name)
        
        # Create music and geo collections if they don't exist
        if not db.has_collection(music_collection_name):
            logging.info(f"Creating collection: {music_collection_name}")
            db.create_collection(music_collection_name)
        
        if not db.has_collection(geo_collection_name):
            logging.info(f"Creating collection: {geo_collection_name}")
            db.create_collection(geo_collection_name)
        
        music_collection = db.collection(music_collection_name)
        geo_collection = db.collection(geo_collection_name)
        
        # Validate collection access
        if object_collection is None:
            logging.error(f"Could not find collection: {object_collection_name}")
            return False
        
        if music_collection is None:
            logging.error(f"Could not find collection: {music_collection_name}")
            return False
        
        if geo_collection is None:
            logging.error(f"Could not find collection: {geo_collection_name}")
            return False
        
        # Default parameters
        positive_count = dataset_params.get("positive_count", 10)
        negative_count = dataset_params.get("negative_count", 40)
        direct_match_pct = dataset_params.get("direct_match_pct", 0.5)
        music_pct = dataset_params.get("music_pct", 0.25)
        geo_pct = dataset_params.get("geo_pct", 0.25)
        batch_size = dataset_params.get("batch_size", 50)
        
        # Process each query
        for query in test_queries:
            logging.info(f"Generating test data for query: {query}")
            
            # Generate enhanced test data with activity dependencies
            direct_match_files, music_dependent_files, geo_dependent_files, negative_files = (
                generate_enhanced_test_data(
                    query, 
                    positive_count,
                    negative_count,
                    direct_match_pct,
                    music_pct,
                    geo_pct
                )
            )
            
            # Log the breakdown
            logging.info(f"Generated file breakdown for '{query}':")
            logging.info(f"  Direct match files: {len(direct_match_files)}")
            logging.info(f"  Music-dependent files: {len(music_dependent_files)}")
            logging.info(f"  Geo-dependent files: {len(geo_dependent_files)}")
            logging.info(f"  Negative files: {len(negative_files)}")
            
            # Combine all positive files for tracking
            positive_files = direct_match_files + music_dependent_files + geo_dependent_files
            
            # Upload files to database and track them
            all_files = positive_files + negative_files
            
            # Process in batches
            for i in range(0, len(all_files), batch_size):
                batch = all_files[i:i+batch_size]
                try:
                    # Insert as a batch
                    object_collection.import_bulk(batch, on_duplicate="update")
                    
                    # Track each file
                    for file in batch:
                        file_id = file["_key"]
                        is_positive = file.get("_debug", {}).get("is_positive", False)
                        
                        if is_positive:
                            tracker.add_positive_example(query, file_id)
                        else:
                            tracker.add_negative_example(query, file_id)
                            
                        # Track activity dependencies
                        activity_dependent = file.get("_debug", {}).get("activity_dependent", False)
                        activity_type = file.get("_debug", {}).get("activity_type", None)
                        
                        if activity_dependent:
                            if activity_type == "music":
                                tracker.set_activity_dependency(file_id, music_collection_name, True)
                                tracker.set_activity_dependency(file_id, geo_collection_name, False)
                            elif activity_type == "geo":
                                tracker.set_activity_dependency(file_id, music_collection_name, False)
                                tracker.set_activity_dependency(file_id, geo_collection_name, True)
                except Exception as e:
                    logging.error(f"Error inserting file batch: {e}")
            
            # Generate and upload music activity data
            music_activities = []
            
            # Generate music activity for all music-dependent files
            music_activities.extend(generate_music_activity_data(music_dependent_files, query))
            
            # Also generate some music activity for direct match files (no dependency)
            music_activities.extend(generate_music_activity_data(direct_match_files, query))
            
            # Process music activities in batches
            for i in range(0, len(music_activities), batch_size):
                batch = music_activities[i:i+batch_size]
                try:
                    music_collection.import_bulk(batch, on_duplicate="update")
                except Exception as e:
                    logging.error(f"Error inserting music activity batch: {e}")
            
            # Generate and upload geo activity data
            geo_activities = []
            
            # Generate geo activity for all geo-dependent files
            geo_activities.extend(generate_geo_activity_data(geo_dependent_files, query))
            
            # Also generate some geo activity for direct match files (no dependency)
            geo_activities.extend(generate_geo_activity_data(direct_match_files, query))
            
            # Process geo activities in batches
            for i in range(0, len(geo_activities), batch_size):
                batch = geo_activities[i:i+batch_size]
                try:
                    geo_collection.import_bulk(batch, on_duplicate="update")
                except Exception as e:
                    logging.error(f"Error inserting geo activity batch: {e}")
            
            logging.info(f"Completed data generation for query: {query}")
            logging.info(f"  Uploaded {len(music_activities)} music activities")
            logging.info(f"  Uploaded {len(geo_activities)} geo activities")
        
        # Save truth data
        tracker.save()
        return True
        
    except Exception as e:
        logging.error(f"Error generating ablation test data: {e}")
        import traceback
        traceback.print_exc()
        return False


def setup_logging(level=logging.INFO):
    """Set up logging configuration."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("generate_ablation_data_enhanced.log")
        ]
    )


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Enhanced test data generator for ablation testing')
    parser.add_argument('--positive-count', type=int, default=10,
                      help='Number of positive examples per query (default: 10)')
    parser.add_argument('--negative-count', type=int, default=40,
                      help='Number of negative examples per query (default: 40)')
    parser.add_argument('--direct-match-pct', type=float, default=0.5,
                      help='Percentage of positive examples that match without activity data (default: 0.5)')
    parser.add_argument('--music-pct', type=float, default=0.25,
                      help='Percentage of activity-dependent examples that depend on music (default: 0.25)')
    parser.add_argument('--geo-pct', type=float, default=0.25,
                      help='Percentage of activity-dependent examples that depend on geo (default: 0.25)')
    parser.add_argument('--output-dir', type=str, default="./ablation_results",
                      help='Directory to save results (default: ./ablation_results)')
    parser.add_argument('--reset-db', action='store_true',
                      help='Reset the database before generating data')
    parser.add_argument('--debug', action='store_true',
                      help='Enable debug logging')
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Setup logging
    setup_logging(level=logging.DEBUG if args.debug else logging.INFO)
    logging.info("Starting enhanced ablation test data generation")
    
    # Initialize DB config
    db_config = IndalekoDBConfig()
    
    # Reset database if requested
    if args.reset_db:
        logging.info("Resetting database...")
        try:
            # Using Bash to run Python command to reset the database
            import subprocess
            subprocess.run(["python", "-m", "db.db_config", "reset"], check=True)
            logging.info("Database reset successful")
            
            # Re-initialize the DB config
            db_config = IndalekoDBConfig()
        except Exception as e:
            logging.error(f"Failed to reset database: {e}")
            return 1
    
    # Initialize TruthDataTracker
    tracker = TruthDataTracker(output_dir=args.output_dir)
    
    # Configure test queries - these will be used for ablation testing
    test_queries = [
        "Find all documents I worked on yesterday",
        "Find PDF files I opened in Microsoft Word",
        "Find files I accessed while listening to music",
        "Show me files I edited last week from home",
        "Find documents created in Seattle",
        "Show me Excel files I worked on during the COVID meeting",
        "Show me all files I shared while using Spotify",
        "Find presentations I created for the quarterly meeting"
    ]
    
    # Configure dataset parameters
    dataset_params = {
        "positive_count": args.positive_count,
        "negative_count": args.negative_count,
        "direct_match_pct": args.direct_match_pct,
        "music_pct": args.music_pct,
        "geo_pct": args.geo_pct,
        "output_dir": args.output_dir,
        "batch_size": 50  # Process in batches of 50
    }
    
    # Generate test data for all queries
    success = generate_test_data_for_all_queries(db_config, test_queries, dataset_params, tracker)
    
    if success:
        logging.info("Enhanced test data generation completed successfully")
        
        # Print summary
        direct_match_count = int(args.positive_count * args.direct_match_pct)
        music_dep_count = int((args.positive_count - direct_match_count) * args.music_pct / (args.music_pct + args.geo_pct))
        geo_dep_count = args.positive_count - direct_match_count - music_dep_count
        
        print("\nData Generation Summary:")
        print(f"Generated data for {len(test_queries)} test queries")
        print(f"Each query has:")
        print(f"  {direct_match_count} direct match files (match without activity data)")
        print(f"  {music_dep_count} music-dependent files (require music activity data)")
        print(f"  {geo_dep_count} geo-dependent files (require geo activity data)")
        print(f"  {args.negative_count} negative files (should not match)")
        print(f"\nResults saved to: {args.output_dir}")
        
        # Show expected ablation impact
        print("\nExpected Ablation Impact:")
        print(f"Baseline F1 Score: 1.0")
        print(f"When ablating music collection: Expected F1: {1 - (music_dep_count / args.positive_count):.2f}")
        print(f"When ablating geo collection: Expected F1: {1 - (geo_dep_count / args.positive_count):.2f}")
        print(f"When ablating both: Expected F1: {direct_match_count / args.positive_count:.2f}")
        
        return 0
    else:
        logging.error("Enhanced test data generation failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())