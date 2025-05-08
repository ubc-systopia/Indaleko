#!/usr/bin/env python3
"""Demo script for location activity collector and recorder.

This script demonstrates the complete workflow for generating, recording,
and querying location activity data for ablation testing.
"""

import logging
import uuid
from typing import Any

from ablation.collectors.location_collector import LocationActivityCollector
from ablation.ner.entity_manager import NamedEntityManager
from ablation.recorders.location_recorder import LocationActivityRecorder


def setup_logging():
    """Set up logging for the demo."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def generate_and_record_data(
    collector: LocationActivityCollector,
    recorder: LocationActivityRecorder,
    count: int = 50,
) -> list[dict[str, Any]]:
    """Generate and record a batch of location activities.

    Args:
        collector: The location activity collector.
        recorder: The location activity recorder.
        count: The number of activities to generate and record.

    Returns:
        List[Dict[str, Any]]: The generated activities.
    """
    logging.info(f"Generating {count} location activities...")
    activities = collector.generate_batch(count)

    logging.info(f"Recording {count} location activities...")
    success = recorder.record_batch(activities)

    if success:
        logging.info(f"Successfully recorded {count} location activities.")
    else:
        logging.error("Failed to record location activities.")

    return activities


def generate_and_record_truth_data(
    collector: LocationActivityCollector,
    recorder: LocationActivityRecorder,
    query: str,
    query_id: uuid.UUID = None,
) -> uuid.UUID:
    """Generate and record truth data for a query.

    Args:
        collector: The location activity collector.
        recorder: The location activity recorder.
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
    recorder: LocationActivityRecorder,
    queries: list[str],
) -> None:
    """Run demo queries against the recorded data.

    Args:
        recorder: The location activity recorder.
        queries: List of query strings to run.
    """
    for i, query in enumerate(queries, 1):
        logging.info(f"Running query {i}: {query}")
        results = recorder.get_records_by_query(query)

        logging.info(f"Found {len(results)} matching records for query: {query}")

        # Display the first 3 results
        for j, result in enumerate(results[:3], 1):
            logging.info(f"Result {j}:")
            logging.info(f"  Location: {result.get('location_name', 'N/A')}")
            logging.info(f"  Type: {result.get('location_type', 'N/A')}")
            logging.info(f"  Device: {result.get('device_name', 'N/A')}")
            logging.info(f"  Source: {result.get('source', 'N/A')}")
            if "coordinates" in result:
                coords = result["coordinates"]
                logging.info(f"  Coordinates: {coords.get('latitude', 0)}, {coords.get('longitude', 0)}")
            logging.info("")


def main():
    """Run the location activity demo."""
    # Set up logging
    setup_logging()

    logging.info("Starting location activity demo")

    # Create entity manager
    entity_manager = NamedEntityManager()

    # Create collector and recorder
    collector = LocationActivityCollector(entity_manager=entity_manager)
    recorder = LocationActivityRecorder()

    # Clean up any existing data
    recorder.delete_all()

    # Generate and record a batch of random location activities
    activities = generate_and_record_data(collector, recorder, count=100)

    # Generate and record activities matching specific queries
    test_queries = [
        "Find files I accessed while at Home",
        "Show me documents I worked on at the Coffee Shop",
        "What files did I access at the Library using my iPhone?",
        "Find photos taken at the Park",
        "Show emails I sent from the Airport",
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
        "Home",
        "Coffee Shop",
        "Library iPhone",
        "Park",
        "Airport",
        "Work",
        "iPhone",
        "gps",
        "wifi",
    ]

    run_demo_queries(recorder, demo_queries)

    logging.info("Location activity demo completed")


if __name__ == "__main__":
    main()
