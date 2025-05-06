"""
Ablation testing framework for evaluating the impact of specific metadata types
on query precision and recall.

This module provides tools to test how the absence of specific collections
affects query results, allowing for quantitative measurement of each
metadata type's contribution to query effectiveness.

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

import logging
import os
import re
import sys
import time
from typing import Dict, List, Any, Tuple, Optional, Set, Union
import json

# Add the Indaleko root to the path
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import our fixed execute_query function instead of the one from query.cli
try:
    from tools.data_generator_enhanced.testing.ablation_execute_query import fixed_execute_query as execute_query
    logging.info("Using fixed execute_query function in ablation_tester")
except ImportError:
    logging.warning("Could not import fixed_execute_query in ablation_tester, falling back to original")
    from query.cli import execute_query
from db.db_config import IndalekoDBConfig
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from db.db_collections import IndalekoDBCollections


class AQLAnalyzer:
    """Utility for analyzing AQL queries and how they change with ablation."""

    def __init__(self):
        """Initialize the AQL analyzer."""
        # Regular expression to find collection references in AQL
        self.collection_pattern = re.compile(r'FOR\s+\w+\s+IN\s+([a-zA-Z0-9_]+)')

    def extract_collections(self, aql: str) -> List[str]:
        """
        Extract collection names from an AQL query string.

        Args:
            aql: The AQL query string to analyze

        Returns:
            List of collection names found in the query
        """
        if not aql:
            return []

        return self.collection_pattern.findall(aql)

    def compare_queries(self, baseline_aql: str, ablated_aql: str) -> Dict[str, Any]:
        """
        Compare baseline and ablated AQL queries to identify differences.

        Args:
            baseline_aql: The original AQL query
            ablated_aql: The AQL query after ablation

        Returns:
            Dictionary with collections found in each query and the differences
        """
        baseline_collections = self.extract_collections(baseline_aql)
        ablated_collections = self.extract_collections(ablated_aql)

        missing_collections = set(baseline_collections) - set(ablated_collections)
        new_collections = set(ablated_collections) - set(baseline_collections)

        return {
            "baseline_collections": baseline_collections,
            "ablated_collections": ablated_collections,
            "missing_collections": list(missing_collections),
            "new_collections": list(new_collections)
        }


class MetricsCalculator:
    """Utility for calculating precision and recall metrics."""

    @staticmethod
    def calculate_metrics(
        baseline_results: List[Dict[str, Any]],
        ablated_results: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        Calculate precision and recall metrics by comparing results.

        Args:
            baseline_results: Results from the baseline query
            ablated_results: Results from the ablated query

        Returns:
            Dictionary with precision, recall, and f1 metrics
        """
        # Extract IDs from results
        baseline_ids = []
        ablated_ids = []

        # Look for common ID fields
        id_fields = ["_id", "_key", "ID", "ObjectIdentifier", "Handle", "URI"]

        # Process baseline results
        for result in baseline_results:
            for field in id_fields:
                if field in result:
                    baseline_ids.append(result[field])
                    break

        # Process ablated results
        for result in ablated_results:
            for field in id_fields:
                if field in result:
                    ablated_ids.append(result[field])
                    break

        # Convert to sets for comparison
        baseline_set = set(baseline_ids)
        ablated_set = set(ablated_ids)

        # Calculate true positives, false positives, false negatives
        true_positives = len(ablated_set.intersection(baseline_set))
        false_positives = len(ablated_set - baseline_set)
        false_negatives = len(baseline_set - ablated_set)

        # Calculate precision, recall, F1
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "baseline_count": len(baseline_set),
            "ablated_count": len(ablated_set)
        }


class CollectionManager:
    """Manages collection visibility for ablation testing."""

    def __init__(self):
        """Initialize the collection manager."""
        self.metadata_manager = IndalekoDBCollectionsMetadata()

    def ablate_collection(self, collection_name: str) -> bool:
        """
        Ablate a collection, making it invisible to queries.

        Args:
            collection_name: Name of the collection to ablate

        Returns:
            True if the collection was successfully ablated, False otherwise
        """
        logging.info(f"Ablating collection: {collection_name}")
        self.metadata_manager.ablate_collection(collection_name)
        return True

    def restore_collection(self, collection_name: str) -> bool:
        """
        Restore a previously ablated collection.

        Args:
            collection_name: Name of the collection to restore

        Returns:
            True if the collection was successfully restored, False otherwise
        """
        logging.info(f"Restoring collection: {collection_name}")
        return self.metadata_manager.restore_collection(collection_name)

    def get_ablated_collections(self) -> Set[str]:
        """
        Get the set of currently ablated collections.

        Returns:
            Set of ablated collection names
        """
        return self.metadata_manager.get_ablated_collections()


class CollectionTruncator:
    """Manages collection truncation as an alternative ablation approach."""

    def __init__(self):
        """Initialize the collection truncator."""
        self.db_config = IndalekoDBConfig()
        self.db = self.db_config.get_arangodb()
        self.truncated_collections = set()

    def truncate_collection(self, collection_name: str) -> bool:
        """
        Empty a collection without removing it.

        Args:
            collection_name: Name of the collection to truncate

        Returns:
            True if the collection was successfully truncated, False otherwise
        """
        try:
            collection = self.db.collection(collection_name)
            collection.truncate()
            self.truncated_collections.add(collection_name)
            logging.info(f"Truncated collection: {collection_name}")
            return True
        except Exception as e:
            logging.error(f"Error truncating collection {collection_name}: {e}")
            return False

    def get_truncated_collections(self) -> Set[str]:
        """
        Get the set of truncated collections.

        Returns:
            Set of truncated collection names
        """
        return self.truncated_collections.copy()


class AblationTester:
    """Main class for testing collection ablation impact on queries."""

    def __init__(self):
        """Initialize the ablation tester."""
        self.collection_manager = CollectionManager()
        self.truncator = CollectionTruncator()
        self.aql_analyzer = AQLAnalyzer()
        self.metrics_calculator = MetricsCalculator()

    def test_collection_ablation(
        self,
        query: str,
        collections_to_ablate: List[str],
        use_truncation: bool = False
    ) -> Dict[str, Any]:
        """
        Test how ablating specific collections affects query results.

        Args:
            query: Natural language query to test
            collections_to_ablate: List of collections to ablate
            use_truncation: If True, truncate collections instead of hiding them

        Returns:
            Dictionary with test results and metrics
        """
        logging.info(f"Testing ablation of collections: {collections_to_ablate}")
        logging.info(f"Query: {query}")

        # Step 1: Run baseline query
        logging.info("Running baseline query...")
        baseline_start = time.time()
        baseline_results, baseline_aql = self._execute_query(query)
        baseline_time = time.time() - baseline_start

        # Step 2: Ablate collections
        if use_truncation:
            for collection in collections_to_ablate:
                self.truncator.truncate_collection(collection)
        else:
            for collection in collections_to_ablate:
                self.collection_manager.ablate_collection(collection)

        # Step 3: Run ablated query
        logging.info("Running ablated query...")
        ablated_start = time.time()
        ablated_results, ablated_aql = self._execute_query(query)
        ablated_time = time.time() - ablated_start

        # Step 4: Restore collections (if using ablation, not truncation)
        if not use_truncation:
            for collection in collections_to_ablate:
                self.collection_manager.restore_collection(collection)

        # Step 5: Analyze AQL
        aql_analysis = self.aql_analyzer.compare_queries(baseline_aql, ablated_aql)

        # Step 6: Calculate metrics
        metrics = self.metrics_calculator.calculate_metrics(baseline_results, ablated_results)

        # Step 7: Prepare and return results
        result = {
            "query": query,
            "ablated_collections": collections_to_ablate,
            "use_truncation": use_truncation,
            "baseline": {
                "result_count": len(baseline_results),
                "aql": baseline_aql,
                "execution_time": baseline_time
            },
            "ablated": {
                "result_count": len(ablated_results),
                "aql": ablated_aql,
                "execution_time": ablated_time
            },
            "aql_analysis": aql_analysis,
            "metrics": metrics,
            "timestamp": time.time()
        }

        return result

    def run_ablation_series(
        self,
        query: str,
        collection_groups: Dict[str, List[str]],
        use_truncation: bool = False
    ) -> Dict[str, Any]:
        """
        Run a series of ablation tests, testing each collection group separately.

        Args:
            query: Natural language query to test
            collection_groups: Dictionary mapping group names to collections
            use_truncation: If True, truncate collections instead of hiding them

        Returns:
            Dictionary with results for each group
        """
        series_results = {
            "query": query,
            "timestamp": time.time(),
            "use_truncation": use_truncation,
            "results": {}
        }

        # Run baseline first (no ablation)
        logging.info("Running baseline query...")
        baseline_results, baseline_aql = self._execute_query(query)

        series_results["baseline"] = {
            "result_count": len(baseline_results),
            "aql": baseline_aql
        }

        # Test each collection group
        for group_name, collections in collection_groups.items():
            logging.info(f"Testing ablation group: {group_name}")
            result = self.test_collection_ablation(query, collections, use_truncation)
            series_results["results"][group_name] = result

        return series_results

    def _execute_query(self, query: str) -> Tuple[List[Dict[str, Any]], str]:
        """
        Execute a query and capture both results and AQL.

        Args:
            query: The natural language query to execute

        Returns:
            Tuple of (results, aql)
        """
        # Use global execute_query function from query.cli module
        results = execute_query(query, capture_aql=True)

        # The AQL is attached to the results in "_debug" field
        aql = ""
        if results and "_debug" in results[0]:
            aql = results[0]["_debug"].get("aql", "")

            # Remove _debug field from results
            for result in results:
                if "_debug" in result:
                    del result["_debug"]

        return results, aql

    def save_results(self, results: Dict[str, Any], filename: str) -> None:
        """
        Save ablation test results to a file.

        Args:
            results: The test results to save
            filename: Path to save the results to
        """
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)

        logging.info(f"Results saved to {filename}")


def main():
    """Test the ablation framework with a simple example."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Initialize the tester
    tester = AblationTester()

    # Define collection groups for testing
    collection_groups = {
        "activity": [
            IndalekoDBCollections.Indaleko_ActivityContext_Collection,
            IndalekoDBCollections.Indaleko_TempActivityContext_Collection,
            IndalekoDBCollections.Indaleko_GeoActivityContext_Collection,
            IndalekoDBCollections.Indaleko_MusicActivityContext_Collection
        ],
        "semantic": [
            IndalekoDBCollections.Indaleko_SemanticData_Collection
        ],
        "storage": [
            IndalekoDBCollections.Indaleko_Object_Collection,
            IndalekoDBCollections.Indaleko_Relationship_Collection
        ]
    }

    # Get a test query from command line
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = "Find all PDF documents that I edited last week"

    # Run an ablation test series
    results = tester.run_ablation_series(query, collection_groups)

    # Save the results
    tester.save_results(results, "ablation_test_results.json")

    # Print a summary
    print("\nAblation Test Summary:")
    print(f"Query: {query}")
    print("\nBaseline results:", results["baseline"]["result_count"])

    for group, group_result in results["results"].items():
        metrics = group_result["metrics"]
        print(f"\n{group} ablation:")
        print(f"  Precision: {metrics['precision']:.2f}")
        print(f"  Recall: {metrics['recall']:.2f}")
        print(f"  F1 Score: {metrics['f1']:.2f}")

    print("\nComplete results saved to ablation_test_results.json")


if __name__ == "__main__":
    main()
