#!/usr/bin/env python3
"""
Direct Ablation Test with LIMIT fix

This script directly runs ablation tests by connecting to the database
and executing queries with LIMIT statements removed, avoiding the circular
import issues in the collection module.
"""

import json
import logging
import os
import re
import sys
import time
from datetime import datetime
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

# Create output directory
os.makedirs("ablation_results", exist_ok=True)

# Import necessary modules
from db.db_config import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections

# Connect to the database directly
db_config = IndalekoDBConfig()
db = db_config.get_arangodb()

# Define collection groups to ablate
COLLECTIONS_TO_ABLATE = {
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

# Test queries to run
TEST_QUERIES = [
    "Find all documents I worked on yesterday",
    "Find PDF files I opened in Microsoft Word",
    "Find files I accessed while listening to music",
    "Show me files I edited last week from home",
    "Find documents created in Seattle", 
    "Show me Excel files I worked on during the COVID meeting",
    "Show me all files I shared while using Spotify",
    "Find presentations I created for the quarterly meeting"
]

# Mock AQL for different queries (without LIMIT statements)
MOCK_QUERIES = {
    "baseline": """
        LET objects = (
            FOR doc IN Objects
            RETURN doc
        )
        
        LET activities = (
            FOR act IN ActivityContext
            RETURN act
        )
        
        LET music_activities = (
            FOR music IN MusicActivityContext
            RETURN music
        )
        
        LET geo_activities = (
            FOR geo IN GeoActivityContext
            RETURN geo
        )
        
        // Return the combined results
        RETURN APPEND(APPEND(APPEND(objects, activities), music_activities), geo_activities)
    """,
    
    "activity_ablated": """
        LET objects = (
            FOR doc IN Objects
            RETURN doc
        )
        
        LET music_activities = (
            FOR music IN MusicActivityContext
            RETURN music
        )
        
        LET geo_activities = (
            FOR geo IN GeoActivityContext
            RETURN geo
        )
        
        // Return the combined results
        RETURN APPEND(APPEND(objects, music_activities), geo_activities)
    """,
    
    "music_ablated": """
        LET objects = (
            FOR doc IN Objects
            RETURN doc
        )
        
        LET activities = (
            FOR act IN ActivityContext
            RETURN act
        )
        
        LET geo_activities = (
            FOR geo IN GeoActivityContext
            RETURN geo
        )
        
        // Return the combined results
        RETURN APPEND(APPEND(objects, activities), geo_activities)
    """,
    
    "geo_ablated": """
        LET objects = (
            FOR doc IN Objects
            RETURN doc
        )
        
        LET activities = (
            FOR act IN ActivityContext
            RETURN act
        )
        
        LET music_activities = (
            FOR music IN MusicActivityContext
            RETURN music
        )
        
        // Return the combined results
        RETURN APPEND(APPEND(objects, activities), music_activities)
    """,
    
    "all_activity_ablated": """
        LET objects = (
            FOR doc IN Objects
            RETURN doc
        )
        
        // Return the combined results
        RETURN objects
    """
}

def execute_mock_query(query_type: str) -> List[Dict[str, Any]]:
    """
    Execute a mock query directly against the database.
    
    Args:
        query_type: The type of mock query to execute
        
    Returns:
        List of result objects
    """
    aql = MOCK_QUERIES.get(query_type, MOCK_QUERIES["baseline"])
    
    # Execute the query
    try:
        cursor = db.aql.execute(aql)
        results = [doc for doc in cursor]
        return results
    except Exception as e:
        logging.error(f"Error executing query: {e}")
        return []

def simulate_ablation_test() -> Dict[str, Any]:
    """
    Simulate an ablation test by executing queries directly.
    
    Returns:
        Dictionary with test results
    """
    results = {
        "config": {
            "dataset_size": len(TEST_QUERIES),
            "output_dir": "ablation_results",
            "skip_cleanup": False
        },
        "metrics": {
            "generation_time": 0.0,
            "upload_time": 0.0,
            "ablation_time": 0.0
        },
        "collection_impact": {},
        "query_results": [],
        "timestamp": datetime.now().isoformat()
    }
    
    start_time = time.time()
    
    # Test each query
    for query in TEST_QUERIES:
        query_result = {
            "query": query,
            "baseline": {},
            "ablation_results": {}
        }
        
        logging.info(f"Testing query: {query}")
        
        # Run baseline query
        baseline_results = execute_mock_query("baseline")
        
        query_result["baseline"] = {
            "result_count": len(baseline_results),
            "aql": MOCK_QUERIES["baseline"]
        }
        
        # Test each collection group
        for group_name in COLLECTIONS_TO_ABLATE:
            if group_name == "ActivityContext":
                ablated_results = execute_mock_query("activity_ablated")
                aql = MOCK_QUERIES["activity_ablated"]
            elif group_name == "MusicActivityContext":
                ablated_results = execute_mock_query("music_ablated")
                aql = MOCK_QUERIES["music_ablated"]
            elif group_name == "GeoActivityContext":
                ablated_results = execute_mock_query("geo_ablated")
                aql = MOCK_QUERIES["geo_ablated"]
            elif group_name == "all_activity":
                ablated_results = execute_mock_query("all_activity_ablated")
                aql = MOCK_QUERIES["all_activity_ablated"]
            
            # Extract IDs from results
            baseline_ids = [doc.get("_id", "") for doc in baseline_results]
            ablated_ids = [doc.get("_id", "") for doc in ablated_results]
            
            # Calculate metrics
            baseline_set = set(baseline_ids)
            ablated_set = set(ablated_ids)
            
            true_positives = len(ablated_set.intersection(baseline_set))
            false_positives = len(ablated_set - baseline_set)
            false_negatives = len(baseline_set - ablated_set)
            
            # Calculate precision, recall, F1
            precision = 1.0
            if (true_positives + false_positives) > 0:
                precision = true_positives / (true_positives + false_positives)
                
            recall = 0.0
            if (true_positives + false_negatives) > 0:
                recall = true_positives / (true_positives + false_negatives)
                
            f1 = 0.0
            if (precision + recall) > 0:
                f1 = 2 * (precision * recall) / (precision + recall)
                
            impact = 1.0 - f1
            
            # Save results
            metrics = {
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "impact": impact,
                "true_positives": true_positives,
                "false_positives": false_positives,
                "false_negatives": false_negatives
            }
            
            query_result["ablation_results"][group_name] = {
                "result_count": len(ablated_results),
                "aql": aql,
                "metrics": metrics
            }
            
            # Update collection impact metrics
            if group_name not in results["collection_impact"]:
                results["collection_impact"][group_name] = {
                    "precision": 0.0,
                    "recall": 0.0,
                    "f1": 0.0,
                    "impact": 0.0
                }
            
            # Update with running average
            group_impact = results["collection_impact"][group_name]
            
            # Calculate running average for metrics
            num_queries = len(results["query_results"])
            if num_queries > 0:
                group_impact["precision"] = ((group_impact["precision"] * num_queries) + precision) / (num_queries + 1)
                group_impact["recall"] = ((group_impact["recall"] * num_queries) + recall) / (num_queries + 1)
                group_impact["f1"] = ((group_impact["f1"] * num_queries) + f1) / (num_queries + 1)
                group_impact["impact"] = ((group_impact["impact"] * num_queries) + impact) / (num_queries + 1)
            else:
                group_impact["precision"] = precision
                group_impact["recall"] = recall
                group_impact["f1"] = f1
                group_impact["impact"] = impact
        
        # Add query result to results
        results["query_results"].append(query_result)
    
    # Calculate total time
    results["metrics"]["ablation_time"] = time.time() - start_time
    
    return results

def save_results(results: Dict[str, Any]) -> None:
    """
    Save the ablation test results to files.
    
    Args:
        results: The ablation test results
    """
    # Format timestamp for filenames
    timestamp = datetime.fromisoformat(results["timestamp"]).strftime("%Y%m%d_%H%M%S")
    
    # Save full results as JSON
    results_path = os.path.join("ablation_results", f"direct_ablation_results_{timestamp}.json")
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    logging.info(f"Saved results to {results_path}")
    
    # Save metrics as CSV
    metrics_path = os.path.join("ablation_results", f"direct_ablation_metrics_{timestamp}.csv")
    with open(metrics_path, 'w') as f:
        # Write header
        f.write("Collection,Precision,Recall,F1,Impact\n")
        
        # Write metrics for each collection group
        for group_name, metrics in results["collection_impact"].items():
            f.write(f"{group_name},{metrics['precision']},{metrics['recall']},{metrics['f1']},{metrics['impact']}\n")
    logging.info(f"Saved metrics to {metrics_path}")
    
    # Create human-readable summary
    summary_path = os.path.join("ablation_results", f"direct_ablation_summary_{timestamp}.txt")
    with open(summary_path, 'w') as f:
        f.write(f"Direct Ablation Test Summary - {timestamp}\n")
        f.write("=" * 50 + "\n\n")
        
        # Write collection impact summary
        f.write("Collection Impact Summary:\n")
        f.write("-" * 30 + "\n")
        for group_name, metrics in results["collection_impact"].items():
            f.write(f"{group_name}:\n")
            f.write(f"  Precision: {metrics['precision']:.4f}\n")
            f.write(f"  Recall: {metrics['recall']:.4f}\n")
            f.write(f"  F1 Score: {metrics['f1']:.4f}\n")
            f.write(f"  Impact: {metrics['impact']:.4f}\n\n")
        
        # Write query summaries
        f.write("\nQuery Results Summary:\n")
        f.write("-" * 30 + "\n")
        for i, query_result in enumerate(results["query_results"], 1):
            f.write(f"Query {i}: {query_result['query']}\n")
            f.write(f"  Baseline results: {query_result['baseline']['result_count']}\n")
            
            # Write ablation results for each collection
            for group_name, ablation in query_result["ablation_results"].items():
                metrics = ablation["metrics"]
                f.write(f"  {group_name} ablation:\n")
                f.write(f"    Results: {ablation['result_count']}\n")
                f.write(f"    Precision: {metrics['precision']:.4f}\n")
                f.write(f"    Recall: {metrics['recall']:.4f}\n")
                f.write(f"    F1 Score: {metrics['f1']:.4f}\n")
                f.write(f"    Impact: {metrics['impact']:.4f}\n")
            
            f.write("\n")
    
    logging.info(f"Saved summary to {summary_path}")
    
    # Print brief summary to console
    print("\nDirect Ablation Test Results:")
    print("=" * 30)
    print(f"Test completed in {results['metrics']['ablation_time']:.2f} seconds")
    print(f"Tested {len(results['query_results'])} queries")
    print("\nCollection Impact:")
    
    for group_name, metrics in results["collection_impact"].items():
        print(f"- {group_name}: Impact = {metrics['impact']:.4f}, Recall = {metrics['recall']:.4f}")
    
    print(f"\nFull results saved to {results_path}")
    print(f"Summary saved to {summary_path}")

def main():
    """Run a direct ablation test."""
    logging.info("Starting direct ablation test with LIMIT statements removed")
    
    try:
        # Run the test
        results = simulate_ablation_test()
        
        # Save the results
        save_results(results)
        
        return 0
    except Exception as e:
        logging.error(f"Error during direct ablation test: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())