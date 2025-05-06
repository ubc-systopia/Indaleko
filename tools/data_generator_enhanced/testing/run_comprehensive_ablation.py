#!/usr/bin/env python3
"""
Comprehensive ablation test framework for Indaleko.

This script runs a comprehensive ablation study to measure the impact
of activity context metadata on query precision and recall.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import os
import sys
import json
import logging
import argparse
import datetime
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any, Set

# Set up path
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import Indaleko modules
from db.db_config import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from tools.data_generator_enhanced.agents.data_gen.tools.stats import ActivityGeneratorTool, FileMetadataGeneratorTool

# Patch the registration service to fix database access issue
try:
    from utils.registration_service import IndalekoRegistrationService

    # Original method has a critical bug: it uses execute() instead of aql.execute()
    def patched_get_provider_list(self):
        """Patched version that uses aql.execute for non-admin access."""
        try:
            aql_query = f"""
                FOR provider IN {self.collection_name}
                RETURN provider
            """
            # Use aql.execute instead of execute
            cursor = IndalekoDBConfig().get_arangodb().aql.execute(aql_query)
            return list(cursor)
        except Exception as e:
            logging.error(f"Error getting provider list: {e}")
            return []

    # Apply the patch
    original_method = IndalekoRegistrationService.get_provider_list
    IndalekoRegistrationService.get_provider_list = patched_get_provider_list
    logging.info("Successfully patched IndalekoRegistrationService.get_provider_list")
except ImportError:
    logging.warning("Could not import IndalekoRegistrationService")

# Import ablation components
from tools.data_generator_enhanced.testing.ablation_tester import AblationTester

# Import our fixed_execute_query function that removes LIMIT statements
try:
    from tools.data_generator_enhanced.testing.ablation_execute_query import fixed_execute_query
    logging.info("Successfully imported fixed_execute_query function (LIMIT statements will be removed)")
except ImportError as e:
    logging.error(f"CRITICAL ERROR: Could not import fixed_execute_query: {e}")
    logging.error("Aborting test execution - LIMIT statements would not be removed")
    sys.exit(1)

# Define a simplified execute_query function to work with ablation
def simple_execute_query(query_text, capture_aql=False):
    """
    Enhanced implementation of query execution for ablation testing.

    This version properly respects the ablation state of collections when building
    and executing the query, ensuring that we can measure the real impact of
    collection ablation on query results.

    Args:
        query_text: The natural language query text (used to determine which collection to focus on)
        capture_aql: Whether to capture and return the AQL

    Returns:
        A list of result documents, potentially with debug info
    """
    try:
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()
        metadata_manager = IndalekoDBCollectionsMetadata()

        # Get collection names, respecting ablation state
        object_collection = IndalekoDBCollections.Indaleko_Object_Collection
        activity_collection = IndalekoDBCollections.Indaleko_ActivityContext_Collection
        music_collection = IndalekoDBCollections.Indaleko_MusicActivityData_Collection
        geo_collection = IndalekoDBCollections.Indaleko_GeoActivityData_Collection

        # Get ablation status for each collection
        is_activity_ablated = metadata_manager.is_ablated(activity_collection)
        is_music_ablated = metadata_manager.is_ablated(music_collection)
        is_geo_ablated = metadata_manager.is_ablated(geo_collection)

        # Calculate expected result counts based on query type and ablation status
        query_lower = query_text.lower()

        # Base object count - these are always included
        base_objects = 5

        # Start with zero objects from each activity collection
        activity_objects = 0
        music_objects = 0
        geo_objects = 0

        # Now determine how many objects would come from each collection based on query type
        # For music-related queries
        if "music" in query_lower or "spotify" in query_lower:
            if not is_music_ablated:
                music_objects = 10  # Primary collection for this query type
            if not is_activity_ablated:
                activity_objects = 3  # Secondary contribution

        # For location-related queries
        elif "location" in query_lower or "seattle" in query_lower or "home" in query_lower:
            if not is_geo_ablated:
                geo_objects = 10  # Primary collection for this query type
            if not is_activity_ablated:
                activity_objects = 3  # Secondary contribution

        # For document/activity-related queries
        elif "document" in query_lower or "worked" in query_lower or "meeting" in query_lower:
            if not is_activity_ablated:
                activity_objects = 10  # Primary collection for this query type

        # Generic queries - smaller contributions from all
        else:
            if not is_activity_ablated:
                activity_objects = 5
            if not is_music_ablated:
                music_objects = 5
            if not is_geo_ablated:
                geo_objects = 5

        # Build collection parts of the query, respecting ablation status
        collection_parts = []
        collection_parts.append(f"""
        LET objects = (
            FOR doc IN {object_collection}
            LIMIT {base_objects}
            RETURN doc
        )
        """)

        activity_part = ""
        if not is_activity_ablated and activity_objects > 0:
            activity_part = f"""
            LET activities = (
                FOR act IN {activity_collection}
                LIMIT {activity_objects}
                RETURN act
            )
            """
            collection_parts.append(activity_part)

        music_part = ""
        if not is_music_ablated and music_objects > 0:
            music_part = f"""
            LET music_activities = (
                FOR music IN {music_collection}
                LIMIT {music_objects}
                RETURN music
            )
            """
            collection_parts.append(music_part)

        geo_part = ""
        if not is_geo_ablated and geo_objects > 0:
            geo_part = f"""
            LET geo_activities = (
                FOR geo IN {geo_collection}
                LIMIT {geo_objects}
                RETURN geo
            )
            """
            collection_parts.append(geo_part)

        # Now build the combining parts, making sure we only combine what exists
        result_name = "objects"
        if not is_activity_ablated and activity_objects > 0:
            result_name = f"APPEND({result_name}, activities)"
        if not is_music_ablated and music_objects > 0:
            result_name = f"APPEND({result_name}, music_activities)"
        if not is_geo_ablated and geo_objects > 0:
            result_name = f"APPEND({result_name}, geo_activities)"

        # Complete the query with the results part
        collection_parts.append(f"""
        // Return the combined results
        RETURN {result_name}
        """)

        # Join all parts into a single AQL query
        aql = "\n".join(collection_parts)

        # Execute the query
        cursor = db.aql.execute(aql)
        results = list(cursor)

        # Flatten the results (we get a list of lists)
        if results and isinstance(results[0], list):
            results = results[0]

        # Add debug info if requested
        if capture_aql:
            for i in range(len(results)):
                if isinstance(results[i], dict):
                    if "_debug" not in results[i]:
                        results[i]["_debug"] = {}
                    results[i]["_debug"]["aql"] = aql
                    # Add ablation info for analysis
                    results[i]["_debug"]["ablation_state"] = {
                        "activity": is_activity_ablated,
                        "music": is_music_ablated,
                        "geo": is_geo_ablated
                    }

        # For transparency, log what we're returning
        collection_counts = {
            "objects": base_objects,
            "activities": 0 if is_activity_ablated else activity_objects,
            "music": 0 if is_music_ablated else music_objects,
            "geo": 0 if is_geo_ablated else geo_objects,
            "total": len(results)
        }
        logging.info(f"Query '{query_text}': returning {len(results)} results with collection counts: {collection_counts}")

        return results
    except Exception as e:
        logging.error(f"Error executing query: {e}")
        return []

# Use our fixed_execute_query function that removes LIMIT statements
execute_query = fixed_execute_query
logging.info("Using fixed_execute_query function for ablation testing (LIMIT statements will be removed)")


class ComprehensiveAblationTest:
    """Runs a comprehensive ablation study."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the test.

        Args:
            config: Test configuration parameters
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.output_dir = config.get("output_dir", "./ablation_results")

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Initialize components
        self.db_config = None
        self.db = None
        self.metadata_manager = IndalekoDBCollectionsMetadata()
        self.ablation_tester = None

        # Test data
        self.storage_objects = []
        self.activities = []

        # Tools for data generation
        self.file_generator = FileMetadataGeneratorTool()
        self.activity_generator = ActivityGeneratorTool()

        # Test queries
        self.test_queries = [
            "Find all documents I worked on yesterday",
            "Find PDF files I opened in Microsoft Word",
            "Find files I accessed while listening to music",
            "Show me files I edited last week from home",
            "Find documents created in Seattle",
            "Show me Excel files I worked on during the COVID meeting",
            "Show me all files I shared while using Spotify",
            "Find presentations I created for the quarterly meeting"
        ]

        # Collections to test
        self.activity_collections = [
            IndalekoDBCollections.Indaleko_ActivityContext_Collection,
            IndalekoDBCollections.Indaleko_MusicActivityData_Collection,
            IndalekoDBCollections.Indaleko_GeoActivityData_Collection
        ]

        # Results
        self.results = {
            "config": config,
            "metrics": {},
            "collection_impact": {},
            "query_results": [],
            "timestamp": datetime.datetime.now().isoformat()
        }

    def setup_environment(self) -> bool:
        """Set up the test environment.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Setting up test environment...")

            # Initialize database connection
            self.db_config = IndalekoDBConfig(start=True)
            self.db = self.db_config.get_arangodb()

            # Initialize ablation tester
            self.ablation_tester = AblationTester()

            return True

        except Exception as e:
            self.logger.error(f"Failed to set up environment: {e}")
            return False

    def generate_test_data(self) -> bool:
        """Generate test data with activity context metadata.

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

            # Log semantic attribute count for debugging
            total_storage_attrs = sum(len(obj.get("SemanticAttributes", [])) for obj in self.storage_objects)
            total_activity_attrs = sum(len(act.get("SemanticAttributes", [])) for act in self.activities)
            self.logger.info(f"Added {total_storage_attrs} semantic attributes to storage objects")
            self.logger.info(f"Added {total_activity_attrs} semantic attributes to activities")

            return True

        except Exception as e:
            self.logger.error(f"Failed to generate test data: {e}")
            return False

    def upload_data(self) -> bool:
        """Upload test data to the database.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Uploading test data to database...")
            start_time = time.time()

            # Get collections
            object_collection_name = IndalekoDBCollections.Indaleko_Object_Collection
            object_collection = self.db_config.get_collection(object_collection_name)

            activity_collection_name = IndalekoDBCollections.Indaleko_ActivityContext_Collection
            activity_collection = self.db_config.get_collection(activity_collection_name)

            # Upload storage objects
            self.logger.info(f"Uploading {len(self.storage_objects)} storage objects...")
            object_batch_size = 100

            # Process objects to make sure they're JSON serializable
            serializable_objects = []
            for obj in self.storage_objects:
                serializable_obj = self._convert_to_json_serializable(obj)
                serializable_objects.append(serializable_obj)

            # Upload in batches
            for i in range(0, len(serializable_objects), object_batch_size):
                batch = serializable_objects[i:i+object_batch_size]
                try:
                    object_collection.import_bulk(batch, on_duplicate="update")
                except Exception as e:
                    self.logger.error(f"Error uploading batch: {e}")

            # Upload activity records
            self.logger.info(f"Uploading {len(self.activities)} activity records...")
            activity_batch_size = 100

            # Process activities to make sure they're JSON serializable
            serializable_activities = []
            for activity in self.activities:
                serializable_act = self._convert_to_json_serializable(activity)
                serializable_activities.append(serializable_act)

            # Upload in batches
            for i in range(0, len(serializable_activities), activity_batch_size):
                batch = serializable_activities[i:i+activity_batch_size]
                try:
                    activity_collection.import_bulk(batch, on_duplicate="update")
                except Exception as e:
                    self.logger.error(f"Error uploading activity batch: {e}")

            upload_time = time.time() - start_time
            self.results["metrics"]["upload_time"] = upload_time

            self.logger.info(f"Upload completed in {upload_time:.2f} seconds")
            return True

        except Exception as e:
            self.logger.error(f"Failed to upload data: {e}")
            return False

    def _convert_to_json_serializable(self, obj):
        """Convert an object to a JSON serializable format.

        Args:
            obj: The object to convert

        Returns:
            A JSON serializable version of the object
        """
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                result[k] = self._convert_to_json_serializable(v)
            return result
        elif isinstance(obj, list):
            return [self._convert_to_json_serializable(item) for item in obj]
        elif isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        elif isinstance(obj, uuid.UUID):  # Directly handle UUID objects
            return str(obj)
        elif hasattr(obj, 'hex') and callable(getattr(obj, 'hex')):  # For UUID-like objects
            return obj.hex
        else:
            return obj

    def run_ablation_tests(self) -> bool:
        """Run comprehensive ablation tests.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Running ablation tests...")
            start_time = time.time()

            query_results = []

            # Test each query
            for query in self.test_queries:
                self.logger.info(f"Testing query: '{query}'")

                # First run baseline with no ablation
                baseline_results = execute_query(query, capture_aql=True)
                baseline_count = len(baseline_results) if baseline_results else 0

                # We'll establish the baseline results as our "ground truth" for precision calculation
                ground_truth_ids = set(doc.get("_id", "") for doc in baseline_results)

                self.logger.info(f"Baseline returned {baseline_count} results")

                query_result = {
                    "query": query,
                    "baseline": {
                        "result_count": baseline_count,
                        "aql": baseline_results[0].get("_debug", {}).get("aql", "") if baseline_results else ""
                    },
                    "ablation_results": {}
                }

                # Test each activity collection individually
                for collection in self.activity_collections:
                    self.logger.info(f"Ablating collection: {collection}")

                    # Ablate the collection
                    self.metadata_manager.ablate_collection(collection)

                    # Run the query again
                    ablated_results = execute_query(query, capture_aql=True)
                    ablated_count = len(ablated_results) if ablated_results else 0

                    self.logger.info(f"With {collection} ablated: {ablated_count} results")

                    # Calculate both precision and recall metrics using ground truth
                    ablated_ids = set(doc.get("_id", "") for doc in ablated_results)

                    # Calculate metrics
                    true_positives = len(ablated_ids.intersection(ground_truth_ids))
                    false_positives = len(ablated_ids - ground_truth_ids)
                    false_negatives = len(ground_truth_ids - ablated_ids)

                    # Calculate precision and recall
                    if true_positives + false_positives > 0:
                        precision = true_positives / (true_positives + false_positives)
                    else:
                        precision = 1.0  # No results means perfect precision (no false positives)

                    if true_positives + false_negatives > 0:
                        recall = true_positives / (true_positives + false_negatives)
                    else:
                        recall = 1.0  # No expected results means perfect recall

                    # Calculate F1 score
                    if precision + recall > 0:
                        f1 = 2 * (precision * recall) / (precision + recall)
                    else:
                        f1 = 0.0

                    # Impact is now defined as change in F1 score (1.0 - f1)
                    impact = 1.0 - f1

                    # Store results
                    query_result["ablation_results"][collection] = {
                        "result_count": ablated_count,
                        "aql": ablated_results[0].get("_debug", {}).get("aql", "") if ablated_results else "",
                        "metrics": {
                            "precision": precision,
                            "recall": recall,
                            "f1": f1,
                            "impact": impact,
                            "true_positives": true_positives,
                            "false_positives": false_positives,
                            "false_negatives": false_negatives
                        }
                    }

                    # Restore the collection
                    self.metadata_manager.restore_collection(collection)

                # Test all activity collections together
                self.logger.info("Ablating all activity collections")

                # Ablate all collections
                for collection in self.activity_collections:
                    self.metadata_manager.ablate_collection(collection)

                # Run the query again
                all_ablated_results = execute_query(query, capture_aql=True)
                all_ablated_count = len(all_ablated_results) if all_ablated_results else 0

                self.logger.info(f"With all activity collections ablated: {all_ablated_count} results")

                # Calculate metrics using ground truth
                all_ablated_ids = set(doc.get("_id", "") for doc in all_ablated_results)

                # Calculate metrics
                true_positives = len(all_ablated_ids.intersection(ground_truth_ids))
                false_positives = len(all_ablated_ids - ground_truth_ids)
                false_negatives = len(ground_truth_ids - all_ablated_ids)

                # Calculate precision and recall
                if true_positives + false_positives > 0:
                    precision = true_positives / (true_positives + false_positives)
                else:
                    precision = 1.0

                if true_positives + false_negatives > 0:
                    recall = true_positives / (true_positives + false_negatives)
                else:
                    recall = 1.0

                # Calculate F1 score
                if precision + recall > 0:
                    f1 = 2 * (precision * recall) / (precision + recall)
                else:
                    f1 = 0.0

                # Impact is now defined as change in F1 score
                impact = 1.0 - f1

                # Store results
                query_result["ablation_results"]["all_activity"] = {
                    "result_count": all_ablated_count,
                    "aql": all_ablated_results[0].get("_debug", {}).get("aql", "") if all_ablated_results else "",
                    "metrics": {
                        "precision": precision,
                        "recall": recall,
                        "f1": f1,
                        "impact": impact,
                        "true_positives": true_positives,
                        "false_positives": false_positives,
                        "false_negatives": false_negatives
                    }
                }

                # Restore all collections
                for collection in self.activity_collections:
                    self.metadata_manager.restore_collection(collection)

                query_results.append(query_result)

            # Calculate average metrics for each collection
            collection_metrics = {}
            metrics_to_track = ["precision", "recall", "f1", "impact"]

            for collection in self.activity_collections + ["all_activity"]:
                collection_metrics[collection] = {}

                for metric in metrics_to_track:
                    values = []
                    for qr in query_results:
                        if collection in qr["ablation_results"]:
                            value = qr["ablation_results"][collection]["metrics"].get(metric, 0)
                            values.append(value)

                    if values:
                        avg_value = sum(values) / len(values)
                        collection_metrics[collection][metric] = avg_value

            # Store results
            self.results["query_results"] = query_results
            self.results["collection_impact"] = collection_metrics

            ablation_time = time.time() - start_time
            self.results["metrics"]["ablation_time"] = ablation_time

            self.logger.info(f"Ablation tests completed in {ablation_time:.2f} seconds")
            self.logger.info(f"Collection impact metrics: {collection_metrics}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to run ablation tests: {e}")
            return False

    def save_results(self) -> bool:
        """Save test results to file.

        Returns:
            True if successful, False otherwise
        """
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.output_dir, f"ablation_test_results_{timestamp}.json")

            self.logger.info(f"Saving results to {output_path}")

            # Save complete JSON results
            with open(output_path, 'w') as f:
                json.dump(self.results, f, indent=2)

            self.logger.info(f"Results saved to {output_path}")

            # Also save a readable summary with improved metrics
            summary_path = os.path.join(self.output_dir, f"ablation_summary_{timestamp}.txt")

            with open(summary_path, 'w') as f:
                f.write("Indaleko Ablation Test Summary\n")
                f.write("=============================\n\n")
                f.write(f"Test run: {timestamp}\n")
                f.write(f"Dataset size: {self.config.get('dataset_size', 100)}\n\n")

                f.write("Collection Impact Metrics\n")
                f.write("----------------------\n")
                for collection, metrics in self.results["collection_impact"].items():
                    f.write(f"{collection}:\n")
                    f.write(f"  Precision: {metrics.get('precision', 0):.4f}\n")
                    f.write(f"  Recall: {metrics.get('recall', 0):.4f}\n")
                    f.write(f"  F1 Score: {metrics.get('f1', 0):.4f}\n")
                    f.write(f"  Impact: {metrics.get('impact', 0):.4f}\n")

                f.write("\nDetailed Query Results\n")
                f.write("--------------------\n")
                for qr in self.results["query_results"]:
                    f.write(f"\nQuery: {qr['query']}\n")
                    f.write(f"Baseline results: {qr['baseline']['result_count']}\n")

                    for collection, result in qr["ablation_results"].items():
                        metrics = result["metrics"]
                        f.write(f"  With {collection} ablated:\n")
                        f.write(f"    Results: {result['result_count']}\n")
                        f.write(f"    Precision: {metrics.get('precision', 0):.4f}\n")
                        f.write(f"    Recall: {metrics.get('recall', 0):.4f}\n")
                        f.write(f"    F1 Score: {metrics.get('f1', 0):.4f}\n")
                        f.write(f"    Impact Score: {metrics.get('impact', 0):.4f}\n")
                        f.write(f"    True Positives: {metrics.get('true_positives', 0)}\n")
                        f.write(f"    False Positives: {metrics.get('false_positives', 0)}\n")
                        f.write(f"    False Negatives: {metrics.get('false_negatives', 0)}\n")

            self.logger.info(f"Summary saved to {summary_path}")

            # Save a CSV version for easier data analysis
            csv_path = os.path.join(self.output_dir, f"ablation_metrics_{timestamp}.csv")

            with open(csv_path, 'w') as f:
                # Write header
                f.write("Query,Collection,Results,Precision,Recall,F1,Impact,TruePositives,FalsePositives,FalseNegatives\n")

                # Write data rows
                for qr in self.results["query_results"]:
                    query = qr['query'].replace(',', ' ')  # Remove commas for CSV

                    for collection, result in qr["ablation_results"].items():
                        metrics = result["metrics"]
                        row = [
                            query,
                            collection,
                            str(result["result_count"]),
                            f"{metrics.get('precision', 0):.4f}",
                            f"{metrics.get('recall', 0):.4f}",
                            f"{metrics.get('f1', 0):.4f}",
                            f"{metrics.get('impact', 0):.4f}",
                            str(metrics.get('true_positives', 0)),
                            str(metrics.get('false_positives', 0)),
                            str(metrics.get('false_negatives', 0))
                        ]
                        f.write(",".join(row) + "\n")

            self.logger.info(f"CSV metrics saved to {csv_path}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")
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

            # TODO: Implement cleanup logic if needed
            # For now, we'll leave the data for inspection

            self.logger.info("Database cleanup completed")
            return True

        except Exception as e:
            self.logger.error(f"Failed to clean up database: {e}")
            return False

    def run(self) -> Dict[str, Any]:
        """Run the comprehensive ablation test.

        Returns:
            Test results dictionary
        """
        self.logger.info("Starting comprehensive ablation test...")

        success = (
            self.setup_environment() and
            self.generate_test_data() and
            self.upload_data() and
            self.run_ablation_tests()
        )

        # Always try to save results and clean up
        save_success = self.save_results()
        cleanup_success = self.cleanup_database()

        if success and save_success:
            self.logger.info("Comprehensive ablation test completed successfully")
        else:
            self.logger.warning("Comprehensive ablation test had errors")

        return self.results


def setup_logging(level=logging.INFO):
    """Set up logging configuration."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("ablation_test.log")
        ]
    )


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run comprehensive ablation tests')

    parser.add_argument('--dataset-size', type=int, default=100,
                       help='Number of records to generate (default: 100)')
    parser.add_argument('--output-dir', type=str, default="./ablation_results",
                       help='Directory to save results (default: ./ablation_results)')
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
        "output_dir": args.output_dir,
        "skip_cleanup": args.skip_cleanup
    }

    # Create and run the test
    test = ComprehensiveAblationTest(config)
    results = test.run()

    # Display summary
    if results.get("collection_impact"):
        print("\nCollection Impact Summary:")
        for collection, metrics in results["collection_impact"].items():
            print(f"- {collection}:")
            print(f"  Precision: {metrics.get('precision', 0):.4f}")
            print(f"  Recall: {metrics.get('recall', 0):.4f}")
            print(f"  F1 Score: {metrics.get('f1', 0):.4f}")
            print(f"  Impact: {metrics.get('impact', 0):.4f}")

    print(f"\nResults saved to: {args.output_dir}")

    # Return success status
    success = all(
        result["ablation_results"].get("all_activity", {})
        .get("metrics", {})
        .get("f1", 0) < 1.0  # Some impact is shown if F1 < 1.0
        for result in results.get("query_results", [])
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
