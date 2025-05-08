#!/usr/bin/env python3
"""Script to generate synthetic data for ablation testing."""

import argparse
import logging
import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from research.ablation.collectors.music_collector import MusicActivityCollector
from research.ablation.ner.entity_manager import NamedEntityManager
from research.ablation.query.generator import QueryGenerator
from research.ablation.recorders.music_recorder import MusicActivityRecorder


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f"synthetic_data_generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        ],
    )


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Generate synthetic data for ablation testing")

    parser.add_argument(
        "--activity-type",
        choices=["music", "location", "task", "collaboration", "storage", "media", "all"],
        default="music",
        help="The type of activity data to generate (default: music)",
    )

    parser.add_argument("--count", type=int, default=100, help="The number of activities to generate (default: 100)")

    parser.add_argument("--queries", type=int, default=10, help="The number of test queries to generate (default: 10)")

    parser.add_argument(
        "--output-dir",
        type=str,
        default="../results/raw",
        help="The directory to write output files to (default: ../results/raw)",
    )

    parser.add_argument("--record", action="store_true", help="Record the generated data to the database")

    return parser.parse_args()


def generate_music_activities(count: int, record: bool = False) -> list[dict]:
    """Generate synthetic music activities.

    Args:
        count: The number of activities to generate.
        record: Whether to record the activities to the database.

    Returns:
        List[Dict]: The generated activities.
    """
    logging.info(f"Generating {count} music activities")

    # Create entity manager and collector
    entity_manager = NamedEntityManager()
    collector = MusicActivityCollector(entity_manager=entity_manager)

    # Generate activities
    activities = []
    for _ in range(count):
        activity = collector.collect()
        activities.append(activity)

    # Record activities if requested
    if record:
        recorder = MusicActivityRecorder()

        for activity in activities:
            success = recorder.record(activity)
            if not success:
                logging.warning(f"Failed to record activity: {activity.get('id')}")

    return activities


def generate_test_queries(count: int, activity_type: str = "music") -> list[tuple[str, str]]:
    """Generate test queries for ablation testing.

    Args:
        count: The number of queries to generate.
        activity_type: The type of activity to generate queries for.

    Returns:
        List[Tuple[str, str]]: A list of (query, activity_type) tuples.
    """
    logging.info(f"Generating {count} test queries for {activity_type} activities")

    # Create query generator
    generator = QueryGenerator()

    # Generate queries
    queries = generator.generate_queries(count=count)

    # Filter queries by activity type if specified
    if activity_type != "all":
        queries = [(query, qtype) for query, qtype in queries if qtype == activity_type]

    return queries


def main():
    """Main function."""
    # Set up logging
    setup_logging()

    # Parse arguments
    args = parse_args()

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Generate activities
    if args.activity_type == "music" or args.activity_type == "all":
        music_activities = generate_music_activities(args.count, args.record)

        # Write activities to file
        output_file = os.path.join(args.output_dir, f"music_activities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(output_file, "w") as f:
            import json

            json.dump(music_activities, f, default=str, indent=2)

        logging.info(f"Wrote {len(music_activities)} music activities to {output_file}")

    # Generate test queries
    queries = generate_test_queries(args.queries, args.activity_type)

    # Write queries to file
    query_file = os.path.join(args.output_dir, f"test_queries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(query_file, "w") as f:
        import json

        json.dump([(q, t) for q, t in queries], f, indent=2)

    logging.info(f"Wrote {len(queries)} test queries to {query_file}")


if __name__ == "__main__":
    main()
