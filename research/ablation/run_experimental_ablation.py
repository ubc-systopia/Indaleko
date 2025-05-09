#!/usr/bin/env python3
"""
Comprehensive experimental design for ablation testing with control/test group methodology.

This script implements a rigorous experimental approach for ablation studies:
1. Divides activity types into control (4) and test (2) groups
2. Runs tests across all 15 possible ablation combinations
3. Generates multiple queries per combination
4. Runs crossover experiments by flipping control/test groups
5. Analyzes results with proper statistical methods

Usage:
    python run_experimental_ablation.py [--iterations N] [--seed SEED]
"""

import argparse
import itertools
import logging
import random
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


class ExperimentalAblationRunner:
    """
    Implements a comprehensive experimental design for ablation studies.

    This class manages the entire experimental process:
    1. Divides activity types into control and test groups
    2. Runs tests with systematic ablation of collections
    3. Performs crossover experiments
    4. Analyzes and reports results with statistical validity
    """

    def __init__(
        self,
        iterations: int = 3,
        queries_per_combination: int = 5,
        seed_value: int = 42,
        output_dir: str | None = None,
        use_enhanced_query_generator: bool = True,
    ):
        """
        Initialize the experimental ablation runner.

        Args:
            iterations: Number of experimental iterations to run
            queries_per_combination: Number of queries to generate for each ablation combination
            seed_value: Random seed for reproducibility
            output_dir: Directory to save results
            use_enhanced_query_generator: Whether to use the enhanced query generator
        """
        self.iterations = iterations
        self.queries_per_combination = queries_per_combination
        self.seed_value = seed_value
        random.seed(seed_value)

        # Set up logging
        self.logger = logging.getLogger(__name__)

        # Set up output directory
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.output_dir = output_dir or f"ablation_results_{timestamp}"
        Path(self.output_dir).mkdir(exist_ok=True, parents=True)

        # Connect to database
        self.db_config = IndalekoDBConfig()
        db = self.db_config.get_arangodb()
        self.ablation_db = AblationDatabase(db_config=self.db_config)

        # Initialize LLM query generator
        if use_enhanced_query_generator:
            self.query_generator = EnhancedQueryGenerator()
        else:
            self.query_generator = LLMQueryGenerator()

        # Initialize results manager
        self.results_manager = AblationResultsManager(output_dir=self.output_dir)

        # Define all activity data providers
        self.activity_providers = [
            ActivityDataProvider("Music", MusicActivityCollector, MusicActivityRecorder),
            ActivityDataProvider("Location", LocationActivityCollector, LocationActivityRecorder),
            ActivityDataProvider("Task", TaskActivityCollector, TaskActivityRecorder),
            ActivityDataProvider("Collaboration", CollaborationActivityCollector, CollaborationActivityRecorder),
            ActivityDataProvider("Storage", StorageActivityCollector, StorageActivityRecorder),
            ActivityDataProvider("Media", MediaActivityCollector, MediaActivityRecorder),
        ]

    def generate_experimental_groups(self) -> list[tuple[list[str], list[str]]]:
        """
        Generate experimental groups for multiple iterations.

        Returns:
            List of (control_group, test_group) tuples for each iteration
        """
        all_groups = []
        provider_names = [provider.name for provider in self.activity_providers]

        # For the specified number of iterations, create different control/test group splits
        for i in range(self.iterations):
            # Shuffle the providers to get different combinations
            shuffled_providers = provider_names.copy()
            random.shuffle(shuffled_providers)

            # Split into control (4) and test (2) groups
            control_group = shuffled_providers[:4]
            test_group = shuffled_providers[4:]

            # Add the group split to our list
            all_groups.append((control_group, test_group))

            # For crossover design, also add the flipped groups
            all_groups.append((test_group, control_group))

        return all_groups

    def generate_ablation_combinations(self, group: list[str]) -> list[set[str]]:
        """
        Generate all possible ablation combinations for a group.

        Args:
            group: List of activity type names in the group

        Returns:
            List of sets, where each set contains the collections to ablate
        """
        combinations = []

        # Generate all possible combinations of collections to ablate
        # Start with 1 (ablate just one collection) up to len(group)-1
        for r in range(1, len(group)):
            for combo in itertools.combinations(group, r):
                combinations.append(set(combo))

        return combinations

    def run_experiment(self):
        """
        Run the complete experimental ablation study.

        This method:
        1. Generates experimental groups
        2. For each group configuration:
            a. Generates synthetic data
            b. Establishes baseline performance
            c. Runs ablation tests for all combinations
            d. Records and analyzes results
        """
        self.logger.info("Starting experimental ablation study")

        # Generate all experimental groups (control/test pairs)
        experimental_groups = self.generate_experimental_groups()
        self.logger.info(f"Generated {len(experimental_groups)} experimental group configurations")

        # Initialize entity manager (for collectors that need it)
        entity_manager = {}

        # For each group configuration (iteration + crossover)
        for iteration, (control_group, test_group) in enumerate(experimental_groups):
            self.logger.info(f"Running iteration {iteration//2 + 1}" + f" {'(crossover)' if iteration % 2 else ''}")
            self.logger.info(f"Control group: {control_group}")
            self.logger.info(f"Test group: {test_group}")

            # Get provider objects for each group
            control_providers = [p for p in self.activity_providers if p.name in control_group]
            test_providers = [p for p in self.activity_providers if p.name in test_group]
            all_providers = control_providers + test_providers

            # Save experiment configuration
            self.results_manager.record_experiment_configuration(
                iteration_id=f"{iteration//2 + 1}{'c' if iteration % 2 else ''}",
                control_group=control_group,
                test_group=test_group,
            )

            # Initialize collections and generate synthetic data
            self.logger.info("Initializing collections and generating synthetic data")
            for provider in all_providers:
                # Initialize collector based on whether it supports entity_manager
                if provider.name in ["Location", "Music", "Task", "Collaboration"]:
                    # These collectors support entity_manager
                    collector = provider.collector(entity_manager=entity_manager, seed_value=self.seed_value)
                else:
                    # Storage and Media collectors only support seed_value
                    collector = provider.collector(seed_value=self.seed_value)

                # Initialize recorder
                recorder = provider.recorder()

                # Generate and record synthetic data
                self.logger.info(f"Generating synthetic data for {provider.name} activity")
                collection_data = collector.collect()
                recorder.record(collection_data)

                # Generate truth data
                self.logger.info(f"Generating truth data for {provider.name} activity")
                truth_data = collector.generate_truth_data()
                recorder.record_truth_data(truth_data)

            # Generate queries for the test group (the group we'll be testing ablation on)
            self.logger.info("Generating test queries for the test group")
            test_queries = []
            for provider in test_providers:
                # Generate specified number of queries for each test provider
                for i in range(self.queries_per_combination):
                    query = self.query_generator.generate_query(
                        activity_type=provider.name,
                        query_index=i,
                        seed=self.seed_value + i,
                    )
                    test_queries.append((provider.name, query))

            # Save generated queries
            with open(f"{self.output_dir}/test_queries_iteration_{iteration}.txt", "w") as f:
                for provider_name, query in test_queries:
                    f.write(f"{provider_name}: {query}\n")

            # Initialize ablation tester
            tester = AblationTester(
                db_config=self.db_config,
                ablation_db=self.ablation_db,
                results_manager=self.results_manager,
                query_generator=self.query_generator,
            )

            # Establish baseline performance (no ablation)
            self.logger.info("Establishing baseline performance (no ablation)")
            baseline_results = tester.run_baseline_test(queries=test_queries, experiment_id=f"iteration_{iteration}")

            # Generate ablation combinations for the test group
            ablation_combinations = self.generate_ablation_combinations(test_group)
            self.logger.info(f"Generated {len(ablation_combinations)} ablation combinations")

            # Run ablation tests for each combination
            for ablate_set in ablation_combinations:
                self.logger.info(f"Testing ablation of: {ablate_set}")

                # Collections to ablate
                ablate_collections = [
                    getattr(IndalekoDBCollections, f"Indaleko_Ablation_{name}_Activity_Collection")
                    for name in ablate_set
                ]

                # Run ablation test
                tester.run_ablation_test(
                    ablate_collections=ablate_collections,
                    queries=test_queries,
                    experiment_id=f"iteration_{iteration}",
                    ablation_id=f"{'_'.join(sorted(ablate_set))}",
                )

            # Restore collections for the next iteration
            self.logger.info("Restoring collections for next iteration")
            tester.restore_collections()

        # Generate final report
        self.logger.info("Generating final analysis and visualizations")
        self.results_manager.generate_report()

        self.logger.info(f"Experiment completed. Results saved to {self.output_dir}")
        return True


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run experimental ablation study")
    parser.add_argument("--iterations", type=int, default=3, help="Number of iterations to run (default: 3)")
    parser.add_argument("--queries", type=int, default=5, help="Number of queries per combination (default: 5)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save results (default: timestamped directory)",
    )
    parser.add_argument(
        "--basic-generator",
        action="store_true",
        help="Use basic LLM query generator instead of enhanced version",
    )
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Configure logging
    configure_logging()

    # Run the experiment
    try:
        runner = ExperimentalAblationRunner(
            iterations=args.iterations,
            queries_per_combination=args.queries,
            seed_value=args.seed,
            output_dir=args.output_dir,
            use_enhanced_query_generator=not args.basic_generator,
        )
        success = runner.run_experiment()

        if not success:
            logging.error("Experiment failed")
            sys.exit(1)

    except Exception as e:
        logging.exception(f"Fatal error during experiment: {e}")
        sys.exit(1)

    logging.info("Experiment completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
