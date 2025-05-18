#!/usr/bin/env python3
"""
Generate test data for ablation testing.

This script generates synthetic data with both positive and negative examples
specifically designed to demonstrate the impact of ablation on query precision and recall.

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
        
        # Also save a summary
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
        
        logging.info(f"Truth summary saved to {summary_path}")
        return output_path


def generate_file_id() -> str:
    """Generate a unique file ID."""
    return str(uuid.uuid4())


def generate_activity_id() -> str:
    """Generate a unique activity ID."""
    return str(uuid.uuid4())


def convert_to_json_serializable(obj: Any) -> Any:
    """Convert an object to a JSON serializable format.
    
    Args:
        obj: The object to convert
        
    Returns:
        A JSON serializable version of the object
    """
    if isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    else:
        return obj


def generate_semantic_attribute(identifier: str, value: Any) -> Dict[str, Any]:
    """Generate a semantic attribute.
    
    Args:
        identifier: The attribute identifier
        value: The attribute value
        
    Returns:
        A semantic attribute dictionary
    """
    return {
        "Identifier": identifier,
        "Value": value
    }


def generate_positive_negative_file_metadata(query: str, positive_count: int, negative_count: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Generate both positive and negative file metadata examples for the given query.
    
    Args:
        query: The query to generate examples for
        positive_count: Number of positive examples to generate
        negative_count: Number of negative examples to generate
        
    Returns:
        A tuple of (positive_examples, negative_examples)
    """
    positive_examples = []
    negative_examples = []
    
    # Extract keywords from query to determine what types of files to generate
    query_lower = query.lower()
    
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
    
    # Generate positive examples that match query criteria
    for i in range(positive_count):
        file_id = generate_file_id()
        file_type = random.choice(file_types)
        
        # Generate creation and modification dates within the time range
        created_at = random.uniform(time_range[0].timestamp(), time_range[1].timestamp())
        created_date = datetime.datetime.fromtimestamp(created_at, datetime.timezone.utc)
        
        modified_at = random.uniform(created_date.timestamp(), time_range[1].timestamp())
        modified_date = datetime.datetime.fromtimestamp(modified_at, datetime.timezone.utc)
        
        accessed_at = random.uniform(modified_date.timestamp(), time_range[1].timestamp())
        accessed_date = datetime.datetime.fromtimestamp(accessed_at, datetime.timezone.utc)
        
        # Create base file metadata
        file_name = f"test_file_{i}.{file_type}"
        file_path = f"/Test/Positives"
        file_size = random.randint(1000, 10000000)
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
        
        # Match Indaleko object schema
        file_metadata = {
            "_key": file_id,
            "URI": f"file://{file_path}/{file_name}",
            "ObjectIdentifier": file_id,
            "Timestamps": [
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
            ],
            "Size": file_size,
            "Record": {
                "SourceIdentifier": {
                    "Identifier": str(uuid.uuid4()),
                    "Version": "1.0",
                    "Description": "Generated by ablation test data generator"
                },
                "Timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "Data": base64.b64encode(b"x").decode('ascii')
            },
            "SemanticAttributes": [],
            "Label": file_name,
            "LocalPath": file_path,
            "LocalIdentifier": str(random.randint(1000000000, 9999999999)),
            "PosixFileAttributes": "S_IFREG",
            "WindowsFileAttributes": None
        }
        
        # Add semantic attributes
        semantic_attributes = []
        
        # File name attribute
        semantic_attributes.append(generate_semantic_attribute(
            "701af169-b044-4877-8bcf-0cd21ed3172f",  # Standard ID for file name
            file_name
        ))
        
        # File path attribute
        semantic_attributes.append(generate_semantic_attribute(
            "1ef8c7e3-2527-4435-b485-22f549dafaf3",  # Standard ID for file path
            file_path
        ))
        
        # File size attribute
        semantic_attributes.append(generate_semantic_attribute(
            "966d0b9b-90a9-4781-95b8-cbf141399511",  # Standard ID for file size
            file_size
        ))
        
        # File extension attribute
        semantic_attributes.append(generate_semantic_attribute(
            "f93c9f59-0cc7-4628-89dc-9f0c686d81e7",  # Standard ID for file extension
            file_type
        ))
        
        # MIME type attribute
        semantic_attributes.append(generate_semantic_attribute(
            "f71ee08f-a5ae-4d75-9794-fb30330b3ce7",  # Standard ID for MIME type
            mime_type
        ))
        
        # Add location if in query
        if location and "location" in query_lower:
            semantic_attributes.append(generate_semantic_attribute(
                "6bcb0a8b-28c8-47d2-a7e6-d910f717694a",  # Made-up ID for location
                location
            ))
        
        # Add application if in query
        if application:
            semantic_attributes.append(generate_semantic_attribute(
                "7a32a229-54b1-460e-86be-5ea421f1fcad",  # Made-up ID for application
                application
            ))
        
        # Add activity-specific attributes
        if activity:
            semantic_attributes.append(generate_semantic_attribute(
                "2f8e3d10-49e7-4c7f-bd15-5fc8e85d8039",  # Made-up ID for activity
                activity
            ))
        
        # Add meeting-related attributes if in query
        if "meeting" in query_lower:
            meeting_type = "COVID" if "covid" in query_lower else "quarterly"
            semantic_attributes.append(generate_semantic_attribute(
                "3e88a0d5-b642-4cb1-a818-7fcd5e9e7b1c",  # Made-up ID for meeting
                meeting_type
            ))
        
        # Add sharing-related attributes if in query
        if "shared" in query_lower or "share" in query_lower:
            semantic_attributes.append(generate_semantic_attribute(
                "4f99b0e2-c357-4d82-b91c-8d9e7a6a192d",  # Made-up ID for shared status
                True
            ))
        
        # Set the semantic attributes on the file metadata
        file_metadata["SemanticAttributes"] = semantic_attributes
        
        positive_examples.append(file_metadata)
    
    # Generate negative examples that don't match query criteria
    for i in range(negative_count):
        file_id = generate_file_id()
        
        # For negative examples, use opposite values from what the query is looking for
        
        # Use file types not in the query
        if len(file_types) < len(["pdf", "docx", "txt", "xlsx", "pptx", "jpg", "png", "html"]):
            neg_file_types = [ft for ft in ["pdf", "docx", "txt", "xlsx", "pptx", "jpg", "png", "html"] if ft not in file_types]
        else:
            neg_file_types = file_types
        
        file_type = random.choice(neg_file_types)
        
        # Use dates outside the query's time range
        outside_range_date = time_range[0] - datetime.timedelta(days=random.randint(15, 30))
        
        # Create base file metadata for negative examples
        file_name = f"neg_file_{i}.{file_type}"
        file_path = f"/Test/Negatives"
        file_size = random.randint(1000, 10000000)
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
        
        # Match Indaleko object schema
        file_metadata = {
            "_key": file_id,
            "URI": f"file://{file_path}/{file_name}",
            "ObjectIdentifier": file_id,
            "Timestamps": [
                {
                    "Label": str(uuid.uuid4()),
                    "Value": outside_range_date.isoformat(),
                    "Description": "Created"
                },
                {
                    "Label": str(uuid.uuid4()),
                    "Value": outside_range_date.isoformat(),
                    "Description": "Modified"
                },
                {
                    "Label": str(uuid.uuid4()),
                    "Value": outside_range_date.isoformat(),
                    "Description": "Accessed"
                }
            ],
            "Size": file_size,
            "Record": {
                "SourceIdentifier": {
                    "Identifier": str(uuid.uuid4()),
                    "Version": "1.0",
                    "Description": "Generated by ablation test data generator"
                },
                "Timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "Data": base64.b64encode(b"x").decode('ascii')
            },
            "SemanticAttributes": [],
            "Label": file_name,
            "LocalPath": file_path,
            "LocalIdentifier": str(random.randint(1000000000, 9999999999)),
            "PosixFileAttributes": "S_IFREG",
            "WindowsFileAttributes": None
        }
        
        # Add negative semantic attributes (not matching query)
        semantic_attributes = []
        
        # File name attribute
        semantic_attributes.append(generate_semantic_attribute(
            "701af169-b044-4877-8bcf-0cd21ed3172f",  # Standard ID for file name
            file_name
        ))
        
        # File path attribute
        semantic_attributes.append(generate_semantic_attribute(
            "1ef8c7e3-2527-4435-b485-22f549dafaf3",  # Standard ID for file path
            file_path
        ))
        
        # File size attribute
        semantic_attributes.append(generate_semantic_attribute(
            "966d0b9b-90a9-4781-95b8-cbf141399511",  # Standard ID for file size
            file_size
        ))
        
        # File extension attribute
        semantic_attributes.append(generate_semantic_attribute(
            "f93c9f59-0cc7-4628-89dc-9f0c686d81e7",  # Standard ID for file extension
            file_type
        ))
        
        # MIME type attribute
        semantic_attributes.append(generate_semantic_attribute(
            "f71ee08f-a5ae-4d75-9794-fb30330b3ce7",  # Standard ID for MIME type
            mime_type
        ))
        
        # Add wrong location if location in query
        if location:
            wrong_locations = [loc for loc in locations if loc != location]
            semantic_attributes.append(generate_semantic_attribute(
                "6bcb0a8b-28c8-47d2-a7e6-d910f717694a",  # Made-up ID for location
                random.choice(wrong_locations)
            ))
        
        # Add wrong application if application in query
        if application:
            wrong_apps = [app for app in applications if app != application]
            semantic_attributes.append(generate_semantic_attribute(
                "7a32a229-54b1-460e-86be-5ea421f1fcad",  # Made-up ID for application
                random.choice(wrong_apps)
            ))
        
        # Set the semantic attributes on the file metadata
        file_metadata["SemanticAttributes"] = semantic_attributes
        
        negative_examples.append(file_metadata)
    
    return positive_examples, negative_examples


def generate_music_activity_data(files: List[Dict[str, Any]], query: str, is_positive: bool) -> List[Dict[str, Any]]:
    """Generate music activity data for the given files.
    
    Args:
        files: The files to generate activity data for
        query: The original query
        is_positive: Whether these are positive examples (matching query)
        
    Returns:
        A list of music activity records
    """
    music_activities = []
    query_lower = query.lower()
    
    # Determine if query is related to music
    is_music_query = "music" in query_lower or "spotify" in query_lower
    
    # Skip if not relevant to this collection
    if not is_music_query and not ("files" in query_lower and not is_positive):
        return []
    
    # Define some music metadata for generation
    artists = ["The Beatles", "Taylor Swift", "Beyoncé", "BTS", "Drake", "Adele"]
    songs = ["Bohemian Rhapsody", "Shake It Off", "Single Ladies", "Dynamite", "God's Plan", "Hello"]
    albums = ["Abbey Road", "1989", "Lemonade", "Map of the Soul", "Scorpion", "25"]
    
    # Create one activity record per file
    for file in files:
        activity_id = generate_activity_id()
        file_id = file["_key"]
        
        # Base activity timestamp around file modification time
        file_modified_str = None
        for ts in file["Timestamps"]:
            if ts["Description"] == "Modified":
                file_modified_str = ts["Value"]
                break
        
        if not file_modified_str:
            file_modified_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
        file_modified = datetime.datetime.fromisoformat(file_modified_str)
        activity_time = file_modified + datetime.timedelta(minutes=random.randint(-30, 30))
        
        # Generate app name based on query and positive/negative status
        app_name = "Spotify" if "spotify" in query_lower and is_positive else random.choice(["Spotify", "Apple Music", "YouTube Music"])
        
        # Create activity record following similar schema to Objects
        activity = {
            "_key": activity_id,
            "ObjectId": file_id,
            "Action": "played",
            "Application": app_name,
            "Record": {
                "SourceIdentifier": {
                    "Identifier": str(uuid.uuid4()),
                    "Version": "1.0",
                    "Description": "Generated by ablation test data generator"
                },
                "Timestamp": activity_time.isoformat(),
                "Data": base64.b64encode(b"x").decode('ascii')
            },
            "Attributes": {
                "Artist": random.choice(artists),
                "Song": random.choice(songs),
                "Album": random.choice(albums),
                "Duration": random.randint(30, 300)  # Seconds
            },
            "SemanticAttributes": []
        }
        
        # Add semantic attributes
        semantic_attributes = []
        
        # Basic activity attributes
        semantic_attributes.append(generate_semantic_attribute(
            "b4a2a6b8-1c7d-42d9-8f8e-6d9e48a5b3c7",  # Made-up ID for activity type
            "MUSIC"
        ))
        
        semantic_attributes.append(generate_semantic_attribute(
            "7a32a229-54b1-460e-86be-5ea421f1fcad",  # ID for application
            app_name
        ))
        
        semantic_attributes.append(generate_semantic_attribute(
            "a8c3d4e5-f6g7-h8i9-j0k1-l2m3n4o5p6q7",  # Made-up ID for timestamp
            activity_time.isoformat()
        ))
        
        # Music-specific attributes
        semantic_attributes.append(generate_semantic_attribute(
            "r8s9t0u1-v2w3-x4y5-z6a7-b8c9d0e1f2g3",  # Made-up ID for artist
            activity["Attributes"]["Artist"]
        ))
        
        semantic_attributes.append(generate_semantic_attribute(
            "h3i4j5k6-l7m8-n9o0-p1q2-r3s4t5u6v7w8",  # Made-up ID for song
            activity["Attributes"]["Song"]
        ))
        
        semantic_attributes.append(generate_semantic_attribute(
            "x8y9z0a1-b2c3-d4e5-f6g7-h8i9j0k1l2m3",  # Made-up ID for album
            activity["Attributes"]["Album"]
        ))
        
        # Set the semantic attributes
        activity["SemanticAttributes"] = semantic_attributes
        
        # Add to the list
        music_activities.append(activity)
    
    return music_activities


def generate_geo_activity_data(files: List[Dict[str, Any]], query: str, is_positive: bool) -> List[Dict[str, Any]]:
    """Generate geo activity data for the given files.
    
    Args:
        files: The files to generate activity data for
        query: The original query
        is_positive: Whether these are positive examples (matching query)
        
    Returns:
        A list of geo activity records
    """
    geo_activities = []
    query_lower = query.lower()
    
    # Determine if query is related to location
    is_location_query = "location" in query_lower or "seattle" in query_lower or "home" in query_lower
    
    # Skip if not relevant to this collection
    if not is_location_query and not ("files" in query_lower and not is_positive):
        return []
    
    # Location data
    locations = {
        "home": {"lat": 47.6062, "long": -122.3321, "address": "123 Home St, Seattle, WA"},
        "office": {"lat": 47.6149, "long": -122.1941, "address": "456 Office Ave, Redmond, WA"},
        "seattle": {"lat": 47.6062, "long": -122.3321, "address": "Downtown Seattle, WA"},
        "portland": {"lat": 45.5152, "long": -122.6784, "address": "Portland, OR"},
        "san francisco": {"lat": 37.7749, "long": -122.4194, "address": "San Francisco, CA"},
        "new york": {"lat": 40.7128, "long": -74.0060, "address": "New York, NY"}
    }
    
    # Find target location from query
    target_location = None
    for loc in locations.keys():
        if loc in query_lower:
            target_location = loc
            break
    
    # Default to home if no location specified
    if target_location is None:
        target_location = "home"
    
    # Select location based on whether this is a positive or negative example
    if is_positive:
        location_key = target_location
    else:
        # For negative examples, pick a location different from the target
        other_locations = [loc for loc in locations.keys() if loc != target_location]
        location_key = random.choice(other_locations)
    
    location_data = locations[location_key]
    
    # Create one activity record per file
    for file in files:
        activity_id = generate_activity_id()
        file_id = file["_key"]
        
        # Base activity timestamp around file modification time
        file_modified_str = None
        for ts in file["Timestamps"]:
            if ts["Description"] == "Modified":
                file_modified_str = ts["Value"]
                break
        
        if not file_modified_str:
            file_modified_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
        file_modified = datetime.datetime.fromisoformat(file_modified_str)
        activity_time = file_modified + datetime.timedelta(minutes=random.randint(-30, 30))
        
        # Add some randomness to location coordinates
        lat = location_data["lat"] + random.uniform(-0.01, 0.01)
        long = location_data["long"] + random.uniform(-0.01, 0.01)
        
        # Create activity record
        activity = {
            "_key": activity_id,
            "ObjectId": file_id,
            "LocationName": location_key,
            "Record": {
                "SourceIdentifier": {
                    "Identifier": str(uuid.uuid4()),
                    "Version": "1.0",
                    "Description": "Generated by ablation test data generator"
                },
                "Timestamp": activity_time.isoformat(),
                "Data": base64.b64encode(b"x").decode('ascii')
            },
            "Coordinates": {
                "Latitude": lat,
                "Longitude": long
            },
            "Address": location_data["address"],
            "Attributes": {
                "LocationAccuracy": random.uniform(1.0, 10.0),
                "ConnectionType": random.choice(["WiFi", "Cellular", "Ethernet"])
            },
            "SemanticAttributes": []
        }
        
        # Add semantic attributes
        semantic_attributes = []
        
        # Basic activity attributes
        semantic_attributes.append(generate_semantic_attribute(
            "b4a2a6b8-1c7d-42d9-8f8e-6d9e48a5b3c7",  # Made-up ID for activity type
            "LOCATION"
        ))
        
        semantic_attributes.append(generate_semantic_attribute(
            "a8c3d4e5-f6g7-h8i9-j0k1-l2m3n4o5p6q7",  # Made-up ID for timestamp
            activity_time.isoformat()
        ))
        
        # Location-specific attributes
        semantic_attributes.append(generate_semantic_attribute(
            "6bcb0a8b-28c8-47d2-a7e6-d910f717694a",  # ID for location name
            location_key
        ))
        
        semantic_attributes.append(generate_semantic_attribute(
            "n3o4p5q6-r7s8-t9u0-v1w2-x3y4z5a6b7c8",  # Made-up ID for latitude
            lat
        ))
        
        semantic_attributes.append(generate_semantic_attribute(
            "d8e9f0g1-h2i3-j4k5-l6m7-n8o9p0q1r2s3",  # Made-up ID for longitude
            long
        ))
        
        semantic_attributes.append(generate_semantic_attribute(
            "t3u4v5w6-x7y8-z9a0-b1c2-d3e4f5g6h7i8",  # Made-up ID for address
            activity["Address"]
        ))
        
        # Set the semantic attributes
        activity["SemanticAttributes"] = semantic_attributes
        
        # Add to the list
        geo_activities.append(activity)
    
    return geo_activities


def generate_ablation_test_data(db_config: IndalekoDBConfig, test_queries: List[str], dataset_params: Dict[str, Any], tracker: TruthDataTracker) -> bool:
    """Generate test data for ablation testing.
    
    Args:
        db_config: Database configuration
        test_queries: List of test queries
        dataset_params: Parameters for data generation
        tracker: Truth data tracker to record which documents should match each query
        
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
        positive_count = dataset_params.get("positive_count", 5)
        negative_count = dataset_params.get("negative_count", 45)
        
        # Generate test data for each query
        for query in test_queries:
            logging.info(f"Generating test data for query: {query}")
            
            # Generate positive and negative file metadata examples
            positive_files, negative_files = generate_positive_negative_file_metadata(
                query, 
                positive_count, 
                negative_count
            )
            
            # Upload file metadata to Object collection
            logging.info(f"Uploading {len(positive_files)} positive and {len(negative_files)} negative file examples for query: {query}")
            
            # First positive files
            for file in positive_files:
                try:
                    # Make sure the file is JSON serializable
                    serializable_file = convert_to_json_serializable(file)
                    object_collection.insert(serializable_file)
                    
                    # Track this as a positive example for the query
                    tracker.add_positive_example(query, file["_key"])
                    
                except Exception as e:
                    logging.error(f"Error inserting positive file: {e}")
            
            # Then negative files
            for file in negative_files:
                try:
                    # Make sure the file is JSON serializable
                    serializable_file = convert_to_json_serializable(file)
                    object_collection.insert(serializable_file)
                    
                    # Track this as a negative example for the query
                    tracker.add_negative_example(query, file["_key"])
                    
                except Exception as e:
                    logging.error(f"Error inserting negative file: {e}")
            
            # Generate music activity data for files
            logging.info(f"Generating music activity data for query: {query}")
            
            # Generate for positive and negative examples
            positive_music_activities = generate_music_activity_data(positive_files, query, True)
            negative_music_activities = generate_music_activity_data(negative_files, query, False)
            
            # Upload music activity data
            for activity in positive_music_activities + negative_music_activities:
                try:
                    # Make sure the activity is JSON serializable
                    serializable_activity = convert_to_json_serializable(activity)
                    music_collection.insert(serializable_activity)
                    
                    # Track activity dependency - this positive example depends on music collection
                    is_positive = activity["ObjectId"] in [file["_key"] for file in positive_files]
                    tracker.set_activity_dependency(activity["ObjectId"], music_collection_name, is_positive)
                    
                except Exception as e:
                    logging.error(f"Error inserting music activity: {e}")
            
            # Generate geo activity data for files
            logging.info(f"Generating geo activity data for query: {query}")
            
            # Generate for positive and negative examples
            positive_geo_activities = generate_geo_activity_data(positive_files, query, True)
            negative_geo_activities = generate_geo_activity_data(negative_files, query, False)
            
            # Upload geo activity data
            for activity in positive_geo_activities + negative_geo_activities:
                try:
                    # Make sure the activity is JSON serializable
                    serializable_activity = convert_to_json_serializable(activity)
                    geo_collection.insert(serializable_activity)
                    
                    # Track activity dependency - this positive example depends on geo collection
                    is_positive = activity["ObjectId"] in [file["_key"] for file in positive_files]
                    tracker.set_activity_dependency(activity["ObjectId"], geo_collection_name, is_positive)
                    
                except Exception as e:
                    logging.error(f"Error inserting geo activity: {e}")
        
        # Save truth data
        tracker.save()
        return True
        
    except Exception as e:
        logging.error(f"Error generating ablation test data: {e}")
        return False


def setup_logging(level=logging.INFO):
    """Set up logging configuration."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("generate_ablation_data.log")
        ]
    )


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate test data for ablation testing')
    parser.add_argument('--positive-count', type=int, default=5,
                      help='Number of positive examples per query (default: 5)')
    parser.add_argument('--negative-count', type=int, default=45,
                      help='Number of negative examples per query (default: 45)')
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
    logging.info("Starting ablation test data generation")
    
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
    
    # Configure test queries
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
        "output_dir": args.output_dir
    }
    
    # Generate test data
    success = generate_ablation_test_data(db_config, test_queries, dataset_params, tracker)
    
    if success:
        logging.info("Test data generation completed successfully")
        print(f"Generated {args.positive_count} positive and {args.negative_count} negative examples for each of {len(test_queries)} queries")
        print(f"Results saved to: {args.output_dir}")
        return 0
    else:
        logging.error("Test data generation failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())