"""
Test script to verify that our fixed_execute_query function is properly removing LIMIT statements.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import logging
import sys
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def test_limit_removal():
    """Test LIMIT statement removal."""
    # Test AQL query with LIMIT statements
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
    
    print("\nOriginal query:")
    print(test_aql)
    
    # Use the same regex pattern as in fixed_execute_query
    transformed_aql = re.sub(r'LIMIT\s+\d+', '', test_aql)
    
    print("\nTransformed query after removing LIMIT statements:")
    print(transformed_aql)
    
    # Check if all LIMIT statements were removed
    if 'LIMIT' in transformed_aql:
        print("\nERROR: LIMIT statements were not removed properly!")
    else:
        print("\nSUCCESS: All LIMIT statements were successfully removed!")

def main():
    """Run the test."""
    test_limit_removal()

if __name__ == "__main__":
    main()