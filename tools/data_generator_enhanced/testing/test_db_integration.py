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
import random
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

            # No need to add semantic attributes anymore; FileMetadataGeneratorTool now adds them
            # self._add_semantic_attributes_to_objects()
            # Just log the semantic attribute count for debugging
            self._analyze_attribute_presence()

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

            # Add semantic attributes to activities as well
            self._add_semantic_attributes_to_activities()

            generation_time = time.time() - start_time
            self.results["metrics"]["generation_time"] = generation_time

            self.logger.info(f"Generated {len(self.storage_objects)} storage objects and "
                           f"{len(self.activities)} activity records in {generation_time:.2f} seconds")
            
            # Log semantic attribute count for debugging
            total_storage_attrs = sum(len(obj.get("SemanticAttributes", [])) for obj in self.storage_objects)
            total_activity_attrs = sum(len(act.get("SemanticAttributes", [])) for act in self.activities)
            self.logger.info(f"Added {total_storage_attrs} semantic attributes to storage objects")
            self.logger.info(f"Added {total_activity_attrs} semantic attributes to activities")

            # Analyze attribute usage
            self._analyze_attribute_usage()
            return True

        except Exception as e:
            self.logger.error(f"Failed to generate test data: {e}")
            return False
            
    def _analyze_attribute_presence(self) -> None:
        """Analyze the presence of semantic attributes in the generated data."""
        # Count objects with semantic attributes
        objects_with_attrs = 0
        total_storage_attrs = 0
        
        for obj in self.storage_objects:
            if "SemanticAttributes" in obj and obj["SemanticAttributes"]:
                objects_with_attrs += 1
                total_storage_attrs += len(obj["SemanticAttributes"])
                
        self.logger.info(f"{objects_with_attrs}/{len(self.storage_objects)} objects have semantic attributes")
        if objects_with_attrs > 0:
            self.logger.info(f"Average {total_storage_attrs / objects_with_attrs:.1f} attributes per object")
            
            # Print first 3 attributes of first object with attributes for debugging
            for obj in self.storage_objects:
                if "SemanticAttributes" in obj and obj["SemanticAttributes"]:
                    sample = obj["SemanticAttributes"][:3]
                    self.logger.info(f"Sample attributes: {sample}")
                    break
            
    def _add_semantic_attributes_to_objects(self) -> None:
        """Add semantic attributes to storage objects.
        
        This fixes the issue where FileMetadataGeneratorTool doesn't add semantic attributes.
        """
        from tools.data_generator_enhanced.agents.data_gen.core.semantic_attributes import SemanticAttributeRegistry
        
        self.logger.info("Adding semantic attributes to storage objects...")
        
        # Add semantic attributes to each storage object
        for obj in self.storage_objects:
            # Make sure SemanticAttributes exists and is a list
            if "SemanticAttributes" not in obj or not isinstance(obj["SemanticAttributes"], list):
                obj["SemanticAttributes"] = []
                
            # Add file name attribute
            if "Label" in obj:
                file_name_attr = {
                    "Identifier": SemanticAttributeRegistry.get_attribute_id(
                        SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_NAME"),
                    "Value": obj["Label"]
                }
                obj["SemanticAttributes"].append(file_name_attr)
                
            # Add file path attribute
            if "LocalPath" in obj:
                file_path_attr = {
                    "Identifier": SemanticAttributeRegistry.get_attribute_id(
                        SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_PATH"),
                    "Value": obj["LocalPath"]
                }
                obj["SemanticAttributes"].append(file_path_attr)
                
            # Add file size attribute
            if "Size" in obj:
                file_size_attr = {
                    "Identifier": SemanticAttributeRegistry.get_attribute_id(
                        SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_SIZE"),
                    "Value": obj["Size"]
                }
                obj["SemanticAttributes"].append(file_size_attr)
                
            # Add file extension attribute if available
            if "Label" in obj and "." in obj["Label"]:
                extension = obj["Label"].split(".")[-1]
                file_ext_attr = {
                    "Identifier": SemanticAttributeRegistry.get_attribute_id(
                        SemanticAttributeRegistry.DOMAIN_STORAGE, "FILE_EXTENSION"),
                    "Value": extension
                }
                obj["SemanticAttributes"].append(file_ext_attr)
                
            # Add MIME type as a semantic attribute
            mime_types = {
                "txt": "text/plain",
                "pdf": "application/pdf",
                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                "jpg": "image/jpeg",
                "png": "image/png",
                "mp4": "video/mp4",
                "mp3": "audio/mpeg",
                "zip": "application/zip",
                "html": "text/html",
                "css": "text/css",
                "js": "application/javascript",
                "json": "application/json",
                "xml": "application/xml",
                "md": "text/markdown",
                "csv": "text/csv"
            }
            
            if "Label" in obj and "." in obj["Label"]:
                extension = obj["Label"].split(".")[-1].lower()
                if extension in mime_types:
                    mime_attr = {
                        "Identifier": SemanticAttributeRegistry.get_attribute_id(
                            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "MIME_TYPE"),
                        "Value": mime_types[extension]
                    }
                    obj["SemanticAttributes"].append(mime_attr)
            
    def _add_semantic_attributes_to_activities(self) -> None:
        """Add semantic attributes to activity records."""
        from tools.data_generator_enhanced.agents.data_gen.core.semantic_attributes import SemanticAttributeRegistry
        
        self.logger.info("Adding semantic attributes to activity records...")
        
        # Common applications for different activities
        applications = ["Microsoft Word", "Adobe Reader", "Microsoft Excel", 
                       "Google Chrome", "Firefox", "Visual Studio Code", 
                       "Outlook", "Spotify", "VLC Media Player"]
        
        # Common platforms
        platforms = ["Windows", "macOS", "Linux", "iOS", "Android"]
        
        # Ensure the first activity has the specific attributes we'll look for in the complex query
        if len(self.activities) > 0:
            first_activity = self.activities[0]
            
            # Make sure SemanticAttributes exists and is a list
            if "SemanticAttributes" not in first_activity or not isinstance(first_activity["SemanticAttributes"], list):
                first_activity["SemanticAttributes"] = []
                
            # Add specific application attribute for test query
            app_attr = {
                "Identifier": SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY, "DATA_APPLICATION"),
                "Value": "Microsoft Word"
            }
            first_activity["SemanticAttributes"].append(app_attr)
            
            # Add specific platform attribute for test query
            platform_attr = {
                "Identifier": SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY, "DATA_PLATFORM"),
                "Value": "Windows"
            }
            first_activity["SemanticAttributes"].append(platform_attr)
            
            # Add activity type attribute
            type_attr = {
                "Identifier": SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY, "ACTIVITY_TYPE"),
                "Value": "CREATE"
            }
            first_activity["SemanticAttributes"].append(type_attr)
            
            # Add remaining activities with random attributes
            for i, activity in enumerate(self.activities):
                if i == 0:  # Skip the first one since we already processed it
                    continue
                    
                # Make sure SemanticAttributes exists and is a list
                if "SemanticAttributes" not in activity or not isinstance(activity["SemanticAttributes"], list):
                    activity["SemanticAttributes"] = []
                    
                # Add application attribute
                app_attr = {
                    "Identifier": SemanticAttributeRegistry.get_attribute_id(
                        SemanticAttributeRegistry.DOMAIN_ACTIVITY, "DATA_APPLICATION"),
                    "Value": random.choice(applications)
                }
                activity["SemanticAttributes"].append(app_attr)
                
                # Add platform attribute
                platform_attr = {
                    "Identifier": SemanticAttributeRegistry.get_attribute_id(
                        SemanticAttributeRegistry.DOMAIN_ACTIVITY, "DATA_PLATFORM"),
                    "Value": random.choice(platforms)
                }
                activity["SemanticAttributes"].append(platform_attr)
                
                # Add activity type attribute
                activity_types = ["CREATE", "READ", "MODIFY", "DELETE", "SHARE"]
                type_attr = {
                    "Identifier": SemanticAttributeRegistry.get_attribute_id(
                        SemanticAttributeRegistry.DOMAIN_ACTIVITY, "ACTIVITY_TYPE"),
                    "Value": random.choice(activity_types)
                }
                activity["SemanticAttributes"].append(type_attr)
        else:
            self.logger.warning("No activities to add semantic attributes to")

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

            # Generate and run test queries
            query_results = []

            # 1. Find any object with semantic attributes
            self.logger.info("Running basic semantic attribute query...")

            # Just find any object with semantic attributes
            test_obj = None
            test_attr = None
            test_value = None

            # First try to find the first object with semantic attributes
            for obj in self.storage_objects:
                if "SemanticAttributes" in obj and obj["SemanticAttributes"]:
                    test_obj = obj
                    test_attr = obj["SemanticAttributes"][0]
                    test_value = test_attr.get("Value")
                    if test_value is not None:
                        break

            if not test_obj or not test_attr or test_value is None:
                self.logger.warning("Couldn't find any object with semantic attributes")
                return False

            # Get attribute details for logging and query
            attr_id = test_attr.get("Identifier")
            attr_name = "BasicAttribute"  # We don't know the name at this point

            self.logger.info(f"Testing with attribute ID: {attr_id}, value: {test_value}")

# These lines are redundant with our new approach and can be removed

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

            # 2. Cross-collection query (finding activities with any semantic attributes)
            self.logger.info("Running cross-collection query...")

            # Find any activity with semantic attributes
            test_activity = None
            test_activity_attr = None
            test_activity_value = None

            for activity in self.activities:
                if "SemanticAttributes" in activity and activity["SemanticAttributes"]:
                    test_activity = activity
                    test_activity_attr = activity["SemanticAttributes"][0]
                    test_activity_value = test_activity_attr.get("Value")
                    if test_activity_value is not None:
                        break

            if not test_activity or not test_activity_attr or test_activity_value is None:
                self.logger.warning("Couldn't find any activity with semantic attributes")
            else:
                # Get attribute details for logging and query
                activity_attr_id = test_activity_attr.get("Identifier")
                self.logger.info(f"Testing with activity attribute ID: {activity_attr_id}, value: {test_activity_value}")

                # Execute AQL query to find activities with this attribute
                aql_query = f"""
                FOR activity IN {IndalekoDBCollections.Indaleko_MusicActivityData_Collection}
                    FOR attr IN activity.SemanticAttributes
                        FILTER attr.Identifier == @attr_id AND attr.Value == @attr_value
                        RETURN activity
                """

                cursor = self.db.aql.execute(
                    aql_query,
                    bind_vars={
                        "attr_id": activity_attr_id,
                        "attr_value": test_activity_value
                    }
                )
                results = list(cursor)

                query_results.append({
                    "query_id": 2,
                    "description": "Activity collection query for semantic attributes",
                    "criteria": {"attr_id": activity_attr_id, "value": test_activity_value},
                    "expected_matches": 1,  # We know at least one should match
                    "actual_matches": len(results),
                    "success": len(results) >= 1
                })

            # 3. Run complex query with fixed values that we set in _add_semantic_attributes_to_activities
            self.logger.info("Running complex query with multiple attributes...")

            # Find attributes for platform and application
            platform_attr_id = SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ACTIVITY, "DATA_PLATFORM"
            )
            application_attr_id = SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ACTIVITY, "DATA_APPLICATION"
            )

            # We know the first activity has been set with specific values in _add_semantic_attributes_to_activities
            if len(self.activities) > 0:
                # Fixed values from _add_semantic_attributes_to_activities
                test_platform = "Windows"
                test_application = "Microsoft Word"
                
                self.logger.info(f"Testing with platform: {test_platform}, application: {test_application}")
                
                # Verify they're set correctly (for debugging)
                if len(self.activities) > 0 and "SemanticAttributes" in self.activities[0]:
                    for attr in self.activities[0]["SemanticAttributes"]:
                        if attr.get("Identifier") == platform_attr_id:
                            self.logger.info(f"Platform value in activity: {attr.get('Value')}")
                        elif attr.get("Identifier") == application_attr_id:
                            self.logger.info(f"Application value in activity: {attr.get('Value')}")
                
                # Execute AQL query with multiple criteria
                # Simplified query that doesn't depend on array access
                aql_query = f"""
                FOR activity IN {IndalekoDBCollections.Indaleko_MusicActivityData_Collection}
                    FILTER (
                        FOR attr IN activity.SemanticAttributes
                            FILTER attr.Identifier == @platform_attr_id AND attr.Value == @platform
                            RETURN 1
                    )[0] == 1
                    AND
                    (
                        FOR attr IN activity.SemanticAttributes
                            FILTER attr.Identifier == @app_attr_id AND attr.Value == @application
                            RETURN 1
                    )[0] == 1
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

                # Show actual results for debugging
                self.logger.info(f"Found {len(results)} matching activities")
                if len(results) == 0:
                    # Fallback query to check if the attributes exist at all
                    self.logger.info("No matches found, running diagnostic query...")
                    diag_query = f"""
                    FOR activity IN {IndalekoDBCollections.Indaleko_MusicActivityData_Collection}
                        LET platform_attrs = (
                            FOR attr IN activity.SemanticAttributes
                                FILTER attr.Identifier == @platform_attr_id
                                RETURN attr.Value
                        )
                        LET app_attrs = (
                            FOR attr IN activity.SemanticAttributes
                                FILTER attr.Identifier == @app_attr_id
                                RETURN attr.Value
                        )
                        RETURN {{ 
                            _key: activity._key,
                            platforms: platform_attrs,
                            applications: app_attrs
                        }}
                    """
                    
                    diag_cursor = self.db.aql.execute(
                        diag_query,
                        bind_vars={
                            "platform_attr_id": platform_attr_id,
                            "app_attr_id": application_attr_id
                        }
                    )
                    diag_results = list(diag_cursor)
                    self.logger.info(f"Diagnostic results: {diag_results}")

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
            else:
                self.logger.warning("No activities available for complex query test")

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
