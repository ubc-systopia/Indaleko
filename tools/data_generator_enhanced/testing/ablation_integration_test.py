#!/usr/bin/env python3
"""
End-to-end integration test for Indaleko ablation testing framework.

This module provides a complete implementation of the ablation test pipeline,
starting from database setup through test data generation, query execution,
and result reporting.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import os
import sys
import logging
import argparse
import json
import random
import time
import datetime
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Union

# Add the Indaleko root to the path
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
from tools.data_generator_enhanced.testing.truth_data_tracker import TruthDataTracker
from tools.data_generator_enhanced.testing.cluster_generator import ClusterGenerator
from tools.data_generator_enhanced.testing.query_generator_enhanced import QueryGenerator
from tools.data_generator_enhanced.testing.ablation_execute_query import fixed_execute_query
from tools.data_generator_enhanced.testing.ablation_tester import AblationTester

# Import the same data generator tools as used in run_comprehensive_ablation.py
try:
    from tools.data_generator_enhanced.agents.data_gen.tools.stats import ActivityGeneratorTool, FileMetadataGeneratorTool
except ImportError as e:
    logging.error(f"Error importing generator tools: {e}")
    ActivityGeneratorTool = None
    FileMetadataGeneratorTool = None


class AblationIntegrationTest:
    """End-to-end integration test for ablation testing framework."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the integration test.
        
        Args:
            config: Dictionary with test configuration
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Set up random seed for reproducibility
        seed = config.get("seed", 42)
        random.seed(seed)
        self.logger.info(f"Initialized with random seed {seed}")
        
        # Set up output directory
        self.output_dir = config.get("output_dir", "ablation_results")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize database connection
        self.db_config = None
        self.db = None
        self.setup_database()
        
        # Initialize components
        self.truth_tracker = TruthDataTracker(
            db_path=os.path.join(self.output_dir, "ablation_results.db")
        )
        self.cluster_generator = ClusterGenerator(seed=seed)
        self.query_generator = QueryGenerator(seed=seed)
        self.ablation_tester = AblationTester()
        
        # Initialize data generator tools
        if FileMetadataGeneratorTool is None or ActivityGeneratorTool is None:
            self.logger.error("Data generator tools are not available")
        else:
            self.file_generator = FileMetadataGeneratorTool()
            self.activity_generator = ActivityGeneratorTool()
            self.logger.info("Initialized data generator tools")
        
        # Track state
        self.study_id = None
        self.cluster = None
        self.cluster_id = None
        self.queries = {"experimental": [], "control": []}
        self.generated_data = {
            "storage": [],
            "activity": []
        }
        self.storage_objects = []
        self.activities = []
        
        # Initialize results dictionary
        self.results = {
            "config": config,
            "metrics": {},
            "collection_impact": {},
            "query_results": [],
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Initialize metadata manager
        self.collections_metadata = IndalekoDBCollectionsMetadata(self.db_config)
    
    def setup_database(self) -> bool:
        """Set up database connection.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Setting up database connection...")
            self.db_config = IndalekoDBConfig()
            self.db = self.db_config.get_arangodb()
            self.logger.info("Database connection established")
            return True
        except Exception as e:
            self.logger.error(f"Error setting up database: {e}")
            return False
    
    def reset_database(self) -> bool:
        """Reset the database to a clean state.
        
        This method resets all ablated collections and truncates target collections
        to prepare for test data generation.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Resetting database...")
            
            # Restore all ablated collections
            ablated_collections = self.collections_metadata.get_ablated_collections()
            for collection in ablated_collections:
                self.collections_metadata.restore_collection(collection)
            
            # Truncate all collections that we'll use for testing
            # Only if explicitly configured to do so
            if self.config.get("truncate_collections", False):
                test_collections = [
                    IndalekoDBCollections.Indaleko_Object_Collection,
                    IndalekoDBCollections.Indaleko_ActivityContext_Collection,
                    IndalekoDBCollections.Indaleko_MusicActivityData_Collection,
                    IndalekoDBCollections.Indaleko_GeoActivityData_Collection,
                    IndalekoDBCollections.Indaleko_TempActivityData_Collection,
                    IndalekoDBCollections.Indaleko_SemanticData_Collection,
                    IndalekoDBCollections.Indaleko_Query_History_Collection
                ]
                
                for collection_name in test_collections:
                    try:
                        collection = self.db.collection(collection_name)
                        collection.truncate()
                        self.logger.info(f"Truncated collection {collection_name}")
                    except Exception as e:
                        self.logger.warning(f"Error truncating collection {collection_name}: {e}")
            
            self.logger.info("Database reset completed")
            return True
        except Exception as e:
            self.logger.error(f"Error resetting database: {e}")
            return False
    
    def create_study(self) -> bool:
        """Create a new ablation study record.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Creating ablation study record...")
            
            study_name = self.config.get("study_name", f"Ablation Study {datetime.datetime.now().strftime('%Y-%m-%d')}")
            study_description = self.config.get("study_description", "Automated ablation test for activity metadata")
            
            study_parameters = {
                "seed": self.config.get("seed", 42),
                "truncate_collections": self.config.get("truncate_collections", False),
                "experimental_sources": 4,
                "control_sources": 2,
                "dataset_size": self.config.get("dataset_size", 100),
                "truth_ratio": self.config.get("truth_ratio", 0.1),
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            self.study_id = self.truth_tracker.create_study(
                name=study_name,
                description=study_description,
                parameters=study_parameters
            )
            
            self.logger.info(f"Created study {self.study_id}: {study_name}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating study: {e}")
            return False
    
    def create_cluster(self) -> bool:
        """Create a test cluster for the study.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Creating test cluster...")
            
            # Generate a single balanced cluster
            clusters = self.cluster_generator.create_balanced_clusters()
            self.cluster = clusters[0]  # Use the first cluster
            
            # Extract source names
            experimental_sources = [source["name"] for source in self.cluster["experimental_sources"]]
            control_sources = [source["name"] for source in self.cluster["control_sources"]]
            
            # Add cluster to the study
            self.cluster_id = self.truth_tracker.add_cluster(
                study_id=self.study_id,
                name=self.cluster["name"],
                experimental_sources=experimental_sources,
                control_sources=control_sources
            )
            
            self.logger.info(f"Created cluster {self.cluster_id}: {self.cluster['name']}")
            self.logger.info(f"Experimental sources: {experimental_sources}")
            self.logger.info(f"Control sources: {control_sources}")
            self.logger.info(f"Experimental categories: {self.cluster['experimental_categories']}")
            self.logger.info(f"Control categories: {self.cluster['control_categories']}")
            
            # Save cluster to file for reference
            cluster_file = os.path.join(self.output_dir, f"cluster_{self.cluster_id}.json")
            with open(cluster_file, 'w') as f:
                json.dump(self.cluster, f, indent=2)
            
            self.logger.info(f"Cluster saved to {cluster_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating cluster: {e}")
            return False
    
    def generate_queries(self) -> bool:
        """Generate test queries for the cluster.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Generating test queries...")
            
            # Decide whether to use LLM or template-based generation
            use_llm = self.config.get("use_llm", False)
            num_queries = self.config.get("num_queries", 10)
            
            if use_llm:
                llm_provider = self.config.get("llm_provider", "openai")
                self.logger.info(f"Using LLM-based query generation with {llm_provider}...")
                
                self.queries = self.query_generator.generate_queries_with_llm(
                    cluster=self.cluster,
                    num_queries=num_queries,
                    llm_provider=llm_provider
                )
            else:
                self.logger.info("Using template-based query generation...")
                
                self.queries = self.query_generator.generate_queries_for_cluster(
                    cluster=self.cluster,
                    num_queries=num_queries
                )
            
            # Add queries to the study
            for query_type, query_list in self.queries.items():
                for query in query_list:
                    query_id = self.truth_tracker.add_query(
                        study_id=self.study_id,
                        text=query["text"],
                        category=query_type,
                        metadata_categories=query.get("categories", [])
                    )
                    # Add the ID to the query for reference
                    query["id"] = query_id
            
            # Save queries to file for reference
            query_file = os.path.join(self.output_dir, f"queries_{self.study_id}.json")
            with open(query_file, 'w') as f:
                json.dump(self.queries, f, indent=2)
            
            total_queries = len(self.queries["experimental"]) + len(self.queries["control"])
            self.logger.info(f"Generated {total_queries} queries and saved to {query_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error generating queries: {e}")
            return False
    
    def generate_test_data(self) -> bool:
        """Generate synthetic test data for queries.
        
        This method creates both storage objects and associated activity records
        for testing queries against.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Generating synthetic test data...")
            start_time = time.time()
            
            # Check if generator tools are available
            if not hasattr(self, 'file_generator') or not hasattr(self, 'activity_generator'):
                self.logger.error("Data generator tools are not available")
                return False
            
            # Generate base storage objects
            dataset_size = self.config.get("dataset_size", 100)
            self.logger.info(f"Generating {dataset_size} storage objects...")
            
            # Generate storage objects
            storage_result = self.file_generator.execute({
                "count": dataset_size,
                "criteria": {}
            })
            self.storage_objects = storage_result["records"]
            self.generated_data["storage"] = self.storage_objects
            
            # Debug the storage objects structure
            if self.storage_objects and len(self.storage_objects) > 0:
                first_obj = self.storage_objects[0]
                self.logger.debug(f"First storage object keys: {list(first_obj.keys())}")
                self.logger.debug(f"Sample storage object: {first_obj}")
            else:
                self.logger.error("No storage objects were generated")
            
            self.logger.info(f"Generated {len(self.storage_objects)} storage objects")
            
            # Generate activity records for a subset of storage objects
            activity_count = dataset_size // 2
            self.logger.info(f"Generating {activity_count} activity records...")
            
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
            self.generated_data["activity"] = self.activities
            
            generation_time = time.time() - start_time
            self.results["metrics"]["generation_time"] = generation_time

            self.logger.info(f"Generated {len(self.storage_objects)} storage objects and "
                   f"{len(self.activities)} activity records in {generation_time:.2f} seconds")

            # Log semantic attribute count for debugging
            total_storage_attrs = sum(len(obj.get("SemanticAttributes", [])) for obj in self.storage_objects)
            total_activity_attrs = sum(len(act.get("SemanticAttributes", [])) for act in self.activities)
            self.logger.info(f"Added {total_storage_attrs} semantic attributes to storage objects")
            self.logger.info(f"Added {total_activity_attrs} semantic attributes to activities")
            
            # Each query needs some matching records
            truth_count_per_query = max(5, int(dataset_size * self.config.get("truth_ratio", 0.1)))
            
            # Track all the objects we've already marked as truth data
            truth_objects = set()
            
            # Process each query and generate matching activity records
            for query_type, query_list in self.queries.items():
                for query in query_list:
                    query_text = query["text"]
                    query_categories = set(query.get("categories", []))
                    query_id = query["id"]
                    
                    self.logger.info(f"Generating truth data for query: {query_text}")
                    
                    # Choose random storage objects for this query's truth data
                    available_objects = []
                    for obj in self.storage_objects:
                        # Check if _key exists, otherwise use ObjectIdentifier
                        if "_key" in obj:
                            key = obj["_key"]
                        elif "ObjectIdentifier" in obj:
                            key = obj["ObjectIdentifier"]
                        else:
                            # Generate a key if none exists
                            key = str(uuid.uuid4())
                            obj["_key"] = key
                            
                        if key not in truth_objects:
                            available_objects.append(obj)
                    
                    # If we don't have enough objects left, reuse some
                    if len(available_objects) < truth_count_per_query:
                        self.logger.warning(
                            f"Not enough unique objects left for query {query_id}, reusing some objects"
                        )
                        available_objects = storage_objects
                    
                    truth_objects_for_query = random.sample(
                        available_objects,
                        min(len(available_objects), truth_count_per_query)
                    )
                    
                    # Mark these objects as used
                    for obj in truth_objects_for_query:
                        # Check if _key exists, otherwise use ObjectIdentifier
                        if "_key" in obj:
                            key = obj["_key"]
                        elif "ObjectIdentifier" in obj:
                            key = obj["ObjectIdentifier"]
                        else:
                            # Generate a key if none exists
                            key = str(uuid.uuid4())
                            obj["_key"] = key
                            
                        truth_objects.add(key)
                    
                    # Generate matching activity records
                    for obj in truth_objects_for_query:
                        # Generate activity data that matches the query
                        activity_options = {
                            "count": 1,  # Generate one activity record
                            "criteria": {
                                "storage_objects": [obj],
                                "categories": list(query_categories),
                                "related_to_query": query_text
                            }
                        }
                        
                        # The ActivityGeneratorTool uses execute() method, not generate_activity_record()
                        activity_result = self.activity_generator.execute(activity_options)
                        activity_record = activity_result["records"][0] if activity_result.get("records") else {}
                        self.generated_data["activity"].append(activity_record)
                        
                        # Add truth data record
                        # Determine document ID
                        if "_key" in obj:
                            doc_id = obj["_key"]
                        elif "ObjectIdentifier" in obj:
                            doc_id = obj["ObjectIdentifier"]
                        else:
                            # Should already have _key from previous processing
                            doc_id = obj["_key"]
                            
                        self.truth_tracker.add_truth_data(
                            query_id=query_id,
                            document_id=doc_id,
                            matching=True,
                            metadata={
                                "storage_type": obj.get("Type", "Unknown"),
                                "activity_type": activity_record.get("ActivityType", "Unknown"),
                                "categories": list(query_categories)
                            }
                        )
            
            # Generate non-matching activity records for remaining storage objects
            remaining_count = activity_count - len(self.generated_data["activity"])
            if remaining_count > 0:
                self.logger.info(f"Generating {remaining_count} non-matching activity records...")
                
                # Select objects not used for truth data if possible
                available_objects = []
                for obj in self.storage_objects:
                    # Check if _key exists, otherwise use ObjectIdentifier
                    if "_key" in obj:
                        key = obj["_key"]
                    elif "ObjectIdentifier" in obj:
                        key = obj["ObjectIdentifier"]
                    else:
                        # Generate a key if none exists
                        key = str(uuid.uuid4())
                        obj["_key"] = key
                        
                    if key not in truth_objects:
                        available_objects.append(obj)
                
                # If we don't have enough, use all objects
                if len(available_objects) < remaining_count:
                    available_objects = self.storage_objects
                
                for i in range(remaining_count):
                    obj = random.choice(available_objects)
                    
                    # Generate generic activity data
                    activity_options = {
                        "count": 1,  # Generate one activity record
                        "criteria": {
                            "storage_objects": [obj],
                            "categories": random.sample(["temporal", "activity", "spatial", "content"], 2)
                        }
                    }
                    
                    # The ActivityGeneratorTool uses execute() method, not generate_activity_record()
                    activity_result = self.activity_generator.execute(activity_options)
                    activity_record = activity_result["records"][0] if activity_result.get("records") else {}
                    self.generated_data["activity"].append(activity_record)
            
            # Save generated data to files for reference
            storage_file = os.path.join(self.output_dir, f"storage_data_{self.study_id}.json")
            with open(storage_file, 'w') as f:
                json.dump(self.generated_data["storage"][:10], f, indent=2)  # Save just a sample
            
            activity_file = os.path.join(self.output_dir, f"activity_data_{self.study_id}.json")
            with open(activity_file, 'w') as f:
                json.dump(self.generated_data["activity"][:10], f, indent=2)  # Save just a sample
            
            self.logger.info(f"Generated {len(self.generated_data['storage'])} storage objects and "
                           f"{len(self.generated_data['activity'])} activity records")
            self.logger.info(f"Data samples saved to {storage_file} and {activity_file}")
            
            return True
        except Exception as e:
            self.logger.error(f"Error generating test data: {e}")
            return False
    
    def upload_test_data(self) -> bool:
        """Upload generated test data to the database.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Uploading test data to database...")
            
            # Upload storage objects
            objects_collection = self.db.collection(IndalekoDBCollections.Indaleko_Object_Collection)
            storage_batch_size = 100
            
            storage_count = len(self.generated_data["storage"])
            uploaded_storage = 0
            
            self.logger.info(f"Uploading {storage_count} storage objects in batches of {storage_batch_size}...")
            
            # Upload in batches
            for i in range(0, storage_count, storage_batch_size):
                batch = self.generated_data["storage"][i:i+storage_batch_size]
                try:
                    objects_collection.import_bulk(batch, on_duplicate="update")
                    uploaded_storage += len(batch)
                    self.logger.info(f"Uploaded storage batch {i//storage_batch_size + 1}: {len(batch)} objects")
                except Exception as e:
                    self.logger.error(f"Error uploading storage batch: {e}")
            
            # Upload activity records
            # Group by activity type to send to appropriate collections
            activity_records = {
                "ActivityContext": [],
                "MusicActivityContext": [],
                "GeoActivityContext": [],
                "TempActivityContext": [],
                "QueryHistory": []
            }
            
            # Sort records by type
            for record in self.generated_data["activity"]:
                activity_type = record.get("ActivityType", "default")
                
                if "music" in activity_type.lower() or "spotify" in activity_type.lower():
                    activity_records["MusicActivityContext"].append(record)
                elif "location" in activity_type.lower() or "geo" in activity_type.lower():
                    activity_records["GeoActivityContext"].append(record)
                elif "temperature" in activity_type.lower() or "thermostat" in activity_type.lower():
                    activity_records["TempActivityContext"].append(record)
                elif "query" in activity_type.lower() or "search" in activity_type.lower():
                    # Add to Query History collection
                    activity_records["QueryHistory"].append(record)
                else:
                    # Add to general activity context
                    activity_records["ActivityContext"].append(record)
            
            # Upload each activity type
            activity_batch_size = 50
            total_uploaded_activity = 0
            
            for activity_type, records in activity_records.items():
                # Skip empty record lists
                if not records:
                    continue
                    
                # Get the correct collection name
                collection_name = None
                if activity_type == "ActivityContext":
                    collection_name = IndalekoDBCollections.Indaleko_ActivityContext_Collection
                elif activity_type == "MusicActivityContext":
                    collection_name = IndalekoDBCollections.Indaleko_MusicActivityData_Collection
                elif activity_type == "GeoActivityContext":
                    collection_name = IndalekoDBCollections.Indaleko_GeoActivityData_Collection
                elif activity_type == "TempActivityContext":
                    collection_name = IndalekoDBCollections.Indaleko_TempActivityData_Collection
                elif activity_type == "QueryHistory":
                    collection_name = IndalekoDBCollections.Indaleko_Query_History_Collection
                
                if collection_name:
                    try:
                        collection = self.db.collection(collection_name)
                        record_count = len(records)
                        
                        self.logger.info(f"Uploading {record_count} {activity_type} records...")
                        
                        for i in range(0, record_count, activity_batch_size):
                            batch = records[i:i+activity_batch_size]
                            try:
                                collection.import_bulk(batch, on_duplicate="update")
                                total_uploaded_activity += len(batch)
                                self.logger.info(f"Uploaded {activity_type} batch {i//activity_batch_size + 1}: {len(batch)} records")
                            except Exception as e:
                                self.logger.error(f"Error uploading {activity_type} batch: {e}")
                    except Exception as e:
                        self.logger.error(f"Error with collection {collection_name}: {e}")
            
            self.logger.info(f"Uploaded {uploaded_storage} storage objects and {total_uploaded_activity} activity records")
            return True
        except Exception as e:
            self.logger.error(f"Error uploading test data: {e}")
            return False
    
    def run_ablation_tests(self) -> bool:
        """Run ablation tests for each query.
        
        This method executes each query with various ablated collections
        and records the results.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Running ablation tests...")
            
            # Get all queries
            all_queries = []
            all_queries.extend(self.queries["experimental"])
            all_queries.extend(self.queries["control"])
            
            # Get experimental and control sources
            experimental_sources = [
                source["collection"] for source in self.cluster["experimental_sources"]
            ]
            control_sources = [
                source["collection"] for source in self.cluster["control_sources"]
            ]
            
            # Run tests for each query
            for query in all_queries:
                query_text = query["text"]
                query_id = query["id"]
                
                self.logger.info(f"Testing query: {query_text}")
                
                # Step 1: Run baseline query (no ablation)
                self.logger.info("Running baseline query...")
                baseline_start = time.time()
                baseline_results = fixed_execute_query(query_text, capture_aql=True)
                baseline_time = time.time() - baseline_start
                
                # Extract IDs from results
                baseline_ids = set()
                for result in baseline_results:
                    if isinstance(result, dict) and "_key" in result:
                        baseline_ids.add(result["_key"])
                
                self.logger.info(f"Baseline query returned {len(baseline_ids)} unique results in {baseline_time:.2f} seconds")
                
                # Step 2: Run tests with experimental sources ablated
                if experimental_sources:
                    # First ablate each experimental source individually
                    for source in experimental_sources:
                        self.logger.info(f"Ablating experimental source: {source}")
                        
                        # Ablate the source
                        self.collections_metadata.ablate_collection(source)
                        
                        # Run the query
                        ablated_start = time.time()
                        ablated_results = fixed_execute_query(query_text, capture_aql=True)
                        ablated_time = time.time() - ablated_start
                        
                        # Extract IDs from results
                        ablated_ids = set()
                        for result in ablated_results:
                            if isinstance(result, dict) and "_key" in result:
                                ablated_ids.add(result["_key"])
                        
                        self.logger.info(f"Ablating {source} returned {len(ablated_ids)} unique results in {ablated_time:.2f} seconds")
                        
                        # Calculate metrics
                        true_positives = len(ablated_ids.intersection(baseline_ids))
                        false_positives = len(ablated_ids - baseline_ids)
                        false_negatives = len(baseline_ids - ablated_ids)
                        
                        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 1.0
                        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 1.0
                        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
                        impact = 1.0 - f1_score
                        
                        # Get the AQL query used
                        aql_query = ""
                        if ablated_results and "_debug" in ablated_results[0]:
                            aql_query = ablated_results[0]["_debug"].get("aql", "")
                        
                        # Record the result
                        self.truth_tracker.add_ablation_result(
                            study_id=self.study_id,
                            cluster_id=self.cluster_id,
                            query_id=query_id,
                            ablated_sources=[source],
                            returned_ids=list(ablated_ids),
                            precision=precision,
                            recall=recall,
                            f1_score=f1_score,
                            impact=impact,
                            execution_time_ms=int(ablated_time * 1000),
                            aql_query=aql_query
                        )
                        
                        # Restore the source
                        self.collections_metadata.restore_collection(source)
                    
                    # Now ablate all experimental sources together
                    self.logger.info("Ablating all experimental sources together...")
                    
                    # Ablate all experimental sources
                    for source in experimental_sources:
                        self.collections_metadata.ablate_collection(source)
                    
                    # Run the query
                    ablated_start = time.time()
                    ablated_results = fixed_execute_query(query_text, capture_aql=True)
                    ablated_time = time.time() - ablated_start
                    
                    # Extract IDs from results
                    ablated_ids = set()
                    for result in ablated_results:
                        if isinstance(result, dict) and "_key" in result:
                            ablated_ids.add(result["_key"])
                    
                    self.logger.info(f"Ablating all experimental sources returned {len(ablated_ids)} unique results in {ablated_time:.2f} seconds")
                    
                    # Calculate metrics
                    true_positives = len(ablated_ids.intersection(baseline_ids))
                    false_positives = len(ablated_ids - baseline_ids)
                    false_negatives = len(baseline_ids - ablated_ids)
                    
                    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 1.0
                    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 1.0
                    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
                    impact = 1.0 - f1_score
                    
                    # Get the AQL query used
                    aql_query = ""
                    if ablated_results and "_debug" in ablated_results[0]:
                        aql_query = ablated_results[0]["_debug"].get("aql", "")
                    
                    # Record the result
                    self.truth_tracker.add_ablation_result(
                        study_id=self.study_id,
                        cluster_id=self.cluster_id,
                        query_id=query_id,
                        ablated_sources=experimental_sources,
                        returned_ids=list(ablated_ids),
                        precision=precision,
                        recall=recall,
                        f1_score=f1_score,
                        impact=impact,
                        execution_time_ms=int(ablated_time * 1000),
                        aql_query=aql_query
                    )
                    
                    # Restore all experimental sources
                    for source in experimental_sources:
                        self.collections_metadata.restore_collection(source)
                
                # Step 3: Run tests with control sources ablated
                if control_sources:
                    # First ablate each control source individually
                    for source in control_sources:
                        self.logger.info(f"Ablating control source: {source}")
                        
                        # Ablate the source
                        self.collections_metadata.ablate_collection(source)
                        
                        # Run the query
                        ablated_start = time.time()
                        ablated_results = fixed_execute_query(query_text, capture_aql=True)
                        ablated_time = time.time() - ablated_start
                        
                        # Extract IDs from results
                        ablated_ids = set()
                        for result in ablated_results:
                            if isinstance(result, dict) and "_key" in result:
                                ablated_ids.add(result["_key"])
                        
                        self.logger.info(f"Ablating {source} returned {len(ablated_ids)} unique results in {ablated_time:.2f} seconds")
                        
                        # Calculate metrics
                        true_positives = len(ablated_ids.intersection(baseline_ids))
                        false_positives = len(ablated_ids - baseline_ids)
                        false_negatives = len(baseline_ids - ablated_ids)
                        
                        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 1.0
                        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 1.0
                        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
                        impact = 1.0 - f1_score
                        
                        # Get the AQL query used
                        aql_query = ""
                        if ablated_results and "_debug" in ablated_results[0]:
                            aql_query = ablated_results[0]["_debug"].get("aql", "")
                        
                        # Record the result
                        self.truth_tracker.add_ablation_result(
                            study_id=self.study_id,
                            cluster_id=self.cluster_id,
                            query_id=query_id,
                            ablated_sources=[source],
                            returned_ids=list(ablated_ids),
                            precision=precision,
                            recall=recall,
                            f1_score=f1_score,
                            impact=impact,
                            execution_time_ms=int(ablated_time * 1000),
                            aql_query=aql_query
                        )
                        
                        # Restore the source
                        self.collections_metadata.restore_collection(source)
                    
                    # Now ablate all control sources together
                    self.logger.info("Ablating all control sources together...")
                    
                    # Ablate all control sources
                    for source in control_sources:
                        self.collections_metadata.ablate_collection(source)
                    
                    # Run the query
                    ablated_start = time.time()
                    ablated_results = fixed_execute_query(query_text, capture_aql=True)
                    ablated_time = time.time() - ablated_start
                    
                    # Extract IDs from results
                    ablated_ids = set()
                    for result in ablated_results:
                        if isinstance(result, dict) and "_key" in result:
                            ablated_ids.add(result["_key"])
                    
                    self.logger.info(f"Ablating all control sources returned {len(ablated_ids)} unique results in {ablated_time:.2f} seconds")
                    
                    # Calculate metrics
                    true_positives = len(ablated_ids.intersection(baseline_ids))
                    false_positives = len(ablated_ids - baseline_ids)
                    false_negatives = len(baseline_ids - ablated_ids)
                    
                    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 1.0
                    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 1.0
                    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
                    impact = 1.0 - f1_score
                    
                    # Get the AQL query used
                    aql_query = ""
                    if ablated_results and "_debug" in ablated_results[0]:
                        aql_query = ablated_results[0]["_debug"].get("aql", "")
                    
                    # Record the result
                    self.truth_tracker.add_ablation_result(
                        study_id=self.study_id,
                        cluster_id=self.cluster_id,
                        query_id=query_id,
                        ablated_sources=control_sources,
                        returned_ids=list(ablated_ids),
                        precision=precision,
                        recall=recall,
                        f1_score=f1_score,
                        impact=impact,
                        execution_time_ms=int(ablated_time * 1000),
                        aql_query=aql_query
                    )
                    
                    # Restore all control sources
                    for source in control_sources:
                        self.collections_metadata.restore_collection(source)
            
            self.logger.info("All ablation tests completed successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error running ablation tests: {e}")
            return False
    
    def generate_report(self) -> bool:
        """Generate a comprehensive report for the study.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Generating ablation study report...")
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = os.path.join(self.output_dir, f"ablation_report_{timestamp}.md")
            
            # Generate the report using the TruthDataTracker
            self.truth_tracker.generate_report(self.study_id, report_path)
            self.logger.info(f"Ablation report generated at {report_path}")
            
            # Also generate a simple summary
            summary_path = os.path.join(self.output_dir, f"ablation_summary_{timestamp}.txt")
            
            with open(summary_path, 'w') as f:
                # Get study summary
                summary = self.truth_tracker.get_study_summary(self.study_id)
                
                f.write("Indaleko Ablation Test Summary\n")
                f.write("=============================\n\n")
                f.write(f"Study: {summary['study']['name']}\n")
                f.write(f"Date: {datetime.datetime.fromtimestamp(summary['study']['created_at'])}\n")
                f.write(f"Cluster: {self.cluster['name']}\n\n")
                
                f.write("Source Impact Metrics\n")
                f.write("--------------------\n")
                for source, metrics in summary['metrics']['sources'].items():
                    f.write(f"{source}:\n")
                    f.write(f"  Precision: {metrics.get('precision', 0):.4f}\n")
                    f.write(f"  Recall: {metrics.get('recall', 0):.4f}\n")
                    f.write(f"  F1 Score: {metrics.get('f1', 0):.4f}\n")
                    f.write(f"  Impact: {metrics.get('impact', 0):.4f}\n")
                
                f.write("\nExperimental vs. Control Sources\n")
                f.write("------------------------------\n")
                f.write("Experimental Sources:\n")
                for source in summary['clusters'][0]['experimental_sources']:
                    f.write(f"  - {source}\n")
                
                f.write("\nControl Sources:\n")
                for source in summary['clusters'][0]['control_sources']:
                    f.write(f"  - {source}\n")
                
                # Include summary statistics
                experimental_sources = summary['clusters'][0]['experimental_sources']
                control_sources = summary['clusters'][0]['control_sources']
                
                # Calculate average impact for experimental and control sources
                exp_impact = 0.0
                exp_count = 0
                control_impact = 0.0
                control_count = 0
                
                for source, metrics in summary['metrics']['sources'].items():
                    if source in experimental_sources:
                        exp_impact += metrics.get('impact', 0)
                        exp_count += 1
                    elif source in control_sources:
                        control_impact += metrics.get('impact', 0)
                        control_count += 1
                
                avg_exp_impact = exp_impact / exp_count if exp_count > 0 else 0
                avg_control_impact = control_impact / control_count if control_count > 0 else 0
                
                f.write("\nSummary Statistics\n")
                f.write("-----------------\n")
                f.write(f"Average Experimental Impact: {avg_exp_impact:.4f}\n")
                f.write(f"Average Control Impact: {avg_control_impact:.4f}\n")
                f.write(f"Difference: {abs(avg_exp_impact - avg_control_impact):.4f}\n")
                
                # Add conclusion
                f.write("\nConclusion\n")
                f.write("----------\n")
                if avg_exp_impact > avg_control_impact:
                    diff_percent = (avg_exp_impact / avg_control_impact - 1) * 100 if avg_control_impact > 0 else float('inf')
                    f.write(f"Experimental sources have {diff_percent:.1f}% greater impact on query results.\n")
                    f.write("The null hypothesis that activity data does not impact query performance is REJECTED.\n")
                elif avg_exp_impact < avg_control_impact:
                    diff_percent = (avg_control_impact / avg_exp_impact - 1) * 100 if avg_exp_impact > 0 else float('inf')
                    f.write(f"Control sources have {diff_percent:.1f}% greater impact on query results.\n")
                    f.write("This result is unexpected and warrants further investigation.\n")
                else:
                    f.write("Experimental and control sources have equal impact on query results.\n")
                    f.write("The null hypothesis cannot be rejected based on this test.\n")
            
            self.logger.info(f"Summary report generated at {summary_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error generating report: {e}")
            return False
    
    def cleanup(self) -> bool:
        """Clean up resources.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Cleaning up resources...")
            
            # Restore all ablated collections
            ablated_collections = self.collections_metadata.get_ablated_collections()
            for collection in ablated_collections:
                self.collections_metadata.restore_collection(collection)
            
            # Close the truth data tracker
            self.truth_tracker.close()
            
            self.logger.info("Cleanup completed successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            return False
    
    def run_test(self) -> Dict[str, Any]:
        """Run the complete integration test.
        
        Returns:
            Dictionary with test results
        """
        start_time = time.time()
        self.logger.info("Starting ablation integration test...")
        
        success = True
        results = {
            "success": False,
            "study_id": None,
            "cluster_id": None,
            "timestamp": datetime.datetime.now().isoformat(),
            "config": self.config,
            "errors": []
        }
        
        try:
            # Step 1: Reset the database
            if not self.reset_database():
                self.logger.error("Failed to reset database. Aborting test.")
                results["errors"].append("Database reset failed")
                return results
            
            # Step 2: Create study record
            if not self.create_study():
                self.logger.error("Failed to create study record. Aborting test.")
                results["errors"].append("Study creation failed")
                return results
            
            results["study_id"] = self.study_id
            
            # Step 3: Create test cluster
            if not self.create_cluster():
                self.logger.error("Failed to create test cluster. Aborting test.")
                results["errors"].append("Cluster creation failed")
                return results
                
            results["cluster_id"] = self.cluster_id
            
            # Step 4: Generate test queries
            if not self.generate_queries():
                self.logger.error("Failed to generate test queries. Aborting test.")
                results["errors"].append("Query generation failed")
                return results
            
            # Step 5: Generate test data
            if not self.generate_test_data():
                self.logger.error("Failed to generate test data. Aborting test.")
                results["errors"].append("Test data generation failed")
                return results
            
            # Step 6: Upload test data
            if not self.upload_test_data():
                self.logger.error("Failed to upload test data. Aborting test.")
                results["errors"].append("Test data upload failed")
                return results
            
            # Step 7: Run ablation tests
            if not self.run_ablation_tests():
                self.logger.error("Failed to run ablation tests. Aborting test.")
                results["errors"].append("Ablation test execution failed")
                return results
            
            # Step 8: Generate report
            if not self.generate_report():
                self.logger.error("Failed to generate ablation report.")
                results["errors"].append("Report generation failed")
                success = False
            
            # Step 9: Clean up
            if not self.cleanup():
                self.logger.error("Failed to clean up resources.")
                results["errors"].append("Cleanup failed")
                success = False
            
            # Calculate execution time
            execution_time = time.time() - start_time
            results["execution_time"] = execution_time
            
            if success:
                self.logger.info(f"Ablation integration test completed successfully in {execution_time:.2f} seconds")
                results["success"] = True
            else:
                self.logger.warning(f"Ablation integration test completed with warnings in {execution_time:.2f} seconds")
                results["success"] = False
            
            return results
            
        except Exception as e:
            self.logger.error(f"Unexpected error in ablation integration test: {e}")
            import traceback
            traceback.print_exc()
            
            results["errors"].append(f"Unexpected error: {str(e)}")
            results["success"] = False
            
            # Attempt cleanup
            self.cleanup()
            
            return results


def setup_logging(level=logging.INFO, log_file=None):
    """Set up logging configuration.
    
    Args:
        level: Logging level (default: INFO)
        log_file: Optional log file path
    """
    handlers = [logging.StreamHandler()]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers
    )


def parse_args():
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Run ablation integration test")
    
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--dataset-size", type=int, default=100,
                        help="Number of test data records to generate (default: 100)")
    parser.add_argument("--num-queries", type=int, default=10,
                        help="Number of test queries to generate (default: 10)")
    parser.add_argument("--output-dir", type=str, default="ablation_results",
                        help="Output directory for results (default: ablation_results)")
    parser.add_argument("--truncate-collections", action="store_true",
                        help="Truncate collections before running the test")
    parser.add_argument("--use-llm", action="store_true",
                        help="Use LLM for query generation")
    parser.add_argument("--llm-provider", type=str, default="openai",
                        choices=["openai", "anthropic"],
                        help="LLM provider for query generation (default: openai)")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    
    return parser.parse_args()


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()
    
    # Set up logging
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(args.output_dir, f"ablation_test_{timestamp}.log")
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    setup_logging(
        level=logging.DEBUG if args.debug else logging.INFO,
        log_file=log_file
    )
    
    # Configure the test
    config = {
        "seed": args.seed,
        "dataset_size": args.dataset_size,
        "num_queries": args.num_queries,
        "output_dir": args.output_dir,
        "truncate_collections": args.truncate_collections,
        "use_llm": args.use_llm,
        "llm_provider": args.llm_provider,
        "study_name": f"Ablation Study {timestamp}",
        "study_description": "Automated ablation test for activity metadata"
    }
    
    # Create and run the test
    test = AblationIntegrationTest(config)
    results = test.run_test()
    
    # Display results
    if results["success"]:
        print("\nAblation integration test completed successfully!")
    else:
        print("\nAblation integration test completed with errors:")
        for error in results["errors"]:
            print(f"- {error}")
    
    print(f"\nResults saved to directory: {args.output_dir}")
    
    # Return exit code
    return 0 if results["success"] else 1


if __name__ == "__main__":
    sys.exit(main())