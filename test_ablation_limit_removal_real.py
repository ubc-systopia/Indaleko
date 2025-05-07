#!/usr/bin/env python3
"""
Test the LIMIT removal with real examples from ablation test results.

This script tests the regex pattern on actual examples from the
ablation_test_results_20250506_041309.json file.
"""

import re
import logging
import json
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def load_real_ablation_results():
    """Load actual AQL queries from ablation test results."""
    # Path to the ablation results file
    results_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "ablation_results",
        "ablation_test_results_20250506_041309.json"
    )
    
    # Check if the file exists
    if not os.path.exists(results_path):
        logging.error(f"Ablation results file not found at: {results_path}")
        return None
    
    # Load the JSON file
    try:
        with open(results_path, 'r') as f:
            results = json.load(f)
        logging.info(f"Successfully loaded ablation results from {results_path}")
        return results
    except Exception as e:
        logging.error(f"Error loading ablation results: {e}")
        return None

def test_limit_removal_on_real_examples():
    """Test LIMIT removal on real AQL queries from ablation tests."""
    # Load the real ablation results
    results = load_real_ablation_results()
    if not results:
        return False
    
    # Extract some AQL queries from the results
    aql_examples = []
    for query_result in results.get("query_results", []):
        baseline_aql = query_result.get("baseline", {}).get("aql")
        if baseline_aql:
            aql_examples.append(baseline_aql)
    
    logging.info(f"Found {len(aql_examples)} AQL examples in ablation results")
    
    # Test each example
    success = True
    for i, aql in enumerate(aql_examples, 1):
        logging.info(f"\nExample {i} - Original AQL:")
        logging.info(aql)
        
        # Apply the regex to remove LIMIT statements
        modified_aql = re.sub(r'LIMIT\s+\d+', '', aql)
        
        logging.info(f"\nExample {i} - Modified AQL:")
        logging.info(modified_aql)
        
        # Check if there are any LIMIT statements left
        if "LIMIT" in modified_aql:
            logging.error(f"Failed: Example {i} still has LIMIT statements")
            success = False
        else:
            logging.info(f"Success: Example {i} has all LIMIT statements removed")
    
    return success

if __name__ == "__main__":
    test_result = test_limit_removal_on_real_examples()
    print(f"\nTest {'Passed' if test_result else 'Failed'}")