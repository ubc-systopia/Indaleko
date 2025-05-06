"""
Basic test for collection ablation.

This script performs a simple test of the ablation mechanism without
requiring complex database operations.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import logging
import sys

from db.db_collection_metadata import IndalekoDBCollectionsMetadata

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def test_simple_ablation():
    """Test the basic ablation mechanism without executing queries."""
    try:
        logging.info("Testing basic ablation mechanism")

        # Initialize the collection metadata manager
        metadata_manager = IndalekoDBCollectionsMetadata()

        # Get initial collections
        collections_before = metadata_manager.get_all_collections_metadata()
        logging.info(f"Initial collections count: {len(collections_before)}")

        # Choose a collection to ablate
        for collection_name in collections_before:
            logging.info(f"Found collection: {collection_name}")
            test_collection = collection_name
            break

        # Ablate the collection
        if test_collection:
            logging.info(f"Ablating collection: {test_collection}")
            metadata_manager.ablate_collection(test_collection)

            # Get updated collections
            collections_after = metadata_manager.get_all_collections_metadata()
            logging.info(f"Collections after ablation: {len(collections_after)}")

            # Verify the collection is hidden
            if test_collection in collections_after:
                logging.error(f"Collection {test_collection} still visible after ablation")
                return False
            else:
                logging.info(f"Collection {test_collection} successfully ablated")

            # Restore the collection
            logging.info(f"Restoring collection: {test_collection}")
            metadata_manager.restore_collection(test_collection)

            # Verify restoration
            collections_final = metadata_manager.get_all_collections_metadata()
            if test_collection not in collections_final:
                logging.error(f"Collection {test_collection} not restored properly")
                return False

            logging.info(f"Collection {test_collection} successfully restored")
            return True
        else:
            logging.error("No collections found to test ablation")
            return False

    except Exception as e:
        logging.exception(f"Error during ablation test: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    if test_simple_ablation():
        logging.info("Basic ablation test PASSED")
        sys.exit(0)
    else:
        logging.error("Basic ablation test FAILED")
        sys.exit(1)
