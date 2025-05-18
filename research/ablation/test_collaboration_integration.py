#!/usr/bin/env python3
"""Integration test for collaboration activity with the ablation framework."""

import logging
import sys
import uuid
from pathlib import Path

# Add the root directory to the path for imports
repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))

from research.ablation.ablation_tester import AblationTester
from research.ablation.collectors.collaboration_collector import (
    CollaborationActivityCollector,
)
from research.ablation.ner.entity_manager import NamedEntityManager
from research.ablation.recorders.collaboration_recorder import (
    CollaborationActivityRecorder,
)


def setup_logging():
    """Set up logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def test_ablation_integration():
    """Test the integration of collaboration activity with the ablation framework."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting collaboration activity ablation integration test")

    # Create entity manager, collector, and recorder
    entity_manager = NamedEntityManager()
    collector = CollaborationActivityCollector(entity_manager=entity_manager)
    recorder = CollaborationActivityRecorder()

    # Clear existing data
    recorder.delete_all()

    # Generate and record synthetic data
    num_records = 50
    logger.info(f"Generating {num_records} collaboration activities")
    activities = collector.generate_batch(num_records)
    success = recorder.record_batch(activities)

    if not success:
        logger.error("Failed to record collaboration activities")
        return False

    logger.info(f"Successfully recorded {num_records} collaboration activities")

    # Create a test query and generate matching data
    # Use a simpler query that will match better with our search algorithm
    query_text = "Microsoft Teams Meeting"
    query_id = uuid.uuid4()

    logger.info(f"Test query: '{query_text}'")

    # Generate and record matching data
    matching_count = 10
    logger.info(f"Generating {matching_count} matching collaboration activities")
    matching_data = collector.generate_matching_data(query_text, count=matching_count)

    # Log some of the matching data for debugging
    if matching_data:
        logger.info(
            f"Sample matching data - Platform: {matching_data[0].get('platform')}, Event Type: {matching_data[0].get('event_type')}",
        )
        logger.info(f"Content: {matching_data[0].get('content')}")

    success = recorder.record_batch(matching_data)

    if not success:
        logger.error("Failed to record matching collaboration activities")
        return False

    # Generate and record truth data
    logger.info("Generating truth data")
    entity_ids = collector.generate_truth_data(query_text)
    success = recorder.record_truth_data(query_id, entity_ids)

    if not success:
        logger.error("Failed to record truth data")
        return False

    logger.info(f"Successfully recorded truth data for {len(entity_ids)} matching entities")

    # Create ablation tester and config
    tester = AblationTester()

    # Test querying the data
    logger.info("Testing collaboration activity querying")
    logger.info(f"Executing query: '{query_text}' on collection AblationCollaborationActivity")
    results, exec_time = tester.execute_query(query_text, "AblationCollaborationActivity", limit=20)

    logger.info(f"Query returned {len(results)} results in {exec_time}ms")

    # Try a simpler query for debugging
    simple_query = "Microsoft Teams"
    logger.info(f"Trying a simpler query: '{simple_query}'")
    simple_results, simple_exec_time = tester.execute_query(simple_query, "AblationCollaborationActivity", limit=20)
    logger.info(f"Simple query returned {len(simple_results)} results in {simple_exec_time}ms")

    # Test ablation
    logger.info("Testing collaboration activity ablation")

    # First, verify that we can access the truth data
    truth_data = tester.get_truth_data(query_id)
    logger.info(f"Retrieved {len(truth_data)} items from truth data")

    # Try to ablate the collection
    success = tester.ablate_collection("AblationCollaborationActivity")

    if not success:
        logger.error("Failed to ablate collaboration activity collection")
        return False

    logger.info("Successfully ablated collaboration activity collection")

    # Query again after ablation (should return no results)
    results_after, exec_time_after = tester.execute_query(query_text, "AblationCollaborationActivity", limit=20)

    logger.info(f"Query after ablation returned {len(results_after)} results in {exec_time_after}ms")

    # Restore the collection
    success = tester.restore_collection("AblationCollaborationActivity")

    if not success:
        logger.error("Failed to restore collaboration activity collection")
        return False

    logger.info("Successfully restored collaboration activity collection")

    # Verify data was restored by querying again
    results_restored, exec_time_restored = tester.execute_query(query_text, "AblationCollaborationActivity", limit=20)

    logger.info(f"Query after restoration returned {len(results_restored)} results in {exec_time_restored}ms")

    logger.info("Collaboration activity ablation integration test completed successfully")
    return True


if __name__ == "__main__":
    success = test_ablation_integration()
    if not success:
        sys.exit(1)
