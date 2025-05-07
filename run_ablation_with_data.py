#!/usr/bin/env python3
"""
Ablation testing with pre-generated test data.

This script runs ablation tests using pre-generated test data, measures the impact 
of ablating various collections on query results, and generates a comprehensive report.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import os
import sys
import logging
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

# Set up environment variables and paths
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

def setup_logging(level=logging.INFO):
    """Set up logging configuration."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    logging.info("Logging initialized.")

def run_data_generation():
    """Run the data generation script."""
    logging.info("Generating test data...")
    
    try:
        result = subprocess.run(
            ["python", "generate_ablation_test_data.py"],
            check=True,
            capture_output=True,
            text=True
        )
        
        logging.info("Data generation completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Data generation failed: {e}")
        logging.error(f"Output: {e.output}")
        logging.error(f"Error: {e.stderr}")
        return False

def run_ablation_tests():
    """Run ablation tests for each query from the truth data."""
    logging.info("Starting ablation tests...")
    
    try:
        # Load truth data to get queries
        with open("ablation_results/truth_data.json", "r") as f:
            truth_data = json.load(f)
        
        # Get the test queries
        queries = list(truth_data["query_truth_data"].keys())
        logging.info(f"Found {len(queries)} queries to test.")
        
        # For each query, determine the collection to ablate based on metadata
        for query in queries:
            query_data = truth_data["query_truth_data"][query]
            collection = query_data["metadata"]["collection"]
            
            logging.info(f"Testing query: '{query}' by ablating collection: {collection}")
            
            # Run the ablation test for this query
            result = subprocess.run(
                [
                    "python", "run_ablation_test.py",
                    "--mode", "simple",
                    "--query", query,
                    "--collection", collection,
                    "--debug"
                ],
                check=True,
                capture_output=True,
                text=True
            )
            
            logging.info(f"Completed test for query: '{query}'")
            
            # Give DB connection time to release
            time.sleep(1)
        
        # Also run a comprehensive test
        logging.info("Running comprehensive ablation test...")
        result = subprocess.run(
            [
                "python", "run_ablation_test.py",
                "--mode", "comprehensive",
                "--num-clusters", "3",
                "--num-queries", "10",
                "--dataset-size", "50",
                "--output-dir", "ablation_results/comprehensive",
                "--debug"
            ],
            check=True,
            capture_output=True,
            text=True
        )
        
        logging.info("All ablation tests completed successfully.")
        return True
    except Exception as e:
        logging.error(f"Error running ablation tests: {e}")
        return False

def generate_final_report():
    """Generate a final report combining all test results."""
    logging.info("Generating final report...")
    
    try:
        # Create output directory
        os.makedirs("ablation_results/comprehensive", exist_ok=True)
        
        # Find all simple test results
        results_files = []
        for f in os.listdir("ablation_results"):
            if f.startswith("simple_ablation_") and f.endswith(".json"):
                results_files.append(os.path.join("ablation_results", f))
        
        results_files.sort(key=os.path.getmtime)  # Sort by modification time
        
        # Load the most recent results
        recent_results = []
        for f in results_files[-len(results_files):]:
            with open(f, "r") as file:
                recent_results.append(json.load(file))
        
        # Load truth data
        with open("ablation_results/truth_data.json", "r") as f:
            truth_data = json.load(f)
        
        # Generate report
        report_path = "ablation_results/final_report.md"
        with open(report_path, "w") as f:
            f.write("# Indaleko Ablation Study Final Report\n\n")
            f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Summary\n\n")
            f.write("This report summarizes the impact of ablating different collections on query performance.\n\n")
            
            f.write("## Test Queries\n\n")
            f.write("| Query | Collection | Expected Matches |\n")
            f.write("|-------|------------|-----------------|\n")
            
            for query, data in truth_data["query_truth_data"].items():
                collection = data["metadata"]["collection"]
                match_count = len(data["matching_document_ids"])
                f.write(f"| {query} | {collection} | {match_count} |\n")
            
            f.write("\n## Individual Test Results\n\n")
            f.write("| Query | Collection | Baseline Results | Ablated Results | Precision | Recall | F1 Score | Impact |\n")
            f.write("|-------|------------|------------------|-----------------|-----------|--------|----------|--------|\n")
            
            for result in recent_results:
                query = result["query"]
                collection = ", ".join(result["ablated_collections"])
                baseline_count = result["metrics"]["baseline_count"]
                ablated_count = result["metrics"]["ablated_count"]
                precision = result["metrics"].get("precision", 0)
                recall = result["metrics"].get("recall", 0)
                f1 = result["metrics"].get("f1", 0)
                impact = 0 if f1 == 0 else 1 - f1
                
                f.write(f"| {query} | {collection} | {baseline_count} | {ablated_count} | {precision:.4f} | {recall:.4f} | {f1:.4f} | {impact:.4f} |\n")
            
            # Add conclusions
            f.write("\n## Conclusions\n\n")
            
            # Calculate average impact by collection
            collection_impacts = {}
            for result in recent_results:
                collection = result["ablated_collections"][0] if result["ablated_collections"] else "Unknown"
                impact = 0 if result["metrics"].get("f1", 0) == 0 else 1 - result["metrics"].get("f1", 0)
                
                if collection not in collection_impacts:
                    collection_impacts[collection] = {"total": 0, "count": 0}
                
                collection_impacts[collection]["total"] += impact
                collection_impacts[collection]["count"] += 1
            
            f.write("### Collection Impact Analysis\n\n")
            f.write("| Collection | Average Impact | Test Count |\n")
            f.write("|------------|----------------|------------|\n")
            
            for collection, data in collection_impacts.items():
                avg_impact = data["total"] / data["count"] if data["count"] > 0 else 0
                f.write(f"| {collection} | {avg_impact:.4f} | {data['count']} |\n")
            
            f.write("\n### Findings\n\n")
            
            # Sort collections by impact
            sorted_collections = sorted(
                collection_impacts.items(), 
                key=lambda x: x[1]["total"] / x[1]["count"] if x[1]["count"] > 0 else 0,
                reverse=True
            )
            
            if sorted_collections:
                most_important = sorted_collections[0][0]
                most_impact = sorted_collections[0][1]["total"] / sorted_collections[0][1]["count"] if sorted_collections[0][1]["count"] > 0 else 0
                
                f.write(f"1. The {most_important} collection has the highest impact on query results with an average impact of {most_impact:.4f}.\n")
                
                if len(sorted_collections) > 1:
                    least_important = sorted_collections[-1][0]
                    least_impact = sorted_collections[-1][1]["total"] / sorted_collections[-1][1]["count"] if sorted_collections[-1][1]["count"] > 0 else 0
                    
                    f.write(f"2. The {least_important} collection has the lowest impact on query results with an average impact of {least_impact:.4f}.\n")
                
                f.write("\n3. Implications for the null hypothesis (\"activity data does not impact query performance\"):\n")
                if most_impact > 0.1:  # Threshold for significance
                    f.write("   - The null hypothesis is rejected. Activity data has a significant impact on query performance.\n")
                else:
                    f.write("   - The null hypothesis cannot be rejected with the current data. More testing is needed.\n")
            
            f.write("\n## Raw Result Data\n\n")
            f.write("Full test result details can be found in the JSON files in the `ablation_results` directory.\n")
        
        logging.info(f"Final report generated at {report_path}")
        return True
    except Exception as e:
        logging.error(f"Error generating final report: {e}")
        return False

def main():
    """Main function."""
    setup_logging(level=logging.INFO)
    logging.info("Starting ablation testing with real data...")
    
    # Create output directory
    os.makedirs("ablation_results", exist_ok=True)
    
    # Step 1: Generate test data
    if not run_data_generation():
        logging.error("Data generation failed. Aborting.")
        return 1
    
    # Step 2: Run ablation tests
    if not run_ablation_tests():
        logging.error("Ablation tests failed. Aborting.")
        return 1
    
    # Step 3: Generate final report
    if not generate_final_report():
        logging.error("Report generation failed.")
        return 1
    
    logging.info("Ablation testing completed successfully.")
    logging.info("Results are available in the 'ablation_results' directory.")
    return 0

if __name__ == "__main__":
    sys.exit(main())