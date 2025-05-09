#!/usr/bin/env python3
"""
Minimal experimental ablation runner for testing.

This script runs a minimal version of the experimental ablation framework:
1. Uses a predefined control/test group split
2. Runs a small number of queries
3. Tests only one ablation combination
4. Useful for validating the implementation before running full experiments
"""

import argparse
import logging
import sys
import time
from pathlib import Path

from db.db_collections import IndalekoDBCollections
from db.db_config import IndalekoDBConfig
from research.ablation.ablation_tester import AblationTester
from research.ablation.collectors.collaboration_collector import (
    CollaborationActivityCollector,
)
from research.ablation.collectors.location_collector import LocationActivityCollector
from research.ablation.collectors.media_collector import MediaActivityCollector
from research.ablation.collectors.music_collector import MusicActivityCollector
from research.ablation.collectors.storage_collector import StorageActivityCollector
from research.ablation.collectors.task_collector import TaskActivityCollector
from research.ablation.db.database import AblationDatabase
from research.ablation.models.ablation_results import AblationResultsManager
from research.ablation.query.enhanced.enhanced_query_generator import (
    EnhancedQueryGenerator,
)
from research.ablation.query.llm_query_generator import LLMQueryGenerator
from research.ablation.recorders.collaboration_recorder import (
    CollaborationActivityRecorder,
)
from research.ablation.recorders.location_recorder import LocationActivityRecorder
from research.ablation.recorders.media_recorder import MediaActivityRecorder
from research.ablation.recorders.music_recorder import MusicActivityRecorder
from research.ablation.recorders.storage_recorder import StorageActivityRecorder
from research.ablation.recorders.task_recorder import TaskActivityRecorder
from utils.i_logging import configure_logging


class ActivityDataProvider:
    """Provider for activity data sources."""

    def __init__(self, name, collector, recorder):
        self.name = name
        self.collector = collector
        self.recorder = recorder


def run_minimal_experiment(use_enhanced_generator: bool = True):
    """
    Run a minimal experiment to test the framework.

    Args:
        use_enhanced_generator: Whether to use the enhanced query generator
    """
    # Configure logging
    logger = logging.getLogger(__name__)
    logger.info("Starting minimal ablation experiment")

    # Set up output directory
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = f"ablation_minimal_{timestamp}"
    Path(output_dir).mkdir(exist_ok=True, parents=True)

    # Connect to database
    db_config = IndalekoDBConfig()
    db = db_config.get_arangodb()
    ablation_db = AblationDatabase(db_config=db_config)

    # Initialize LLM query generator
    if use_enhanced_generator:
        query_generator = EnhancedQueryGenerator()
    else:
        query_generator = LLMQueryGenerator()

    # Initialize results manager
    results_manager = AblationResultsManager(output_dir=output_dir)

    # Define activity data providers
    activity_providers = [
        ActivityDataProvider("Music", MusicActivityCollector, MusicActivityRecorder),
        ActivityDataProvider("Location", LocationActivityCollector, LocationActivityRecorder),
        ActivityDataProvider("Task", TaskActivityCollector, TaskActivityRecorder),
        ActivityDataProvider("Collaboration", CollaborationActivityCollector, CollaborationActivityRecorder),
        ActivityDataProvider("Storage", StorageActivityCollector, StorageActivityRecorder),
        ActivityDataProvider("Media", MediaActivityCollector, MediaActivityRecorder),
    ]

    # Define control and test groups
    # Control: Music, Location, Task, Collaboration
    # Test: Storage, Media
    control_group = ["Music", "Location", "Task", "Collaboration"]
    test_group = ["Storage", "Media"]

    # Save experiment configuration
    results_manager.record_experiment_configuration(
        iteration_id="minimal", control_group=control_group, test_group=test_group,
    )

    logger.info(f"Control group: {control_group}")
    logger.info(f"Test group: {test_group}")

    # Initialize entity manager (for collectors that need it)
    entity_manager = {}

    # For each activity type, generate and record data
    for provider in activity_providers:
        # Initialize collector based on whether it supports entity_manager
        if provider.name in ["Location", "Music", "Task", "Collaboration"]:
            # These collectors support entity_manager
            collector = provider.collector(entity_manager=entity_manager, seed_value=42)
        else:
            # Storage and Media collectors only support seed_value
            collector = provider.collector(seed_value=42)

        # Initialize recorder
        recorder = provider.recorder()

        # Generate and record synthetic data
        logger.info(f"Generating synthetic data for {provider.name} activity")
        collection_data = collector.collect()
        recorder.record(collection_data)

        # Generate truth data
        logger.info(f"Generating truth data for {provider.name} activity")
        truth_data = collector.generate_truth_data()
        recorder.record_truth_data(truth_data)

    # Generate queries for test group (Storage, Media)
    test_queries = []
    for provider_name in test_group:
        provider = next(p for p in activity_providers if p.name == provider_name)

        # Generate 2 queries for each test provider
        for i in range(2):
            query = query_generator.generate_query(activity_type=provider.name, query_index=i, seed=42 + i)
            test_queries.append((provider.name, query))

    # Save generated queries
    with open(f"{output_dir}/test_queries.txt", "w") as f:
        for provider_name, query in test_queries:
            f.write(f"{provider_name}: {query}\n")

    # Initialize ablation tester
    tester = AblationTester(
        db_config=db_config, ablation_db=ablation_db, results_manager=results_manager, query_generator=query_generator,
    )

    # Establish baseline performance (no ablation)
    logger.info("Establishing baseline performance (no ablation)")
    baseline_results = tester.run_baseline_test(queries=test_queries, experiment_id="minimal")

    # Test ablation of one collection
    for collection_name in test_group:
        logger.info(f"Testing ablation of: {collection_name}")

        # Collection to ablate
        ablate_collection = getattr(IndalekoDBCollections, f"Indaleko_Ablation_{collection_name}_Activity_Collection")

        # Run ablation test
        tester.run_ablation_test(
            ablate_collections=[ablate_collection],
            queries=test_queries,
            experiment_id="minimal",
            ablation_id=collection_name,
        )

    # Generate report
    logger.info("Generating report")
    results_manager.generate_report()

    # Restore collections
    logger.info("Restoring collections")
    tester.restore_collections()

    logger.info(f"Minimal experiment completed. Results saved to {output_dir}")
    return True


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run minimal ablation experiment")
    parser.add_argument(
        "--basic-generator", action="store_true", help="Use basic LLM query generator instead of enhanced version",
    )
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Configure logging
    configure_logging()

    try:
        success = run_minimal_experiment(use_enhanced_generator=not args.basic_generator)

        if not success:
            logging.error("Minimal experiment failed")
            sys.exit(1)

    except Exception as e:
        logging.exception(f"Fatal error during minimal experiment: {e}")
        sys.exit(1)

    logging.info("Minimal experiment completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
