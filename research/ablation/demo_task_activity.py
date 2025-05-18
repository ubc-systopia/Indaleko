#!/usr/bin/env python3
"""Demo script for task activity collector and recorder.

This script demonstrates the complete workflow for generating, recording,
and querying task activity data for ablation testing.
"""

import logging
import uuid
from typing import Any

from ablation.collectors.task_collector import TaskActivityCollector
from ablation.ner.entity_manager import NamedEntityManager
from ablation.recorders.task_recorder import TaskActivityRecorder


def setup_logging():
    """Set up logging for the demo."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def generate_and_record_data(
    collector: TaskActivityCollector,
    recorder: TaskActivityRecorder,
    count: int = 50,
) -> list[dict[str, Any]]:
    """Generate and record a batch of task activities.

    Args:
        collector: The task activity collector.
        recorder: The task activity recorder.
        count: The number of activities to generate and record.

    Returns:
        List[Dict[str, Any]]: The generated activities.
    """
    logging.info(f"Generating {count} task activities...")
    activities = collector.generate_batch(count)

    logging.info(f"Recording {count} task activities...")
    success = recorder.record_batch(activities)

    if success:
        logging.info(f"Successfully recorded {count} task activities.")
    else:
        logging.error("Failed to record task activities.")

    return activities


def generate_and_record_truth_data(
    collector: TaskActivityCollector,
    recorder: TaskActivityRecorder,
    query: str,
    query_id: uuid.UUID = None,
) -> uuid.UUID:
    """Generate and record truth data for a query.

    Args:
        collector: The task activity collector.
        recorder: The task activity recorder.
        query: The query string.
        query_id: Optional query ID. If not provided, a new one will be generated.

    Returns:
        uuid.UUID: The query ID.
    """
    if query_id is None:
        query_id = uuid.uuid4()

    logging.info(f"Generating truth data for query: {query}")
    entity_ids = collector.generate_truth_data(query)

    logging.info(f"Recording truth data for query ID: {query_id}")
    success = recorder.record_truth_data(query_id, entity_ids)

    if success:
        logging.info(f"Successfully recorded truth data for {len(entity_ids)} matching entities.")
    else:
        logging.error("Failed to record truth data.")

    return query_id


def run_demo_queries(
    recorder: TaskActivityRecorder,
    queries: list[str],
) -> None:
    """Run demo queries against the recorded data.

    Args:
        recorder: The task activity recorder.
        queries: List of query strings to run.
    """
    for i, query in enumerate(queries, 1):
        logging.info(f"Running query {i}: {query}")
        results = recorder.get_records_by_query(query)

        logging.info(f"Found {len(results)} matching records for query: {query}")

        # Display the first 3 results
        for j, result in enumerate(results[:3], 1):
            logging.info(f"Result {j}:")
            logging.info(f"  Task: {result.get('task_name', 'N/A')}")
            logging.info(f"  Application: {result.get('application', 'N/A')}")
            logging.info(f"  Window Title: {result.get('window_title', 'N/A')}")
            logging.info(f"  User: {result.get('user', 'N/A')}")
            logging.info(f"  Duration: {result.get('duration_seconds', 0)} seconds")
            logging.info(f"  Active: {result.get('active', False)}")
            logging.info("")


def main():
    """Run the task activity demo."""
    # Set up logging
    setup_logging()

    logging.info("Starting task activity demo")

    # Create entity manager
    entity_manager = NamedEntityManager()

    # Create collector and recorder
    collector = TaskActivityCollector(entity_manager=entity_manager)
    recorder = TaskActivityRecorder()

    # Clean up any existing data
    recorder.delete_all()

    # Generate and record a batch of random task activities
    activities = generate_and_record_data(collector, recorder, count=100)

    # Generate and record activities matching specific queries
    test_queries = [
        "Find documents I edited in Microsoft Word",
        "Show me spreadsheets I worked on using Excel",
        "What presentations did I create in PowerPoint?",
        "Find code I worked on in Visual Studio Code",
        "Show me chat sessions in Slack",
    ]

    # Generate matching data for each query
    for query in test_queries:
        matching_data = collector.generate_matching_data(query, count=10)
        recorder.record_batch(matching_data)

        # Generate truth data for the query
        query_id = uuid.uuid4()
        generate_and_record_truth_data(collector, recorder, query, query_id)

    # Verify data was recorded
    count = recorder.count_records()
    logging.info(f"Total records in database: {count}")

    # Run demo queries
    demo_queries = [
        "Microsoft Word",
        "Excel",
        "PowerPoint",
        "Visual Studio Code",
        "Slack",
        "alice",
        "data analysis",
        "presentation design",
        "code editing",
    ]

    run_demo_queries(recorder, demo_queries)

    logging.info("Task activity demo completed")


if __name__ == "__main__":
    main()
