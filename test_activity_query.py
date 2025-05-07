#!/usr/bin/env python3
"""
Test script specifically for querying the ActivityContext collection.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import logging
import os
import sys
import time
import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"activity_query_test_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
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

def test_activity_query_with_limit():
    """Test query on ActivityContext with LIMIT."""
    try:
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()
        
        aql_query = """
        LET activities = (
            FOR act IN ActivityContext
            LIMIT 50
            RETURN act
        )
        RETURN activities
        """
        
        logging.info("Executing query with LIMIT 50 on ActivityContext")
        
        start_time = time.time()
        cursor = db.aql.execute(aql_query)
        results = list(cursor)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Flatten the results if needed
        if results and isinstance(results[0], list):
            results = results[0]
        
        result_count = len(results)
        logging.info(f"Query returned {result_count} results in {execution_time:.2f} seconds")
        
        return result_count, execution_time
    except Exception as e:
        logging.error(f"Error in test_activity_query_with_limit: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0

def test_activity_query_random_sample():
    """Test query on ActivityContext with a random sample (no LIMIT)."""
    try:
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()
        
        aql_query = """
        LET activities = (
            FOR act IN ActivityContext
            FILTER RAND() < 0.0001  // Return approximately 0.01% of records
            RETURN act
        )
        RETURN activities
        """
        
        logging.info("Executing query with RAND() < 0.0001 filter on ActivityContext")
        
        start_time = time.time()
        cursor = db.aql.execute(aql_query)
        results = list(cursor)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Flatten the results if needed
        if results and isinstance(results[0], list):
            results = results[0]
        
        result_count = len(results)
        logging.info(f"Query returned {result_count} results in {execution_time:.2f} seconds")
        
        return result_count, execution_time
    except Exception as e:
        logging.error(f"Error in test_activity_query_random_sample: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0

def test_activity_query_all():
    """Test query that returns ALL ActivityContext documents (no LIMIT)."""
    try:
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()
        
        # First, get the count using AQL COUNT
        count_query = """
        RETURN COUNT(ActivityContext)
        """
        
        logging.info("Counting ActivityContext documents...")
        
        count_cursor = db.aql.execute(count_query)
        count_result = list(count_cursor)
        total_count = count_result[0] if count_result else 0
        
        logging.info(f"ActivityContext has {total_count} documents")
        
        # Now try to fetch all documents
        aql_query = """
        LET activities = (
            FOR act IN ActivityContext
            RETURN act
        )
        RETURN activities
        """
        
        logging.info("Executing query without LIMIT on ActivityContext (fetching ALL documents)")
        logging.info("This may take a long time...")
        
        start_time = time.time()
        cursor = db.aql.execute(aql_query)
        
        # Use a batched approach for logging progress
        batch_size = 10000
        results = []
        batch_count = 0
        
        for i, doc in enumerate(cursor):
            results.append(doc)
            if (i + 1) % batch_size == 0:
                batch_count += 1
                elapsed = time.time() - start_time
                logging.info(f"Processed {(i + 1):,} documents in {elapsed:.2f} seconds...")
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Flatten the results if needed
        if results and isinstance(results[0], list):
            results = results[0]
        
        result_count = len(results)
        logging.info(f"Query returned {result_count:,} results in {execution_time:.2f} seconds")
        
        return result_count, execution_time
    except Exception as e:
        logging.error(f"Error in test_activity_query_all: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0

def main():
    """Run the tests."""
    logging.info("Starting ActivityContext query tests")
    
    # Test collection count
    try:
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()
        
        collection = db.collection("ActivityContext")
        count = collection.count()
        logging.info(f"Collection ActivityContext has {count:,} documents")
    except Exception as e:
        logging.error(f"Error counting collection: {e}")
    
    # Run the tests
    try:
        logging.info("Running test with LIMIT")
        limit_count, limit_time = test_activity_query_with_limit()
        
        logging.info("Running test with random sample")
        random_count, random_time = test_activity_query_random_sample()
        
        # This might take a very long time if the collection is large
        logging.info("Running test to fetch ALL documents")
        all_count, all_time = test_activity_query_all()
        
        # Print summary
        logging.info("\nTest Results Summary:")
        logging.info(f"Query with LIMIT: {limit_count} results in {limit_time:.2f} seconds")
        logging.info(f"Query with random sample: {random_count} results in {random_time:.2f} seconds")
        logging.info(f"Query ALL documents: {all_count:,} results in {all_time:.2f} seconds")
        
    except Exception as e:
        logging.error(f"Error running tests: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()