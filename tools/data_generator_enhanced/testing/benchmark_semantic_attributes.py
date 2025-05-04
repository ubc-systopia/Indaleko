"""
Benchmark suite for evaluating semantic attribute consistency across queries.

This benchmark specifically tests how semantic attribute consistency affects
query precision and recall metrics - an important validation of realistic
data generation capabilities.
"""

import argparse
import datetime
import json
import uuid
import logging
import os
import random
import sys
import time
import uuid
from typing import Dict, List, Any, Tuple, Optional

# JSON encoder that can handle UUIDs and datetimes
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj)

# Setup path for imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import Indaleko data models
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from data_models.i_object import IndalekoObjectDataModel

# Import data generator components
from tools.data_generator_enhanced.agents.data_gen.core.semantic_attributes import SemanticAttributeRegistry
from tools.data_generator_enhanced.agents.data_gen.tools.stats import ActivityGeneratorTool, FileMetadataGeneratorTool


class BenchmarkConfig:
    """Configuration for semantic attribute benchmark."""

    def __init__(self,
                 dataset_size: int = 1000,
                 query_count: int = 5,
                 attribute_domains: List[str] = None,
                 output_path: str = None):
        """Initialize benchmark configuration.

        Args:
            dataset_size: Number of records to generate
            query_count: Number of queries to test
            attribute_domains: Domains to include in testing
            output_path: Path to save results
        """
        self.dataset_size = dataset_size
        self.query_count = query_count
        self.attribute_domains = attribute_domains or [
            SemanticAttributeRegistry.DOMAIN_ACTIVITY,
            SemanticAttributeRegistry.DOMAIN_STORAGE,
            SemanticAttributeRegistry.DOMAIN_SEMANTIC
        ]

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_path = output_path or f"benchmark_results_{timestamp}.json"


class SemanticAttributeBenchmark:
    """Benchmark for semantic attribute consistency across queries."""

    def __init__(self, config: BenchmarkConfig):
        """Initialize the benchmark.

        Args:
            config: Benchmark configuration
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        # Tools for data generation
        self.file_generator = FileMetadataGeneratorTool()
        self.activity_generator = ActivityGeneratorTool()

        # Storage for generated data and results
        self.storage_objects = []
        self.activities = []
        self.queries = []
        self.results = {
            "config": {
                "dataset_size": config.dataset_size,
                "query_count": config.query_count,
                "attribute_domains": config.attribute_domains
            },
            "metrics": {
                "generation_time": 0,
                "query_time": 0,
            },
            "attribute_stats": {},
            "query_results": []
        }

    def generate_test_data(self) -> None:
        """Generate test data for benchmarking."""
        self.logger.info(f"Generating {self.config.dataset_size} test records...")
        start_time = time.time()

        # Generate storage objects first
        storage_result = self.file_generator.execute({
            "count": self.config.dataset_size,
            "criteria": {}
        })
        self.storage_objects = storage_result["records"]

        # Generate activities for a subset of storage objects
        activity_objects = random.sample(
            self.storage_objects,
            min(len(self.storage_objects), int(self.config.dataset_size * 0.8))
        )

        activity_result = self.activity_generator.execute({
            "count": self.config.dataset_size // 2,
            "criteria": {
                "storage_objects": activity_objects
            }
        })
        self.activities = activity_result["records"]

        generation_time = time.time() - start_time
        self.results["metrics"]["generation_time"] = generation_time

        self.logger.info(f"Generated {len(self.storage_objects)} storage objects and "
                         f"{len(self.activities)} activity records in {generation_time:.2f} seconds")

        # Analyze attribute usage
        self._analyze_attribute_usage()

    def _analyze_attribute_usage(self) -> None:
        """Analyze semantic attribute usage across the dataset."""
        attribute_counts = {}

        # Analyze storage objects
        for obj in self.storage_objects:
            if "SemanticAttributes" in obj:
                for attr in obj["SemanticAttributes"]:
                    identifier = attr.get("Identifier")
                    if identifier:
                        attribute_counts[identifier] = attribute_counts.get(identifier, 0) + 1

        # Analyze activities
        for activity in self.activities:
            if "SemanticAttributes" in activity:
                for attr in activity["SemanticAttributes"]:
                    identifier = attr.get("Identifier")
                    if identifier:
                        attribute_counts[identifier] = attribute_counts.get(identifier, 0) + 1

        # Get top attributes by frequency
        top_attributes = sorted(
            [(k, v) for k, v in attribute_counts.items()],
            key=lambda x: x[1],
            reverse=True
        )[:20]

        self.results["attribute_stats"] = {
            "unique_attributes": len(attribute_counts),
            "total_attributes": sum(attribute_counts.values()),
            "top_attributes": [
                {"id": attr_id, "count": count, "name": SemanticAttributeRegistry.get_attribute_name(attr_id)}
                for attr_id, count in top_attributes
            ]
        }

    def generate_test_queries(self) -> None:
        """Generate test queries for benchmarking."""
        self.logger.info(f"Generating {self.config.query_count} test queries...")

        self.queries = []

        # Get the most common attributes to query
        if not self.results["attribute_stats"].get("top_attributes"):
            self._analyze_attribute_usage()

        top_attributes = self.results["attribute_stats"].get("top_attributes", [])
        if not top_attributes:
            self.logger.warning("No attributes found for query generation")
            return

        # Generate queries based on attribute combinations
        for i in range(self.config.query_count):
            # Select 1-3 attributes to combine
            query_attr_count = random.randint(1, min(3, len(top_attributes)))
            selected_attrs = random.sample(top_attributes, query_attr_count)

            query_criteria = {}
            expected_matches = set()

            # Build query and track expected matches
            for attr_info in selected_attrs:
                attr_id = attr_info["id"]
                attr_name = attr_info["name"]

                # Get actual values from dataset
                attr_values = []

                # Look in storage objects
                for idx, obj in enumerate(self.storage_objects):
                    if "SemanticAttributes" in obj:
                        for attr in obj.get("SemanticAttributes", []):
                            if attr.get("Identifier") == attr_id:
                                attr_values.append(attr.get("Value"))
                                # This object matches one of our criteria
                                expected_matches.add(f"storage_{idx}")

                # Look in activities
                for idx, activity in enumerate(self.activities):
                    if "SemanticAttributes" in activity:
                        for attr in activity.get("SemanticAttributes", []):
                            if attr.get("Identifier") == attr_id:
                                attr_values.append(attr.get("Value"))
                                # This activity matches one of our criteria
                                expected_matches.add(f"activity_{idx}")

                # Select a random value if available
                if attr_values:
                    query_criteria[attr_name] = random.choice(attr_values)

            # Create query object
            query = {
                "criteria": query_criteria,
                "expected_match_count": len(expected_matches),
                "description": f"Query {i+1}: {', '.join(attr_info['name'] for attr_info in selected_attrs)}"
            }

            self.queries.append(query)
            self.logger.debug(f"Generated query: {query['description']} with {query['expected_match_count']} expected matches")

        self.logger.info(f"Generated {len(self.queries)} test queries")

    def run_queries(self) -> None:
        """Run test queries and analyze results."""
        if not self.queries:
            self.generate_test_queries()

        self.logger.info(f"Running {len(self.queries)} queries...")
        start_time = time.time()

        query_results = []

        for i, query in enumerate(self.queries):
            self.logger.debug(f"Running query {i+1}: {query['description']}")

            # Simulate query execution
            matches_found = self._execute_simulated_query(query["criteria"])
            expected_matches = query["expected_match_count"]

            # Calculate precision and recall
            precision = len(matches_found) / max(1, len(matches_found))
            recall = len(matches_found) / max(1, expected_matches)
            f1 = 2 * (precision * recall) / max(0.0001, precision + recall)

            query_result = {
                "query_id": i + 1,
                "description": query["description"],
                "criteria": query["criteria"],
                "expected_matches": expected_matches,
                "actual_matches": len(matches_found),
                "precision": precision,
                "recall": recall,
                "f1_score": f1
            }

            query_results.append(query_result)
            self.logger.debug(f"Query {i+1} results: Precision={precision:.2f}, Recall={recall:.2f}, F1={f1:.2f}")

        query_time = time.time() - start_time
        self.results["metrics"]["query_time"] = query_time
        self.results["query_results"] = query_results

        # Calculate aggregate metrics
        avg_precision = sum(r["precision"] for r in query_results) / max(1, len(query_results))
        avg_recall = sum(r["recall"] for r in query_results) / max(1, len(query_results))
        avg_f1 = sum(r["f1_score"] for r in query_results) / max(1, len(query_results))

        self.results["metrics"].update({
            "avg_precision": avg_precision,
            "avg_recall": avg_recall,
            "avg_f1": avg_f1
        })

        self.logger.info(f"Ran {len(query_results)} queries in {query_time:.2f} seconds")
        self.logger.info(f"Average metrics: Precision={avg_precision:.2f}, Recall={avg_recall:.2f}, F1={avg_f1:.2f}")

    def _execute_simulated_query(self, criteria: Dict[str, Any]) -> List[str]:
        """Simulate query execution against the dataset.

        This is a simple simulation that checks if objects match all criteria.
        In a real system, this would use AQL or another query language.

        Args:
            criteria: Query criteria with attribute names and values

        Returns:
            List of matching object IDs
        """
        matches = []

        # Convert attribute names back to IDs for matching
        criteria_ids = {}
        for attr_name, attr_value in criteria.items():
            # Find matching attribute ID
            for domain in self.config.attribute_domains:
                attr_id = None
                for registered_attr in SemanticAttributeRegistry.get_all_attributes().get(domain, {}):
                    if registered_attr.endswith(attr_name.split("_")[-1]):
                        attr_id = SemanticAttributeRegistry.get_attribute_id(domain, attr_name.split("_")[-1])
                        break

                if attr_id:
                    criteria_ids[attr_id] = attr_value
                    break

        # Check storage objects
        for idx, obj in enumerate(self.storage_objects):
            if "SemanticAttributes" in obj:
                match = True
                found_criteria = set()

                for attr in obj.get("SemanticAttributes", []):
                    attr_id = attr.get("Identifier")
                    attr_value = attr.get("Value")

                    if attr_id in criteria_ids and attr_value == criteria_ids[attr_id]:
                        found_criteria.add(attr_id)

                # Object must match all criteria
                if found_criteria == set(criteria_ids.keys()):
                    matches.append(f"storage_{idx}")

        # Check activities
        for idx, activity in enumerate(self.activities):
            if "SemanticAttributes" in activity:
                match = True
                found_criteria = set()

                for attr in activity.get("SemanticAttributes", []):
                    attr_id = attr.get("Identifier")
                    attr_value = attr.get("Value")

                    if attr_id in criteria_ids and attr_value == criteria_ids[attr_id]:
                        found_criteria.add(attr_id)

                # Activity must match all criteria
                if found_criteria == set(criteria_ids.keys()):
                    matches.append(f"activity_{idx}")

        return matches

    def save_results(self) -> None:
        """Save benchmark results to file."""
        output_path = self.config.output_path
        self.logger.info(f"Saving results to {output_path}")

        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2, cls=CustomJSONEncoder)

        self.logger.info(f"Results saved to {output_path}")

    def run(self) -> Dict[str, Any]:
        """Run the complete benchmark."""
        self.logger.info("Starting semantic attribute benchmark...")

        self.generate_test_data()
        self.generate_test_queries()
        self.run_queries()
        self.save_results()

        self.logger.info("Benchmark completed successfully")

        return self.results


def setup_logging(level=logging.INFO):
    """Set up logging configuration."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Semantic attribute benchmark suite')

    parser.add_argument('--dataset-size', type=int, default=1000,
                        help='Number of records to generate (default: 1000)')
    parser.add_argument('--query-count', type=int, default=5,
                        help='Number of queries to test (default: 5)')
    parser.add_argument('--output', type=str, default=None,
                        help='Path to save results (default: benchmark_results_TIMESTAMP.json)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Setup logging
    setup_logging(level=logging.DEBUG if args.debug else logging.INFO)

    # Create and run benchmark
    config = BenchmarkConfig(
        dataset_size=args.dataset_size,
        query_count=args.query_count,
        output_path=args.output
    )

    benchmark = SemanticAttributeBenchmark(config)
    results = benchmark.run()

    # Display summary
    print("\nBenchmark Summary:")
    print(f"- Dataset Size: {config.dataset_size}")
    print(f"- Generation Time: {results['metrics']['generation_time']:.2f} seconds")
    print(f"- Query Count: {config.query_count}")
    print(f"- Query Time: {results['metrics']['query_time']:.2f} seconds")
    print(f"- Average Precision: {results['metrics']['avg_precision']:.4f}")
    print(f"- Average Recall: {results['metrics']['avg_recall']:.4f}")
    print(f"- Average F1 Score: {results['metrics']['avg_f1']:.4f}")
    print(f"\nResults saved to: {config.output_path}")


if __name__ == "__main__":
    main()
