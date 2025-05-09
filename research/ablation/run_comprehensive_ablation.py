#!/usr/bin/env python3
"""Comprehensive ablation test runner with cross-collection support.

This script implements a complete ablation testing framework that can measure
the impact of ablating different activity data types on search precision and recall.
It supports testing multiple activity collections and handles cross-collection dependencies.
"""

import argparse
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

# Making sure we keep a global reference for debugging
db_config = None

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# Check for visualization dependencies
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from db.db_config import IndalekoDBConfig
from research.ablation.ablation_tester import AblationConfig, AblationTester
from research.ablation.base import ISyntheticCollector, ISyntheticRecorder
from research.ablation.collectors.collaboration_collector import (
    CollaborationActivityCollector,
)
from research.ablation.collectors.location_collector import LocationActivityCollector
from research.ablation.collectors.media_collector import MediaActivityCollector
from research.ablation.collectors.music_collector import MusicActivityCollector
from research.ablation.collectors.storage_collector import StorageActivityCollector
from research.ablation.collectors.task_collector import TaskActivityCollector
from research.ablation.data_sanity_checker import DataSanityChecker
from research.ablation.ner.entity_manager import NamedEntityManager
from research.ablation.query.enhanced.enhanced_query_generator import (
    EnhancedQueryGenerator,
)
from research.ablation.recorders.collaboration_recorder import (
    CollaborationActivityRecorder,
)
from research.ablation.recorders.location_recorder import LocationActivityRecorder
from research.ablation.recorders.media_recorder import MediaActivityRecorder
from research.ablation.recorders.music_recorder import MusicActivityRecorder
from research.ablation.recorders.storage_recorder import StorageActivityRecorder
from research.ablation.recorders.task_recorder import TaskActivityRecorder
from research.ablation.utils.uuid_utils import generate_deterministic_uuid


def setup_logging(verbose=False):
    """Set up logging for the ablation test runner."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )


class TestDataComponents(BaseModel):
    """Components for test data generation.

    This class holds the components needed to generate test data for different
    activity types, including the collector and recorder classes.
    """

    collector: type[ISyntheticCollector]
    recorder: type[ISyntheticRecorder]
    name: str
    hash_name: str
    hash_property_name: str

    model_config = {
        "arbitrary_types_allowed": True,
    }


def generate_test_data(
    entity_manager: NamedEntityManager,
    activity_data_providers: list[TestDataComponents],
    count: int = 100,
) -> dict:
    """Generate synthetic test data for all activity types.

    Args:
        entity_manager: The named entity manager for consistent entity references
        activity_data_providers: List of tuples containing activity data provider name, collector, and recorder
        count: Number of test records to generate per collection

    Returns:
        dict: Dictionary of generated data by collection type
    """
    logging.info(f"Generating {count} records for each activity type...")

    test_data = {}
    collections_loaded = []

    # Debug: check if collections exist before starting
    try:
        db_config = IndalekoDBConfig()
        db = db_config.get_arangodb()
        for provider in activity_data_providers:
            collection_name = f"Ablation{provider.name}Activity"
            if db.has_collection(collection_name):
                doc_count = db.aql.execute(f"RETURN LENGTH({collection_name})").next()
                logging.info(f"Debug: Collection {collection_name} exists with {doc_count} documents")
            else:
                logging.warning(f"Debug: Collection {collection_name} does not exist")
    except Exception as e:
        logging.exception(f"Error checking collections: {e}")

    for activity_data_provider in activity_data_providers:
        # Initialize collector based on whether it supports entity_manager
        collector_class = activity_data_provider.collector
        if activity_data_provider.name in ["Location", "Music", "Task", "Collaboration"]:
            # These collectors support entity_manager
            collector = collector_class(entity_manager=entity_manager, seed_value=42)
        else:
            # Storage and Media collectors only support seed_value
            collector = collector_class(seed_value=42)
        recorder = activity_data_provider.recorder()

        # Debug: Print recorder class details
        logging.info(f"Debug: Using recorder: {recorder.__class__.__name__}")
        collection_name = getattr(recorder, "get_collection_name", lambda: "Unknown")()
        logging.info(f"Debug: Collection name from recorder: {collection_name}")

        data = collector.generate_batch(count)

        # Debug: Log sample data
        if data:
            sample = data[0]
            logging.info(f"Debug: Sample data for {activity_data_provider.name}: {sample.get('id', 'no-id')}")
            logging.info(f"Debug: Sample keys: {list(sample.keys())}")

        # Ensure all data has an ID field and _key field for ArangoDB
        for item in data:
            if "id" not in item:
                # Create a content hash based on common fields or activity-specific fields
                content_hash = f"{activity_data_provider.hash_name}:{item.get(activity_data_provider.hash_property_name, 'unknown')}"
                item["id"] = generate_deterministic_uuid(content_hash)

            # Ensure _key field is set for ArangoDB
            if "_key" not in item and "id" in item:
                item["_key"] = str(item["id"])

        # Debug: Generate query with matching data to test query generation
        test_query = f"Find {activity_data_provider.name.lower()} activity"
        if activity_data_provider.name == "Music":
            test_query = "Find songs by Taylor Swift that I listened to at Home"
        elif activity_data_provider.name == "Location":
            test_query = "Find activities at Home"

        matching_data = collector.generate_matching_data(test_query, 3)
        logging.info(f"Debug: Generated {len(matching_data)} matching records for test query: '{test_query}'")
        if matching_data:
            logging.info(f"Debug: Matching data sample: {matching_data[0].get('id', 'no-id')}")

        batch_success = recorder.record_batch(data)

        if batch_success:
            collections_loaded.append(activity_data_provider.name)
            test_data[activity_data_provider.name] = data
            logging.info("Successfully loaded %s %s activity records", len(data), activity_data_provider.name)

            # Debug: Verify what was loaded in the database
            try:
                collection_name = f"Ablation{activity_data_provider.name}Activity"
                doc_count = db.aql.execute(f"RETURN LENGTH({collection_name})").next()
                logging.info(f"Debug: After loading, collection {collection_name} has {doc_count} documents")

                # Check a sample document
                sample_doc = db.aql.execute(f"FOR doc IN {collection_name} LIMIT 1 RETURN doc").next()
                logging.info(f"Debug: Sample document keys: {list(sample_doc.keys())}")
            except Exception as e:
                logging.exception(f"Error verifying loaded data: {e}")
        else:
            logging.warning("Failed to record %s data", activity_data_provider.name)

    logging.info(f"Successfully loaded data for {len(collections_loaded)} collections: {', '.join(collections_loaded)}")
    return test_data


def generate_cross_collection_queries(
    entity_manager: NamedEntityManager,
    ablation_tester: AblationTester,
    count: int = 5,
) -> list[dict[str, object]]:
    """Generate test queries that depend on multiple activity types.

    Args:
        entity_manager: The named entity manager for consistent entity references
        ablation_tester: The ablation tester for recording truth data
        count: Number of test queries to generate per combination

    Returns:
        list: List of generated queries with metadata
    """
    logging.info("Generating cross-collection test queries...")

    queries = []

    # Debug: Initial truth data check
    debug_truth_counts = {}
    for collection_name in ["AblationLocationActivity", "AblationMusicActivity"]:
        query_count = ablation_tester.db.aql.execute(f"RETURN LENGTH({ablation_tester.TRUTH_COLLECTION})").next()
        collection_truth_count = len(
            ablation_tester.db.aql.execute(
                f"""FOR doc IN {ablation_tester.TRUTH_COLLECTION}
                FILTER doc.collection == '{collection_name}'
                RETURN doc""",
            ).batch(),
        )

        debug_truth_counts[collection_name] = {
            "total_truth_records": query_count,
            f"{collection_name}_records": collection_truth_count,
        }
        logging.info(f"Debug: Collection {collection_name} has {collection_truth_count} truth records")

    # Collection combinations to test
    combinations = [
        ["AblationLocationActivity", "AblationMusicActivity"],
    ]

    # Task and Collaboration activity testing enabled:
    combinations.extend(
        [
            ["AblationLocationActivity", "AblationTaskActivity"],
            ["AblationTaskActivity", "AblationMusicActivity"],
            ["AblationLocationActivity", "AblationCollaborationActivity"],
            ["AblationMusicActivity", "AblationCollaborationActivity"],
            ["AblationTaskActivity", "AblationCollaborationActivity"],
        ],
    )

    # Storage and Media activity testing enabled:
    combinations.extend(
        [
            ["AblationStorageActivity", "AblationLocationActivity"],
            ["AblationStorageActivity", "AblationMusicActivity"],
            ["AblationStorageActivity", "AblationTaskActivity"],
            ["AblationStorageActivity", "AblationCollaborationActivity"],
            ["AblationMediaActivity", "AblationLocationActivity"],
            ["AblationMediaActivity", "AblationMusicActivity"],
            ["AblationMediaActivity", "AblationTaskActivity"],
            ["AblationMediaActivity", "AblationCollaborationActivity"],
            ["AblationStorageActivity", "AblationMediaActivity"],
        ],
    )

    for collection_pair in combinations:
        collection1, collection2 = collection_pair
        logging.info(f"Generating queries for {collection1} and {collection2} pair")

        # Templates for different collection combinations
        music_location_templates = [
            "Find songs by {artist} that I listened to at {location}",
            "Show me music I played while working at {location}",
            "What was I listening to when I was at {location} last week?",
            "Find tracks by {artist} from my {location} playlist",
            "Show me songs I added to my library while at {location}",
        ]

        task_location_templates = [
            "Find documents related to {task} that I worked on at {location}",
            "Show me files for the {task} project I edited at {location}",
            "What files did I work on for {task} while at {location}?",
            "Find presentations for {task} I prepared at {location}",
            "Show me spreadsheets related to {task} that I worked on at {location}",
        ]

        collaboration_location_templates = [
            "Find meetings that happened at {location}",
            "Show me all file shares that occurred at {location}",
            "What events were scheduled at {location} last week?",
            "Find all collaboration activities from {location}",
            "Show me all emails sent while at {location}",
        ]

        collaboration_music_templates = [
            "Find meeting recordings where we discussed {artist}",
            "Show me files shared during the {genre} playlist session",
            "What meetings happened while I was listening to {artist}?",
            "Find all emails about {genre} music festival",
            "Show me calendar events related to the {artist} concert",
        ]

        collaboration_task_templates = [
            "Find meetings related to the {task} project",
            "Show me files shared for the {task} task",
            "What emails were exchanged about {task}?",
            "Find all calendar events for the {task} deadline",
            "Show me code reviews for the {task} implementation",
        ]

        storage_location_templates = [
            "Find files I created at {location}",
            "Show me documents I accessed while at {location}",
            "What files did I modify at {location} last week?",
            "Find images I copied to my {location} folder",
            "Show me all files I deleted from my {location} directory",
        ]

        storage_music_templates = [
            "Find audio files related to {artist}",
            "Show me music files I downloaded while listening to {genre}",
            "What playlists did I create for {artist}?",
            "Find all mp3 files in my {genre} collection",
            "Show me album covers I downloaded for {artist}",
        ]

        storage_task_templates = [
            "Find files related to the {task} project",
            "Show me documents I modified for {task}",
            "What spreadsheets did I create for the {task} presentation?",
            "Find all backups of the {task} documents",
            "Show me files I shared as part of the {task}",
        ]

        storage_collaboration_templates = [
            "Find files shared during the {event} meeting",
            "Show me documents attached to emails about {project}",
            "What files were uploaded during the {team} collaboration session?",
            "Find all presentations used in the {event} meeting",
            "Show me files accessed by multiple team members during {project}",
        ]

        media_location_templates = [
            "Find videos I watched at {location}",
            "Show me photos I viewed while at {location}",
            "What games did I play at {location}?",
            "Find streaming content I accessed from {location}",
            "Show me media consumption patterns at {location}",
        ]

        media_music_templates = [
            "Find music videos by {artist}",
            "Show me concerts I watched for {genre} music",
            "What album documentaries did I watch about {artist}?",
            "Find all the game soundtracks composed by {artist}",
            "Show me videos from the {genre} festival",
        ]

        media_task_templates = [
            "Find tutorial videos related to my {task}",
            "Show me educational content I watched for {task} research",
            "What reference images did I use for the {task} design?",
            "Find all the screenshots I captured while working on {task}",
            "Show me videos I bookmarked for the {task} project",
        ]

        media_collaboration_templates = [
            "Find recorded meetings with the {team} team",
            "Show me video calls I had about the {project}",
            "What screen shares did I view during the {event} meeting?",
            "Find all the presentation recordings from {team} meetings",
            "Show me collaborative design sessions for the {project}",
        ]

        storage_media_templates = [
            "Find video files I downloaded recently",
            "Show me images I saved while watching {content}",
            "What media files were moved to my collection from {platform}?",
            "Find all screenshots I took while watching {content}",
            "Show me backups of my media library from {platform}",
        ]

        # Use the new integrated LLM query generator for diverse queries
        diverse_queries = []
        try:
            # Map collection names to activity types
            collection_to_activity_type = {
                "AblationMusicActivity": "music",
                "AblationLocationActivity": "location",
                "AblationTaskActivity": "task",
                "AblationCollaborationActivity": "collaboration",
                "AblationStorageActivity": "storage",
                "AblationMediaActivity": "media",
            }

            # Determine activity types from collections
            activity_types = [
                collection_to_activity_type.get(c, "location")
                for c in collection_pair
                if c in collection_to_activity_type
            ]

            # Make sure we have valid activity types
            if not activity_types:
                logging.error(f"CRITICAL: No valid activity types found for collections: {collection_pair}")
                logging.error("This is required for proper ablation testing - fix the collection mapping")
                sys.exit(1)  # Fail-stop immediately - no fallbacks

            # Generate queries for EACH activity type in the pair
            # This ensures we have collection-specific queries for proper evaluation
            generator = EnhancedQueryGenerator()
            diverse_queries = []

            for activity_type in activity_types:
                logging.info(f"Generating enhanced queries for activity type: {activity_type}")

                # Generate queries with proper fail-stop approach - NO fallbacks
                try:
                    activity_queries = generator.generate_enhanced_queries(
                        activity_type, count=count // len(activity_types) + 1,
                    )
                    logging.info(
                        f"Successfully generated {len(activity_queries)} diverse queries for {activity_type} using LLM",
                    )
                    diverse_queries.extend(activity_queries)
                except Exception as query_gen_error:
                    logging.exception(
                        f"CRITICAL: Failed to generate diverse queries using EnhancedQueryGenerator: {query_gen_error}",
                    )
                    logging.exception("This is required for proper ablation testing - fix the query generator")
                    sys.exit(1)  # Fail-stop immediately - no fallbacks

            # Ensure we have queries to work with - fail-stop approach
            if not diverse_queries:
                logging.error("CRITICAL: EnhancedQueryGenerator returned empty results")
                logging.error("This is required for proper ablation testing - fix the query generator")
                sys.exit(1)  # Fail-stop immediately - no fallbacks

            # Limit to requested count in case we generated more
            diverse_queries = diverse_queries[:count]
            logging.info(f"Final query count: {len(diverse_queries)} queries for combination {collection_pair}")

        except Exception as e:
            logging.exception(f"CRITICAL: Unexpected error in query generation setup: {e}")
            logging.exception("This is required for proper ablation testing - fix the query generator infrastructure")
            sys.exit(1)  # Fail-stop immediately - no fallbacks

        # Since we're using fail-stop approach, any LLM generation failure would have already terminated execution
        # But we'll keep these parameters available for reference if they're needed later

        # Parameters for query generation and entity reference
        locations = ["Home", "Office", "Coffee Shop", "Library", "Airport"]
        artists = ["Taylor Swift", "The Beatles", "Beyoncé", "Ed Sheeran", "Drake"]
        tasks = ["Quarterly Report", "Project Proposal", "Marketing Plan", "Budget Analysis", "Research Paper"]

        # Register consistent entities
        entity_manager.register_entity("location", "Home")
        entity_manager.register_entity("task", "Quarterly Report")
        entity_manager.register_entity("music", "Classical Piano")
        entity_manager.register_entity("artist", "Taylor Swift")

        # Generate queries for this combination
        for i in range(count):
            # Since we've implemented fail-stop for LLM query generation,
            # we can be confident that diverse_queries has enough entries
            if i < len(diverse_queries):
                query_text = diverse_queries[i]
            else:
                # This should never happen with our fail-stop approach, but just in case,
                # log an error and exit instead of falling back to a template-based approach
                logging.error(
                    f"CRITICAL: Not enough diverse queries generated. Expected {count}, got {len(diverse_queries)}",
                )
                sys.exit(1)

            # Debug: Check for actual Taylor Swift music data in the collection
            if "MusicActivity" in collection1 or "MusicActivity" in collection2:
                try:
                    music_collection = "AblationMusicActivity"
                    music_data = db_config.get_arangodb().aql.execute(
                        f"""
                        FOR doc IN {music_collection}
                        FILTER doc.artist == 'Taylor Swift'
                        RETURN doc
                        """,
                    )
                    music_count = len(music_data.batch())
                    logging.info(f"Debug: Found {music_count} actual Taylor Swift music activity records")
                    if music_count > 0:
                        sample = music_data.next()
                        logging.info(f"Debug: Sample Taylor Swift music activity: {sample.get('_key', 'unknown')}")
                except Exception as e:
                    logging.exception(f"Error checking music data: {e}")

            # Generate deterministic query ID
            query_id = generate_deterministic_uuid(f"query:{collection1}:{collection2}:{i}")

            # Generate matching entities for each collection
            matching_entities = {}

            for collection in collection_pair:
                # Query the database for real document keys instead of generating random ones
                try:
                    # Get 5 actual document keys from the collection
                    entity_ids = []
                    cursor = ablation_tester.db.aql.execute(
                        f"""
                        FOR doc IN {collection}
                        LIMIT 5
                        RETURN doc._key
                        """,
                    )

                    # Extract the document keys
                    for doc_key in cursor:
                        entity_ids.append(doc_key)

                    # If we didn't get enough documents, log an error
                    if len(entity_ids) < 5:
                        logging.warning(f"Only found {len(entity_ids)} documents in {collection}")

                    # Debug: Log entity IDs before storing
                    logging.info(f"Debug: Found {len(entity_ids)} actual document keys for {collection}")
                    if entity_ids:
                        logging.info(f"Debug: Sample entity ID: {entity_ids[0]}")

                    # Store truth data with composite key
                    store_success = ablation_tester.store_truth_data(query_id, collection, entity_ids)
                except Exception as e:
                    logging.exception(f"Error querying collection {collection}: {e}")
                    store_success = False
                if not store_success:
                    logging.error(f"Failed to store truth data for query {query_id} in collection {collection}")
                else:
                    logging.info(f"Debug: Successfully stored {len(entity_ids)} truth records for {collection}")

                    # Verify truth data was stored correctly
                    try:
                        retrieved_truth = ablation_tester.get_truth_data(query_id, collection)
                        logging.info(f"Debug: Retrieved {len(retrieved_truth)} truth entities for {collection}")
                        if len(retrieved_truth) != len(entity_ids):
                            logging.error(
                                f"Truth data mismatch: stored {len(entity_ids)}, retrieved {len(retrieved_truth)}",
                            )
                    except Exception as e:
                        logging.exception(f"Error verifying truth data: {e}")

                matching_entities[collection] = entity_ids

            # Add query to the list
            queries.append(
                {
                    "id": str(query_id),
                    "text": query_text,
                    "type": "cross_collection",
                    "collections": collection_pair,
                    "matching_entities": matching_entities,
                },
            )

            logging.info(f"Generated query {i+1}/{count} for {collection1} + {collection2}: '{query_text}'")

    return queries


def test_ablation_impact(ablation_tester: AblationTester, queries: list[dict[str, object]]):
    """Test the impact of ablating each collection on query results.

    Args:
        ablation_tester: The ablation tester to use
        queries: List of query dictionaries with metadata

    Returns:
        dict: Dictionary of impact metrics by collection and query
    """
    logging.info("Testing ablation impact...")

    impact_metrics = {}

    for query in queries:
        query_id = uuid.UUID(query["id"])
        query_text = query["text"]
        collections = query.get("collections", [])

        logging.info(f"Testing ablation impact for query: '{query_text}'")

        # Configure the ablation test
        config = AblationConfig(
            collections_to_ablate=collections,
            query_limit=100,
            include_metrics=True,
            include_execution_time=True,
            verbose=True,
        )

        # Run the ablation test
        results = ablation_tester.run_ablation_test(config, query_id, query_text)

        # Store the results - Fix for Pydantic V2 deprecation warning
        impact_metrics[str(query_id)] = {
            "query_text": query_text,
            "results": {k: r.model_dump() for k, r in results.items()},
        }

        logging.info(f"Completed ablation test for query {query_id}")

    return impact_metrics


def visualize_results(impact_metrics: dict[str, object], output_dir: str):
    """Create visualizations of ablation test results.

    Args:
        impact_metrics: Dictionary of impact metrics by query
        output_dir: Directory to save visualizations

    Returns:
        list: List of saved visualization file paths
    """
    logging.info("Generating visualizations...")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    saved_files = []

    # Extract data for visualization
    collections = set()
    impact_data = []

    for query_id, query_data in impact_metrics.items():
        query_text = query_data["query_text"]
        results = query_data["results"]

        for impact_key, metrics in results.items():
            if "_impact_on_" in impact_key:
                # Extract collection names from impact key
                src, dst = impact_key.split("_impact_on_")
                src = src.split("Ablation")[1].split("Activity")[0]
                dst = dst.split("Ablation")[1].split("Activity")[0]

                collections.add(src)
                collections.add(dst)

                # Extract metrics
                impact_data.append(
                    {
                        "query_id": query_id,
                        "query_text": query_text,
                        "source_collection": src,
                        "target_collection": dst,
                        "precision": metrics["precision"],
                        "recall": metrics["recall"],
                        "f1_score": metrics["f1_score"],
                        "impact": 1.0 - metrics["f1_score"],
                    },
                )

    if not impact_data:
        logging.warning("No impact data available for visualization")
        return []

    # Convert to DataFrame
    df = pd.DataFrame(impact_data)

    # 1. Impact Heatmap
    plt.figure(figsize=(10, 8))
    pivot_df = df.pivot_table(index="source_collection", columns="target_collection", values="impact", aggfunc="mean")

    sns.heatmap(pivot_df, annot=True, cmap="YlOrRd", vmin=0, vmax=1, fmt=".2f")
    plt.title("Impact of Ablating Source Collection on Target Collection")
    plt.tight_layout()

    heatmap_path = os.path.join(output_dir, "impact_heatmap.png")
    plt.savefig(heatmap_path)
    saved_files.append(heatmap_path)
    plt.close()

    # 2. Precision/Recall Scatter Plot
    plt.figure(figsize=(10, 8))
    sns.scatterplot(x="precision", y="recall", hue="source_collection", size="impact", sizes=(50, 200), data=df)
    plt.title("Precision vs. Recall by Collection")
    plt.xlim(0, 1)
    plt.ylim(0, 1)
    plt.tight_layout()

    scatter_path = os.path.join(output_dir, "precision_recall.png")
    plt.savefig(scatter_path)
    saved_files.append(scatter_path)
    plt.close()

    # 3. Impact by Collection Bar Chart
    plt.figure(figsize=(12, 8))
    impact_by_collection = df.groupby("source_collection")["impact"].mean().reset_index()
    sns.barplot(x="source_collection", y="impact", data=impact_by_collection)
    plt.title("Average Impact by Collection")
    plt.ylim(0, 1)
    plt.tight_layout()

    barchart_path = os.path.join(output_dir, "impact_by_collection.png")
    plt.savefig(barchart_path)
    saved_files.append(barchart_path)
    plt.close()

    # 4. F1 Score by Collection
    plt.figure(figsize=(12, 8))
    f1_by_collection = df.groupby("source_collection")["f1_score"].mean().reset_index()
    sns.barplot(x="source_collection", y="f1_score", data=f1_by_collection)
    plt.title("Average F1 Score by Collection")
    plt.ylim(0, 1)
    plt.tight_layout()

    f1_path = os.path.join(output_dir, "f1_by_collection.png")
    plt.savefig(f1_path)
    saved_files.append(f1_path)
    plt.close()

    logging.info(f"Saved {len(saved_files)} visualizations to {output_dir}")

    return saved_files


def generate_summary_report(impact_metrics: dict[str, object], output_dir: str):
    """Generate a summary report of ablation test results.

    Args:
        impact_metrics: Dictionary of impact metrics by query
        output_dir: Directory to save the report

    Returns:
        str: Path to the generated report
    """
    logging.info("Generating summary report...")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Extract data for the report
    collections = set()
    impact_data = []

    for query_id, query_data in impact_metrics.items():
        query_text = query_data["query_text"]
        results = query_data["results"]

        for impact_key, metrics in results.items():
            if "_impact_on_" in impact_key:
                # Extract collection names from impact key
                src, dst = impact_key.split("_impact_on_")
                src = src.split("Ablation")[1].split("Activity")[0]
                dst = dst.split("Ablation")[1].split("Activity")[0]

                collections.add(src)
                collections.add(dst)

                # Extract metrics
                impact_data.append(
                    {
                        "query_id": query_id,
                        "query_text": query_text,
                        "source_collection": src,
                        "target_collection": dst,
                        "precision": metrics["precision"],
                        "recall": metrics["recall"],
                        "f1_score": metrics["f1_score"],
                        "impact": 1.0 - metrics["f1_score"],
                        "true_positives": metrics["true_positives"],
                        "false_positives": metrics["false_positives"],
                        "false_negatives": metrics["false_negatives"],
                    },
                )

    if not impact_data:
        logging.warning("No impact data available for report")
        return ""

    # Convert to DataFrame for analysis
    df = pd.DataFrame(impact_data)

    # Generate report content
    report = []
    report.append("# Ablation Study Results Summary\n")
    report.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    report.append("## Overview\n")
    report.append(f"This report summarizes the results of ablation testing for {len(collections)} activity types: ")
    report.append(", ".join(sorted(collections)))
    report.append(".\n\n")
    report.append(f"A total of {len(impact_metrics)} test queries were evaluated, ")
    report.append(f"generating {len(impact_data)} impact measurements.\n")

    report.append("## Impact Summary\n")

    # Average impact by collection
    report.append("### Average Impact by Collection\n")
    report.append("Impact represents how much query performance degrades when a collection is removed.\n")
    report.append("Higher values indicate more important collections.\n\n")
    report.append("| Collection | Average Impact | Precision | Recall | F1 Score |\n")
    report.append("|------------|---------------|-----------|--------|----------|\n")

    collection_impacts = (
        df.groupby("source_collection")
        .agg({"impact": "mean", "precision": "mean", "recall": "mean", "f1_score": "mean"})
        .reset_index()
    )

    for _, row in collection_impacts.sort_values("impact", ascending=False).iterrows():
        report.append(f"| {row['source_collection']} | {row['impact']:.3f} | {row['precision']:.3f} | ")
        report.append(f"{row['recall']:.3f} | {row['f1_score']:.3f} |\n")

    report.append("\n## Cross-Collection Dependencies\n")
    report.append(
        "This table shows how ablating each collection (rows) affects queries targeting other collections (columns).\n\n",
    )

    # Create a pivot table for cross-collection impact
    pivot_df = df.pivot_table(index="source_collection", columns="target_collection", values="impact", aggfunc="mean")

    # Generate the table
    header = "| Source \\ Target | " + " | ".join(sorted(pivot_df.columns)) + " |\n"
    separator = "|" + "|".join(["-" * 15] * (len(pivot_df.columns) + 1)) + "|\n"
    report.append(header)
    report.append(separator)

    for idx, row in pivot_df.iterrows():
        line = f"| {idx} |"
        for col in sorted(pivot_df.columns):
            val = row.get(col, np.nan)
            if pd.isna(val):
                line += " N/A |"
            else:
                line += f" {val:.3f} |"
        report.append(line + "\n")

    report.append("\n## Query Analysis\n")
    report.append("### Most Affected Queries\n")
    report.append("| Query | Source Collection | Target Collection | Impact |\n")
    report.append("|-------|-------------------|-------------------|--------|\n")

    # Top 5 most affected queries
    top_impacts = df.sort_values("impact", ascending=False).head(5)
    for _, row in top_impacts.iterrows():
        truncated_query = row["query_text"][:50] + "..." if len(row["query_text"]) > 50 else row["query_text"]
        report.append(f"| {truncated_query} | {row['source_collection']} | ")
        report.append(f"{row['target_collection']} | {row['impact']:.3f} |\n")

    report.append("\n## Recommendations\n")
    high_impact_collections = collection_impacts[collection_impacts["impact"] > 0.5]["source_collection"].tolist()
    if high_impact_collections:
        report.append("Based on the ablation results, the following collections have high impact scores ")
        report.append("and should be prioritized in the search infrastructure:\n\n")
        for coll in high_impact_collections:
            report.append(
                f"- **{coll}**: Impact score {collection_impacts[collection_impacts['source_collection'] == coll]['impact'].values[0]:.3f}\n",
            )
    else:
        report.append("No collections showed particularly high impact scores (>0.5). ")
        report.append("This suggests that no single activity type is critical for overall search performance.\n")

    # Strongest cross-collection dependencies
    top_dependencies = (
        df[df["source_collection"] != df["target_collection"]].sort_values("impact", ascending=False).head(3)
    )
    if not top_dependencies.empty:
        report.append("\nThe strongest cross-collection dependencies were found between:\n\n")
        for _, row in top_dependencies.iterrows():
            report.append(
                f"- **{row['source_collection']}** → **{row['target_collection']}**: Impact {row['impact']:.3f}\n",
            )

        report.append("\nThese dependencies suggest that optimizing collection relationships could ")
        report.append("improve search performance by leveraging cross-collection information.\n")

    # Save the report
    report_path = os.path.join(output_dir, "ablation_summary.md")
    with open(report_path, "w") as f:
        f.write("".join(report))

    logging.info(f"Saved summary report to {report_path}")

    return report_path


def clear_existing_data():
    """Clear existing data from all activity collections."""
    logging.info("Clearing existing data...")

    collections = [
        "AblationLocationActivity",
        "AblationTaskActivity",
        "AblationMusicActivity",
        "AblationCollaborationActivity",
        "AblationStorageActivity",
        "AblationMediaActivity",
        "AblationTruthData",
    ]

    # Following fail-stop model - let exceptions propagate
    db_config = IndalekoDBConfig()
    db = db_config.get_arangodb()

    for collection_name in collections:
        if db.has_collection(collection_name):
            db.aql.execute(f"FOR doc IN {collection_name} REMOVE doc IN {collection_name}")
            logging.info(f"Cleared collection {collection_name}")

    logging.info("Data cleared successfully")


def main():
    """Run the comprehensive ablation test."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run comprehensive ablation tests")
    parser.add_argument("--count", type=int, default=100, help="Number of test records per collection")
    parser.add_argument("--queries", type=int, default=5, help="Number of test queries per collection combination")
    parser.add_argument("--clear", action="store_true", help="Clear existing data before running tests")
    parser.add_argument("--visualize", action="store_true", help="Generate visualizations")
    parser.add_argument("--output-dir", type=str, help="Output directory for results")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    # Set up logging
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)

    # Create output directory with timestamp if not specified
    output_dir = args.output_dir
    if not output_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"ablation_results_{timestamp}"

    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"Starting comprehensive ablation tests, results will be saved to {output_dir}")

    # Following fail-stop model: no try-except here
    # This allows errors to propagate and cause immediate failure

    # Create cleanup variable for finally block
    ablation_tester = None

    # Clear existing data if requested
    if args.clear:
        clear_existing_data()

    # Initialize entity manager for consistent entity references
    entity_manager = NamedEntityManager()

    # Initialize ablation tester
    ablation_tester = AblationTester()

    # Initialize global db config for debugging
    global db_config
    db_config = IndalekoDBConfig()

    # Set up activity data providers
    # Each provider is a tuple: (name, collector_class, recorder_class)
    activity_data_providers = [
        TestDataComponents(
            name="Location",
            collector=LocationActivityCollector,
            recorder=LocationActivityRecorder,
            hash_name="location",
            hash_property_name="location_name",
        ),
        TestDataComponents(
            name="Music",
            collector=MusicActivityCollector,
            recorder=MusicActivityRecorder,
            hash_name="music",
            hash_property_name="artist",
        ),
        TestDataComponents(
            name="Task",
            collector=TaskActivityCollector,
            recorder=TaskActivityRecorder,
            hash_name="task",
            hash_property_name="task_type",
        ),
        TestDataComponents(
            name="Collaboration",
            collector=CollaborationActivityCollector,
            recorder=CollaborationActivityRecorder,
            hash_name="collaboration",
            hash_property_name="event_title",
        ),
        TestDataComponents(
            name="Storage",
            collector=StorageActivityCollector,
            recorder=StorageActivityRecorder,
            hash_name="storage",
            hash_property_name="file_type",
        ),
        TestDataComponents(
            name="Media",
            collector=MediaActivityCollector,
            recorder=MediaActivityRecorder,
            hash_name="media",
            hash_property_name="media_type",
        ),
    ]

    # Generate test data using the providers
    test_data = generate_test_data(entity_manager, activity_data_providers, count=args.count)

    if not test_data:
        logger.error("Failed to generate test data")
        sys.exit(1)

    # Generate cross-collection test queries
    # This must happen BEFORE data sanity check, since it creates the truth data
    queries = generate_cross_collection_queries(entity_manager, ablation_tester, count=args.queries)
    if not queries:
        logger.error("Failed to generate test queries")
        sys.exit(1)

    # Run data sanity check AFTER truth data has been generated
    logger.info("Running data sanity check...")
    checker = DataSanityChecker(fail_fast=True)  # Using fail_fast=True for fail-stop model
    sanity_check_passed = checker.run_all_checks()
    if not sanity_check_passed:
        logger.error("Data sanity check failed")
        sys.exit(1)

    # Test ablation impact
    impact_metrics = test_ablation_impact(ablation_tester, queries)

    # Save raw metrics with additional debugging info
    metrics_path = os.path.join(output_dir, "impact_metrics.json")
    with open(metrics_path, "w") as f:
        # Convert UUID objects to strings to prevent JSON serialization errors
        serializable_metrics = json.loads(
            json.dumps(impact_metrics, default=lambda o: str(o) if isinstance(o, uuid.UUID) else o),
        )

        # Add truth data to help with debugging
        for query_id, query_data in serializable_metrics.items():
            # Add debug info to each result
            for impact_key, result in query_data["results"].items():
                # If AQL query exists, make sure it's in the output
                if "aql_query" in result:
                    # Remove whitespace for cleaner output
                    result["aql_query"] = result["aql_query"].strip()

                # Extract collection from impact key
                if "_impact_on_" in impact_key:
                    _, target_collection = impact_key.split("_impact_on_")

                    # Add truth data info
                    try:
                        truth_data = ablation_tester.get_truth_data(uuid.UUID(query_id), target_collection)
                        result["truth_data"] = list(truth_data)
                        result["truth_data_count"] = len(truth_data)
                    except Exception as e:
                        logger.error(f"Error getting truth data for query {query_id}: {e}")

        json.dump(serializable_metrics, f, indent=2)

    logger.info(f"Saved raw metrics to {metrics_path}")

    # Generate visualizations if requested
    if args.visualize:
        visualize_results(impact_metrics, output_dir)

    # Generate summary report
    report_path = generate_summary_report(impact_metrics, output_dir)

    if report_path:
        logger.info(f"Test completed successfully, see {report_path} for summary")
    else:
        logger.warning("Test completed but no report was generated")

    # Ensure cleanup is run regardless of success/failure
    if ablation_tester:
        ablation_tester.cleanup()


if __name__ == "__main__":
    main()
