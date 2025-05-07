#!/usr/bin/env python3
"""
Simple test for LIMIT statement removal in AQL queries.

This script tests the regex pattern we're using in ablation_execute_query.py
to remove LIMIT statements from AQL queries.
"""

import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def test_limit_removal():
    """Test the LIMIT statement removal with various AQL patterns."""
    # Example AQL from ablation study results
    test_aql = """
        LET objects = (
            FOR doc IN Objects
            LIMIT 5
            RETURN doc
        )
        

            LET activities = (
                FOR act IN ActivityContext
                LIMIT 10
                RETURN act
            )
            

        // Return the combined results
        RETURN APPEND(objects, activities)
    """
    
    logging.info("Original AQL query:")
    logging.info(test_aql)
    
    # Apply the regex to remove LIMIT statements
    modified_aql = re.sub(r'LIMIT\s+\d+', '', test_aql)
    
    logging.info("\nModified AQL query (LIMIT statements removed):")
    logging.info(modified_aql)
    
    # Check if there are any LIMIT statements left
    if "LIMIT" in modified_aql:
        logging.error("Failed: LIMIT statements still present in the modified query")
        return False
    else:
        logging.info("Success: All LIMIT statements were removed from the query")
        return True

if __name__ == "__main__":
    test_result = test_limit_removal()
    print(f"\nTest {'Passed' if test_result else 'Failed'}")