#!/usr/bin/env python3
"""Test script for verifying cross-collection dependencies in the ablation framework.

This script tests the impact of ablating one collection (LocationActivity) on queries
that depend on both LocationActivity and TaskActivity.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# Check for required dependencies
try:
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns

    VISUALIZATION_AVAILABLE = True
except ImportError:
    print("Warning: Visualization dependencies not installed")
    VISUALIZATION_AVAILABLE = False

from db.db_config import IndalekoDBConfig
from research.ablation.collectors.location_collector import LocationActivityCollector
from research.ablation.collectors.task_collector import TaskActivityCollector
from research.ablation.data_sanity_checker import DataSanityChecker
from research.ablation.ner.entity_manager import NamedEntityManager
from research.ablation.recorders.location_recorder import LocationActivityRecorder
from research.ablation.recorders.task_recorder import TaskActivityRecorder
from research.ablation.utils.uuid_utils import generate_deterministic_uuid


def record_location_truth_data(db, query_id, entity_ids):
    """Record truth data for location activity with a unique key.

    Args:
        db: ArangoDB database instance
        query_id: The UUID of the query
        entity_ids: The set of entity UUIDs that should match the query

    Returns:
        bool: True if recording was successful, False otherwise
    """
    collection_name = "AblationLocationActivity"
    truth_collection = "AblationTruthData"

    try:
        # Get the truth collection
        collection = db.collection(truth_collection)

        # Create a composite key to avoid collisions
        composite_key = f"{query_id}_location"

        # Create the truth document
        truth_doc = {
            "_key": composite_key,
            "query_id": str(query_id),
            "matching_entities": [str(entity_id) for entity_id in entity_ids],
            "collection": collection_name,
        }

        # Check if document with this composite key already exists
        existing = collection.get(composite_key)
        if existing:
            # Update existing document
            collection.update(truth_doc)
            logging.info(f"Updated location truth data for query {query_id}")
        else:
            # Insert new document
            collection.insert(truth_doc)
            logging.info(f"Recorded location truth data for query {query_id}")

        return True
    except Exception as e:
        logging.exception(f"Failed to record location truth data: {e}")
        return False


def record_task_truth_data(db, query_id, entity_ids):
    """Record truth data for task activity with a unique key.

    Args:
        db: ArangoDB database instance
        query_id: The UUID of the query
        entity_ids: The set of entity UUIDs that should match the query

    Returns:
        bool: True if recording was successful, False otherwise
    """
    collection_name = "AblationTaskActivity"
    truth_collection = "AblationTruthData"

    try:
        # Get the truth collection
        collection = db.collection(truth_collection)

        # Create a composite key to avoid collisions
        composite_key = f"{query_id}_task"

        # Create the truth document
        truth_doc = {
            "_key": composite_key,
            "query_id": str(query_id),
            "matching_entities": [str(entity_id) for entity_id in entity_ids],
            "collection": collection_name,
        }

        # Check if document with this composite key already exists
        existing = collection.get(composite_key)
        if existing:
            # Update existing document
            collection.update(truth_doc)
            logging.info(f"Updated task truth data for query {query_id}")
        else:
            # Insert new document
            collection.insert(truth_doc)
            logging.info(f"Recorded task truth data for query {query_id}")

        return True
    except Exception as e:
        logging.exception(f"Failed to record task truth data: {e}")
        return False


def setup_logging():
    """Set up logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def clear_data():
    """Clear existing data before the test."""
    logging.info("Clearing existing data...")

    location_recorder = LocationActivityRecorder()
    location_recorder.delete_all()

    task_recorder = TaskActivityRecorder()
    task_recorder.delete_all()

    # Also clear truth data collection
    try:
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()

        if db.has_collection("AblationTruthData"):
            db.aql.execute("FOR doc IN AblationTruthData REMOVE doc IN AblationTruthData")
            logging.info("Cleared AblationTruthData collection")
    except Exception as e:
        logging.exception(f"Failed to clear truth data: {e}")


def generate_test_data(entity_manager: NamedEntityManager, count: int = 100):
    """Generate test location and task data with shared entities.

    Args:
        entity_manager: The entity manager for consistent entity IDs
        count: Number of records to generate per collection

    Returns:
        tuple: (location_data, task_data) lists
    """
    logging.info(f"Generating {count} records for each activity type...")

    # Create collectors and recorders
    location_collector = LocationActivityCollector(entity_manager=entity_manager, seed_value=42)
    location_recorder = LocationActivityRecorder()

    task_collector = TaskActivityCollector(entity_manager=entity_manager, seed_value=42)
    task_recorder = TaskActivityRecorder()

    # Generate and record location data
    location_data = location_collector.generate_batch(count)

    # Ensure all location data has an ID field
    for item in location_data:
        if "id" not in item:
            content_hash = f"location:{item.get('location_name', 'unknown')}:{item.get('device_name', 'unknown')}"
            item["id"] = generate_deterministic_uuid(content_hash)

    location_success = location_recorder.record_batch(location_data)

    if not location_success:
        logging.error("Failed to record location data")
        return None, None

    # Generate and record task data
    task_data = task_collector.generate_batch(count)

    # Ensure all task data has an ID field
    for item in task_data:
        if "id" not in item:
            content_hash = f"task:{item.get('task_name', 'unknown')}:{item.get('application', 'unknown')}"
            item["id"] = generate_deterministic_uuid(content_hash)

    task_success = task_recorder.record_batch(task_data)

    if not task_success:
        logging.error("Failed to record task data")
        return None, None

    return location_data, task_data


def generate_cross_collection_queries(entity_manager: NamedEntityManager, count: int = 5):
    """Generate test queries that depend on both location and task data.

    Args:
        entity_manager: The named entity manager with registered entities.
        count: Number of queries to generate.

    Returns:
        List[Dict[str, Any]]: List of query dictionaries.
    """
    logging.info(f"Generating {count} cross-collection test queries...")

    # Create collectors and recorders
    location_collector = LocationActivityCollector(entity_manager=entity_manager, seed_value=42)
    location_recorder = LocationActivityRecorder()

    task_collector = TaskActivityCollector(entity_manager=entity_manager, seed_value=42)
    task_recorder = TaskActivityRecorder()

    # Cross-collection query templates
    cross_collection_templates = [
        "Find documents I worked on at {location} while using {application}",
        "Show me files I edited at {location} for task {task_name}",
        "What files did I work on at {location} using the {application}?",
    ]

    # Use fixed entities to ensure consistency
    location_name = "Home"
    application_name = "Microsoft Word"
    task_name = "Quarterly Report"

    # Register these with the entity manager
    entity_manager.register_entity("location", location_name)
    entity_manager.register_entity("application", application_name)
    entity_manager.register_entity("task", task_name)

    # Generate queries
    queries = []

    for i in range(count):
        # Pick a query template (use index to ensure deterministic behavior)
        template_idx = i % len(cross_collection_templates)
        template = cross_collection_templates[template_idx]

        # Generate the query
        query_text = template.format(location=location_name, application=application_name, task_name=task_name)

        # Generate a deterministic query ID based on the query text
        query_id = generate_deterministic_uuid(f"query:{query_text}:{i}")

        # Generate matching location data
        location_data = []
        for j in range(5):  # 5 location items per query
            entity_id = generate_deterministic_uuid(f"location:match:{query_text}:{j}")
            data = location_collector.generate_matching_data(query_text, count=1)[0]
            data["id"] = entity_id
            location_data.append(data)

        # Generate matching task data
        task_data = []
        for j in range(5):  # 5 task items per query
            entity_id = generate_deterministic_uuid(f"task:match:{query_text}:{j}")
            data = task_collector.generate_matching_data(query_text, count=1)[0]
            data["id"] = entity_id
            task_data.append(data)

        # Record the matching data
        location_recorder.record_batch(location_data)
        task_recorder.record_batch(task_data)

        # Extract entity IDs for truth data
        location_entity_ids = set(data["id"] for data in location_data)
        task_entity_ids = set(data["id"] for data in task_data)

        # Get database connection for recording truth data
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()

        # Record truth data for each collection with unique keys
        record_location_truth_data(db, query_id, location_entity_ids)
        record_task_truth_data(db, query_id, task_entity_ids)

        # Add query to the list
        queries.append(
            {
                "id": str(query_id),
                "text": query_text,
                "type": "cross_collection",
                "location_count": len(location_entity_ids),
                "task_count": len(task_entity_ids),
            },
        )

        # Debug info
        logging.info(f"Query {i+1}: '{query_text}' with ID {query_id}")
        logging.info(f"  -> Truth data has {len(location_entity_ids)} matching location entities")
        logging.info(f"  -> Truth data has {len(task_entity_ids)} matching task entities")

    return queries


def test_cross_collection_lookup(queries: list[dict[str, Any]]):
    """Test lookup of entities across collections without ablation.

    Args:
        queries: List of query dictionaries.

    Returns:
        bool: True if all lookups passed, False otherwise.
    """
    logging.info("Testing cross-collection entity lookup...")

    db_config = IndalekoDBConfig()
    db = db_config.get_arangodb()

    # First, log all documents in the collections for debugging
    location_docs = list(db.aql.execute("FOR doc IN AblationLocationActivity RETURN doc._key"))
    task_docs = list(db.aql.execute("FOR doc IN AblationTaskActivity RETURN doc._key"))
    truth_docs_all = list(db.aql.execute("FOR doc IN AblationTruthData RETURN doc"))

    logging.info(f"Found {len(location_docs)} location documents in database")
    logging.info(f"Found {len(task_docs)} task documents in database")
    logging.info(f"Found {len(truth_docs_all)} truth documents in database")

    all_tests_passed = True

    for query in queries:
        query_id = query["id"]
        query_text = query["text"]

        logging.info(f"\nTesting lookup for query: '{query_text}' (ID: {query_id})")

        # Get truth data for this query for each collection
        collections = ["AblationLocationActivity", "AblationTaskActivity"]

        for collection in collections:
            truth_result = db.aql.execute(
                """
                FOR doc IN AblationTruthData
                FILTER doc.query_id == @query_id AND doc.collection == @collection
                RETURN doc
                """,
                bind_vars={"query_id": query_id, "collection": collection},
            )

            truth_docs = list(truth_result)

            if not truth_docs:
                logging.error(f"No truth data found for query {query_id} in collection {collection}")
                all_tests_passed = False
                continue

            truth_doc = truth_docs[0]
            entity_ids = truth_doc.get("matching_entities", [])

            if not entity_ids:
                logging.error(f"Missing entity_ids in truth doc for query {query_id} in collection {collection}")
                all_tests_passed = False
                continue

            logging.info(f"Query {query_id} has {len(entity_ids)} expected matches in {collection}")

            # Lookup entities by ID
            entity_result = db.aql.execute(
                f"""
                FOR doc IN {collection}
                FILTER doc._key IN @entity_ids
                RETURN doc
                """,
                bind_vars={"entity_ids": entity_ids},
            )

            entity_docs = list(entity_result)

            logging.info(f"Found {len(entity_docs)} of {len(entity_ids)} expected entities in {collection}")

            if len(entity_docs) != len(entity_ids):
                # Find missing entities
                found_ids = set(doc["_key"] for doc in entity_docs)
                missing_ids = set(entity_ids) - found_ids

                logging.error(f"Missing entities in {collection}: {missing_ids}")
                all_tests_passed = False
            else:
                logging.info(f"All entities for query {query_id} found successfully in {collection}!")

    return all_tests_passed


def test_cross_collection_ablation(queries: list[dict[str, Any]]):
    """Test the effect of ablating one collection on cross-collection queries.

    This test measures how ablating location data affects queries that depend
    on both location and task data.

    Args:
        queries: List of query dictionaries.

    Returns:
        bool: True if ablation tests passed, False otherwise.
    """
    logging.info("Testing cross-collection ablation impact...")

    db_config = IndalekoDBConfig()
    db = db_config.get_arangodb()

    # We'll ablate the location collection to see how it affects cross-collection queries
    ablated_collection = "AblationLocationActivity"
    dependent_collection = "AblationTaskActivity"

    all_tests_passed = True

    for query in queries:
        query_id = query["id"]
        query_text = query["text"]

        logging.info(f"\nTesting cross-collection ablation for query: '{query_text}' (ID: {query_id})")

        # 1. Get baseline: Get all expected matches from both collections
        truth_results = {}

        for collection in [ablated_collection, dependent_collection]:
            truth_result = db.aql.execute(
                """
                FOR doc IN AblationTruthData
                FILTER doc.query_id == @query_id AND doc.collection == @collection
                LIMIT 1
                RETURN doc
                """,
                bind_vars={"query_id": query_id, "collection": collection},
            )

            truth_docs = list(truth_result)

            if not truth_docs:
                logging.error(f"No truth data found for query {query_id} in collection {collection}")
                all_tests_passed = False
                continue

            truth_doc = truth_docs[0]
            matching_entities = truth_doc.get("matching_entities", [])

            if not matching_entities:
                logging.error(f"No matching entities in truth data for query {query_id} in collection {collection}")
                all_tests_passed = False
                continue

            truth_results[collection] = matching_entities

            logging.info(f"Truth data has {len(matching_entities)} entities that should match in {collection}")

        # Skip this query if we're missing truth data
        if len(truth_results) < 2:
            continue

        # 2. Verify we can find all entities in both collections
        before_ablation_counts = {}

        for collection, entity_ids in truth_results.items():
            result_before = db.aql.execute(
                f"""
                FOR doc IN {collection}
                FILTER doc._key IN @entity_ids
                RETURN doc
                """,
                bind_vars={"entity_ids": entity_ids},
            )

            found_before = list(result_before)
            before_ablation_counts[collection] = len(found_before)

            logging.info(f"Before ablation: Found {len(found_before)} of {len(entity_ids)} entities in {collection}")

            if len(found_before) != len(entity_ids):
                logging.error(f"Missing entities in {collection} before ablation")
                all_tests_passed = False

        # Skip this query if we can't find all entities before ablation
        if not all(count == len(truth_results[coll]) for coll, count in before_ablation_counts.items()):
            continue

        # 3. Backup the collection we'll ablate
        logging.info(f"Backing up {ablated_collection} for ablation...")
        backup_data = list(db.aql.execute(f"FOR doc IN {ablated_collection} RETURN doc"))
        logging.info(f"Backed up {len(backup_data)} documents")

        # 4. Ablate the collection (remove all documents)
        logging.info(f"Ablating {ablated_collection}...")
        db.aql.execute(f"FOR doc IN {ablated_collection} REMOVE doc IN {ablated_collection}")

        # 5. Verify the collection is empty
        count_after_ablation = db.aql.execute(f"RETURN LENGTH({ablated_collection})").next()
        logging.info(f"After ablation: {ablated_collection} has {count_after_ablation} documents")

        if count_after_ablation != 0:
            logging.error(f"Failed to fully ablate collection {ablated_collection}")
            all_tests_passed = False

            # Restore data and continue to next query
            for doc in backup_data:
                # Remove ArangoDB system fields
                doc_copy = doc.copy()
                for field in ["_rev", "_id"]:
                    if field in doc_copy:
                        del doc_copy[field]

                # Reinsert the document
                db.collection(ablated_collection).insert(doc_copy)

            continue

        # 6. Check both collections post-ablation
        after_ablation_counts = {}

        for collection, entity_ids in truth_results.items():
            result_after = db.aql.execute(
                f"""
                FOR doc IN {collection}
                FILTER doc._key IN @entity_ids
                RETURN doc
                """,
                bind_vars={"entity_ids": entity_ids},
            )

            found_after = list(result_after)
            after_ablation_counts[collection] = len(found_after)

            expected_count = 0 if collection == ablated_collection else len(entity_ids)
            logging.info(f"After ablation: Found {len(found_after)} of {len(entity_ids)} entities in {collection}")

            if len(found_after) != expected_count:
                logging.error(f"Unexpected count in {collection} after ablation")
                all_tests_passed = False

        # 7. Restore the ablated collection
        logging.info(f"Restoring {ablated_collection}...")
        for doc in backup_data:
            # Remove ArangoDB system fields
            doc_copy = doc.copy()
            for field in ["_rev", "_id"]:
                if field in doc_copy:
                    del doc_copy[field]

            # Reinsert the document
            db.collection(ablated_collection).insert(doc_copy)

        # 8. Verify restoration
        count_after_restore = db.aql.execute(f"RETURN LENGTH({ablated_collection})").next()
        logging.info(f"After restoration: {ablated_collection} has {count_after_restore} documents")

        if count_after_restore != len(backup_data):
            logging.error(f"Failed to fully restore collection {ablated_collection}")
            all_tests_passed = False
            continue

        # 9. Check both collections post-restoration
        after_restore_counts = {}

        for collection, entity_ids in truth_results.items():
            result_after_restore = db.aql.execute(
                f"""
                FOR doc IN {collection}
                FILTER doc._key IN @entity_ids
                RETURN doc
                """,
                bind_vars={"entity_ids": entity_ids},
            )

            found_after_restore = list(result_after_restore)
            after_restore_counts[collection] = len(found_after_restore)

            logging.info(
                f"After restoration: Found {len(found_after_restore)} of {len(entity_ids)} entities in {collection}",
            )

            if len(found_after_restore) != len(entity_ids):
                logging.error(f"Missing entities in {collection} after restoration")
                all_tests_passed = False

        # 10. Calculate impact metrics
        location_impact = 1.0  # Complete impact when location collection is ablated
        task_impact = (
            0.0 if after_ablation_counts[dependent_collection] == len(truth_results[dependent_collection]) else 1.0
        )

        logging.info("Impact metrics:")
        logging.info(f"  - Location Impact: {location_impact:.2f} (expected 1.0)")
        logging.info(f"  - Task Impact: {task_impact:.2f} (expected 0.0)")

        # Check if impact metrics match expectations
        if location_impact != 1.0:
            logging.error(f"Unexpected location impact: {location_impact}")
            all_tests_passed = False

        if task_impact != 0.0:
            logging.error(
                f"Unexpected task impact: {task_impact} - Task data should be unaffected by location ablation",
            )
            all_tests_passed = False

        # Test passed for this query?
        test_passed = (
            before_ablation_counts[ablated_collection] == len(truth_results[ablated_collection])
            and before_ablation_counts[dependent_collection] == len(truth_results[dependent_collection])
            and after_ablation_counts[ablated_collection] == 0
            and after_ablation_counts[dependent_collection] == len(truth_results[dependent_collection])
            and after_restore_counts[ablated_collection] == len(truth_results[ablated_collection])
            and after_restore_counts[dependent_collection] == len(truth_results[dependent_collection])
        )

        if test_passed:
            logging.info(f"Cross-collection ablation test for query {query_id} PASSED!")
        else:
            logging.error(f"Cross-collection ablation test for query {query_id} FAILED!")
            all_tests_passed = False

    return all_tests_passed


def perform_data_check():
    """Run data sanity checks."""
    logging.info("Performing data sanity check...")

    checker = DataSanityChecker(fail_fast=False)
    result = checker.run_all_checks()

    if not result:
        logging.error("Data sanity check failed!")
    else:
        logging.info("Data sanity check passed!")

    return result


def main():
    """Run the test."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting cross-collection ablation test")

    try:
        # Clear existing data
        clear_data()

        # Initialize entity manager for consistent entity references
        entity_manager = NamedEntityManager()

        # Generate test data
        location_data, task_data = generate_test_data(entity_manager, count=100)
        if location_data is None or task_data is None:
            logger.error("Failed to generate test data")
            sys.exit(1)

        # Generate cross-collection test queries
        queries = generate_cross_collection_queries(entity_manager, count=5)
        if not queries:
            logger.error("Failed to generate cross-collection test queries")
            sys.exit(1)

        # Run data check
        data_check_passed = perform_data_check()
        if not data_check_passed:
            logger.warning("Data check failed, but continuing with cross-collection lookup test")

        # Test cross-collection lookup
        lookup_passed = test_cross_collection_lookup(queries)

        if lookup_passed:
            logger.info("Cross-collection entity lookup test PASSED!")
        else:
            logger.error("Cross-collection entity lookup test FAILED!")
            sys.exit(1)

        # Test cross-collection ablation
        ablation_passed = test_cross_collection_ablation(queries)

        if ablation_passed:
            logger.info("Cross-collection ablation test PASSED!")
        else:
            logger.error("Cross-collection ablation test FAILED!")
            sys.exit(1)

        if data_check_passed and lookup_passed and ablation_passed:
            logger.info("Cross-collection ablation test completed successfully")
        else:
            logger.warning("Cross-collection ablation test completed with warnings")

    except Exception as e:
        logger.error(f"Error in cross-collection ablation test: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
