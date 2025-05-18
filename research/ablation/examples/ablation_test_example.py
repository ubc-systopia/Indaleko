#!/usr/bin/env python3
"""
Example script demonstrating the ablation testing framework.

This script shows how to use the TruthTracker and AblationTestRunner
to perform ablation tests on activity data.
"""

import logging
import sys
import uuid
from pathlib import Path

from ..models.activity import ActivityType
from ..query.truth_tracker import TruthTracker
from ..testing.test_runner import AblationTestRunner


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger(__name__)


def prepare_test_data(tracker: TruthTracker) -> None:
    """Prepare test data for the ablation test.

    This function creates some sample truth data to demonstrate
    how the ablation framework works.

    Args:
        tracker: The TruthTracker instance to use.
    """
    # Sample queries with truth data
    test_queries = [
        {
            "id": str(uuid.uuid4()),
            "text": "What music did I listen to last week?",
            "matching_ids": [str(uuid.uuid4()) for _ in range(3)],
            "activity_types": ["MUSIC"],
            "difficulty": "easy",
            "metadata": {"entities": [], "temporal": "last week"},
        },
        {
            "id": str(uuid.uuid4()),
            "text": "Where was I on Tuesday afternoon?",
            "matching_ids": [str(uuid.uuid4()) for _ in range(2)],
            "activity_types": ["LOCATION"],
            "difficulty": "medium",
            "metadata": {"entities": [], "temporal": "Tuesday afternoon"},
        },
        {
            "id": str(uuid.uuid4()),
            "text": "What tasks did I complete related to the Indaleko project?",
            "matching_ids": [str(uuid.uuid4()) for _ in range(4)],
            "activity_types": ["TASK"],
            "difficulty": "hard",
            "metadata": {"entities": ["Indaleko"], "relations": ["related to"]},
        },
        {
            "id": str(uuid.uuid4()),
            "text": "What videos did I watch on YouTube last month?",
            "matching_ids": [str(uuid.uuid4()) for _ in range(5)],
            "activity_types": ["MEDIA"],
            "difficulty": "medium",
            "metadata": {"entities": ["YouTube"], "temporal": "last month"},
        },
        {
            "id": str(uuid.uuid4()),
            "text": "What files did I share with Alice yesterday?",
            "matching_ids": [str(uuid.uuid4()) for _ in range(3)],
            "activity_types": ["COLLABORATION"],
            "difficulty": "medium",
            "metadata": {"entities": ["Alice"], "temporal": "yesterday"},
        },
    ]

    # Record truth data for each query
    for query in test_queries:
        tracker.record_query_truth(
            query_id=query["id"],
            matching_ids=query["matching_ids"],
            query_text=query["text"],
            activity_types=query["activity_types"],
            difficulty=query["difficulty"],
            metadata=query["metadata"],
        )


def run_ablation_test(logger: logging.Logger) -> None:
    """Run a demonstration ablation test.

    Args:
        logger: The logger to use.
    """
    # Initialize the truth tracker
    tracker = TruthTracker()

    # Clear any existing test data
    tracker.clear_all_records()

    # Prepare test data
    logger.info("Preparing test data...")
    prepare_test_data(tracker)

    # Initialize the test runner
    logger.info("Initializing test runner...")
    test_runner = AblationTestRunner(
        test_name="Example Ablation Test", description="Demonstrating the ablation testing framework",
    )

    # Run the test
    logger.info("Running ablation test...")
    test_metadata = test_runner.run_test(
        num_queries=5,  # We'll use the 5 queries we prepared
        activity_types=[
            ActivityType.MUSIC,
            ActivityType.LOCATION,
            ActivityType.TASK,
            ActivityType.COLLABORATION,
            ActivityType.MEDIA,
        ],
    )

    # Display results
    logger.info(f"Test complete! Test ID: {test_metadata.test_id}")
    logger.info(f"Total time: {test_metadata.total_execution_time_ms:.2f} ms")
    logger.info(f"Average query time: {test_metadata.average_query_time_ms:.2f} ms")

    logger.info("Impact ranking (collections sorted by F1 score impact):")
    for i, impact in enumerate(test_metadata.impact_ranking):
        logger.info(f"{i+1}. {impact['collection']}: {impact['impact']:.4f}")

    # Save truth data to file for reference
    output_dir = Path("./ablation_results")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "truth_data.json"
    tracker.save_to_file(output_path)
    logger.info(f"Truth data saved to: {output_path}")


def main():
    """Main function."""
    logger = setup_logging()
    logger.info("Starting ablation test example...")

    try:
        run_ablation_test(logger)
        logger.info("Example completed successfully")
    except Exception as e:
        if "database connection" in str(e).lower():
            logger.critical(f"FATAL: Database connection failed: {e}", exc_info=True)
            print("\n" + "!" * 80)
            print("DATABASE CONNECTION FAILED - ABLATION TESTS CANNOT RUN")
            print("!" * 80 + "\n")
        else:
            logger.error(f"Error running example: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
