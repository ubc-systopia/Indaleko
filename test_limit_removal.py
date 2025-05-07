"""
Test script to verify the removal of LIMIT statements from AQL queries.

This script tests the regular expression used in ablation_execute_query.py
to remove LIMIT statements from AQL queries.
"""

import re
import sys

def remove_limits(aql_query: str) -> str:
    """Remove LIMIT statements from an AQL query."""
    return re.sub(r'LIMIT\s+\d+', '', aql_query)

def test_limit_removal():
    """Test the LIMIT removal function with various AQL query patterns."""
    test_cases = [
        # Simple query with LIMIT
        (
            "FOR doc IN Objects FILTER doc.Type == 'PDF' LIMIT 5 RETURN doc",
            "FOR doc IN Objects FILTER doc.Type == 'PDF'  RETURN doc"
        ),
        # Query with multiple LIMITs
        (
            """
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
            
            RETURN APPEND(objects, activities)
            """,
            """
            LET objects = (
                FOR doc IN Objects
                
                RETURN doc
            )
            
            LET activities = (
                FOR act IN ActivityContext
                
                RETURN act
            )
            
            RETURN APPEND(objects, activities)
            """
        ),
        # Query with LIMIT and other parameters
        (
            "FOR doc IN Objects FILTER doc.Size > 1000 LIMIT 20 SORT doc.Name RETURN doc",
            "FOR doc IN Objects FILTER doc.Size > 1000  SORT doc.Name RETURN doc"
        ),
        # Query with LIMIT on multiple lines
        (
            """
            FOR doc IN Objects
            FILTER doc.Type == 'PDF'
            LIMIT 
                15
            RETURN doc
            """,
            """
            FOR doc IN Objects
            FILTER doc.Type == 'PDF'
            
                15
            RETURN doc
            """
        ),
    ]
    
    for i, (input_query, expected_output) in enumerate(test_cases, 1):
        print(f"Test case {i}:")
        result = remove_limits(input_query)
        
        # Fix whitespace for comparison - normalize newlines and multiple spaces
        result_normalized = re.sub(r'\s+', ' ', result).strip()
        expected_normalized = re.sub(r'\s+', ' ', expected_output).strip()
        
        if result_normalized == expected_normalized:
            print("✅ PASSED")
        else:
            print("❌ FAILED")
            print("Input:")
            print(input_query)
            print("\nExpected output:")
            print(expected_output)
            print("\nActual output:")
            print(result)
        print("\n" + "-" * 50 + "\n")
    
    # Also test the regex used in ablation_execute_query.py
    print("Testing regex from ablation_execute_query.py:")
    original_regex = r'LIMIT\s+\d+'
    test_query = """
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
    
    RETURN APPEND(objects, activities)
    """
    
    modified_query = re.sub(original_regex, '', test_query)
    print(modified_query)

if __name__ == "__main__":
    test_limit_removal()
    sys.exit(0)