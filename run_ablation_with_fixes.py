#!/usr/bin/env python3
"""
Run ablation tests with fixes for LIMIT statements.

This script runs ablation tests with a modified version of execute_query that removes
LIMIT statements from AQL queries to provide more accurate recall metrics.
"""

import logging
import os
import sys
import re
import time
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import necessary modules
from query.query_processing.nl_parser import NLParser
from query.query_processing.enhanced_nl_parser import EnhancedNLParser
from query.query_processing.query_translator.aql_translator import AQLTranslator
from query.query_processing.query_translator.enhanced_aql_translator import EnhancedAQLTranslator
from query.search_execution.query_executor.aql_executor import AQLExecutor
from query.query_processing.data_models.translator_input import TranslatorInput
from db.db_config import IndalekoDBConfig
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from db.db_collections import IndalekoDBCollections

# Define a modified execute_query function that removes LIMIT statements
def execute_query_without_limits(query_text: str, capture_aql: bool = False) -> List[Dict[str, Any]]:
    """
    Execute a query without LIMIT statements and return the results.

    Args:
        query_text: The natural language query text to execute
        capture_aql: If True, include the AQL in the results

    Returns:
        List of result objects from the query
    """
    logging.info(f"Executing query without limits: {query_text}")
    
    # Initialize components
    db_config = IndalekoDBConfig()
    collections_metadata = IndalekoDBCollectionsMetadata(db_config)
    
    # Create query processors with the metadata
    nl_parser = EnhancedNLParser(collections_metadata=collections_metadata)
    translator = EnhancedAQLTranslator(collections_metadata=collections_metadata)
    executor = AQLExecutor()
    
    # Parse the query
    parsed_query = nl_parser.parse_enhanced(query_text)
    
    # Create translator input
    translator_input = TranslatorInput(
        Query=parsed_query,
        Connector=None  # No connector needed for this test
    )
    
    # Translate to AQL
    translation_result = translator.translate_enhanced(parsed_query, translator_input)
    
    # Save the original AQL for debugging
    original_aql = translation_result.aql_query
    logging.info(f"Original AQL query: {original_aql}")
    
    # Remove LIMIT statements from the AQL
    modified_aql = re.sub(r'LIMIT\s+\d+', '', original_aql)
    translation_result.aql_query = modified_aql
    logging.info(f"Modified AQL query (LIMIT statements removed): {modified_aql}")
    
    # Execute the modified query
    results = executor.execute(modified_aql, db_config, bind_vars=translation_result.bind_vars)
    
    # Add AQL to results if requested
    if capture_aql and results:
        for result in results:
            if not isinstance(result, dict):
                continue
            
            if "_debug" not in result:
                result["_debug"] = {}
            
            result["_debug"]["aql"] = modified_aql
            result["_debug"]["original_aql"] = original_aql
    
    logging.info(f"Query returned {len(results)} results")
    return results

def run_ablation_test(queries: List[str], collections_to_ablate: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    Run an ablation test with modified query execution.
    
    Args:
        queries: List of natural language queries to test
        collections_to_ablate: Dictionary mapping collection group names to collections
        
    Returns:
        Dictionary with test results
    """
    db_config = IndalekoDBConfig()
    collection_metadata = IndalekoDBCollectionsMetadata(db_config)
    
    results = {
        "config": {
            "dataset_size": len(queries),
            "output_dir": "ablation_results",
            "skip_cleanup": False
        },
        "metrics": {
            "generation_time": 0,
            "upload_time": 0,
            "ablation_time": 0
        },
        "collection_impact": {},
        "query_results": [],
        "timestamp": datetime.now().isoformat()
    }
    
    start_time = time.time()
    
    # Test each query
    for query in queries:
        query_result = {
            "query": query,
            "baseline": {},
            "ablation_results": {}
        }
        
        # Run baseline query with all collections
        logging.info(f"Running baseline query: {query}")
        baseline_results = execute_query_without_limits(query, capture_aql=True)
        
        # Extract baseline AQL from results
        baseline_aql = ""
        if baseline_results and "_debug" in baseline_results[0]:
            baseline_aql = baseline_results[0]["_debug"]["aql"]
        
        query_result["baseline"] = {
            "result_count": len(baseline_results),
            "aql": baseline_aql
        }
        
        # Test each collection group
        for group_name, collections in collections_to_ablate.items():
            logging.info(f"Testing ablation of {group_name}: {collections}")
            
            # Ablate collections
            for collection in collections:
                collection_metadata.ablate_collection(collection)
            
            # Run query with ablated collections
            ablated_results = execute_query_without_limits(query, capture_aql=True)
            
            # Extract ablated AQL from results
            ablated_aql = ""
            if ablated_results and "_debug" in ablated_results[0]:
                ablated_aql = ablated_results[0]["_debug"]["aql"]
            
            # Calculate metrics
            true_positives = 0
            false_positives = 0
            false_negatives = 0
            
            # Extract IDs from baseline and ablated results
            baseline_ids = []
            ablated_ids = []
            
            # Extract IDs from baseline results
            for result in baseline_results:
                if "_id" in result:
                    baseline_ids.append(result["_id"])
                elif "_key" in result:
                    baseline_ids.append(result["_key"])
            
            # Extract IDs from ablated results
            for result in ablated_results:
                if "_id" in result:
                    ablated_ids.append(result["_id"])
                elif "_key" in result:
                    ablated_ids.append(result["_key"])
            
            # Convert to sets for comparison
            baseline_set = set(baseline_ids)
            ablated_set = set(ablated_ids)
            
            # Calculate metrics
            true_positives = len(ablated_set.intersection(baseline_set))
            false_positives = len(ablated_set - baseline_set)
            false_negatives = len(baseline_set - ablated_set)
            
            precision = 1.0  # Precision should be 1.0 if there are no false positives
            if (true_positives + false_positives) > 0:
                precision = true_positives / (true_positives + false_positives)
                
            recall = 0.0
            if (true_positives + false_negatives) > 0:
                recall = true_positives / (true_positives + false_negatives)
                
            f1 = 0.0
            if (precision + recall) > 0:
                f1 = 2 * (precision * recall) / (precision + recall)
                
            impact = 1.0 - f1
            
            # Save metrics
            metrics = {
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "impact": impact,
                "true_positives": true_positives,
                "false_positives": false_positives,
                "false_negatives": false_negatives
            }
            
            # Save ablation results
            query_result["ablation_results"][group_name] = {
                "result_count": len(ablated_results),
                "aql": ablated_aql,
                "metrics": metrics
            }
            
            # Track collection impact scores
            if group_name not in results["collection_impact"]:
                results["collection_impact"][group_name] = {
                    "precision": 0,
                    "recall": 0,
                    "f1": 0,
                    "impact": 0
                }
                
            # Update collection impact with running average
            group_impact = results["collection_impact"][group_name]
            group_impact["precision"] = (group_impact["precision"] * (len(results["query_results"])) + precision) / (len(results["query_results"]) + 1)
            group_impact["recall"] = (group_impact["recall"] * (len(results["query_results"])) + recall) / (len(results["query_results"]) + 1)
            group_impact["f1"] = (group_impact["f1"] * (len(results["query_results"])) + f1) / (len(results["query_results"]) + 1)
            group_impact["impact"] = (group_impact["impact"] * (len(results["query_results"])) + impact) / (len(results["query_results"]) + 1)
            
            # Restore collections
            for collection in collections:
                collection_metadata.restore_collection(collection)
        
        # Save query result
        results["query_results"].append(query_result)
    
    # Calculate total time
    results["metrics"]["ablation_time"] = time.time() - start_time
    
    return results

def save_results(results: Dict[str, Any], output_dir: str = "ablation_results") -> None:
    """
    Save ablation test results to files.
    
    Args:
        results: The ablation test results
        output_dir: Directory to save results in
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Format timestamp for filenames
    timestamp = datetime.fromisoformat(results["timestamp"]).strftime("%Y%m%d_%H%M%S")
    
    # Save full results as JSON
    results_path = os.path.join(output_dir, f"ablation_test_results_{timestamp}.json")
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    logging.info(f"Saved full results to {results_path}")
    
    # Save metrics as CSV
    metrics_path = os.path.join(output_dir, f"ablation_metrics_{timestamp}.csv")
    with open(metrics_path, 'w') as f:
        # Write header
        f.write("Collection,Precision,Recall,F1,Impact\n")
        
        # Write collection impact metrics
        for collection, metrics in results["collection_impact"].items():
            f.write(f"{collection},{metrics['precision']},{metrics['recall']},{metrics['f1']},{metrics['impact']}\n")
    logging.info(f"Saved metrics to {metrics_path}")
    
    # Create a human-readable summary
    summary_path = os.path.join(output_dir, f"ablation_summary_{timestamp}.txt")
    with open(summary_path, 'w') as f:
        f.write(f"Ablation Test Summary - {results['timestamp']}\n")
        f.write("=" * 50 + "\n\n")
        
        # Write config info
        f.write("Configuration:\n")
        f.write(f"- Dataset size: {results['config']['dataset_size']}\n")
        f.write(f"- Execution time: {results['metrics']['ablation_time']:.2f} seconds\n\n")
        
        # Write collection impact summary
        f.write("Collection Impact Summary:\n")
        f.write("=" * 25 + "\n")
        for collection, metrics in results["collection_impact"].items():
            f.write(f"{collection}:\n")
            f.write(f"  Precision: {metrics['precision']:.4f}\n")
            f.write(f"  Recall: {metrics['recall']:.4f}\n")
            f.write(f"  F1 Score: {metrics['f1']:.4f}\n")
            f.write(f"  Impact: {metrics['impact']:.4f}\n\n")
        
        # Write query results summary
        f.write("Query Results Summary:\n")
        f.write("=" * 25 + "\n")
        for i, query_result in enumerate(results["query_results"], 1):
            f.write(f"Query {i}: {query_result['query']}\n")
            f.write(f"  Baseline results: {query_result['baseline']['result_count']}\n")
            
            # Write ablation results for each collection group
            for group, ablation in query_result["ablation_results"].items():
                f.write(f"  {group} ablation:\n")
                f.write(f"    Results: {ablation['result_count']}\n")
                f.write(f"    Precision: {ablation['metrics']['precision']:.4f}\n")
                f.write(f"    Recall: {ablation['metrics']['recall']:.4f}\n")
                f.write(f"    F1 Score: {ablation['metrics']['f1']:.4f}\n")
                f.write(f"    Impact: {ablation['metrics']['impact']:.4f}\n")
            
            f.write("\n")
    
    logging.info(f"Saved summary to {summary_path}")
    
    # Print a brief summary to console
    print("\nAblation Test Results Summary:")
    print("=" * 30)
    print(f"Test completed in {results['metrics']['ablation_time']:.2f} seconds")
    print(f"Tested {len(results['query_results'])} queries")
    print("\nCollection Impact:")
    for collection, metrics in results["collection_impact"].items():
        print(f"- {collection}: Impact = {metrics['impact']:.4f}, Recall = {metrics['recall']:.4f}")
    print(f"\nFull results saved to {output_dir}/ablation_test_results_{timestamp}.json")
    print(f"Summary available at {output_dir}/ablation_summary_{timestamp}.txt")

def main():
    """Run ablation tests with sample queries."""
    logging.info("Starting ablation tests with LIMIT fix")
    
    # Define test queries
    queries = [
        "Find all documents I worked on yesterday",
        "Find PDF files I opened in Microsoft Word",
        "Find files I accessed while listening to music",
        "Show me files I edited last week from home",
        "Find documents created in Seattle",
        "Show me Excel files I worked on during the COVID meeting",
        "Show me all files I shared while using Spotify",
        "Find presentations I created for the quarterly meeting"
    ]
    
    # Define collection groups to ablate
    collection_groups = {
        "ActivityContext": [
            IndalekoDBCollections.Indaleko_ActivityContext_Collection
        ],
        "MusicActivityContext": [
            IndalekoDBCollections.Indaleko_MusicActivityContext_Collection
        ],
        "GeoActivityContext": [
            IndalekoDBCollections.Indaleko_GeoActivityContext_Collection
        ],
        "all_activity": [
            IndalekoDBCollections.Indaleko_ActivityContext_Collection,
            IndalekoDBCollections.Indaleko_MusicActivityContext_Collection,
            IndalekoDBCollections.Indaleko_GeoActivityContext_Collection
        ]
    }
    
    # Run the tests
    try:
        results = run_ablation_test(queries, collection_groups)
        save_results(results)
    except Exception as e:
        logging.error(f"Error during ablation test: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())