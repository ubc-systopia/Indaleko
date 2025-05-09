#!/usr/bin/env python3
"""
Test script for the query-truth integration in the ablation framework.

This script demonstrates the integration between the QueryGenerator and TruthTracker
components, showing how test queries are paired with their expected results.
"""

import argparse
import logging

from research.ablation.models.activity import ActivityType
from research.ablation.query.generator import QueryGenerator
from research.ablation.query.truth_tracker import TruthTracker


def setup_logging():
    """Set up basic logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def main():
    """Run the query-truth integration test."""
    setup_logging()
    logger = logging.getLogger(__name__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Test query-truth integration")
    parser.add_argument("--query-count", type=int, default=5, help="Number of test queries to generate")
    parser.add_argument(
        "--activity-type",
        choices=[at.name for at in ActivityType],
        help="Specific activity type to test",
    )
    parser.add_argument(
        "--difficulty",
        choices=["easy", "medium", "hard"],
        default="medium",
        help="Difficulty level for test queries",
    )
    parser.add_argument("--diverse", action="store_true", help="Generate diverse queries")
    args = parser.parse_args()

    # Initialize the query generator and truth tracker
    query_generator = QueryGenerator()
    truth_tracker = TruthTracker()

    # Select activity types to test
    activity_types = None
    if args.activity_type:
        activity_type = getattr(ActivityType, args.activity_type)
        activity_types = [activity_type]

    # Generate test queries
    logger.info(f"Generating {args.query_count} test queries")
    if args.diverse:
        queries = query_generator.generate_diverse_queries(
            count=args.query_count,
            activity_types=activity_types,
            difficulty_levels=[args.difficulty],
        )
    else:
        queries = query_generator.generate_queries(
            count=args.query_count,
            activity_types=activity_types,
            difficulty_levels=[args.difficulty],
        )

    # Record ground truth for each query
    for query in queries:
        logger.info(f"Processing query: {query.query_text}")

        # Display query details
        logger.info(f"  Query ID: {query.query_id}")
        logger.info(f"  Activity types: {[at.name for at in query.activity_types]}")
        logger.info(f"  Difficulty: {query.difficulty}")
        logger.info(f"  Expected match count: {len(query.expected_matches)}")

        # Record the ground truth
        success = truth_tracker.record_query_truth(
            query_id=str(query.query_id),
            matching_ids=query.expected_matches,
            query_text=query.query_text,
            activity_types=[at.name for at in query.activity_types],
            difficulty=query.difficulty,
            metadata=query.metadata,
        )

        if success:
            logger.info(f"  Successfully recorded ground truth for query {query.query_id}")
        else:
            logger.error(f"  Failed to record ground truth for query {query.query_id}")

    # Retrieve and verify truth data
    logger.info("\nVerifying truth data retrieval:")
    for query in queries:
        # Retrieve truth data for the query
        truth_record = truth_tracker.get_truth_record(query.query_id)

        if truth_record:
            logger.info(f"Retrieved truth record for query: {truth_record['query_text']}")
            logger.info(f"  Matching document count: {len(truth_record['matching_ids'])}")

            # Verify that the matching IDs match the expected matches
            expected_set = set(query.expected_matches)
            actual_set = set(truth_record["matching_ids"])

            if expected_set == actual_set:
                logger.info("  ✓ Matching IDs match expected matches")
            else:
                logger.error("  ✗ Matching IDs do not match expected matches")
                logger.error(f"    Expected: {expected_set}")
                logger.error(f"    Actual: {actual_set}")
        else:
            logger.error(f"Failed to retrieve truth record for query {query.query_id}")

    # Display metadata statistics
    logger.info("\nActivity type distribution in truth records:")
    distribution = truth_tracker.get_activity_type_distribution()
    for activity_type, count in distribution.items():
        logger.info(f"  {activity_type}: {count} queries")


if __name__ == "__main__":
    main()
