#!/usr/bin/env python3
"""
Script to create indices for the ablation study collections.

This script creates indices for the ablation study collections to optimize
the performance of the queries used in the ablation tests.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

from db.db_config import IndalekoDBConfig


def setup_logging(verbose=False):
    """Set up logging for the script."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )


def create_indices():
    """Create indices for ablation study collections."""
    logger = logging.getLogger(__name__)
    
    # Connect to ArangoDB
    try:
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()
        logger.info("Connected to ArangoDB")
    except Exception as e:
        logger.error(f"Error connecting to ArangoDB: {e}")
        return False
    
    # Define indices for each ablation collection
    collection_indices = {
        "AblationMusicActivity": [
            {"fields": ["artist"], "type": "persistent"},
            {"fields": ["genre"], "type": "persistent"},
            {"fields": ["timestamp"], "type": "persistent"},
        ],
        "AblationLocationActivity": [
            {"fields": ["location_name"], "type": "persistent"},
            {"fields": ["location_type"], "type": "persistent"},
            {"fields": ["timestamp"], "type": "persistent"},
        ],
        "AblationTaskActivity": [
            {"fields": ["task_type"], "type": "persistent"},
            {"fields": ["application"], "type": "persistent"},
            {"fields": ["project"], "type": "persistent"},
            {"fields": ["status"], "type": "persistent"},
            {"fields": ["timestamp"], "type": "persistent"},
        ],
        "AblationCollaborationActivity": [
            {"fields": ["event_type"], "type": "persistent"},
            {"fields": ["platform"], "type": "persistent"},
            {"fields": ["event_title"], "type": "persistent"},
            {"fields": ["participants[*].name"], "type": "persistent"},
            {"fields": ["timestamp"], "type": "persistent"},
        ],
        "AblationStorageActivity": [
            {"fields": ["file_type"], "type": "persistent"},
            {"fields": ["operation"], "type": "persistent"},
            {"fields": ["source"], "type": "persistent"},
            {"fields": ["path"], "type": "persistent"},
            {"fields": ["timestamp"], "type": "persistent"},
        ],
        "AblationMediaActivity": [
            {"fields": ["media_type"], "type": "persistent"},
            {"fields": ["platform"], "type": "persistent"},
            {"fields": ["creator"], "type": "persistent"},
            {"fields": ["title"], "type": "persistent"},
            {"fields": ["timestamp"], "type": "persistent"},
        ],
        "AblationQueryTruth": [
            {"fields": ["query_id"], "type": "persistent"},
            {"fields": ["collection"], "type": "persistent"},
            {"fields": ["matching_entities"], "type": "persistent"},
        ],
    }
    
    # Create indices for each collection
    for collection_name, indices in collection_indices.items():
        # Get collection
        try:
            collection = db.collection(collection_name)
            logger.info(f"Found collection {collection_name}")
        except Exception as e:
            logger.error(f"Error getting collection {collection_name}: {e}")
            continue
        
        # Create indices for this collection
        for index_config in indices:
            try:
                fields = index_config["fields"]
                index_type = index_config["type"]
                
                # Check if index already exists
                existing_indices = collection.indexes()
                field_names = fields if isinstance(fields, list) else [fields]
                
                existing = False
                for idx in existing_indices:
                    if idx["type"] == index_type and set(idx["fields"]) == set(field_names):
                        logger.info(f"Index on {', '.join(field_names)} already exists in {collection_name}")
                        existing = True
                        break
                
                if not existing:
                    # Create index
                    if index_type == "persistent":
                        result = collection.add_persistent_index(fields)
                        logger.info(f"Created persistent index on {', '.join(field_names)} in {collection_name}: {result}")
                    elif index_type == "hash":
                        result = collection.add_hash_index(fields)
                        logger.info(f"Created hash index on {', '.join(field_names)} in {collection_name}: {result}")
                    elif index_type == "skiplist":
                        result = collection.add_skiplist_index(fields)
                        logger.info(f"Created skiplist index on {', '.join(field_names)} in {collection_name}: {result}")
                    elif index_type == "fulltext":
                        result = collection.add_fulltext_index(fields)
                        logger.info(f"Created fulltext index on {', '.join(field_names)} in {collection_name}: {result}")
                    else:
                        logger.warning(f"Unsupported index type: {index_type}")
                
            except Exception as e:
                logger.error(f"Error creating index on {', '.join(field_names)} in {collection_name}: {e}")
    
    logger.info("Finished creating indices for ablation study collections")
    return True


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Create indices for ablation study collections")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(verbose=args.verbose)
    
    # Create indices
    success = create_indices()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())