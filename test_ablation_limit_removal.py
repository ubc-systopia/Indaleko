#!/usr/bin/env python3
"""
Test the LIMIT removal functionality in the ablation framework.

This script uses a mock query to test if the LIMIT statements are properly
removed in the ablation_execute_query.py module.
"""

import logging
import os
import sys
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import the fixed execute_query function
try:
    from tools.data_generator_enhanced.testing.ablation_execute_query import fixed_execute_query
    logging.info("Successfully imported fixed_execute_query")
except ImportError as e:
    logging.error(f"Failed to import fixed_execute_query: {e}")
    sys.exit(1)

# Patch the get_api_key function to avoid needing a real API key
from tools.data_generator_enhanced.testing.ablation_execute_query import get_api_key
original_get_api_key = get_api_key

def mock_get_api_key() -> str:
    """Mock API key for testing."""
    return "sk-dummy-key-for-testing"

# Apply the patch
import tools.data_generator_enhanced.testing.ablation_execute_query as ablation_module
ablation_module.get_api_key = mock_get_api_key

def test_limit_removal():
    """Test if LIMIT statements are properly removed in ablation queries."""
    logging.info("Testing LIMIT removal in ablation queries")
    
    # Define a test query
    test_query = "Find all documents with 'test' in the title"
    
    try:
        # Execute the query using the fixed function
        logging.info(f"Executing query: {test_query}")
        results = fixed_execute_query(test_query, capture_aql=True)
        
        # Check if we got any results
        logging.info(f"Got {len(results)} results")
        
        # Check if the LIMIT statements were removed
        if results and "_debug" in results[0] and "aql" in results[0]["_debug"]:
            aql = results[0]["_debug"]["aql"]
            logging.info(f"Generated AQL: {aql}")
            
            # Check if there are any LIMIT statements left
            if "LIMIT" in aql:
                logging.error("LIMIT statement found in the generated AQL!")
                return False
            else:
                logging.info("No LIMIT statements found in the generated AQL - success!")
                return True
        else:
            logging.warning("No AQL found in the results")
            return False
    except Exception as e:
        logging.error(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Run the test
    success = test_limit_removal()
    sys.exit(0 if success else 1)