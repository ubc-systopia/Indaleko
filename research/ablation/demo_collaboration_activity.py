#!/usr/bin/env python3
"""Demo script for collaboration activity collector and recorder.

This script demonstrates the complete workflow for generating, recording,
and querying collaboration activity data for ablation testing.
"""

import logging
import uuid
from typing import Any

from research.ablation.collectors.collaboration_collector import (
    CollaborationActivityCollector,
)
from research.ablation.ner.entity_manager import NamedEntityManager
from research.ablation.recorders.collaboration_recorder import (
    CollaborationActivityRecorder,
)


def setup_logging():
    """Set up logging for the demo."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def generate_and_record_data(
    collector: CollaborationActivityCollector,
    recorder: CollaborationActivityRecorder,
    count: int = 50,
) -> list[dict[str, Any]]:
    """Generate and record a batch of collaboration activities.

    Args:
        collector: The collaboration activity collector.
        recorder: The collaboration activity recorder.
        count: The number of activities to generate and record.

    Returns:
        List[Dict[str, Any]]: The generated activities.
    """
    logging.info(f"Generating {count} collaboration activities...")
    activities = collector.generate_batch(count)

    logging.info(f"Recording {count} collaboration activities...")
    success = recorder.record_batch(activities)

    if success:
        logging.info(f"Successfully recorded {count} collaboration activities.")
    else:
        logging.error("Failed to record collaboration activities.")

    return activities


def generate_and_record_truth_data(
    collector: CollaborationActivityCollector,
    recorder: CollaborationActivityRecorder,
    query: str,
    query_id: uuid.UUID = None,
) -> uuid.UUID:
    """Generate and record truth data for a query.

    Args:
        collector: The collaboration activity collector.
        recorder: The collaboration activity recorder.
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
    recorder: CollaborationActivityRecorder,
    queries: list[str],
) -> None:
    """Run demo queries against the recorded data.

    Args:
        recorder: The collaboration activity recorder.
        queries: List of query strings to run.
    """
    for i, query in enumerate(queries, 1):
        logging.info(f"Running query {i}: {query}")
        results = recorder.get_records_by_query(query)

        logging.info(f"Found {len(results)} matching records for query: {query}")

        # Display the first 3 results
        for j, result in enumerate(results[:3], 1):
            logging.info(f"Result {j}:")
            logging.info(f"  Platform: {result.get('platform', 'N/A')}")
            logging.info(f"  Event Type: {result.get('event_type', 'N/A')}")
            logging.info(f"  Content: {result.get('content', 'N/A')}")
            logging.info(f"  Source: {result.get('source', 'N/A')}")
            logging.info(f"  Duration: {result.get('duration_seconds', 'N/A')} seconds")

            # Display participants
            participants = result.get("participants", [])
            if participants:
                logging.info("  Participants:")
                for p in participants[:3]:  # Show up to 3 participants
                    if isinstance(p, dict):
                        logging.info(f"    - {p.get('name', 'Unknown')} ({p.get('email', 'No email')})")
                    else:
                        logging.info(f"    - {p!s}")

            logging.info("")


def main():
    """Run the collaboration activity demo."""
    # Set up logging
    setup_logging()

    logging.info("Starting collaboration activity demo")

    # Create entity manager
    entity_manager = NamedEntityManager()

    # Create collector and recorder
    collector = CollaborationActivityCollector(entity_manager=entity_manager)
    recorder = CollaborationActivityRecorder()

    # Clean up any existing data
    recorder.delete_all()

    # Generate and record a batch of random collaboration activities
    activities = generate_and_record_data(collector, recorder, count=100)

    # Generate and record activities matching specific queries
    test_queries = [
        "Find documents shared during the weekly team sync",
        "Show me presentations from Microsoft Teams meetings",
        "What files were discussed in meetings with John Smith?",
        "Show code reviews from GitHub",
        "Find notes from the Project kickoff meeting",
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
        "Microsoft Teams",
        "Meeting",
        "John Smith",
        "Weekly team sync",
        "Code Review",
        "GitHub",
        "Project kickoff",
        "Presentation",
        "Email",
        "Slack",
    ]

    run_demo_queries(recorder, demo_queries)

    logging.info("Collaboration activity demo completed")


if __name__ == "__main__":
    main()
