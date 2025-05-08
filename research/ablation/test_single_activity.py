#!/usr/bin/env python3
"""Test script for verifying a single activity data provider in the ablation framework.

This script tests only LocationActivity to verify the basic ablation functionality works
before attempting cross-collection testing.
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
from research.ablation.data_sanity_checker import DataSanityChecker
from research.ablation.ner.entity_manager import NamedEntityManager
from research.ablation.recorders.location_recorder import LocationActivityRecorder


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

    # Also clear truth data collection
    try:
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()

        if db.has_collection("AblationTruthData"):
            db.aql.execute("FOR doc IN AblationTruthData REMOVE doc IN AblationTruthData")
            logging.info("Cleared AblationTruthData collection")
    except Exception as e:
        logging.exception(f"Failed to clear truth data: {e}")


def generate_test_data(count: int = 100):
    """Generate test location data.

    Args:
        count: Number of location records to generate.
    """
    logging.info(f"Generating {count} location records...")

    entity_manager = NamedEntityManager()

    # Create collector and recorder
    location_collector = LocationActivityCollector(entity_manager=entity_manager, seed_value=42)
    location_recorder = LocationActivityRecorder()

    # Generate and record general data
    location_data = location_collector.generate_batch(count)

    # Ensure all data has an ID field
    for item in location_data:
        if "id" not in item:
            # This will be deterministic based on the content
            from research.ablation.utils.uuid_utils import generate_deterministic_uuid

            content_hash = f"location:{item.get('location_name', 'unknown')}:{item.get('device_name', 'unknown')}"
            item["id"] = generate_deterministic_uuid(content_hash)

    success = location_recorder.record_batch(location_data)

    if not success:
        logging.error("Failed to record location data")
        return None

    return entity_manager


def generate_test_queries(entity_manager: NamedEntityManager, count: int = 5):
    """Generate test queries for location data.

    Args:
        entity_manager: The named entity manager with registered entities.
        count: Number of queries to generate.

    Returns:
        List[Dict[str, Any]]: List of query dictionaries.
    """
    logging.info(f"Generating {count} test queries...")

    # Create collector and recorder for generating query-specific data
    location_collector = LocationActivityCollector(entity_manager=entity_manager, seed_value=42)
    location_recorder = LocationActivityRecorder()

    # Sample query templates
    location_query_templates = [
        "Find files I accessed while at {location}",
        "Show me documents I worked on at the {location}",
        "What files did I access at {location} using my {device}?",
    ]

    # Use a fixed location and device to ensure consistency
    location_name = "Home"
    device_name = "Laptop"

    # Register these with the entity manager
    entity_manager.register_entity("location", location_name)
    entity_manager.register_entity("device", device_name)

    # Generate queries
    queries = []

    from research.ablation.utils.uuid_utils import generate_deterministic_uuid

    for i in range(count):
        # Pick a query template (use index to ensure deterministic behavior)
        template_idx = i % len(location_query_templates)
        template = location_query_templates[template_idx]

        # Generate the query
        query_text = template.format(location=location_name, device=device_name)

        # Generate a deterministic query ID based on the query text
        query_id = generate_deterministic_uuid(f"query:{query_text}:{i}")

        # Generate matching data with deterministic IDs
        matching_data = []
        for j in range(10):
            entity_id = generate_deterministic_uuid(f"location:match:{query_text}:{j}")
            data = location_collector.generate_matching_data(query_text, count=1)[0]
            data["id"] = entity_id
            matching_data.append(data)

        # Record the matching data
        location_recorder.record_batch(matching_data)

        # Extract entity IDs for truth data
        entity_ids = set(data["id"] for data in matching_data)

        # Record truth data
        location_recorder.record_truth_data(query_id, entity_ids)

        # Add query to the list
        queries.append(
            {
                "id": str(query_id),
                "text": query_text,
                "type": "location",
            },
        )

        # Debug info
        logging.info(f"Query {i+1}: '{query_text}' with ID {query_id}")
        logging.info(f"  -> Truth data has {len(entity_ids)} matching entities")

    return queries


def test_direct_lookup(queries: list[dict[str, Any]]):
    """Test direct lookup of entities without ablation.

    This function tests the basic functionality of looking up entities by ID.

    Args:
        queries: List of query dictionaries.
    """
    logging.info("Testing direct entity lookup...")

    db_config = IndalekoDBConfig()
    db = db_config.get_arangodb()

    # First, log all documents in the collections for debugging
    location_docs = list(db.aql.execute("FOR doc IN AblationLocationActivity RETURN doc._key"))
    truth_docs_all = list(db.aql.execute("FOR doc IN AblationTruthData RETURN doc"))

    logging.info(f"Found {len(location_docs)} location documents in database")
    logging.info(f"Found {len(truth_docs_all)} truth documents in database")

    all_tests_passed = True

    for query in queries:
        query_id = query["id"]
        query_text = query["text"]

        logging.info(f"\nTesting lookup for query: '{query_text}' (ID: {query_id})")

        # Get truth data for this query
        truth_result = db.aql.execute(
            """
            FOR doc IN AblationTruthData
            FILTER doc.query_id == @query_id
            RETURN doc
            """,
            bind_vars={"query_id": query_id},
        )

        truth_docs = list(truth_result)

        if not truth_docs:
            logging.error(f"No truth data found for query {query_id}")
            all_tests_passed = False
            continue

        # For each truth doc, lookup the entities
        for truth_doc in truth_docs:
            collection = truth_doc.get("collection")
            entity_ids = truth_doc.get("matching_entities", [])

            if not collection or not entity_ids:
                logging.error(f"Missing collection or entity_ids in truth doc for query {query_id}")
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

            logging.info(f"Found {len(entity_docs)} of {len(entity_ids)} expected entities")

            if len(entity_docs) != len(entity_ids):
                # Find missing entities
                found_ids = set(doc["_key"] for doc in entity_docs)
                missing_ids = set(entity_ids) - found_ids

                logging.error(f"Missing entities: {missing_ids}")

                # Log the entity data we expect to find
                for missing_id in missing_ids:
                    # Check if it exists at all in the collection
                    result = db.aql.execute(
                        f"""
                        FOR doc IN {collection}
                        FILTER doc._key == @id OR doc.id == @id
                        RETURN doc
                        """,
                        bind_vars={"id": missing_id},
                    )
                    docs = list(result)
                    if docs:
                        logging.info(
                            f"Entity exists with different key: {docs[0].get('_key')} vs expected {missing_id}",
                        )
                    else:
                        logging.error(f"Entity {missing_id} doesn't exist in {collection}")

                all_tests_passed = False
            else:
                logging.info(f"All entities for query {query_id} found successfully!")

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


def test_simple_ablation(queries: list[dict[str, Any]]):
    """Test simple ablation for a single activity type.

    Args:
        queries: List of query dictionaries.

    Returns:
        bool: True if ablation test passed, False otherwise.
    """
    logging.info("Testing simple ablation...")

    db_config = IndalekoDBConfig()
    db = db_config.get_arangodb()

    # We'll use the LocationActivity collection for testing
    collection_name = "AblationLocationActivity"

    all_tests_passed = True

    for query in queries:
        query_id = query["id"]
        query_text = query["text"]

        logging.info(f"\nTesting ablation for query: '{query_text}' (ID: {query_id})")

        # 1. First, get the baseline (entities that should match)
        truth_result = db.aql.execute(
            """
            FOR doc IN AblationTruthData
            FILTER doc.query_id == @query_id AND doc.collection == @collection
            LIMIT 1
            RETURN doc
            """,
            bind_vars={"query_id": query_id, "collection": collection_name},
        )

        truth_docs = list(truth_result)

        if not truth_docs:
            logging.error(f"No truth data found for query {query_id} in collection {collection_name}")
            all_tests_passed = False
            continue

        truth_doc = truth_docs[0]
        matching_entities = truth_doc.get("matching_entities", [])

        if not matching_entities:
            logging.error(f"No matching entities in truth data for query {query_id}")
            all_tests_passed = False
            continue

        logging.info(f"Truth data has {len(matching_entities)} entities that should match")

        # 2. Run a query to find these entities (should find all of them)
        result_before = db.aql.execute(
            f"""
            FOR doc IN {collection_name}
            FILTER doc._key IN @entity_ids
            RETURN doc
            """,
            bind_vars={"entity_ids": matching_entities},
        )

        found_before = list(result_before)
        logging.info(f"Before ablation: Found {len(found_before)} of {len(matching_entities)} entities")

        if len(found_before) != len(matching_entities):
            logging.error("Missing entities before ablation")
            all_tests_passed = False
            continue

        # 3. Backup the collection for ablation
        logging.info(f"Backing up {collection_name} for ablation...")
        backup_data = list(db.aql.execute(f"FOR doc IN {collection_name} RETURN doc"))
        logging.info(f"Backed up {len(backup_data)} documents")

        # 4. Ablate the collection (remove all documents)
        logging.info(f"Ablating {collection_name}...")
        db.aql.execute(f"FOR doc IN {collection_name} REMOVE doc IN {collection_name}")

        # 5. Verify the collection is empty
        count_after_ablation = db.aql.execute(f"RETURN LENGTH({collection_name})").next()
        logging.info(f"After ablation: Collection has {count_after_ablation} documents")

        if count_after_ablation != 0:
            logging.error("Failed to fully ablate collection")
            all_tests_passed = False

            # Restore data and continue to next query
            for doc in backup_data:
                # Remove ArangoDB system fields
                doc_copy = doc.copy()
                for field in ["_rev", "_id"]:
                    if field in doc_copy:
                        del doc_copy[field]

                # Reinsert the document
                db.collection(collection_name).insert(doc_copy)

            continue

        # 6. Run the same query after ablation (should find 0 entities)
        result_after = db.aql.execute(
            f"""
            FOR doc IN {collection_name}
            FILTER doc._key IN @entity_ids
            RETURN doc
            """,
            bind_vars={"entity_ids": matching_entities},
        )

        found_after = list(result_after)
        logging.info(f"After ablation: Found {len(found_after)} of {len(matching_entities)} entities")

        if len(found_after) != 0:
            logging.error("Unexpectedly found entities after ablation")
            all_tests_passed = False

        # 7. Restore the collection
        logging.info(f"Restoring {collection_name}...")
        for doc in backup_data:
            # Remove ArangoDB system fields
            doc_copy = doc.copy()
            for field in ["_rev", "_id"]:
                if field in doc_copy:
                    del doc_copy[field]

            # Reinsert the document
            db.collection(collection_name).insert(doc_copy)

        # 8. Verify the collection is restored
        count_after_restore = db.aql.execute(f"RETURN LENGTH({collection_name})").next()
        logging.info(f"After restoration: Collection has {count_after_restore} documents")

        if count_after_restore != len(backup_data):
            logging.error("Failed to fully restore collection")
            all_tests_passed = False
            continue

        # 9. Run the query again after restoration (should find all entities again)
        result_after_restore = db.aql.execute(
            f"""
            FOR doc IN {collection_name}
            FILTER doc._key IN @entity_ids
            RETURN doc
            """,
            bind_vars={"entity_ids": matching_entities},
        )

        found_after_restore = list(result_after_restore)
        logging.info(f"After restoration: Found {len(found_after_restore)} of {len(matching_entities)} entities")

        if len(found_after_restore) != len(matching_entities):
            logging.error("Missing entities after restoration")
            all_tests_passed = False

        # Test passed for this query
        if (
            len(found_before) == len(matching_entities)
            and len(found_after) == 0
            and len(found_after_restore) == len(matching_entities)
        ):
            logging.info(f"Ablation test for query {query_id} PASSED!")
        else:
            logging.error(f"Ablation test for query {query_id} FAILED!")
            all_tests_passed = False

    return all_tests_passed


def main():
    """Run the test."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting single activity test")

    try:
        # Clear existing data
        clear_data()

        # Generate test data
        entity_manager = generate_test_data(count=100)
        if not entity_manager:
            logger.error("Failed to generate test data")
            sys.exit(1)

        # Generate test queries
        queries = generate_test_queries(entity_manager, count=5)
        if not queries:
            logger.error("Failed to generate test queries")
            sys.exit(1)

        # Run data check
        data_check_passed = perform_data_check()
        if not data_check_passed:
            logger.warning("Data check failed, but continuing with direct lookup test")

        # Test direct lookup
        lookup_passed = test_direct_lookup(queries)

        if lookup_passed:
            logger.info("Direct entity lookup test PASSED!")
        else:
            logger.error("Direct entity lookup test FAILED!")
            sys.exit(1)

        # Test simple ablation
        ablation_passed = test_simple_ablation(queries)

        if ablation_passed:
            logger.info("Simple ablation test PASSED!")
        else:
            logger.error("Simple ablation test FAILED!")
            sys.exit(1)

        if data_check_passed and lookup_passed and ablation_passed:
            logger.info("Single activity test completed successfully")
        else:
            logger.warning("Single activity test completed with warnings")

    except Exception as e:
        logger.error(f"Error in single activity test: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
