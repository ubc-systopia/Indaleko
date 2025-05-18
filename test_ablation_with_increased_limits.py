#!/usr/bin/env python3
"""
Test script to verify that our fixed_execute_query function with increased LIMIT values works.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import logging
import os
import sys
import re
import time
import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"test_increased_limits_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
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
from tools.data_generator_enhanced.testing.ablation_execute_query import fixed_execute_query

def test_fixed_execute_query():
    """Test our fixed_execute_query function with increased LIMIT values."""
    query = "Find files I accessed while listening to music"
    
    logging.info(f"Testing fixed_execute_query with query: '{query}'")
    
    start_time = time.time()
    results = fixed_execute_query(query, capture_aql=True)
    end_time = time.time()
    
    execution_time = end_time - start_time
    result_count = len(results)
    
    logging.info(f"Query returned {result_count} results in {execution_time:.2f} seconds")
    
    # Check if we can extract the transformed query from the debug info
    if results and isinstance(results[0], dict) and "_debug" in results[0]:
        aql = results[0]["_debug"].get("aql", "")
        logging.info(f"Transformed query (from debug info):\n{aql}")
    
    return results

def main():
    """Main function to run the test."""
    logging.info("Testing ablation with increased LIMIT values")
    
    # Run the test
    results = test_fixed_execute_query()
    
    # Print summary
    logging.info(f"Test completed with {len(results)} results")

if __name__ == "__main__":
    main()