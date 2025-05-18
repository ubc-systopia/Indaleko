#!/usr/bin/env python3
"""
Test script to evaluate query execution performance and diagnose potential issues.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import logging
import os
import sys
import re
import time
import json
from typing import Dict, List, Any
import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"query_execution_test_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
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

def execute_query(aql_query: str, description: str = ""):
    """Execute an AQL query and time it."""
    try:
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()
        
        logging.info(f"Executing query: {description}")
        logging.info(f"AQL: {aql_query}")
        
        start_time = time.time()
        cursor = db.aql.execute(aql_query)
        results = list(cursor)
        end_time = time.time()
        
        execution_time = end_time - start_time
        result_count = len(results)
        
        if isinstance(results, list) and results and isinstance(results[0], list):
            # Flatten nested lists
            results = results[0]
            result_count = len(results)
            
        logging.info(f"Query returned {result_count} results in {execution_time:.2f} seconds")
        return results, execution_time
    
    except Exception as e:
        logging.error(f"Error executing query: {e}")
        import traceback
        traceback.print_exc()
        return [], 0

def test_with_limit():
    """Test query execution with LIMIT statement."""
    aql_query = """
    LET objects = (
        FOR doc IN Objects
        LIMIT 20
        RETURN doc
    )
    RETURN objects
    """
    
    results, time_taken = execute_query(aql_query, "Query with LIMIT 20")
    return len(results), time_taken

def test_without_limit():
    """Test query execution without LIMIT statement."""
    aql_query = """
    LET objects = (
        FOR doc IN Objects
        RETURN doc
    )
    RETURN objects
    """
    
    results, time_taken = execute_query(aql_query, "Query without LIMIT")
    return len(results), time_taken

def test_with_filter():
    """Test query execution with a FILTER clause instead of LIMIT."""
    aql_query = """
    LET objects = (
        FOR doc IN Objects
        FILTER RAND() < 0.01  // Return approximately 1% of records
        RETURN doc
    )
    RETURN objects
    """
    
    results, time_taken = execute_query(aql_query, "Query with FILTER RAND()")
    return len(results), time_taken

def test_complex_query():
    """Test a more complex query with multiple collections."""
    aql_query = """
    LET objects = (
        FOR doc IN Objects
        LIMIT 10
        RETURN doc
    )
    
    LET activities = (
        FOR act IN ActivityContext
        LIMIT 10
        RETURN act
    )
    
    RETURN APPEND(objects, activities)
    """
    
    results, time_taken = execute_query(aql_query, "Complex query with two collections")
    return len(results), time_taken

def test_complex_query_no_limit():
    """Test a more complex query with multiple collections and no LIMIT."""
    aql_query = """
    LET objects = (
        FOR doc IN Objects
        FILTER RAND() < 0.001  // Return approximately 0.1% of records
        RETURN doc
    )
    
    LET activities = (
        FOR act IN ActivityContext
        FILTER RAND() < 0.001  // Return approximately 0.1% of records
        RETURN act
    )
    
    RETURN APPEND(objects, activities)
    """
    
    results, time_taken = execute_query(aql_query, "Complex query with FILTER instead of LIMIT")
    return len(results), time_taken

def main():
    """Run the tests."""
    logging.info("Starting query execution tests")
    
    # Test collection sizes
    try:
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()
        
        collections = ["Objects", "ActivityContext", "MusicActivityContext", "GeoActivityContext"]
        for collection_name in collections:
            try:
                collection = db.collection(collection_name)
                count = collection.count()
                logging.info(f"Collection {collection_name} has {count} documents")
            except Exception as e:
                logging.error(f"Error counting {collection_name}: {e}")
    except Exception as e:
        logging.error(f"Error connecting to database: {e}")
    
    # Run tests
    tests = [
        ("Query with LIMIT", test_with_limit),
        ("Query with FILTER", test_with_filter),
        ("Complex query", test_complex_query),
        ("Complex query no LIMIT", test_complex_query_no_limit),
        # Run this test last as it might be slow
        ("Query without LIMIT", test_without_limit),
    ]
    
    results = {}
    for name, test_func in tests:
        logging.info(f"Running test: {name}")
        try:
            count, time_taken = test_func()
            results[name] = {"count": count, "time": time_taken}
            logging.info(f"Test {name} completed: {count} results in {time_taken:.2f} seconds")
        except Exception as e:
            logging.error(f"Test {name} failed: {e}")
            results[name] = {"error": str(e)}
    
    # Print summary
    logging.info("\nTest Results Summary:")
    for name, result in results.items():
        if "error" in result:
            logging.info(f"{name}: ERROR - {result['error']}")
        else:
            logging.info(f"{name}: {result['count']} results in {result['time']:.2f} seconds")
    
if __name__ == "__main__":
    main()