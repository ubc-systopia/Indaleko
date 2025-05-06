"""
Minimal test for collection ablation.

This script provides a completely isolated test of the ablation mechanism
without requiring any database connection at all.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import logging
import sys
from typing import Any

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class MockCollectionMetadata:
    """Mock version of IndalekoDBCollectionsMetadata for testing."""

    def __init__(self):
        """Initialize with some mock collections."""
        self._collections = {
            "Objects": {"name": "Objects", "description": "Storage objects"},
            "Relationships": {"name": "Relationships", "description": "Object relationships"},
            "ActivityContext": {"name": "ActivityContext", "description": "Activity context data"},
        }
        self._ablated_collections = set()

    def get_all_collections_metadata(self) -> dict[str, dict[str, Any]]:
        """Get all non-ablated collections metadata."""
        return {name: data for name, data in self._collections.items() if name not in self._ablated_collections}

    def ablate_collection(self, collection_name: str) -> str:
        """Add a collection to the ablation list."""
        if collection_name in self._collections:
            self._ablated_collections.add(collection_name)
            logging.info(f"Ablated collection: {collection_name}")
            return collection_name
        logging.warning(f"Cannot ablate unknown collection: {collection_name}")
        return ""

    def restore_collection(self, collection_name: str) -> bool:
        """Remove a collection from the ablation list."""
        if collection_name in self._ablated_collections:
            self._ablated_collections.remove(collection_name)
            logging.info(f"Restored collection: {collection_name}")
            return True
        logging.warning(f"Collection not ablated: {collection_name}")
        return False

    def is_ablated(self, collection_name: str) -> bool:
        """Check if a collection is currently ablated."""
        return collection_name in self._ablated_collections

    def get_ablated_collections(self) -> set[str]:
        """Get the set of ablated collections."""
        return self._ablated_collections.copy()


class MockQueryTranslator:
    """Mock query translator to test how ablation affects query generation."""

    def __init__(self, metadata_manager: MockCollectionMetadata):
        """Initialize with a metadata manager."""
        self.metadata_manager = metadata_manager

    def translate(self, query_text: str) -> dict[str, Any]:
        """Mock translation of query to AQL."""
        if "document" in query_text.lower() or "file" in query_text.lower():
            collections = []

            # Only include non-ablated collections
            if not self.metadata_manager.is_ablated("Objects"):
                collections.append("Objects")

            if not self.metadata_manager.is_ablated("Relationships"):
                collections.append("Relationships")

            if not collections:
                # No collections available for query
                return {"aql_query": "", "bind_vars": {}, "collections": []}

            # Build mock AQL based on available collections
            aql = ""
            for collection in collections:
                if aql:
                    aql += "\nUNION\n"
                aql += f"FOR doc IN {collection}\n"
                aql += "  FILTER doc.Type == 'PDF'\n"
                aql += "  RETURN { _id: doc._id, Label: doc.Label }"

            return {"aql_query": aql, "bind_vars": {"type": "PDF"}, "collections": collections}
        else:
            # Activity query
            collections = []

            if not self.metadata_manager.is_ablated("ActivityContext"):
                collections.append("ActivityContext")

            if not collections:
                return {"aql_query": "", "bind_vars": {}, "collections": []}

            aql = f"FOR activity IN {collections[0]}\n"
            aql += "  FILTER activity.Type == 'UserActivity'\n"
            aql += "  RETURN activity"

            return {"aql_query": aql, "bind_vars": {}, "collections": collections}


def test_ablation_mechanism():
    """Test that the ablation mechanism correctly hides collections."""
    logging.info("Testing ablation mechanism")

    # Initialize components
    metadata_manager = MockCollectionMetadata()

    # Get initial collection count
    collections_before = metadata_manager.get_all_collections_metadata()
    logging.info(f"Initial collections: {', '.join(collections_before.keys())}")

    # Ablate a collection
    metadata_manager.ablate_collection("Objects")

    # Get collection count after ablation
    collections_after = metadata_manager.get_all_collections_metadata()
    logging.info(f"Collections after ablation: {', '.join(collections_after.keys())}")

    # Verify collection is hidden
    if "Objects" in collections_after:
        logging.error("Objects collection still present after ablation")
        return False

    # Restore the collection
    metadata_manager.restore_collection("Objects")

    # Verify collection is restored
    collections_final = metadata_manager.get_all_collections_metadata()
    logging.info(f"Collections after restoration: {', '.join(collections_final.keys())}")

    if "Objects" not in collections_final:
        logging.error("Objects collection not restored")
        return False

    return True


def test_query_impact():
    """Test how ablation affects query generation."""
    logging.info("Testing impact on query translation")

    # Initialize components
    metadata_manager = MockCollectionMetadata()
    translator = MockQueryTranslator(metadata_manager)

    # Test document query with all collections
    query = "Find all PDF documents"
    baseline_result = translator.translate(query)
    logging.info(f"Baseline query uses collections: {baseline_result['collections']}")

    # Ablate Objects collection
    metadata_manager.ablate_collection("Objects")

    # Test query with ablated collection
    ablated_result = translator.translate(query)
    logging.info(f"Ablated query uses collections: {ablated_result['collections']}")

    # Verify Objects is not used
    if "Objects" in ablated_result["collections"]:
        logging.error("Objects collection still used after ablation")
        return False

    # Restore collection
    metadata_manager.restore_collection("Objects")

    return True


def main():
    """Main entry point for testing."""
    logging.info("Starting minimal ablation tests")

    # Run tests
    ablation_test = test_ablation_mechanism()
    impact_test = test_query_impact()

    # Display results
    logging.info("\nTest Results:")
    logging.info(f"Ablation Mechanism Test: {'PASSED' if ablation_test else 'FAILED'}")
    logging.info(f"Query Impact Test: {'PASSED' if impact_test else 'FAILED'}")

    # Overall result
    all_passed = ablation_test and impact_test
    logging.info(f"Overall Result: {'PASSED' if all_passed else 'FAILED'}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
