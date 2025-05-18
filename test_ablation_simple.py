"""
Simplified test for the ablation mechanism.

This script tests the core functionality of the ablation mechanism
without unnecessary complexity.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import logging
import os
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Add the Indaleko root to the path
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Apply the registration service patch
from utils.registration_service import IndalekoRegistrationService


# Patch the get_provider_list method to use aql.execute instead of execute
def patched_get_provider_list(self):
    """Patched version that uses aql.execute for non-admin access."""
    try:
        from db.db_config import IndalekoDBConfig

        aql_query = f"""
            FOR provider IN {self.collection_name}
            RETURN provider
        """
        # Use aql.execute instead of execute
        cursor = IndalekoDBConfig().get_arangodb().aql.execute(aql_query)
        return list(cursor)
    except Exception as e:
        logging.exception(f"Error getting provider list: {e}")
        return []


# Apply the patch
IndalekoRegistrationService.get_provider_list = patched_get_provider_list
logging.info("Registration service patched for database access")

# Import necessary modules
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from db.db_config import IndalekoDBConfig


def test_collection_metadata():
    """Test that we can access and list collections."""
    db_config = IndalekoDBConfig()
    db = db_config.get_arangodb()
    logging.info("Connected to ArangoDB server")

    try:
        collection_manager = IndalekoDBCollectionsMetadata(db_config)
        collections = collection_manager.get_all_collections_metadata()
        logging.info(f"Successfully retrieved {len(collections)} collections")

        for i, (name, _) in enumerate(collections.items()):
            if i < 5:  # Only show first 5 to avoid cluttering the output
                logging.info(f"Collection: {name}")
            else:
                break

        return True
    except Exception as e:
        logging.exception(f"Error getting collections: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_ablation():
    """Test the basic ablation mechanism."""
    try:
        collection_manager = IndalekoDBCollectionsMetadata()
        collections_before = collection_manager.get_all_collections_metadata()

        # Choose a collection to ablate
        test_collection = None
        for name in collections_before:
            test_collection = name
            break

        if not test_collection:
            logging.error("No collections found")
            return False

        logging.info(f"Testing ablation of collection: {test_collection}")

        # Ablate the collection
        collection_manager.ablate_collection(test_collection)

        # Check that the collection is now hidden
        collections_after = collection_manager.get_all_collections_metadata()
        if test_collection in collections_after:
            logging.error(f"Collection {test_collection} still present after ablation")
            return False

        logging.info(f"Successfully ablated collection: {test_collection}")

        # Restore the collection
        collection_manager.restore_collection(test_collection)

        # Check that the collection is visible again
        collections_final = collection_manager.get_all_collections_metadata()
        if test_collection not in collections_final:
            logging.error(f"Collection {test_collection} not restored properly")
            return False

        logging.info(f"Successfully restored collection: {test_collection}")
        return True

    except Exception as e:
        logging.exception(f"Error during ablation test: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main entry point for testing."""
    logging.info("Starting simplified ablation tests")

    # First test collection access
    metadata_test = test_collection_metadata()
    logging.info(f"Collection metadata access: {'PASSED' if metadata_test else 'FAILED'}")

    if not metadata_test:
        logging.error("Cannot proceed with ablation tests - collection access failed")
        return 1

    # Test ablation
    ablation_test = test_ablation()
    logging.info(f"Ablation test: {'PASSED' if ablation_test else 'FAILED'}")

    return 0 if metadata_test and ablation_test else 1


if __name__ == "__main__":
    sys.exit(main())
