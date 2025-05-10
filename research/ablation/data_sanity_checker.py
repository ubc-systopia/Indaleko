#!/usr/bin/env python3
"""Data Sanity Checker for Ablation Framework.

This module provides utilities to verify the integrity of data in the ablation framework
before running tests. It implements a fail-fast approach for data validation.
"""

import logging
import sys
import uuid

from db.db_config import IndalekoDBConfig


class DataSanityChecker:
    """Validates data integrity for ablation testing.

    This class performs various sanity checks on the data used for ablation testing,
    including verifying collection existence, truth data integrity, entity existence,
    and cross-collection dependencies.
    """

    def __init__(self, fail_fast: bool = True):
        """Initialize the data sanity checker.

        Args:
            fail_fast: If True, raise exception on first validation failure.
        """
        self.logger = logging.getLogger(__name__)
        self.fail_fast = fail_fast
        self.db_config = None
        self.db = None
        self.validation_errors = []
        self._setup_db_connection()

        # Define expected collection names
        self.activity_collections = [
            "AblationLocationActivity",
            "AblationTaskActivity",
            "AblationMusicActivity",
            "AblationCollaborationActivity",
            "AblationStorageActivity",
            "AblationMediaActivity",
        ]

        # Define truth collection name - use the one defined in IndalekoDBCollections
        self.truth_collection = "AblationQueryTruth"

    def _setup_db_connection(self) -> bool:
        """Set up the database connection.

        Returns:
            bool: True if the connection was successful, False otherwise.
        """
        try:
            self.db_config = IndalekoDBConfig()
            self.db = self.db_config.get_arangodb()
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            if self.fail_fast:
                raise
            return False

    def _fail(self, message: str) -> None:
        """Log a validation error and fail-stop with sys.exit(1).

        Args:
            message: The error message to log.
        """
        self.logger.error(f"VALIDATION ERROR: {message}")
        self.validation_errors.append(message)
        if self.fail_fast:
            self.logger.error(f"CRITICAL ERROR: {message}")
            sys.exit(1)  # Use sys.exit(1) for proper fail-stop behavior

    def verify_collections_exist(self) -> bool:
        """Verify that all required collections exist in the database.

        Returns:
            bool: True if all collections exist, False otherwise.
        """
        self.logger.info("Verifying collection existence...")

        if not self.db:
            self._fail("No database connection available")
            return False

        all_collections_exist = True

        # Check activity collections
        for collection_name in self.activity_collections:
            if not self.db.has_collection(collection_name):
                self.logger.warning(f"Collection {collection_name} does not exist")
                all_collections_exist = False

        # Check truth collection
        if not self.db.has_collection(self.truth_collection):
            self._fail(f"Truth collection {self.truth_collection} does not exist")
            return False

        if not all_collections_exist:
            self.logger.warning(
                "Some activity collections don't exist. This may be expected if those activities aren't being tested.",
            )

        return True

    def verify_truth_data_integrity(self) -> bool:
        """Verify the integrity of truth data.

        Checks that truth data documents have the required fields and consistent structure.

        Returns:
            bool: True if truth data is valid, False otherwise.
        """
        self.logger.info("Verifying truth data integrity...")

        if not self.db:
            self._fail("No database connection available")
            return False

        try:
            # Get all truth data documents
            result = self.db.aql.execute(
                f"""
                FOR doc IN {self.truth_collection}
                RETURN doc
                """,
            )

            truth_docs = list(result)

            if not truth_docs:
                self._fail(f"No truth data found in {self.truth_collection}")
                return False

            for doc in truth_docs:
                # Check required fields
                if "query_id" not in doc:
                    self._fail(f"Missing 'query_id' in truth document {doc['_key']}")
                    continue

                # Check for either matching_entities or entity_ids field
                if "matching_entities" not in doc and "entity_ids" not in doc:
                    self._fail(f"Missing 'matching_entities' or 'entity_ids' in truth document {doc['_key']}")
                    continue

                # For documents with entity_ids, treat them the same as matching_entities
                if "entity_ids" in doc and "matching_entities" not in doc:
                    doc["matching_entities"] = doc["entity_ids"]

                if "collection" not in doc:
                    self._fail(f"Missing 'collection' field in truth document {doc['_key']}")
                    continue

                # Check if collection field has valid value
                collection = doc["collection"]
                if collection not in self.activity_collections:
                    self.logger.warning(f"Truth document {doc['_key']} references unknown collection '{collection}'")

                # Get the entities list (either matching_entities or entity_ids)
                entities_list = doc.get("matching_entities", doc.get("entity_ids", []))

                # Check if entities list is a list
                if not isinstance(entities_list, list):
                    self._fail(f"Entity list is not a list in truth document {doc['_key']}")
                    continue

                # Check that entities list is not empty
                if not entities_list:
                    self.logger.warning(f"Empty entity list in truth document {doc['_key']}")

            return True
        except Exception as e:
            self._fail(f"Failed to verify truth data integrity: {e}")
            return False

    def verify_truth_entities_exist(self) -> bool:
        """Verify that entities referenced in truth data exist in their respective collections.

        Returns:
            bool: True if all referenced entities exist, False otherwise.
        """
        self.logger.info("Verifying truth entities existence...")

        if not self.db:
            self._fail("No database connection available")
            return False

        try:
            # Get all truth data documents
            result = self.db.aql.execute(
                f"""
                FOR doc IN {self.truth_collection}
                RETURN doc
                """,
            )

            all_entities_exist = True
            missing_entities = []

            for doc in result:
                collection = doc.get("collection")
                if not collection:
                    continue

                # Skip collections that don't exist
                if not self.db.has_collection(collection):
                    self.logger.warning(f"Collection {collection} referenced in truth data doesn't exist")
                    continue

                # Get entity IDs (either from matching_entities or entity_ids)
                entities_list = doc.get("matching_entities", doc.get("entity_ids", []))

                # Check each entity
                for entity_id in entities_list:
                    entity_exists = False
                    try:
                        # Try to get the entity document
                        entity_doc = self.db.collection(collection).get(entity_id)
                        if entity_doc:
                            entity_exists = True
                    except Exception as e:
                        self.logger.debug(f"Error checking entity {entity_id}: {e}")

                    if not entity_exists:
                        error_msg = (
                            f"Entity {entity_id} referenced in truth data doesn't exist in collection {collection}"
                        )
                        self.logger.error(error_msg)
                        missing_entities.append((entity_id, collection))
                        all_entities_exist = False

            if not all_entities_exist:
                # Use _fail with a detailed error message to enable proper fail-stop
                self._fail(
                    f"Found {len(missing_entities)} entities referenced in truth data that don't exist in their collections: {missing_entities[:5]}",
                )
                return False

            return True
        except Exception as e:
            self._fail(f"Failed to verify truth entities existence: {e}")
            return False

    def verify_query_execution(self, query_ids: list[str] | None = None) -> bool:
        """Verify that queries execute correctly and return expected results.

        Args:
            query_ids: Optional list of query IDs to verify. If None, all queries are verified.

        Returns:
            bool: True if query execution is valid, False otherwise.
        """
        self.logger.info("Verifying query execution...")

        if not self.db:
            self._fail("No database connection available")
            return False

        try:
            # Get truth data documents for specified queries or all queries
            query = f"""
            FOR doc IN {self.truth_collection}
            """

            if query_ids:
                query += """
                FILTER doc.query_id IN @query_ids
                """
                bind_vars = {"query_ids": query_ids}
            else:
                bind_vars = {}

            query += """
            RETURN doc
            """

            result = self.db.aql.execute(query, bind_vars=bind_vars)
            truth_docs = list(result)

            if not truth_docs:
                if query_ids:
                    self._fail(f"No truth data found for query IDs: {query_ids}")
                else:
                    self._fail(f"No truth data found in {self.truth_collection}")
                return False

            all_queries_valid = True

            for doc in truth_docs:
                query_id = doc.get("query_id")
                collection = doc.get("collection")
                # Get entity IDs (either from matching_entities or entity_ids)
                matching_entities = doc.get("matching_entities", doc.get("entity_ids", []))

                if not query_id or not collection or not matching_entities:
                    continue

                # Execute a query to get entities by their IDs
                entity_query = f"""
                FOR doc IN {collection}
                FILTER doc._key IN @entity_ids
                RETURN doc
                """

                entity_result = self.db.aql.execute(entity_query, bind_vars={"entity_ids": matching_entities})

                entity_docs = list(entity_result)

                # Check if all expected entities were found
                if len(entity_docs) != len(matching_entities):
                    self.logger.warning(
                        f"Query {query_id} expected {len(matching_entities)} results, but got {len(entity_docs)} "
                        f"from collection {collection}",
                    )
                    all_queries_valid = False

            if not all_queries_valid:
                self._fail("Some queries do not return the expected results")
                return False

            return True
        except Exception as e:
            self._fail(f"Failed to verify query execution: {e}")
            return False

    def verify_cross_collection_ids(self) -> bool:
        """Verify that entity IDs don't overlap across different collections.

        Returns:
            bool: True if no ID overlaps exist, False otherwise.
        """
        self.logger.info("Verifying cross-collection ID uniqueness...")

        if not self.db:
            self._fail("No database connection available")
            return False

        try:
            collection_entities: dict[str, set[str]] = {}

            # Collect entity IDs from each collection
            for collection_name in self.activity_collections:
                if not self.db.has_collection(collection_name):
                    continue

                result = self.db.aql.execute(
                    f"""
                    FOR doc IN {collection_name}
                    RETURN doc._key
                    """,
                )

                collection_entities[collection_name] = set(result)

            # Check for overlaps
            overlaps_found = False

            for collection1 in collection_entities:
                for collection2 in collection_entities:
                    if collection1 >= collection2:
                        continue

                    # Find overlapping IDs
                    overlap = collection_entities[collection1].intersection(collection_entities[collection2])

                    if overlap:
                        self.logger.warning(
                            f"Found {len(overlap)} overlapping entity IDs between {collection1} and {collection2}",
                        )
                        overlaps_found = True

            if overlaps_found:
                self.logger.warning(
                    "Entity ID overlaps found across collections. This may be normal but can cause cross-collection contamination.",
                )

            return True
        except Exception as e:
            self._fail(f"Failed to verify cross-collection IDs: {e}")
            return False

    def verify_truth_query_ids(self) -> bool:
        """Verify that truth data query IDs are valid UUIDs and composite keys are unique.

        Returns:
            bool: True if all query IDs are valid, False otherwise.
        """
        self.logger.info("Verifying truth query IDs...")

        if not self.db:
            self._fail("No database connection available")
            return False

        try:
            # Get all truth documents with their keys
            result = self.db.aql.execute(
                f"""
                FOR doc IN {self.truth_collection}
                RETURN {{
                    _key: doc._key,
                    query_id: doc.query_id,
                    collection: doc.collection
                }}
                """,
            )

            documents = list(result)

            # Check composite keys (must be unique by design)
            # Check that each query_id + collection combination is unique (composite uniqueness)
            query_collection_combinations = {}
            duplicate_combinations = []

            for doc in documents:
                query_id = doc.get("query_id")
                collection = doc.get("collection")
                key = doc.get("_key")

                if not query_id or not collection:
                    continue

                # Create a tuple key for uniqueness check
                combo_key = (query_id, collection)

                if combo_key in query_collection_combinations:
                    duplicate_combinations.append((query_id, collection))
                else:
                    query_collection_combinations[combo_key] = key

            if duplicate_combinations:
                self.logger.warning(
                    f"Found {len(duplicate_combinations)} duplicate query_id + collection combinations in truth data. "
                    f"This could indicate duplicate truth data entries.",
                )

            # Extract just the query IDs for UUID validation
            query_ids = [doc.get("query_id") for doc in documents if "query_id" in doc]

            # Duplicate query IDs may be normal due to composite keys
            # (one query can have multiple truth docs for different collections)
            unique_query_ids = set(query_ids)
            if len(query_ids) != len(unique_query_ids):
                duplicate_count = len(query_ids) - len(unique_query_ids)
                self.logger.info(
                    f"Found {duplicate_count} duplicate query IDs in truth data. "
                    f"This is expected if you're using composite keys for cross-collection truth data.",
                )

            # Check that all query IDs are valid UUIDs
            invalid_ids = []
            for query_id in unique_query_ids:
                try:
                    uuid.UUID(query_id)
                except (ValueError, TypeError, AttributeError):
                    invalid_ids.append(query_id)

            if invalid_ids:
                self._fail(f"Found {len(invalid_ids)} invalid UUID query IDs in truth data")
                return False

            return True
        except Exception as e:
            self._fail(f"Failed to verify truth query IDs: {e}")
            return False

    def run_all_checks(self) -> bool:
        """Run all sanity checks.

        Returns:
            bool: True if all checks pass, False otherwise.
        """
        self.logger.info("Running all sanity checks...")

        checks = [
            self.verify_collections_exist,
            self.verify_truth_data_integrity,
            self.verify_truth_entities_exist,
            self.verify_query_execution,
            self.verify_cross_collection_ids,
            self.verify_truth_query_ids,
        ]

        all_passed = True

        for check in checks:
            try:
                if not check():
                    all_passed = False
                    if self.fail_fast:
                        break
            except Exception as e:
                self.logger.error(f"Check {check.__name__} failed with exception: {e}")
                all_passed = False
                if self.fail_fast:
                    break

        if all_passed:
            self.logger.info("All sanity checks passed!")
        else:
            self.logger.error(f"Sanity checks failed with {len(self.validation_errors)} errors")
            for i, error in enumerate(self.validation_errors, 1):
                self.logger.error(f"Error {i}: {error}")

        return all_passed


def setup_logging():
    """Set up logging for the sanity checker."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def main():
    """Run the data sanity checker from the command line."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting data sanity checks for ablation framework")

    # Parse command line arguments
    import argparse

    parser = argparse.ArgumentParser(description="Run data sanity checks for ablation framework")
    parser.add_argument("--no-fail-fast", action="store_true", help="Continue checks after first failure")
    parser.add_argument("--query-id", action="append", help="Verify specific query IDs")
    args = parser.parse_args()

    try:
        # Create checker and run checks
        checker = DataSanityChecker(fail_fast=not args.no_fail_fast)
        result = checker.run_all_checks()

        if args.query_id:
            logger.info(f"Verifying specific query IDs: {args.query_id}")
            checker.verify_query_execution(args.query_id)

        # Set exit code based on check results
        if not result:
            logger.error("Data sanity checks failed!")
            sys.exit(1)
        else:
            logger.info("All data sanity checks passed!")
            sys.exit(0)
    except Exception as e:
        logger.error(f"Error running data sanity checks: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
