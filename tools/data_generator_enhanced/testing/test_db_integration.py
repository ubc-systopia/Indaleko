"""
Database integration test for semantic attributes in the data generator.

This script tests the complete roundtrip flow:
1. Generate test data with semantic attributes
2. Upload the data to ArangoDB
3. Execute real AQL queries against the uploaded data
4. Verify query results match expected outputs
"""

import os
import sys
import uuid
import json
import logging
import argparse
import datetime
import time
from typing import Dict, List, Any, Tuple

# Setup path for imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Check if MCP Arango tools are available
HAS_MCP_ARANGO = False
try:
    from mcp__arango_mcp__arango_query import mcp__arango_mcp__arango_query as arango_query
    from mcp__arango_mcp__arango_insert import mcp__arango_mcp__arango_insert as arango_insert
    from mcp__arango_mcp__arango_list_collections import mcp__arango_mcp__arango_list_collections as list_collections
    HAS_MCP_ARANGO = True
except ImportError:
    pass

# Import Indaleko database modules
from db.db_config import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections

# Import data generator components
from tools.data_generator_enhanced.agents.data_gen.core.semantic_attributes import SemanticAttributeRegistry
from tools.data_generator_enhanced.agents.data_gen.tools.stats import ActivityGeneratorTool, FileMetadataGeneratorTool

# Custom JSON encoder for complex types
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj)


def convert_to_json_serializable(obj):
    """Convert an object with UUIDs and datetimes to JSON serializable format.

    Args:
        obj: Object to convert

    Returns:
        JSON serializable object
    """
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            result[k] = convert_to_json_serializable(v)
        return result
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    elif isinstance(obj, datetime.datetime):
        return obj.isoformat()
    else:
        return obj


class DBIntegrationTest:
    """Test database integration with semantic attributes."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the integration test.

        Args:
            config: Test configuration
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize test data
        self.storage_objects = []
        self.activities = []
        self.db_config = None
        self.db = None

        # Tools for data generation
        self.file_generator = FileMetadataGeneratorTool()
        self.activity_generator = ActivityGeneratorTool()

        # Test results
        self.results = {
            "config": config,
            "metrics": {
                "generation_time": 0,
                "upload_time": 0,
                "query_time": 0
            },
            "attribute_stats": {},
            "query_results": []
        }

    def setup_db_connection(self) -> bool:
        """Set up the database connection.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Setting up database connection...")

            # Initialize database config
            self.db_config = IndalekoDBConfig(start=True)
            self.db = self.db_config.get_arangodb()

            # Verify connection
            self.logger.info(f"Connected to ArangoDB: {self.db.properties()}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            return False

    def generate_test_data(self) -> bool:
        """Generate test data with semantic attributes.

        Returns:
            True if successful, False otherwise
        """
        try:
            dataset_size = self.config.get("dataset_size", 100)
            self.logger.info(f"Generating {dataset_size} test records...")
            start_time = time.time()

            # Generate storage objects
            storage_result = self.file_generator.execute({
                "count": dataset_size,
                "criteria": {}
            })
            self.storage_objects = storage_result["records"]

            # Generate activities for a subset of storage objects
            activity_objects = self.storage_objects[:min(len(self.storage_objects),
                                                       int(dataset_size * 0.8))]

            activity_result = self.activity_generator.execute({
                "count": dataset_size // 2,
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
            return True

        except Exception as e:
            self.logger.error(f"Failed to generate test data: {e}")
            return False

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

    def upload_to_database(self) -> bool:
        """Upload test data to the database.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Uploading test data to database...")
            start_time = time.time()

            # Get collections
            self.logger.info("Preparing collections...")

            # Get the Object collection for storage objects
            object_collection_name = IndalekoDBCollections.Indaleko_Object_Collection
            object_collection = self.db_config.get_collection(object_collection_name)
            self.logger.info(f"Using collection: {object_collection_name}")

            # Get the Activity collection for activity records
            # Using the MusicActivityData collection since we don't have a general Activities collection
            activity_collection_name = IndalekoDBCollections.Indaleko_MusicActivityData_Collection
            activity_collection = self.db_config.get_collection(activity_collection_name)
            self.logger.info(f"Using collection: {activity_collection_name}")

            # Upload storage objects
            self.logger.info(f"Uploading {len(self.storage_objects)} storage objects...")
            object_batch_size = 100

            # Process objects to make sure they're JSON serializable
            serializable_objects = []
            for obj in self.storage_objects:
                serializable_objects.append(convert_to_json_serializable(obj))

            # Upload in batches
            for i in range(0, len(serializable_objects), object_batch_size):
                batch = serializable_objects[i:i+object_batch_size]
                object_collection.import_bulk(batch)

            # Upload activity records
            self.logger.info(f"Uploading {len(self.activities)} activity records...")
            activity_batch_size = 100

            # Process activities to make sure they're JSON serializable
            serializable_activities = []
            for activity in self.activities:
                serializable_activities.append(convert_to_json_serializable(activity))

            # Upload in batches
            for i in range(0, len(serializable_activities), activity_batch_size):
                batch = serializable_activities[i:i+activity_batch_size]
                activity_collection.import_bulk(batch)

            upload_time = time.time() - start_time
            self.results["metrics"]["upload_time"] = upload_time

            self.logger.info(f"Upload completed in {upload_time:.2f} seconds")
            return True

        except Exception as e:
            self.logger.error(f"Failed to upload data to database: {e}")
            return False

    def run_queries(self) -> bool:
        """Execute test queries against uploaded data.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Running test queries...")
            start_time = time.time()

            # Get top semantic attributes
            top_attributes = self.results["attribute_stats"].get("top_attributes", [])
            if not top_attributes:
                self.logger.warning("No attributes found for query testing")
                return False

            # Generate and run test queries
            query_results = []

            # 1. Basic query by semantic attribute
            self.logger.info("Running basic semantic attribute query...")
            top_attr = top_attributes[0]

            # Get the semantic attribute value from an object
            attr_id = top_attr["id"]
            attr_name = top_attr["name"]

            # Find an object with this attribute
            test_obj = None
            test_value = None

            for obj in self.storage_objects:
                if "SemanticAttributes" in obj:
                    for attr in obj["SemanticAttributes"]:
                        if attr.get("Identifier") == attr_id:
                            test_obj = obj
                            test_value = attr.get("Value")
                            break
                    if test_obj:
                        break

            if not test_obj or not test_value:
                self.logger.warning(f"Couldn't find test object with attribute {attr_name}")
                return False

            # Execute AQL query to find objects with this attribute
            aql_query = f"""
            FOR doc IN {IndalekoDBCollections.Indaleko_Object_Collection}
                FOR attr IN doc.SemanticAttributes
                    FILTER attr.Identifier == @attr_id AND attr.Value == @attr_value
                    RETURN doc
            """

            cursor = self.db.aql.execute(
                aql_query,
                bind_vars={"attr_id": attr_id, "attr_value": test_value}
            )
            results = list(cursor)

            query_results.append({
                "query_id": 1,
                "description": f"Basic semantic attribute query for {attr_name}",
                "criteria": {"attr_id": attr_id, "value": test_value},
                "expected_matches": 1,  # We know at least one should match
                "actual_matches": len(results),
                "success": len(results) >= 1
            })

            # 2. Cross-collection query (finding activities related to objects)
            self.logger.info("Running cross-collection query...")

            # Find an activity object ID
            test_activity = None
            test_obj_id = None

            for activity in self.activities:
                if "SemanticAttributes" in activity:
                    for attr in activity["SemanticAttributes"]:
                        if attr.get("Identifier") == SemanticAttributeRegistry.get_attribute_id(
                            SemanticAttributeRegistry.DOMAIN_ACTIVITY, "OBJECT_ID"
                        ):
                            test_activity = activity
                            test_obj_id = attr.get("Value")
                            break
                    if test_activity:
                        break

            if not test_activity or not test_obj_id:
                self.logger.warning("Couldn't find test activity with object ID")
            else:
                # Execute AQL query to find activities related to objects
                aql_query = f"""
                FOR activity IN {IndalekoDBCollections.Indaleko_MusicActivityData_Collection}
                    FOR attr IN activity.SemanticAttributes
                        FILTER attr.Identifier == @obj_id_attr AND attr.Value == @obj_id
                        RETURN activity
                """

                cursor = self.db.aql.execute(
                    aql_query,
                    bind_vars={
                        "obj_id_attr": SemanticAttributeRegistry.get_attribute_id(
                            SemanticAttributeRegistry.DOMAIN_ACTIVITY, "OBJECT_ID"
                        ),
                        "obj_id": test_obj_id
                    }
                )
                results = list(cursor)

                query_results.append({
                    "query_id": 2,
                    "description": "Cross-collection query for activities related to objects",
                    "criteria": {"object_id": test_obj_id},
                    "expected_matches": 1,  # We know at least one should match
                    "actual_matches": len(results),
                    "success": len(results) >= 1
                })

            # 3. Complex query with multiple attributes
            self.logger.info("Running complex query with multiple attributes...")

            # Find attributes for platform and application
            platform_attr_id = SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ACTIVITY, "DATA_PLATFORM"
            )
            application_attr_id = SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ACTIVITY, "DATA_APPLICATION"
            )

            # Find a test activity with both
            test_activity = None
            test_platform = None
            test_application = None

            for activity in self.activities:
                if "SemanticAttributes" in activity:
                    has_platform = False
                    has_application = False

                    for attr in activity["SemanticAttributes"]:
                        if attr.get("Identifier") == platform_attr_id:
                            test_platform = attr.get("Value")
                            has_platform = True
                        elif attr.get("Identifier") == application_attr_id:
                            test_application = attr.get("Value")
                            has_application = True

                    if has_platform and has_application:
                        test_activity = activity
                        break

            if not test_activity or not test_platform or not test_application:
                self.logger.warning("Couldn't find test activity with platform and application")
            else:
                # Execute AQL query with multiple criteria
                aql_query = f"""
                FOR activity IN {IndalekoDBCollections.Indaleko_MusicActivityData_Collection}
                    LET platform_attr = (
                        FOR attr IN activity.SemanticAttributes
                            FILTER attr.Identifier == @platform_attr_id
                            RETURN attr.Value
                    )
                    LET app_attr = (
                        FOR attr IN activity.SemanticAttributes
                            FILTER attr.Identifier == @app_attr_id
                            RETURN attr.Value
                    )
                    FILTER platform_attr[0] == @platform AND app_attr[0] == @application
                    RETURN activity
                """

                cursor = self.db.aql.execute(
                    aql_query,
                    bind_vars={
                        "platform_attr_id": platform_attr_id,
                        "app_attr_id": application_attr_id,
                        "platform": test_platform,
                        "application": test_application
                    }
                )
                results = list(cursor)

                query_results.append({
                    "query_id": 3,
                    "description": "Complex query with multiple attributes",
                    "criteria": {
                        "platform": test_platform,
                        "application": test_application
                    },
                    "expected_matches": 1,  # We know at least one should match
                    "actual_matches": len(results),
                    "success": len(results) >= 1
                })

            query_time = time.time() - start_time
            self.results["metrics"]["query_time"] = query_time
            self.results["query_results"] = query_results

            # Calculate success rate
            success_count = sum(1 for r in query_results if r.get("success", False))
            success_rate = success_count / max(1, len(query_results))

            self.results["metrics"]["query_success_rate"] = success_rate

            self.logger.info(f"Queries completed in {query_time:.2f} seconds")
            self.logger.info(f"Query success rate: {success_rate:.2f}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to run queries: {e}")
            return False

    def cleanup_database(self) -> bool:
        """Clean up test data from the database.

        Returns:
            True if successful, False otherwise
        """
        if self.config.get("skip_cleanup", False):
            self.logger.info("Skipping database cleanup")
            return True

        try:
            self.logger.info("Cleaning up test data...")

            # Truncate collections instead of deleting them
            object_collection_name = IndalekoDBCollections.Indaleko_Object_Collection
            if self.db.has_collection(object_collection_name):
                self.logger.info(f"Truncating collection: {object_collection_name}")
                self.db.collection(object_collection_name).truncate()

            activity_collection_name = IndalekoDBCollections.Indaleko_MusicActivityData_Collection
            if self.db.has_collection(activity_collection_name):
                self.logger.info(f"Truncating collection: {activity_collection_name}")
                self.db.collection(activity_collection_name).truncate()

            self.logger.info("Database cleanup completed")
            return True

        except Exception as e:
            self.logger.error(f"Failed to clean up database: {e}")
            return False

    def save_results(self) -> bool:
        """Save test results to file.

        Returns:
            True if successful, False otherwise
        """
        try:
            output_path = self.config.get("output_path", "db_integration_test_results.json")
            self.logger.info(f"Saving results to {output_path}")

            # Create directory if needed
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

            # Convert results to JSON serializable format
            serializable_results = convert_to_json_serializable(self.results)

            with open(output_path, 'w') as f:
                json.dump(serializable_results, f, indent=2)

            self.logger.info(f"Results saved to {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")
            return False

    def run(self) -> Dict[str, Any]:
        """Run the complete database integration test.

        Returns:
            Test results dictionary
        """
        self.logger.info("Starting database integration test...")

        success = (
            self.setup_db_connection() and
            self.generate_test_data() and
            self.upload_to_database() and
            self.run_queries()
        )

        # Always try to clean up, even if previous steps failed
        cleanup_success = self.cleanup_database()

        # Save results
        self.save_results()

        if success and cleanup_success:
            self.logger.info("Database integration test completed successfully")
        else:
            self.logger.warning("Database integration test failed")

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
    parser = argparse.ArgumentParser(description='Database integration test for semantic attributes')

    parser.add_argument('--dataset-size', type=int, default=100,
                        help='Number of records to generate (default: 100)')
    parser.add_argument('--output', type=str, default="db_integration_test_results.json",
                        help='Path to save results (default: db_integration_test_results.json)')
    parser.add_argument('--skip-cleanup', action='store_true',
                        help='Skip database cleanup after test')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Setup logging
    setup_logging(level=logging.DEBUG if args.debug else logging.INFO)

    # Build test configuration
    config = {
        "dataset_size": args.dataset_size,
        "output_path": args.output,
        "skip_cleanup": args.skip_cleanup
    }

    # Create and run the test
    test = DBIntegrationTest(config)
    results = test.run()

    # Display summary
    print("\nDatabase Integration Test Summary:")
    print(f"- Dataset Size: {config['dataset_size']}")
    print(f"- Generation Time: {results['metrics']['generation_time']:.2f} seconds")
    print(f"- Upload Time: {results['metrics']['upload_time']:.2f} seconds")
    print(f"- Query Time: {results['metrics']['query_time']:.2f} seconds")

    if "query_success_rate" in results["metrics"]:
        print(f"- Query Success Rate: {results['metrics']['query_success_rate']:.2f}")

    print(f"\nResults saved to: {config['output_path']}")

    # Return success status
    return results.get("metrics", {}).get("query_success_rate", 0) == 1.0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
