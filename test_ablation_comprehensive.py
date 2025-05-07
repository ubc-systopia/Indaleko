#!/usr/bin/env python3
"""
Simplified version of the comprehensive ablation test framework for Indaleko.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import os
import sys
import json
import logging
import datetime
import time
from pathlib import Path
from typing import Dict, List, Any, Set

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"ablation_comprehensive_test_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)

# Set up path
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import Indaleko modules
from db.db_config import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from tools.data_generator_enhanced.testing.ablation_execute_query import fixed_execute_query

def run_ablation_test():
    """Run a simplified version of the comprehensive ablation test."""
    try:
        logging.info("Starting simplified ablation test")
        
        # Initialize database connection
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()
        logging.info(f"Connected to database Indaleko")
        logging.info("Connected to ArangoDB server")
        
        # Initialize collections metadata
        collections_metadata = IndalekoDBCollectionsMetadata(db_config)
        
        # Define collection groups for testing
        collection_groups = {
            "ActivityContext": [
                "ActivityContext"
            ],
            "MusicActivityContext": [
                "MusicActivityContext"
            ],
            "GeoActivityContext": [
                "GeoActivityContext"
            ],
            "all_activity": [
                "ActivityContext",
                "MusicActivityContext",
                "GeoActivityContext"
            ]
        }
        
        # Define test queries
        test_queries = [
            "Find all documents I worked on yesterday",
            "Find PDF files I opened in Microsoft Word"
        ]
        
        # Store results
        results = {
            "timestamp": datetime.datetime.now().isoformat(),
            "ablation_results": {}
        }
        
        # Run ablation tests for each query
        for query in test_queries:
            logging.info(f"Testing query: '{query}'")
            
            # Store results for this query
            query_results = {
                "query": query,
                "ablation_tests": {}
            }
            
            # Run baseline query (no ablation)
            logging.info("Running baseline query...")
            baseline_results = fixed_execute_query(query, capture_aql=True)
            baseline_count = len(baseline_results)
            logging.info(f"Baseline returned {baseline_count} results")
            
            # Calculate IDs for baseline results
            baseline_ids = extract_ids(baseline_results)
            logging.info(f"Extracted {len(baseline_ids)} unique IDs from baseline results")
            
            # Test each collection group
            for group_name, collections in collection_groups.items():
                logging.info(f"Testing ablation of collection group: {group_name}")
                
                # Ablate the collections
                for collection in collections:
                    collections_metadata.ablate_collection(collection)
                    logging.info(f"Ablated collection: {collection}")
                
                # Run the ablated query
                ablated_results = fixed_execute_query(query, capture_aql=True)
                ablated_count = len(ablated_results)
                logging.info(f"With {group_name} ablated: query returned {ablated_count} results")
                
                # Calculate IDs for ablated results
                ablated_ids = extract_ids(ablated_results)
                
                # Calculate metrics
                metrics = calculate_metrics(baseline_ids, ablated_ids)
                
                # Store results for this ablation test
                query_results["ablation_tests"][group_name] = {
                    "ablated_collections": collections,
                    "baseline_count": baseline_count,
                    "ablated_count": ablated_count,
                    "metrics": metrics
                }
                
                # Restore the collections
                for collection in collections:
                    collections_metadata.restore_collection(collection)
                    logging.info(f"Restored collection: {collection}")
            
            # Store results for this query
            results["ablation_results"][query] = query_results
        
        # Calculate overall metrics for each collection group
        overall_metrics = calculate_overall_metrics(results)
        results["overall_metrics"] = overall_metrics
        
        # Save results to file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "./ablation_results"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"ablation_test_results_{timestamp}.json")
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
            
        logging.info(f"Results saved to {output_file}")
        
        # Generate a summary report
        generate_summary_report(results, timestamp)
        
        return results
        
    except Exception as e:
        logging.error(f"Error in run_ablation_test: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_ids(results: List[Dict[str, Any]]) -> Set[str]:
    """Extract unique IDs from query results."""
    id_fields = ["_id", "_key", "ID", "ObjectIdentifier", "Handle", "URI"]
    ids = set()
    
    for result in results:
        if not isinstance(result, dict):
            continue
            
        for field in id_fields:
            if field in result:
                ids.add(str(result[field]))
                break
                
    return ids

def calculate_metrics(baseline_ids: Set[str], ablated_ids: Set[str]) -> Dict[str, float]:
    """Calculate precision, recall, and F1 metrics."""
    # Calculate true positives, false positives, false negatives
    true_positives = len(ablated_ids.intersection(baseline_ids))
    false_positives = len(ablated_ids - baseline_ids)
    false_negatives = len(baseline_ids - ablated_ids)
    
    # Calculate precision, recall, F1 score
    if true_positives + false_positives > 0:
        precision = true_positives / (true_positives + false_positives)
    else:
        precision = 1.0
        
    if true_positives + false_negatives > 0:
        recall = true_positives / (true_positives + false_negatives)
    else:
        recall = 1.0
        
    if precision + recall > 0:
        f1 = 2 * (precision * recall) / (precision + recall)
    else:
        f1 = 0.0
        
    # Impact is defined as the change in F1 score
    impact = 1.0 - f1
    
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "impact": impact,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives
    }

def calculate_overall_metrics(results: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """Calculate overall metrics for each collection group."""
    # Extract all collection groups
    collection_groups = set()
    metrics_fields = ["precision", "recall", "f1", "impact"]
    
    for query_results in results.get("ablation_results", {}).values():
        for group_name in query_results.get("ablation_tests", {}).keys():
            collection_groups.add(group_name)
    
    # Calculate average metrics for each collection group
    overall_metrics = {}
    
    for group_name in collection_groups:
        group_metrics = {}
        
        for metric in metrics_fields:
            values = []
            
            for query_results in results.get("ablation_results", {}).values():
                if group_name in query_results.get("ablation_tests", {}):
                    value = query_results["ablation_tests"][group_name]["metrics"].get(metric, 0)
                    values.append(value)
            
            if values:
                group_metrics[metric] = sum(values) / len(values)
            else:
                group_metrics[metric] = 0.0
        
        overall_metrics[group_name] = group_metrics
    
    return overall_metrics

def generate_summary_report(results: Dict[str, Any], timestamp: str):
    """Generate a human-readable summary report."""
    output_dir = "./ablation_results"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"ablation_summary_{timestamp}.txt")
    
    with open(output_file, 'w') as f:
        f.write("Indaleko Ablation Test Summary\n")
        f.write("=============================\n\n")
        f.write(f"Test run: {timestamp}\n\n")
        
        # Write overall metrics
        f.write("Collection Impact Metrics\n")
        f.write("----------------------\n")
        for group_name, metrics in results.get("overall_metrics", {}).items():
            f.write(f"{group_name}:\n")
            f.write(f"  Precision: {metrics.get('precision', 0):.4f}\n")
            f.write(f"  Recall: {metrics.get('recall', 0):.4f}\n")
            f.write(f"  F1 Score: {metrics.get('f1', 0):.4f}\n")
            f.write(f"  Impact: {metrics.get('impact', 0):.4f}\n")
        
        # Write detailed results for each query
        f.write("\nDetailed Query Results\n")
        f.write("--------------------\n")
        for query, query_results in results.get("ablation_results", {}).items():
            f.write(f"\nQuery: {query}\n")
            
            for test_name, test_results in query_results.get("ablation_tests", {}).items():
                metrics = test_results.get("metrics", {})
                f.write(f"  With {test_name} ablated:\n")
                f.write(f"    Results: {test_results.get('ablated_count', 0)}\n")
                f.write(f"    Precision: {metrics.get('precision', 0):.4f}\n")
                f.write(f"    Recall: {metrics.get('recall', 0):.4f}\n")
                f.write(f"    F1 Score: {metrics.get('f1', 0):.4f}\n")
                f.write(f"    Impact Score: {metrics.get('impact', 0):.4f}\n")
                f.write(f"    True Positives: {metrics.get('true_positives', 0)}\n")
                f.write(f"    False Positives: {metrics.get('false_positives', 0)}\n")
                f.write(f"    False Negatives: {metrics.get('false_negatives', 0)}\n")
    
    logging.info(f"Summary report saved to {output_file}")

def main():
    """Main entry point."""
    logging.info("Running simplified ablation test")
    run_ablation_test()
    logging.info("Test completed")

if __name__ == "__main__":
    main()