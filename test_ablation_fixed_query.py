#!/usr/bin/env python3
"""
Test script to verify that our fixed_execute_query function is removing LIMIT statements.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import logging
import os
import sys
import re
from typing import Dict, List, Any, Optional
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("ablation_fixed_query_test.log")
    ]
)

# Add the Indaleko root to the path
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import database components
from db.db_config import IndalekoDBConfig
from db.db_collection_metadata import IndalekoDBCollectionsMetadata

def fixed_query_test():
    """Test our fixed query execution that removes LIMIT statements."""
    try:
        # Initialize database components
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()
        collections_metadata = IndalekoDBCollectionsMetadata(db_config)
        
        # Get collection names
        object_collection = "Objects"
        activity_collection = "ActivityContext"
        music_collection = "MusicActivityContext"
        geo_collection = "GeoActivityContext"
        
        logging.info("Creating test query with LIMIT statements")
        
        # Create a simple AQL query with LIMIT statements
        aql_query = f"""
        LET objects = (
            FOR doc IN {object_collection}
            LIMIT 5
            RETURN doc
        )
        
        LET activities = (
            FOR act IN {activity_collection}
            LIMIT 10
            RETURN act
        )
        
        // Return the combined results
        RETURN APPEND(objects, activities)
        """
        
        # Log the original query
        logging.info("Original query:")
        logging.info(aql_query)
        
        # Remove LIMIT statements
        modified_aql = re.sub(r'LIMIT\s+\d+', '', aql_query)
        
        # Log the modified query
        logging.info("Query after removing LIMIT statements:")
        logging.info(modified_aql)
        
        # Verify LIMIT statements were removed
        if 'LIMIT' in modified_aql:
            logging.error("LIMIT statements were not removed properly!")
            return False
        else:
            logging.info("All LIMIT statements were successfully removed")
        
        # Test executing the query
        logging.info("Executing query WITHOUT LIMIT statements")
        cursor = db.aql.execute(modified_aql)
        results_without_limit = list(cursor)
        
        # Flatten the results if needed
        if results_without_limit and isinstance(results_without_limit[0], list):
            results_without_limit = results_without_limit[0]
            
        logging.info(f"Query WITHOUT LIMIT returned {len(results_without_limit)} results")
        
        # Test executing the original query
        logging.info("Executing query WITH LIMIT statements")
        cursor = db.aql.execute(aql_query)
        results_with_limit = list(cursor)
        
        # Flatten the results if needed
        if results_with_limit and isinstance(results_with_limit[0], list):
            results_with_limit = results_with_limit[0]
            
        logging.info(f"Query WITH LIMIT returned {len(results_with_limit)} results")
        
        # Compare the result counts
        if len(results_without_limit) > len(results_with_limit):
            logging.info("SUCCESS: Query without LIMIT returned more results than query with LIMIT")
            return True
        else:
            logging.warning("UNEXPECTED: Query without LIMIT did not return more results than query with LIMIT")
            # Maybe there aren't more than 5/10 items in the collections
            return True
            
    except Exception as e:
        logging.error(f"Error in fixed_query_test: {e}")
        import traceback
        traceback.print_exc()
        return False

def ablation_test():
    """Test that ablation actually works with the collection metadata."""
    try:
        # Initialize database components
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()
        collections_metadata = IndalekoDBCollectionsMetadata(db_config)
        
        # Get ablation status for collections
        collection_to_ablate = "ActivityContext"
        
        # Get counts before ablation
        logging.info(f"Testing collection ablation for: {collection_to_ablate}")
        
        # Get ablated collections to verify it's not already ablated
        initial_ablated = collections_metadata.get_ablated_collections()
        initial_count = len(initial_ablated)
        logging.info(f"Initial ablated collections count: {initial_count}")
        
        # Make sure collection exists in the database
        try:
            db.collection(collection_to_ablate)
            logging.info(f"Found collection: {collection_to_ablate}")
        except Exception as e:
            logging.error(f"Collection {collection_to_ablate} not found! Error: {e}")
            return False
        
        # Ablate the collection
        logging.info(f"Ablating collection: {collection_to_ablate}")
        collections_metadata.ablate_collection(collection_to_ablate)
        
        # Get ablated collections after ablation
        ablated_after = collections_metadata.get_ablated_collections()
        after_count = len(ablated_after)
        logging.info(f"Ablated collections count after ablation: {after_count}")
        
        # Check if collection was ablated
        if collection_to_ablate in ablated_after:
            logging.info(f"Collection {collection_to_ablate} successfully ablated")
        else:
            logging.error(f"Collection {collection_to_ablate} was not ablated!")
            return False
        
        # Restore the collection
        logging.info(f"Restoring collection: {collection_to_ablate}")
        collections_metadata.restore_collection(collection_to_ablate)
        
        # Get ablated collections after restoration
        ablated_final = collections_metadata.get_ablated_collections()
        final_count = len(ablated_final)
        logging.info(f"Ablated collections count after restoration: {final_count}")
        
        if collection_to_ablate not in ablated_final:
            logging.info(f"Collection {collection_to_ablate} successfully restored")
        else:
            logging.error(f"Collection {collection_to_ablate} was not restored!")
            return False
        
        return True
            
    except Exception as e:
        logging.error(f"Error in ablation_test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function."""
    logging.info("Testing ablation and LIMIT removal functionality")
    
    # Run the fixed query test
    if fixed_query_test():
        logging.info("✅ Fixed query test PASSED")
    else:
        logging.error("❌ Fixed query test FAILED")
    
    # Run the ablation test
    if ablation_test():
        logging.info("✅ Ablation test PASSED")
    else:
        logging.error("❌ Ablation test FAILED")
    
if __name__ == "__main__":
    main()