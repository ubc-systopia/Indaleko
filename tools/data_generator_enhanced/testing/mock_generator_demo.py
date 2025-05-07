#!/usr/bin/env python3
"""
Simplified demonstration of the ablation testing framework.

This script provides a simple demo that shows the structure of the ablation
test framework without requiring all the data generators to be implemented.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import os
import sys
import random
import logging
import json
import datetime
import time
from typing import Dict, List, Any

# Add the Indaleko root to the path
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import Indaleko modules
from db.db_collections import IndalekoDBCollections
from tools.data_generator_enhanced.testing.cluster_generator import ClusterGenerator
from tools.data_generator_enhanced.testing.query_generator_enhanced import QueryGenerator
from tools.data_generator_enhanced.testing.truth_data_tracker import TruthDataTracker


def setup_logging(level=logging.INFO, log_file=None):
    """Set up logging configuration."""
    handlers = [logging.StreamHandler()]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers
    )


def demo_cluster_generator(seed=42):
    """Demonstrate the ClusterGenerator."""
    logging.info("Demonstrating ClusterGenerator...")
    
    generator = ClusterGenerator(seed=seed)
    
    # List available sources
    sources = generator.list_sources()
    logging.info(f"Available sources: {len(sources)}")
    for source in sources:
        logging.info(f"- {source['name']}: {source['description']}")
        logging.info(f"  Collection: {source['collection']}")
        logging.info(f"  Categories: {', '.join(source['categories'])}")
    
    # Generate random clusters
    clusters = generator.generate_clusters(num_clusters=3)
    logging.info(f"Generated {len(clusters)} random clusters")
    
    # Generate balanced clusters
    balanced_clusters = generator.create_balanced_clusters()
    logging.info(f"Generated {len(balanced_clusters)} balanced clusters")
    
    return balanced_clusters[0]  # Return the first balanced cluster for use in other demos


def demo_query_generator(cluster, seed=42):
    """Demonstrate the QueryGenerator."""
    logging.info("Demonstrating QueryGenerator...")
    
    generator = QueryGenerator(seed=seed)
    
    # List available categories
    categories = generator.get_available_categories()
    logging.info(f"Available query categories: {', '.join(categories)}")
    
    # Generate some random queries
    logging.info("Generating random queries:")
    for i in range(3):
        query = generator.generate_query()
        logging.info(f"- {query['text']}")
        logging.info(f"  Categories: {', '.join(query['categories'])}")
    
    # Generate queries for the cluster
    queries = generator.generate_queries_for_cluster(cluster, num_queries=6)
    logging.info(f"Generated {len(queries['experimental'])} experimental queries and {len(queries['control'])} control queries")
    
    return queries


def demo_truth_data_tracker(cluster, queries):
    """Demonstrate the TruthDataTracker."""
    logging.info("Demonstrating TruthDataTracker...")
    
    # Use in-memory database for the demo
    tracker = TruthDataTracker(":memory:")
    
    # Create a study
    study_id = tracker.create_study(
        "Demo Ablation Study",
        "Demonstration of the TruthDataTracker",
        {"seed": 42, "clusters": 1, "timestamp": datetime.datetime.now().isoformat()}
    )
    logging.info(f"Created study with ID: {study_id}")
    
    # Add the cluster
    experimental_sources = [source["name"] for source in cluster["experimental_sources"]]
    control_sources = [source["name"] for source in cluster["control_sources"]]
    
    cluster_id = tracker.add_cluster(
        study_id=study_id,
        name=cluster["name"],
        experimental_sources=experimental_sources,
        control_sources=control_sources
    )
    logging.info(f"Added cluster with ID: {cluster_id}")
    
    # Add queries
    query_ids = []
    for query_type, query_list in queries.items():
        for query in query_list:
            query_text = query["text"]
            query_id = tracker.add_query(
                study_id=study_id,
                text=query_text,
                category=query_type,
                metadata_categories=query.get("categories", [])
            )
            logging.info(f"Added {query_type} query: {query_text}")
            query_ids.append(query_id)
    
    # Add some truth data
    for query_id in query_ids:
        for i in range(5):
            document_id = f"doc_{i}_{random.randint(1000, 9999)}"
            is_matching = random.choice([True, False])
            
            tracker.add_truth_data(
                query_id=query_id,
                document_id=document_id,
                matching=is_matching,
                metadata={"type": "document", "created_at": datetime.datetime.now().isoformat()}
            )
        logging.info(f"Added truth data for query {query_id}")
    
    # Add some mock ablation results
    for query_id in query_ids:
        # Add result for individual experimental source ablation
        for source in experimental_sources:
            tracker.add_ablation_result(
                study_id=study_id,
                cluster_id=cluster_id,
                query_id=query_id,
                ablated_sources=[source],
                returned_ids=[f"doc_{i}" for i in range(3)],
                precision=random.uniform(0.7, 1.0),
                recall=random.uniform(0.6, 1.0),
                f1_score=random.uniform(0.65, 1.0),
                impact=random.uniform(0.0, 0.35),
                execution_time_ms=random.randint(10, 100),
                aql_query="FOR doc IN Objects RETURN doc"
            )
        logging.info(f"Added individual experimental source ablation results for query {query_id}")
        
        # Add result for all experimental sources ablated together
        tracker.add_ablation_result(
            study_id=study_id,
            cluster_id=cluster_id,
            query_id=query_id,
            ablated_sources=experimental_sources,
            returned_ids=[f"doc_{i}" for i in range(2)],
            precision=random.uniform(0.5, 0.8),
            recall=random.uniform(0.4, 0.7),
            f1_score=random.uniform(0.45, 0.75),
            impact=random.uniform(0.25, 0.55),
            execution_time_ms=random.randint(10, 100),
            aql_query="FOR doc IN Objects RETURN doc"
        )
        logging.info(f"Added combined experimental source ablation result for query {query_id}")
        
        # Add result for individual control source ablation
        for source in control_sources:
            tracker.add_ablation_result(
                study_id=study_id,
                cluster_id=cluster_id,
                query_id=query_id,
                ablated_sources=[source],
                returned_ids=[f"doc_{i}" for i in range(4)],
                precision=random.uniform(0.8, 1.0),
                recall=random.uniform(0.8, 1.0),
                f1_score=random.uniform(0.8, 1.0),
                impact=random.uniform(0.0, 0.2),
                execution_time_ms=random.randint(10, 100),
                aql_query="FOR doc IN Objects RETURN doc"
            )
        logging.info(f"Added individual control source ablation results for query {query_id}")
        
        # Add result for all control sources ablated together
        tracker.add_ablation_result(
            study_id=study_id,
            cluster_id=cluster_id,
            query_id=query_id,
            ablated_sources=control_sources,
            returned_ids=[f"doc_{i}" for i in range(3)],
            precision=random.uniform(0.7, 0.9),
            recall=random.uniform(0.7, 0.9),
            f1_score=random.uniform(0.7, 0.9),
            impact=random.uniform(0.1, 0.3),
            execution_time_ms=random.randint(10, 100),
            aql_query="FOR doc IN Objects RETURN doc"
        )
        logging.info(f"Added combined control source ablation result for query {query_id}")
    
    # Generate a report
    report_path = "ablation_demo_results/ablation_report.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    tracker.generate_report(study_id, report_path)
    logging.info(f"Generated report at {report_path}")
    
    return study_id


def main():
    """Run the demonstration."""
    # Set up logging
    os.makedirs("ablation_demo_results", exist_ok=True)
    setup_logging(
        level=logging.INFO,
        log_file="ablation_demo_results/demo.log"
    )
    
    logging.info("Starting Ablation Framework Demonstration...")
    start_time = time.time()
    
    # Set random seed for reproducibility
    random.seed(42)
    
    # Demo ClusterGenerator
    cluster = demo_cluster_generator()
    
    # Demo QueryGenerator
    queries = demo_query_generator(cluster)
    
    # Demo TruthDataTracker
    study_id = demo_truth_data_tracker(cluster, queries)
    
    # Generate a simple summary
    with open("ablation_demo_results/summary.md", "w") as f:
        f.write("# Ablation Framework Demonstration Summary\n\n")
        f.write(f"Demonstration completed at {datetime.datetime.now().isoformat()}\n\n")
        f.write("## Components Demonstrated\n\n")
        f.write("- **ClusterGenerator**: Creates 4/2 split of experimental/control sources\n")
        f.write("- **QueryGenerator**: Generates queries targeting specific activity types\n")
        f.write("- **TruthDataTracker**: Records and evaluates test results\n\n")
        f.write("## Demo Results\n\n")
        f.write(f"- Created a balanced cluster with 4 experimental and 2 control sources\n")
        f.write(f"- Generated queries targeting experimental and control categories\n")
        f.write(f"- Recorded mock ablation test results in SQLite database\n")
        f.write(f"- Generated comprehensive report with metrics\n\n")
        f.write("## Next Steps\n\n")
        f.write("To run a full ablation test with real data, implement the following:\n\n")
        f.write("1. StorageGenerator in tools/data_generator_enhanced/generators/storage.py\n")
        f.write("2. ActivityGenerator in tools/data_generator_enhanced/generators/activity.py\n")
        f.write("3. SemanticGenerator in tools/data_generator_enhanced/generators/semantic.py\n\n")
        f.write("Then, run the full test with:\n\n")
        f.write("```bash\n./run_ablation_test.sh\n```\n")
    
    execution_time = time.time() - start_time
    logging.info(f"Demonstration completed in {execution_time:.2f} seconds")
    logging.info("Results saved to ablation_demo_results/")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())