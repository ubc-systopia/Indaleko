#!/usr/bin/env python3
"""Demo script for the ablation testing framework.

This script demonstrates how to use the ablation testing framework to measure
the impact of different activity types on search precision and recall.
"""

import logging
import os
import sys
import uuid
from datetime import datetime
from typing import Any

# Check for required dependencies
try:
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns

    VISUALIZATION_AVAILABLE = True
except ImportError:
    print("Warning: pandas, matplotlib, or seaborn not installed")
    print("Visualizations will not be generated.")
    print("Install dependencies with: pip install -r requirements.txt")
    VISUALIZATION_AVAILABLE = False

# Handle relative imports
if __name__ == "__main__":
    # Add parent directory to sys.path for absolute imports
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from research.ablation.ablation_test_runner import AblationTestRunner
    from research.ablation.ablation_tester import AblationConfig
    from research.ablation.collectors.location_collector import (
        LocationActivityCollector,
    )
    from research.ablation.collectors.task_collector import TaskActivityCollector
    from research.ablation.ner.entity_manager import NamedEntityManager
    from research.ablation.recorders.location_recorder import LocationActivityRecorder
    from research.ablation.recorders.task_recorder import TaskActivityRecorder
else:
    # For relative imports when imported as a module
    from .ablation_test_runner import AblationTestRunner
    from .ablation_tester import AblationConfig
    from .collectors.location_collector import LocationActivityCollector
    from .collectors.task_collector import TaskActivityCollector
    from .ner.entity_manager import NamedEntityManager
    from .recorders.location_recorder import LocationActivityRecorder
    from .recorders.task_recorder import TaskActivityRecorder


def setup_logging():
    """Set up logging for the demo."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def generate_test_data(
    entity_manager: NamedEntityManager,
    num_location_records: int = 200,
    num_task_records: int = 200,
):
    """Generate synthetic test data for the ablation test.

    Args:
        entity_manager: The named entity manager to use.
        num_location_records: Number of location records to generate.
        num_task_records: Number of task records to generate.
    """
    logging.info("Generating test data for ablation testing")

    # Create collectors
    location_collector = LocationActivityCollector(entity_manager=entity_manager)
    task_collector = TaskActivityCollector(entity_manager=entity_manager)

    # Create recorders
    location_recorder = LocationActivityRecorder()
    task_recorder = TaskActivityRecorder()

    # Clear existing data
    location_recorder.delete_all()
    task_recorder.delete_all()

    # Generate and record location data
    logging.info(f"Generating {num_location_records} location records")
    location_data = location_collector.generate_batch(num_location_records)
    location_recorder.record_batch(location_data)

    # Generate and record task data
    logging.info(f"Generating {num_task_records} task records")
    task_data = task_collector.generate_batch(num_task_records)
    task_recorder.record_batch(task_data)

    # Verify data was recorded
    location_count = location_recorder.count_records()
    task_count = task_recorder.count_records()

    logging.info(f"Recorded {location_count} location records")
    logging.info(f"Recorded {task_count} task records")


def generate_test_queries(
    entity_manager: NamedEntityManager,
    num_queries: int = 15,
) -> list[dict[str, Any]]:
    """Generate test queries for the ablation test.

    Args:
        entity_manager: The named entity manager to use.
        num_queries: Number of queries to generate.

    Returns:
        List[Dict[str, Any]]: List of query dictionaries.
    """
    logging.info(f"Generating {num_queries} test queries")

    # Create collectors for generating query-specific data
    location_collector = LocationActivityCollector(entity_manager=entity_manager)
    task_collector = TaskActivityCollector(entity_manager=entity_manager)

    # Create recorders for truth data
    location_recorder = LocationActivityRecorder()
    task_recorder = TaskActivityRecorder()

    # Sample query templates
    location_query_templates = [
        "Find files I accessed while at {location}",
        "Show me documents I worked on at the {location}",
        "What files did I access at {location} using my {device}?",
        "Find photos taken at the {location}",
        "Show emails I sent from the {location}",
    ]

    task_query_templates = [
        "Find documents I edited in {application}",
        "Show me files I worked on using {application}",
        "What documents did I create with {application}?",
        "Find code I wrote in {application}",
        "Show presentations I designed in {application}",
    ]

    # Generate queries
    queries = []

    # Generate location queries
    for _ in range(num_queries // 2 + num_queries % 2):
        # Pick a random location
        location = entity_manager.get_entities_by_type("location")
        if not location:
            continue

        location_name = list(location.keys())[0]

        # Pick a random device
        device = entity_manager.get_entities_by_type("device")
        if device:
            device_name = list(device.keys())[0]
        else:
            device_name = "phone"

        # Pick a random query template
        template = location_query_templates[0]

        # Generate the query
        query_text = template.format(location=location_name, device=device_name)

        # Generate a query ID
        query_id = uuid.uuid4()

        # Generate matching data
        matching_data = location_collector.generate_matching_data(query_text, count=10)
        location_recorder.record_batch(matching_data)

        # Generate truth data
        entity_ids = location_collector.generate_truth_data(query_text)
        location_recorder.record_truth_data(query_id, entity_ids)

        # Add query to the list
        queries.append(
            {
                "id": str(query_id),
                "text": query_text,
                "type": "location",
            },
        )

    # Generate task queries
    for _ in range(num_queries // 2):
        # Pick a random application
        application = task_collector.applications[0]

        # Pick a random query template
        template = task_query_templates[0]

        # Generate the query
        query_text = template.format(application=application)

        # Generate a query ID
        query_id = uuid.uuid4()

        # Generate matching data
        matching_data = task_collector.generate_matching_data(query_text, count=10)
        task_recorder.record_batch(matching_data)

        # Generate truth data
        entity_ids = task_collector.generate_truth_data(query_text)
        task_recorder.record_truth_data(query_id, entity_ids)

        # Add query to the list
        queries.append(
            {
                "id": str(query_id),
                "text": query_text,
                "type": "task",
            },
        )

    return queries


def run_ablation_test(queries: list[dict[str, Any]]):
    """Run the ablation test with the generated queries.

    Args:
        queries: List of query dictionaries.
    """
    logging.info("Running ablation test")

    # Create ablation test runner
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"./ablation_results_{timestamp}"

    runner = AblationTestRunner(output_dir=output_dir)

    # Create ablation config
    config = AblationConfig(
        collections_to_ablate=[
            "AblationLocationActivity",
            "AblationTaskActivity",
        ],
        query_limit=100,
        include_metrics=True,
        include_execution_time=True,
        verbose=True,
    )

    # Run batch tests
    logging.info(f"Running ablation tests for {len(queries)} queries")
    results = runner.run_batch_tests(queries, config, max_queries=len(queries))

    # Save results
    json_path = runner.save_results_json()
    csv_path = runner.save_results_csv()

    logging.info(f"Saved raw results to {json_path}")
    logging.info(f"Saved CSV results to {csv_path}")

    # Generate summary report
    summary_path = runner.generate_summary_report()
    logging.info(f"Generated summary report at {summary_path}")

    # Generate visualizations if dependencies are available
    if VISUALIZATION_AVAILABLE:
        viz_paths = runner.generate_visualizations()
        logging.info(f"Generated {len(viz_paths)} visualizations")
    else:
        logging.warning("Visualizations skipped due to missing dependencies")

    # Clean up
    runner.cleanup()

    logging.info(f"Ablation test completed. Results saved to {output_dir}")

    # Return the output directory for convenience
    return output_dir


def main():
    """Run the ablation test demo."""
    # Set up logging
    setup_logging()

    logging.info("Starting ablation test demo")

    try:
        # Create entity manager
        entity_manager = NamedEntityManager()

        # Generate test data
        generate_test_data(
            entity_manager=entity_manager,
            num_location_records=100,
            num_task_records=100,
        )

        # Generate test queries
        queries = generate_test_queries(
            entity_manager=entity_manager,
            num_queries=10,
        )

        # Run ablation test
        output_dir = run_ablation_test(queries)

        logging.info(f"Ablation test demo completed. Results in {output_dir}")

        # Print results location
        print(f"\nAblation test results saved to: {output_dir}")
        print("Files generated:")
        print("  - ablation_results.json: Raw test results")
        print("  - ablation_results.csv: Results in CSV format")
        print("  - ablation_summary.md: Summary report with metrics")
        print("  - impact_by_collection.png: Chart of collection impact")
        print("  - impact_heatmap.png: Heatmap of impact relationships")
        print("  - precision_recall.png: Precision vs. recall scatter plot")
        print("  - f1_by_collection.png: F1 scores by collection")

    except Exception as e:
        logging.error(f"Error in ablation test demo: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
