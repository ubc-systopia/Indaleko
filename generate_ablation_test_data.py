#!/usr/bin/env python3
"""
Data Generator for Ablation Testing.

This script generates synthetic test data specifically designed for ablation testing.
It creates both matching (positive) and non-matching (negative) examples for each query,
ensuring proper ground truth for measuring precision and recall changes during ablation.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import os
import sys
import logging
import random
import uuid
import datetime
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple

# Set up environment variables and paths
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import Indaleko modules
from db.db_config import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections
from tools.data_generator_enhanced.agents.data_gen.tools.stats import ActivityGeneratorTool, FileMetadataGeneratorTool

# Test queries to ensure we have data matching our scenarios
TEST_QUERIES = [
    "Find all documents I worked on yesterday",
    "Find PDF files I opened in Microsoft Word",
    "Find files I accessed while listening to music",
    "Show me files I edited last week from home",
    "Find documents created in Seattle",
    "Show me Excel files I worked on during the COVID meeting",
    "Show me all files I shared while using Spotify",
    "Find presentations I created for the quarterly meeting"
]

def setup_logging(level=logging.INFO):
    """Set up logging configuration."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    logging.info("Logging initialized.")

def reset_database():
    """Reset the database to a clean state."""
    logging.info("Resetting database...")
    
    try:
        # Create a DB config instance first
        db_config = IndalekoDBConfig()
        # Then call start() with reset=True
        db_config.start(reset=True)
        logging.info("Database reset successful")
        return db_config
    except Exception as e:
        logging.error(f"Error resetting database: {e}")
        return None

def setup_database():
    """Set up database connection."""
    try:
        logging.info("Setting up database connection...")
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()
        logging.info("Database connection established")
        return db_config, db
    except Exception as e:
        logging.error(f"Error setting up database: {e}")
        return None, None

def convert_objects(obj):
    """Recursively convert non-JSON-serializable objects to strings in a nested structure."""
    if isinstance(obj, uuid.UUID):
        return str(obj)
    elif isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif isinstance(obj, datetime.date):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_objects(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_objects(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_objects(item) for item in obj)
    else:
        return obj

def generate_positive_negative_file_metadata(query: str, positive_count: int, negative_count: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Generate both positive and negative file metadata examples for the given query.
    
    Args:
        query: The query to generate examples for
        positive_count: Number of positive examples to generate
        negative_count: Number of negative examples to generate
        
    Returns:
        Tuple of (positive_files, negative_files)
    """
    file_generator = FileMetadataGeneratorTool()
    query_lower = query.lower()
    
    # Generate base objects
    all_files = file_generator.execute({
        "count": positive_count + negative_count,
        "criteria": {}
    }).get("records", [])
    
    if len(all_files) < positive_count + negative_count:
        logging.warning(f"Requested {positive_count + negative_count} files but only generated {len(all_files)}")
    
    # Split into positive and negative examples
    positive_files = all_files[:positive_count] if positive_count <= len(all_files) else all_files[:]
    negative_files = all_files[positive_count:] if positive_count < len(all_files) else []
    
    # Add query-specific metadata to positive examples
    for i, file in enumerate(positive_files):
        # Make sure ObjectIdentifier is set
        if "ObjectIdentifier" not in file:
            file["ObjectIdentifier"] = str(uuid.uuid4())
            
        if "_key" not in file:
            file["_key"] = file["ObjectIdentifier"]
            
        # Flag as a positive example
        file["IsPositiveExample"] = True
        file["QueryIdentifier"] = f"{query}-positive-{i}"
        
        # Add file type based on query
        if "pdf" in query_lower:
            file["Label"] = f"document_{i}.pdf"
            file["Extension"] = ".pdf"
            file["SemanticAttributes"] = file.get("SemanticAttributes", []) + [{
                "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "FileType"},
                "Value": "application/pdf"
            }]
        elif "excel" in query_lower:
            file["Label"] = f"spreadsheet_{i}.xlsx"
            file["Extension"] = ".xlsx"
            file["SemanticAttributes"] = file.get("SemanticAttributes", []) + [{
                "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "FileType"},
                "Value": "application/vnd.ms-excel"
            }]
        elif "presentation" in query_lower:
            file["Label"] = f"presentation_{i}.pptx"
            file["Extension"] = ".pptx"
            file["SemanticAttributes"] = file.get("SemanticAttributes", []) + [{
                "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "FileType"},
                "Value": "application/vnd.ms-powerpoint"
            }]
        
        # Add temporal metadata
        if "yesterday" in query_lower:
            yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
            file["SemanticAttributes"] = file.get("SemanticAttributes", []) + [{
                "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "LastModified"},
                "Value": yesterday.isoformat()
            }]
        elif "last week" in query_lower:
            last_week = datetime.datetime.now() - datetime.timedelta(days=random.randint(3, 7))
            file["SemanticAttributes"] = file.get("SemanticAttributes", []) + [{
                "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "LastModified"},
                "Value": last_week.isoformat()
            }]
            
        # Add location metadata
        if "seattle" in query_lower:
            file["SemanticAttributes"] = file.get("SemanticAttributes", []) + [{
                "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "CreationLocation"},
                "Value": "Seattle, WA"
            }]
        elif "home" in query_lower:
            file["SemanticAttributes"] = file.get("SemanticAttributes", []) + [{
                "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "CreationLocation"},
                "Value": "Home"
            }]
            
        # Add application metadata
        if "microsoft word" in query_lower:
            file["SemanticAttributes"] = file.get("SemanticAttributes", []) + [{
                "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "LastApplication"},
                "Value": "Microsoft Word"
            }]
            
        # Add meeting context
        if "covid meeting" in query_lower:
            file["SemanticAttributes"] = file.get("SemanticAttributes", []) + [{
                "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "MeetingContext"},
                "Value": "COVID Meeting"
            }]
        elif "quarterly meeting" in query_lower:
            file["SemanticAttributes"] = file.get("SemanticAttributes", []) + [{
                "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "MeetingContext"},
                "Value": "Quarterly Meeting"
            }]
    
    # Add query-specific metadata to negative examples (opposite of positive examples)
    for i, file in enumerate(negative_files):
        # Make sure ObjectIdentifier is set
        if "ObjectIdentifier" not in file:
            file["ObjectIdentifier"] = str(uuid.uuid4())
            
        if "_key" not in file:
            file["_key"] = file["ObjectIdentifier"]
            
        # Flag as a negative example
        file["IsPositiveExample"] = False
        file["QueryIdentifier"] = f"{query}-negative-{i}"
        
        # Add file type that doesn't match query
        if "pdf" in query_lower:
            file["Label"] = f"document_{i}.docx"
            file["Extension"] = ".docx"
            file["SemanticAttributes"] = file.get("SemanticAttributes", []) + [{
                "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "FileType"},
                "Value": "application/msword"
            }]
        elif "excel" in query_lower:
            file["Label"] = f"document_{i}.txt"
            file["Extension"] = ".txt"
            file["SemanticAttributes"] = file.get("SemanticAttributes", []) + [{
                "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "FileType"},
                "Value": "text/plain"
            }]
        elif "presentation" in query_lower:
            file["Label"] = f"document_{i}.pdf"
            file["Extension"] = ".pdf"
            file["SemanticAttributes"] = file.get("SemanticAttributes", []) + [{
                "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "FileType"},
                "Value": "application/pdf"
            }]
        
        # Add temporal metadata that doesn't match
        if "yesterday" in query_lower or "last week" in query_lower:
            month_ago = datetime.datetime.now() - datetime.timedelta(days=random.randint(30, 60))
            file["SemanticAttributes"] = file.get("SemanticAttributes", []) + [{
                "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "LastModified"},
                "Value": month_ago.isoformat()
            }]
            
        # Add location metadata that doesn't match
        if "seattle" in query_lower or "home" in query_lower:
            file["SemanticAttributes"] = file.get("SemanticAttributes", []) + [{
                "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "CreationLocation"},
                "Value": "Office"
            }]
            
        # Add application metadata that doesn't match
        if "microsoft word" in query_lower:
            file["SemanticAttributes"] = file.get("SemanticAttributes", []) + [{
                "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "LastApplication"},
                "Value": "Notepad"
            }]
            
        # Add meeting context that doesn't match
        if "covid meeting" in query_lower or "quarterly meeting" in query_lower:
            file["SemanticAttributes"] = file.get("SemanticAttributes", []) + [{
                "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "MeetingContext"},
                "Value": "Team Standup"
            }]
    
    return positive_files, negative_files

def generate_music_activity_data(files: List[Dict[str, Any]], query: str, is_positive: bool) -> List[Dict[str, Any]]:
    """Generate music activity data for the given files.
    
    Args:
        files: List of file metadata to associate with music activity
        query: Query text for context
        is_positive: Whether these are positive or negative examples
        
    Returns:
        List of music activity records
    """
    activities = []
    query_lower = query.lower()
    
    for i, file in enumerate(files):
        activity = {
            "_key": str(uuid.uuid4()),
            "Handle": str(uuid.uuid4()),
            "Timestamp": datetime.datetime.now().isoformat(),
            "ActivityType": "MusicPlayback",
            "ObjectIdentifier": file.get("ObjectIdentifier", file.get("_key", "")),
            "IsPositiveExample": is_positive,
            "SemanticAttributes": [],
            "Cursors": [
                {
                    "Provider": "AblationTestGenerator",
                    "ProviderIdentifier": str(uuid.uuid4()),
                    "Position": i,
                    "Timestamp": datetime.datetime.now().isoformat()
                }
            ]
        }
        
        # Add track/artist details
        if is_positive:
            # For positive examples, match what the query is looking for
            is_spotify = "spotify" in query_lower
            artist = "Taylor Swift" if "taylor swift" in query_lower else "Popular Artist"
            
            activity["Provider"] = "Spotify" if is_spotify else "Generic Music Service"
            activity["Track"] = f"Track {i+1}"
            activity["Album"] = f"Album {i//3 + 1}"
            activity["Artist"] = artist
            activity["Device"] = f"Device-{random.randint(1, 5)}"
            
            # Add semantic attributes
            activity["SemanticAttributes"].extend([
                {
                    "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "Provider"},
                    "Value": "Spotify" if is_spotify else "Generic Music Service"
                },
                {
                    "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "Track"},
                    "Value": f"Track {i+1}"
                },
                {
                    "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "Artist"},
                    "Value": artist
                }
            ])
        else:
            # For negative examples, use different values than what the query seeks
            is_spotify = "spotify" in query_lower
            
            activity["Provider"] = "Apple Music" if is_spotify else "Spotify" # Opposite of what's requested
            activity["Track"] = f"Non-matching Track {i+1}"
            activity["Album"] = f"Non-matching Album {i//3 + 1}"
            activity["Artist"] = "Different Artist"
            activity["Device"] = f"Device-{random.randint(6, 10)}"
            
            # Add semantic attributes
            activity["SemanticAttributes"].extend([
                {
                    "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "Provider"},
                    "Value": "Apple Music" if is_spotify else "Spotify"
                },
                {
                    "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "Track"},
                    "Value": f"Non-matching Track {i+1}"
                },
                {
                    "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "Artist"},
                    "Value": "Different Artist"
                }
            ])
    
        activities.append(activity)
    
    return activities

def generate_geo_activity_data(files: List[Dict[str, Any]], query: str, is_positive: bool) -> List[Dict[str, Any]]:
    """Generate geo activity data for the given files.
    
    Args:
        files: List of file metadata to associate with geo activity
        query: Query text for context
        is_positive: Whether these are positive or negative examples
        
    Returns:
        List of geo activity records
    """
    activities = []
    query_lower = query.lower()
    
    for i, file in enumerate(files):
        activity = {
            "_key": str(uuid.uuid4()),
            "Handle": str(uuid.uuid4()),
            "Timestamp": datetime.datetime.now().isoformat(),
            "ActivityType": "LocationActivity",
            "ObjectIdentifier": file.get("ObjectIdentifier", file.get("_key", "")),
            "IsPositiveExample": is_positive,
            "SemanticAttributes": [],
            "Cursors": [
                {
                    "Provider": "AblationTestGenerator",
                    "ProviderIdentifier": str(uuid.uuid4()),
                    "Position": i,
                    "Timestamp": datetime.datetime.now().isoformat()
                }
            ]
        }
        
        # Add location details
        if is_positive:
            # For positive examples, match what the query is looking for
            if "seattle" in query_lower:
                location = "Seattle, WA"
                latitude = 47.6062
                longitude = -122.3321
            elif "home" in query_lower:
                location = "Home"
                latitude = 47.5432
                longitude = -122.393
            else:
                location = "Office"
                latitude = 47.6149
                longitude = -122.1941
            
            activity["Location"] = location
            activity["Latitude"] = latitude
            activity["Longitude"] = longitude
            activity["Accuracy"] = round(random.uniform(2.0, 10.0), 2)
            
            # Add semantic attributes
            activity["SemanticAttributes"].extend([
                {
                    "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "Location"},
                    "Value": location
                },
                {
                    "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "Coordinates"},
                    "Value": f"{latitude},{longitude}"
                }
            ])
        else:
            # For negative examples, use different values than what the query seeks
            if "seattle" in query_lower:
                location = "Portland, OR"
                latitude = 45.5152
                longitude = -122.6784
            elif "home" in query_lower:
                location = "Office"
                latitude = 47.6149
                longitude = -122.1941
            else:
                location = "Coffee Shop"
                latitude = 47.6615
                longitude = -122.3128
            
            activity["Location"] = location
            activity["Latitude"] = latitude
            activity["Longitude"] = longitude
            activity["Accuracy"] = round(random.uniform(2.0, 10.0), 2)
            
            # Add semantic attributes
            activity["SemanticAttributes"].extend([
                {
                    "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "Location"},
                    "Value": location
                },
                {
                    "Identifier": {"Identifier": str(uuid.uuid4()), "Label": "Coordinates"},
                    "Value": f"{latitude},{longitude}"
                }
            ])
    
        activities.append(activity)
    
    return activities

def map_activity_collection(query: str) -> List[str]:
    """Map query to relevant activity collections.
    
    Args:
        query: Query text
        
    Returns:
        List of collection names that are relevant to this query
    """
    query_lower = query.lower()
    collections = []
    
    # Determine which collections are relevant to this query
    if "music" in query_lower or "spotify" in query_lower:
        collections.append(IndalekoDBCollections.Indaleko_MusicActivityData_Collection)
    
    if "seattle" in query_lower or "home" in query_lower or "location" in query_lower:
        collections.append(IndalekoDBCollections.Indaleko_GeoActivityData_Collection)
    
    return collections

def create_truth_data_file(truth_data: Dict[str, Any], output_dir: str):
    """Create a truth data file for evaluation.
    
    Args:
        truth_data: Truth data dictionary
        output_dir: Directory to save the file
    """
    os.makedirs(output_dir, exist_ok=True)
    truth_file = os.path.join(output_dir, "truth_data.json")
    
    with open(truth_file, "w") as f:
        json.dump(truth_data, f, indent=2)
    
    logging.info(f"Truth data saved to {truth_file}")

def generate_and_upload_test_data(config: Dict[str, Any]) -> bool:
    """Generate and upload test data for ablation studies.
    
    Args:
        config: Configuration parameters
        
    Returns:
        True if successful, False otherwise
    """
    logging.info("Starting ablation test data generation...")
    
    try:
        # Reset database if requested
        if config.get("reset_database", True):
            db_config = reset_database()
            if not db_config:
                logging.error("Failed to reset database. Aborting.")
                return False
        else:
            # Just set up database connection
            db_config, db = setup_database()
            if not db_config or not db:
                logging.error("Failed to set up database connection. Aborting.")
                return False
        
        # Get DB connection
        db = db_config.get_arangodb()
        
        # Create truth data structure
        truth_data = {
            "generated_at": datetime.datetime.now().isoformat(),
            "query_truth_data": {}
        }
        
        # Process each test query
        for query in TEST_QUERIES:
            logging.info(f"Generating data for query: {query}")
            
            # Generate storage objects (both positive and negative examples)
            positive_count = config.get("positive_count", 5)
            negative_count = config.get("negative_count", 45)
            positive_files, negative_files = generate_positive_negative_file_metadata(
                query, positive_count, negative_count
            )
            
            # Get the Objects collection
            object_collection = db.collection(IndalekoDBCollections.Indaleko_Object_Collection)
            if not object_collection:
                logging.error(f"Objects collection not found")
                continue
                
            # Upload storage objects
            positive_ids = []
            try:
                # Upload positive examples
                if positive_files:
                    serializable_positive = [convert_objects(obj) for obj in positive_files]
                    object_collection.import_bulk(serializable_positive, on_duplicate="update")
                    positive_ids = [f"{object_collection.name}/{obj['_key']}" for obj in positive_files]
                    logging.info(f"Uploaded {len(positive_files)} positive files to Objects collection")
                
                # Upload negative examples
                if negative_files:
                    serializable_negative = [convert_objects(obj) for obj in negative_files]
                    object_collection.import_bulk(serializable_negative, on_duplicate="update")
                    logging.info(f"Uploaded {len(negative_files)} negative files to Objects collection")
            except Exception as e:
                logging.error(f"Error uploading storage objects: {e}")
            
            # Generate and upload activity data
            # Different activity types based on the query
            relevant_collections = map_activity_collection(query)
            
            for collection_name in relevant_collections:
                activity_collection = db.collection(collection_name)
                if not activity_collection:
                    logging.warning(f"Collection {collection_name} not found, creating it")
                    activity_collection = db.create_collection(collection_name)
                
                # Generate activity data based on collection type
                if collection_name == IndalekoDBCollections.Indaleko_MusicActivityData_Collection:
                    # Generate music activity data
                    positive_activities = generate_music_activity_data(positive_files, query, True)
                    negative_activities = generate_music_activity_data(negative_files, query, False)
                    
                    # Upload music activity data
                    if positive_activities:
                        serializable_positive = [convert_objects(act) for act in positive_activities]
                        try:
                            activity_collection.import_bulk(serializable_positive, on_duplicate="update")
                            logging.info(f"Uploaded {len(positive_activities)} positive music activities")
                        except Exception as e:
                            logging.error(f"Error uploading positive music activities: {e}")
                    
                    if negative_activities:
                        serializable_negative = [convert_objects(act) for act in negative_activities]
                        try:
                            activity_collection.import_bulk(serializable_negative, on_duplicate="update")
                            logging.info(f"Uploaded {len(negative_activities)} negative music activities")
                        except Exception as e:
                            logging.error(f"Error uploading negative music activities: {e}")
                
                elif collection_name == IndalekoDBCollections.Indaleko_GeoActivityData_Collection:
                    # Generate geo activity data
                    positive_activities = generate_geo_activity_data(positive_files, query, True)
                    negative_activities = generate_geo_activity_data(negative_files, query, False)
                    
                    # Upload geo activity data
                    if positive_activities:
                        serializable_positive = [convert_objects(act) for act in positive_activities]
                        try:
                            activity_collection.import_bulk(serializable_positive, on_duplicate="update")
                            logging.info(f"Uploaded {len(positive_activities)} positive geo activities")
                        except Exception as e:
                            logging.error(f"Error uploading positive geo activities: {e}")
                    
                    if negative_activities:
                        serializable_negative = [convert_objects(act) for act in negative_activities]
                        try:
                            activity_collection.import_bulk(serializable_negative, on_duplicate="update")
                            logging.info(f"Uploaded {len(negative_activities)} negative geo activities")
                        except Exception as e:
                            logging.error(f"Error uploading negative geo activities: {e}")
            
            # Update truth data
            truth_data["query_truth_data"][query] = {
                "matching_document_ids": positive_ids,
                "metadata": {
                    "positive_count": len(positive_files),
                    "negative_count": len(negative_files),
                    "collections": relevant_collections
                }
            }
        
        # Save truth data file
        create_truth_data_file(truth_data, config.get("output_dir", "./ablation_results"))
        
        logging.info("Data generation completed successfully. Ready for ablation testing.")
        return True
    
    except Exception as e:
        logging.error(f"Error generating and uploading test data: {e}")
        return False

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate test data for ablation studies')
    
    parser.add_argument('--positive-count', type=int, default=5,
                      help='Number of positive examples per query (default: 5)')
    parser.add_argument('--negative-count', type=int, default=45,
                      help='Number of negative examples per query (default: 45)')
    parser.add_argument('--output-dir', type=str, default="./ablation_results",
                      help='Directory to save truth data (default: ./ablation_results)')
    parser.add_argument('--no-reset', action='store_true',
                      help='Do not reset the database before generating data')
    parser.add_argument('--debug', action='store_true',
                      help='Enable debug logging')
    
    return parser.parse_args()

def main():
    """Main function."""
    args = parse_args()
    
    # Setup logging
    setup_logging(level=logging.DEBUG if args.debug else logging.INFO)
    
    # Build configuration
    config = {
        "positive_count": args.positive_count,
        "negative_count": args.negative_count,
        "output_dir": args.output_dir,
        "reset_database": not args.no_reset
    }
    
    # Generate and upload test data
    success = generate_and_upload_test_data(config)
    
    # Return success status
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())