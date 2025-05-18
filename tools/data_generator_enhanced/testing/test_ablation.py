"""
Test script for the collection ablation framework.

This script tests whether the ablation mechanism correctly hides collections
from queries and whether this affects query results as expected.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import os
import sys
import logging
from typing import Dict, List, Any, Set

# Add the root directory to the path
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Apply the registration service patch to fix database access
try:
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
except ImportError:
    logging.warning("Could not patch registration service - module not found")

from db.db_config import IndalekoDBConfig
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from db.db_collections import IndalekoDBCollections

# Import our fixed execute_query function instead of the one from query.cli
try:
    from tools.data_generator_enhanced.testing.ablation_execute_query import fixed_execute_query as execute_query
    logging.info("Using fixed execute_query function")
except ImportError:
    logging.warning("Could not import fixed_execute_query, falling back to original")
    from query.cli import execute_query
from tools.data_generator_enhanced.testing.ablation_tester import AblationTester, AQLAnalyzer


def test_ablation_mechanism():
    """Test that the ablation mechanism correctly hides collections."""
    logging.info("Testing collection ablation mechanism")

    # Initialize components
    metadata_manager = IndalekoDBCollectionsMetadata()

    # Choose a collection to ablate
    test_collection = IndalekoDBCollections.Indaleko_Object_Collection

    # Get initial collection metadata
    all_collections_before = metadata_manager.get_all_collections_metadata()

    # Verify the test collection exists
    if test_collection not in all_collections_before:
        logging.error(f"Test collection {test_collection} not found in metadata")
        return False

    logging.info(f"Found test collection {test_collection} in initial metadata")

    # Ablate the collection
    metadata_manager.ablate_collection(test_collection)

    # Get updated collection metadata
    all_collections_after = metadata_manager.get_all_collections_metadata()

    # Verify the test collection is now hidden
    if test_collection in all_collections_after:
        logging.error(f"Test collection {test_collection} still present after ablation")
        return False

    logging.info(f"Test collection {test_collection} successfully ablated")

    # Restore the collection
    metadata_manager.restore_collection(test_collection)

    # Get final collection metadata
    all_collections_final = metadata_manager.get_all_collections_metadata()

    # Verify the test collection is restored
    if test_collection not in all_collections_final:
        logging.error(f"Test collection {test_collection} not restored")
        return False

    logging.info(f"Test collection {test_collection} successfully restored")

    return True


def test_ablation_impact_on_query():
    """Test how collection ablation affects query results."""
    logging.info("Testing ablation impact on query results")

    # Initialize components
    metadata_manager = IndalekoDBCollectionsMetadata()
    aql_analyzer = AQLAnalyzer()

    # Choose a collection to ablate
    test_collection = IndalekoDBCollections.Indaleko_Object_Collection

    # Execute a query that should use the test collection
    test_query = "Find all PDF documents"

    # Run baseline query
    logging.info(f"Running baseline query: '{test_query}'")
    baseline_results = execute_query(test_query, capture_aql=True)

    if not baseline_results:
        logging.warning("Baseline query returned no results. Test may not be valid.")
        return False

    # Extract AQL from results
    baseline_aql = ""
    if baseline_results and "_debug" in baseline_results[0]:
        baseline_aql = baseline_results[0]["_debug"].get("aql", "")

    # Verify the test collection is used in the baseline query
    collections_in_aql = aql_analyzer.extract_collections(baseline_aql)
    if test_collection not in collections_in_aql:
        logging.warning(f"Test collection {test_collection} not used in baseline query. Test may not be valid.")
        return False

    logging.info(f"Baseline query uses collections: {collections_in_aql}")

    # Ablate the test collection
    metadata_manager.ablate_collection(test_collection)

    # Run the query again
    logging.info(f"Running query with ablated collection: '{test_query}'")
    ablated_results = execute_query(test_query, capture_aql=True)

    # Extract AQL from results
    ablated_aql = ""
    if ablated_results and "_debug" in ablated_results[0]:
        ablated_aql = ablated_results[0]["_debug"].get("aql", "")

    # Verify the test collection is NOT used in the ablated query
    collections_in_ablated_aql = aql_analyzer.extract_collections(ablated_aql)
    if test_collection in collections_in_ablated_aql:
        logging.error(f"Test collection {test_collection} still used in ablated query.")
        metadata_manager.restore_collection(test_collection)
        return False

    logging.info(f"Ablated query uses collections: {collections_in_ablated_aql}")

    # Compare query results
    baseline_count = len(baseline_results)
    ablated_count = len(ablated_results)

    logging.info(f"Baseline query returned {baseline_count} results")
    logging.info(f"Ablated query returned {ablated_count} results")

    # Analyze the differences
    aql_analysis = aql_analyzer.compare_queries(baseline_aql, ablated_aql)
    logging.info(f"AQL Analysis: {aql_analysis}")

    # Restore the collection
    metadata_manager.restore_collection(test_collection)

    return True


def test_ablation_tester_class():
    """Test the AblationTester class with a simple example."""
    logging.info("Testing AblationTester class")

    # Initialize tester
    tester = AblationTester()

    # Define test query and collections to ablate
    test_query = "Find all PDF documents"
    collections_to_ablate = [IndalekoDBCollections.Indaleko_Object_Collection]

    # Run ablation test
    logging.info(f"Running ablation test for query: '{test_query}'")
    results = tester.test_collection_ablation(test_query, collections_to_ablate)

    # Verify test results
    if not results:
        logging.error("AblationTester returned no results")
        return False

    # Check if metrics were calculated
    if "metrics" not in results:
        logging.error("AblationTester results missing metrics")
        return False

    # Check if AQL analysis was performed
    if "aql_analysis" not in results:
        logging.error("AblationTester results missing AQL analysis")
        return False

    # Log results
    logging.info(f"Ablation test metrics: {results['metrics']}")
    logging.info(f"Ablation test AQL analysis: {results['aql_analysis']}")

    return True


def main():
    """Main test entry point."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    logging.info("Starting ablation framework tests")

    # Run tests
    ablation_mechanism_test = test_ablation_mechanism()
    query_impact_test = test_ablation_impact_on_query()
    tester_class_test = test_ablation_tester_class()

    # Summary
    logging.info("\nTest Results Summary:")
    logging.info(f"Ablation Mechanism Test: {'PASSED' if ablation_mechanism_test else 'FAILED'}")
    logging.info(f"Query Impact Test: {'PASSED' if query_impact_test else 'FAILED'}")
    logging.info(f"AblationTester Class Test: {'PASSED' if tester_class_test else 'FAILED'}")

    # Overall result
    all_tests_passed = ablation_mechanism_test and query_impact_test and tester_class_test
    logging.info(f"Overall Result: {'PASSED' if all_tests_passed else 'FAILED'}")

    return 0 if all_tests_passed else 1


if __name__ == "__main__":
    sys.exit(main())
