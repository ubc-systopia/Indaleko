#!/usr/bin/env python3
"""Comprehensive ablation test runner with cross-collection support.

This script implements a complete ablation testing framework that can measure
the impact of ablating different activity data types on search precision and recall.
It supports testing multiple activity collections and handles cross-collection dependencies.
"""

import argparse
import json
import logging
import os
import random
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# Check for visualization dependencies
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from db.db_config import IndalekoDBConfig
from research.ablation.ablation_tester import AblationConfig, AblationTester
from research.ablation.base import ISyntheticCollector, ISyntheticRecorder
from research.ablation.collectors.location_collector import LocationActivityCollector
from research.ablation.collectors.music_collector import MusicActivityCollector
from research.ablation.collectors.task_collector import TaskActivityCollector
from research.ablation.data_sanity_checker import DataSanityChecker
from research.ablation.ner.entity_manager import NamedEntityManager
from research.ablation.recorders.location_recorder import LocationActivityRecorder
from research.ablation.recorders.music_recorder import MusicActivityRecorder
from research.ablation.recorders.task_recorder import TaskActivityRecorder
from research.ablation.utils.uuid_utils import generate_deterministic_uuid


def setup_logging():
    """Set up logging for the ablation test runner."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def generate_test_data(
        entity_manager: NamedEntityManager,
        activity_data_providers: list[tuple[str, ISyntheticCollector, ISyntheticRecorder]],
        count: int = 100
) -> dict:
    """Generate synthetic test data for all activity types.

    Args:
        entity_manager: The named entity manager for consistent entity references
        activity_data_providers: List of tuples containing activity data provider name, collector, and recorder
        count: Number of test records to generate per collection

    Returns:
        dict: Dictionary of generated data by collection type
    """
    logging.info(f"Generating {count} records for each activity type...")

    test_data = {}
    collections_loaded = []

    for activity_data_provider_name, collector, recorder in activity_data_providers:
        collector = collector(entity_manager=entity_manager, seed_value=42)
        recorder = recorder()

        data = collector.generate_batch(count)

        # Ensure all data has an ID field
        for item in data:
            if "id" not in item:
                # Create a content hash based on common fields or activity-specific fields
                if activity_data_provider_name == "Location":
                    content_hash = f"location:{item.get('location_name', 'unknown')}:{item.get('device_name', 'unknown')}"
                elif activity_data_provider_name == "Task":
                    content_hash = f"task:{item.get('task_name', 'unknown')}:{item.get('application', 'unknown')}"
                elif activity_data_provider_name == "Music":
                    content_hash = f"music:{item.get('track_name', 'unknown')}:{item.get('artist', 'unknown')}"
                else:
                    # Generic fallback if the activity type is unknown
                    content_hash = f"{activity_data_provider_name}:item-{hash(str(item))}"
                
                item["id"] = generate_deterministic_uuid(content_hash)

        batch_success = recorder.record_batch(data)

        if batch_success:
            collections_loaded.append(activity_data_provider_name)
            test_data[activity_data_provider_name] = data
            logging.info("Successfully loaded %s %s activity records",
                         len(data),
                         activity_data_provider_name
            )
        else:
            logging.warning("Failed to record %s data", activity_data_provider_name)

    logging.info(f"Successfully loaded data for {len(collections_loaded)} collections: {', '.join(collections_loaded)}")
    return test_data


def generate_cross_collection_queries(
        entity_manager: NamedEntityManager,
        ablation_tester: AblationTester,
        count: int = 5
) -> list[dict[str, object]]:
    """Generate test queries that depend on multiple activity types.

    Args:
        entity_manager: The named entity manager for consistent entity references
        ablation_tester: The ablation tester for recording truth data
        count: Number of test queries to generate per combination

    Returns:
        list: List of generated queries with metadata
    """
    logging.info(f"Generating cross-collection test queries...")

    queries = []

    # Collection combinations to test
    combinations = [
        ["AblationLocationActivity", "AblationTaskActivity"],
        ["AblationLocationActivity", "AblationMusicActivity"],
        ["AblationTaskActivity", "AblationMusicActivity"],
    ]

    # Simplified version that just tests location and task for now
    combinations = [["AblationLocationActivity", "AblationTaskActivity"]]

    for collection_pair in combinations:
        collection1, collection2 = collection_pair
        logging.info(f"Generating queries for {collection1} and {collection2} pair")

        # Create a query template that spans both collections
        template = f"Find documents I worked on at {{location}} while listening to {{music}}"
        if "TaskActivity" in collection1 or "TaskActivity" in collection2:
            template = f"Find documents related to {{task}} that I worked on at {{location}}"

        # Register consistent entities
        entity_manager.register_entity("location", "Home")
        entity_manager.register_entity("task", "Quarterly Report")
        entity_manager.register_entity("music", "Classical Piano")

        # Generate queries for this combination
        for i in range(count):
            query_text = template.format(
                location="Home",
                task="Quarterly Report",
                music="Classical Piano"
            )

            # Generate deterministic query ID
            query_id = generate_deterministic_uuid(f"query:{collection1}:{collection2}:{i}")

            # Generate matching entities for each collection
            matching_entities = {}

            for collection in collection_pair:
                # Generate 5 matching entities per collection
                entity_ids = []
                for j in range(5):
                    entity_id = str(generate_deterministic_uuid(f"{collection}:match:{query_text}:{j}"))
                    entity_ids.append(entity_id)

                # Store truth data with composite key
                ablation_tester.store_truth_data(query_id, collection, entity_ids)
                matching_entities[collection] = entity_ids

            # Add query to the list
            queries.append({
                "id": str(query_id),
                "text": query_text,
                "type": "cross_collection",
                "collections": collection_pair,
                "matching_entities": matching_entities
            })

            logging.info(f"Generated query {i+1}/{count} for {collection1} + {collection2}: '{query_text}'")

    return queries


def test_ablation_impact(ablation_tester: AblationTester, queries: list[dict[str, object]]):
    """Test the impact of ablating each collection on query results.

    Args:
        ablation_tester: The ablation tester to use
        queries: List of query dictionaries with metadata

    Returns:
        dict: Dictionary of impact metrics by collection and query
    """
    logging.info("Testing ablation impact...")

    impact_metrics = {}

    for query in queries:
        query_id = uuid.UUID(query["id"])
        query_text = query["text"]
        collections = query.get("collections", [])

        logging.info(f"Testing ablation impact for query: '{query_text}'")

        # Configure the ablation test
        config = AblationConfig(
            collections_to_ablate=collections,
            query_limit=100,
            include_metrics=True,
            include_execution_time=True,
            verbose=True
        )

        # Run the ablation test
        results = ablation_tester.run_ablation_test(config, query_id, query_text)

        # Store the results
        impact_metrics[str(query_id)] = {
            "query_text": query_text,
            "results": {k: r.dict() for k, r in results.items()}
        }

        logging.info(f"Completed ablation test for query {query_id}")

    return impact_metrics


def visualize_results(impact_metrics: dict[str, object], output_dir: str):
    """Create visualizations of ablation test results.

    Args:
        impact_metrics: Dictionary of impact metrics by query
        output_dir: Directory to save visualizations

    Returns:
        list: List of saved visualization file paths
    """
    if not VISUALIZATION_AVAILABLE:
        logging.warning("Visualization dependencies not installed, skipping visualizations")
        return []

    logging.info("Generating visualizations...")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    saved_files = []

    # Extract data for visualization
    collections = set()
    impact_data = []

    for query_id, query_data in impact_metrics.items():
        query_text = query_data["query_text"]
        results = query_data["results"]

        for impact_key, metrics in results.items():
            if "_impact_on_" in impact_key:
                # Extract collection names from impact key
                src, dst = impact_key.split("_impact_on_")
                src = src.split("Ablation")[1].split("Activity")[0]
                dst = dst.split("Ablation")[1].split("Activity")[0]

                collections.add(src)
                collections.add(dst)

                # Extract metrics
                impact_data.append({
                    "query_id": query_id,
                    "query_text": query_text,
                    "source_collection": src,
                    "target_collection": dst,
                    "precision": metrics["precision"],
                    "recall": metrics["recall"],
                    "f1_score": metrics["f1_score"],
                    "impact": 1.0 - metrics["f1_score"]
                })

    if not impact_data:
        logging.warning("No impact data available for visualization")
        return []

    # Convert to DataFrame
    df = pd.DataFrame(impact_data)

    # 1. Impact Heatmap
    plt.figure(figsize=(10, 8))
    pivot_df = df.pivot_table(
        index="source_collection",
        columns="target_collection",
        values="impact",
        aggfunc="mean"
    )

    sns.heatmap(pivot_df, annot=True, cmap="YlOrRd", vmin=0, vmax=1, fmt=".2f")
    plt.title("Impact of Ablating Source Collection on Target Collection")
    plt.tight_layout()

    heatmap_path = os.path.join(output_dir, "impact_heatmap.png")
    plt.savefig(heatmap_path)
    saved_files.append(heatmap_path)
    plt.close()

    # 2. Precision/Recall Scatter Plot
    plt.figure(figsize=(10, 8))
    sns.scatterplot(
        x="precision",
        y="recall",
        hue="source_collection",
        size="impact",
        sizes=(50, 200),
        data=df
    )
    plt.title("Precision vs. Recall by Collection")
    plt.xlim(0, 1)
    plt.ylim(0, 1)
    plt.tight_layout()

    scatter_path = os.path.join(output_dir, "precision_recall.png")
    plt.savefig(scatter_path)
    saved_files.append(scatter_path)
    plt.close()

    # 3. Impact by Collection Bar Chart
    plt.figure(figsize=(12, 8))
    impact_by_collection = df.groupby("source_collection")["impact"].mean().reset_index()
    sns.barplot(x="source_collection", y="impact", data=impact_by_collection)
    plt.title("Average Impact by Collection")
    plt.ylim(0, 1)
    plt.tight_layout()

    barchart_path = os.path.join(output_dir, "impact_by_collection.png")
    plt.savefig(barchart_path)
    saved_files.append(barchart_path)
    plt.close()

    # 4. F1 Score by Collection
    plt.figure(figsize=(12, 8))
    f1_by_collection = df.groupby("source_collection")["f1_score"].mean().reset_index()
    sns.barplot(x="source_collection", y="f1_score", data=f1_by_collection)
    plt.title("Average F1 Score by Collection")
    plt.ylim(0, 1)
    plt.tight_layout()

    f1_path = os.path.join(output_dir, "f1_by_collection.png")
    plt.savefig(f1_path)
    saved_files.append(f1_path)
    plt.close()

    logging.info(f"Saved {len(saved_files)} visualizations to {output_dir}")

    return saved_files


def generate_summary_report(impact_metrics: dict[str, object], output_dir: str):
    """Generate a summary report of ablation test results.

    Args:
        impact_metrics: Dictionary of impact metrics by query
        output_dir: Directory to save the report

    Returns:
        str: Path to the generated report
    """
    logging.info("Generating summary report...")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Extract data for the report
    collections = set()
    impact_data = []

    for query_id, query_data in impact_metrics.items():
        query_text = query_data["query_text"]
        results = query_data["results"]

        for impact_key, metrics in results.items():
            if "_impact_on_" in impact_key:
                # Extract collection names from impact key
                src, dst = impact_key.split("_impact_on_")
                src = src.split("Ablation")[1].split("Activity")[0]
                dst = dst.split("Ablation")[1].split("Activity")[0]

                collections.add(src)
                collections.add(dst)

                # Extract metrics
                impact_data.append({
                    "query_id": query_id,
                    "query_text": query_text,
                    "source_collection": src,
                    "target_collection": dst,
                    "precision": metrics["precision"],
                    "recall": metrics["recall"],
                    "f1_score": metrics["f1_score"],
                    "impact": 1.0 - metrics["f1_score"],
                    "true_positives": metrics["true_positives"],
                    "false_positives": metrics["false_positives"],
                    "false_negatives": metrics["false_negatives"]
                })

    if not impact_data:
        logging.warning("No impact data available for report")
        return ""

    # Convert to DataFrame for analysis
    df = pd.DataFrame(impact_data)

    # Generate report content
    report = []
    report.append("# Ablation Study Results Summary\n")
    report.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    report.append("## Overview\n")
    report.append(f"This report summarizes the results of ablation testing for {len(collections)} activity types: ")
    report.append(", ".join(sorted(collections)))
    report.append(".\n\n")
    report.append(f"A total of {len(impact_metrics)} test queries were evaluated, ")
    report.append(f"generating {len(impact_data)} impact measurements.\n")

    report.append("## Impact Summary\n")

    # Average impact by collection
    report.append("### Average Impact by Collection\n")
    report.append("Impact represents how much query performance degrades when a collection is removed.\n")
    report.append("Higher values indicate more important collections.\n\n")
    report.append("| Collection | Average Impact | Precision | Recall | F1 Score |\n")
    report.append("|------------|---------------|-----------|--------|----------|\n")

    collection_impacts = df.groupby("source_collection").agg({
        "impact": "mean",
        "precision": "mean",
        "recall": "mean",
        "f1_score": "mean"
    }).reset_index()

    for _, row in collection_impacts.sort_values("impact", ascending=False).iterrows():
        report.append(f"| {row['source_collection']} | {row['impact']:.3f} | {row['precision']:.3f} | ")
        report.append(f"{row['recall']:.3f} | {row['f1_score']:.3f} |\n")

    report.append("\n## Cross-Collection Dependencies\n")
    report.append("This table shows how ablating each collection (rows) affects queries targeting other collections (columns).\n\n")

    # Create a pivot table for cross-collection impact
    pivot_df = df.pivot_table(
        index="source_collection",
        columns="target_collection",
        values="impact",
        aggfunc="mean"
    )

    # Generate the table
    header = "| Source \\ Target | " + " | ".join(sorted(pivot_df.columns)) + " |\n"
    separator = "|" + "|".join(["-" * 15] * (len(pivot_df.columns) + 1)) + "|\n"
    report.append(header)
    report.append(separator)

    for idx, row in pivot_df.iterrows():
        line = f"| {idx} |"
        for col in sorted(pivot_df.columns):
            val = row.get(col, np.nan)
            if pd.isna(val):
                line += " N/A |"
            else:
                line += f" {val:.3f} |"
        report.append(line + "\n")

    report.append("\n## Query Analysis\n")
    report.append("### Most Affected Queries\n")
    report.append("| Query | Source Collection | Target Collection | Impact |\n")
    report.append("|-------|-------------------|-------------------|--------|\n")

    # Top 5 most affected queries
    top_impacts = df.sort_values("impact", ascending=False).head(5)
    for _, row in top_impacts.iterrows():
        truncated_query = row["query_text"][:50] + "..." if len(row["query_text"]) > 50 else row["query_text"]
        report.append(f"| {truncated_query} | {row['source_collection']} | ")
        report.append(f"{row['target_collection']} | {row['impact']:.3f} |\n")

    report.append("\n## Recommendations\n")
    high_impact_collections = collection_impacts[collection_impacts["impact"] > 0.5]["source_collection"].tolist()
    if high_impact_collections:
        report.append("Based on the ablation results, the following collections have high impact scores ")
        report.append("and should be prioritized in the search infrastructure:\n\n")
        for coll in high_impact_collections:
            report.append(f"- **{coll}**: Impact score {collection_impacts[collection_impacts['source_collection'] == coll]['impact'].values[0]:.3f}\n")
    else:
        report.append("No collections showed particularly high impact scores (>0.5). ")
        report.append("This suggests that no single activity type is critical for overall search performance.\n")

    # Strongest cross-collection dependencies
    top_dependencies = df[df["source_collection"] != df["target_collection"]].sort_values("impact", ascending=False).head(3)
    if not top_dependencies.empty:
        report.append("\nThe strongest cross-collection dependencies were found between:\n\n")
        for _, row in top_dependencies.iterrows():
            report.append(f"- **{row['source_collection']}** → **{row['target_collection']}**: Impact {row['impact']:.3f}\n")

        report.append("\nThese dependencies suggest that optimizing collection relationships could ")
        report.append("improve search performance by leveraging cross-collection information.\n")

    # Save the report
    report_path = os.path.join(output_dir, "ablation_summary.md")
    with open(report_path, "w") as f:
        f.write("".join(report))

    logging.info(f"Saved summary report to {report_path}")

    return report_path


def clear_existing_data():
    """Clear existing data from all activity collections."""
    logging.info("Clearing existing data...")

    collections = [
        "AblationLocationActivity",
        "AblationTaskActivity",
        "AblationMusicActivity",
        "AblationTruthData"
    ]

    # Following fail-stop model - let exceptions propagate
    db_config = IndalekoDBConfig()
    db = db_config.get_arangodb()

    for collection_name in collections:
        if db.has_collection(collection_name):
            db.aql.execute(f"FOR doc IN {collection_name} REMOVE doc IN {collection_name}")
            logging.info(f"Cleared collection {collection_name}")
            
    logging.info("Data cleared successfully")


def main():
    """Run the comprehensive ablation test."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run comprehensive ablation tests")
    parser.add_argument("--count", type=int, default=100, help="Number of test records per collection")
    parser.add_argument("--queries", type=int, default=5, help="Number of test queries per collection combination")
    parser.add_argument("--clear", action="store_true", help="Clear existing data before running tests")
    parser.add_argument("--visualize", action="store_true", help="Generate visualizations")
    parser.add_argument("--output-dir", type=str, help="Output directory for results")
    args = parser.parse_args()

    # Set up logging
    setup_logging()
    logger = logging.getLogger(__name__)

    # Create output directory with timestamp if not specified
    output_dir = args.output_dir
    if not output_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"ablation_results_{timestamp}"

    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"Starting comprehensive ablation tests, results will be saved to {output_dir}")

    # Following fail-stop model: no try-except here
    # This allows errors to propagate and cause immediate failure

    # Create cleanup variable for finally block
    ablation_tester = None

    # Clear existing data if requested
    if args.clear:
        clear_existing_data()

    # Initialize entity manager for consistent entity references
    entity_manager = NamedEntityManager()

    # Initialize ablation tester
    ablation_tester = AblationTester()

    # Set up activity data providers
    # Each provider is a tuple: (name, collector_class, recorder_class)
    activity_data_providers = [
        ("Location", LocationActivityCollector, LocationActivityRecorder),
        # Only use the following if they're fully implemented:
        # ("Task", TaskActivityCollector, TaskActivityRecorder),
        # ("Music", MusicActivityCollector, MusicActivityRecorder),
    ]
    
    # Generate test data using the providers
    test_data = generate_test_data(
        entity_manager, 
        activity_data_providers,
        count=args.count
    )
    
    if not test_data:
        logger.error("Failed to generate test data")
        sys.exit(1)

    # Run data sanity check
    logger.info("Running data sanity check...")
    checker = DataSanityChecker(fail_fast=True)  # Changed to fail_fast=True for fail-stop model
    sanity_check_passed = checker.run_all_checks()

    # Generate cross-collection test queries
    queries = generate_cross_collection_queries(entity_manager, ablation_tester, count=args.queries)
    if not queries:
        logger.error("Failed to generate test queries")
        sys.exit(1)

    # Test ablation impact
    impact_metrics = test_ablation_impact(ablation_tester, queries)

    # Save raw metrics
    metrics_path = os.path.join(output_dir, "impact_metrics.json")
    with open(metrics_path, "w") as f:
        # Convert UUID objects to strings to prevent JSON serialization errors
        serializable_metrics = json.loads(
            json.dumps(impact_metrics, default=lambda o: str(o) if isinstance(o, uuid.UUID) else o)
        )
        json.dump(serializable_metrics, f, indent=2)

    logger.info(f"Saved raw metrics to {metrics_path}")

    # Generate visualizations if requested
    if args.visualize:
        visualize_results(impact_metrics, output_dir)

    # Generate summary report
    report_path = generate_summary_report(impact_metrics, output_dir)

    if report_path:
        logger.info(f"Test completed successfully, see {report_path} for summary")
    else:
        logger.warning("Test completed but no report was generated")
        
    # Ensure cleanup is run regardless of success/failure
    if ablation_tester:
        ablation_tester.cleanup()


if __name__ == "__main__":
    main()
