#!/usr/bin/env python3
"""Handler Mixin for the Enhanced Data Generator tool.

This mixin defines the command-line arguments and execution behavior for
the Enhanced Data Generator tool.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

from utils.cli.handlermixin import IndalekoHandlermixin


class DataGeneratorHandlerMixin(IndalekoHandlermixin):
    """Handler mixin for the Enhanced Data Generator CLI tool."""

    @staticmethod
    def get_pre_parser() -> argparse.ArgumentParser | None:
        """Define initial arguments (before the main parser)."""
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument(
            "--config",
            type=str,
            help="Path to configuration file",
            default="default",
        )
        parser.add_argument(
            "--headless",
            action="store_true",
            help="Run in headless mode (no interactive prompts)",
        )
        return parser

    @staticmethod
    def setup_logging(args: argparse.Namespace, **kwargs: Dict[str, Any]) -> None:
        """Configure logging based on parsed args."""
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
            logging.debug("Debug logging enabled")
        else:
            logging.getLogger().setLevel(logging.INFO)

    @staticmethod
    def load_configuration(kwargs: Dict[str, Any]) -> None:
        """Load tool-specific configuration from file or defaults."""
        args = kwargs.get("args")
        if not args:
            return

        config_path = args.config
        if config_path == "default":
            # Use default config bundled with the tool
            tool_dir = Path(__file__).parent
            config_path = tool_dir / "config" / "default.json"
        elif not os.path.isabs(config_path):
            # Convert relative path to absolute
            config_path = Path(os.getcwd()) / config_path

        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                kwargs["config"] = config
                logging.info("Loaded configuration from %s", config_path)
        except FileNotFoundError:
            logging.error("Configuration file not found: %s", config_path)
            if args.headless:
                sys.exit(1)
            kwargs["config"] = {"metadata": {"total_records": 1000, "truth_records": 10}}
            logging.warning("Using minimal default configuration")
        except json.JSONDecodeError:
            logging.error("Invalid JSON in configuration file: %s", config_path)
            if args.headless:
                sys.exit(1)
            kwargs["config"] = {"metadata": {"total_records": 1000, "truth_records": 10}}
            logging.warning("Using minimal default configuration")

    @staticmethod
    def add_parameters(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        """Add tool-specific CLI arguments to the parser."""
        # Core functionality options
        generator_group = parser.add_argument_group("Generator Options")
        generator_group.add_argument(
            "--metadata-types",
            type=str,
            help="Comma-separated list of metadata types to generate (default: all)",
            default="storage,semantic,activity,machine_config",
        )
        generator_group.add_argument(
            "--scale-factor",
            type=float,
            help="Scale factor for total number of records (multiplies config value)",
            default=1.0,
        )
        generator_group.add_argument(
            "--truth-factor",
            type=float,
            help="Scale factor for truth records (ratio of total records)",
            default=None,
        )
        generator_group.add_argument(
            "--model-based",
            action="store_true",
            help="Use model-based generation (uses actual data models)",
            default=True,
        )

        # Model-based generator options
        model_group = parser.add_argument_group("Model-Based Generator Options")
        model_group.add_argument(
            "--relationship-strategy",
            type=str,
            choices=["balanced", "storage_semantic_focused", "activity_focused"],
            help="Strategy for relationship generation pattern",
            default="balanced",
        )
        model_group.add_argument(
            "--activity-focus",
            type=str,
            choices=["balanced", "recent", "popular", "diverse"],
            help="Focus strategy for activity generation",
            default="balanced",
        )
        model_group.add_argument(
            "--activity-sequences",
            action="store_true",
            help="Generate activity sequences (patterns of related activities)",
            default=False,
        )
        model_group.add_argument(
            "--activity-sequence-count",
            type=int,
            help="Number of activity sequences to generate",
            default=None,
        )
        model_group.add_argument(
            "--content-extraction",
            type=float,
            help="Percentage of semantic objects with extracted content (0.0-1.0)",
            default=0.7,
        )
        model_group.add_argument(
            "--mime-types",
            type=str,
            help="Comma-separated list of mime types to prioritize (e.g. 'application/pdf,image/jpeg')",
            default=None,
        )

        # Testing options
        testing_group = parser.add_argument_group("Testing Options")
        testing_group.add_argument(
            "--run-tests",
            action="store_true",
            help="Run tests after generating data",
        )
        testing_group.add_argument(
            "--report-path",
            type=str,
            help="Path to save test reports",
            default="./test_results",
        )
        testing_group.add_argument(
            "--report-format",
            type=str,
            choices=["json", "csv", "md", "html", "pdf"],
            help="Format for test reports",
            default="md",
        )

        # Advanced options
        advanced_group = parser.add_argument_group("Advanced Options")
        advanced_group.add_argument(
            "--clear-collections",
            action="store_true",
            help="Clear existing collections before generating new data",
        )
        advanced_group.add_argument(
            "--seed",
            type=int,
            help="Random seed for reproducible data generation",
            default=None,
        )
        advanced_group.add_argument(
            "--export-statistics",
            type=str,
            help="Export generation statistics to a file",
            default=None,
        )
        advanced_group.add_argument(
            "--export-truth",
            type=str,
            help="Export truth dataset to a file",
            default=None,
        )
        advanced_group.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Enable verbose logging",
        )

        return parser

    @staticmethod
    def performance_configuration(kwargs: Dict[str, Any]) -> bool:
        """Configure performance recording; return False to skip."""
        # Enable performance recording
        return True

    @staticmethod
    def run(kwargs: Dict[str, Any]) -> None:
        """Main entry point for CLI execution."""
        args = kwargs.get("args")
        config = kwargs.get("config", {})

        logging.info("Running %s with args %s", DataGeneratorHandlerMixin.__name__, args)
        logging.info("Loaded configuration with %d total records and %d truth records",
                    config.get("metadata", {}).get("total_records", 0),
                    config.get("metadata", {}).get("truth_records", 0))

        # Process command-line arguments
        metadata_types = [t.strip() for t in args.metadata_types.split(",")]
        scale_factor = args.scale_factor

        # Update configuration based on CLI arguments
        total_records = int(config.get("metadata", {}).get("total_records", 1000) * scale_factor)

        truth_factor = args.truth_factor
        if truth_factor is not None:
            truth_records = int(total_records * truth_factor)
        else:
            truth_records = config.get("metadata", {}).get("truth_records", 10)

        # Set up model-based generation configuration
        model_based = args.model_based

        # Update scenario configuration with CLI arguments
        scenario_config = config.get("default_scenario", {})

        # Add relationships strategy from CLI arguments
        if args.relationship_strategy:
            scenario_config["relationship_strategy"] = args.relationship_strategy

        # Add activity focus from CLI arguments
        if args.activity_focus:
            scenario_config["activity_focus"] = args.activity_focus

        # Configure activity sequences
        if args.activity_sequences:
            scenario_config["activity_sequences"] = True
            if args.activity_sequence_count:
                scenario_config["activity_sequence_count"] = args.activity_sequence_count

        # Configure content extraction
        if args.content_extraction is not None:
            if "semantic_criteria" not in scenario_config:
                scenario_config["semantic_criteria"] = {}
            if "content_extraction" not in scenario_config["semantic_criteria"]:
                scenario_config["semantic_criteria"]["content_extraction"] = {}
            scenario_config["semantic_criteria"]["content_extraction"]["extract_percentage"] = args.content_extraction

        # Configure MIME types
        if args.mime_types:
            mime_types = [m.strip() for m in args.mime_types.split(",")]
            if "semantic_criteria" not in scenario_config:
                scenario_config["semantic_criteria"] = {}
            # Create a distribution that prioritizes the specified MIME types
            mime_distribution = {}
            remaining_weight = 1.0
            weight_per_type = min(0.15, 0.7 / len(mime_types))  # At most 15% per type, 70% total

            for mime_type in mime_types:
                mime_distribution[mime_type] = weight_per_type
                remaining_weight -= weight_per_type

            # Add some default MIME types with the remaining weight
            default_types = {
                "text/plain": 0.1,
                "application/pdf": 0.15,
                "image/jpeg": 0.15,
                "video/mp4": 0.05,
                "audio/mpeg": 0.05
            }

            # Add default types that aren't already specified
            for mime_type, weight in default_types.items():
                if mime_type not in mime_distribution and remaining_weight > 0:
                    adjusted_weight = min(weight, remaining_weight)
                    mime_distribution[mime_type] = adjusted_weight
                    remaining_weight -= adjusted_weight

            scenario_config["semantic_criteria"]["mime_type_distribution"] = mime_distribution

        # Update configuration with scenario settings
        config["default_scenario"] = scenario_config

        # Calculate record counts for each domain
        logging.info(f"Generating dataset with {total_records} total records")

        storage_count = total_records
        semantic_count = int(storage_count * 0.8) if "semantic" in metadata_types else 0
        activity_count = int(storage_count * 0.5) if "activity" in metadata_types else 0
        relationship_count = int(storage_count * 1.5) if "relationship" in metadata_types else 0
        machine_config_count = 5 if "machine_config" in metadata_types else 0

        # Update scenario configuration with counts
        scenario_config["storage_count"] = storage_count
        scenario_config["semantic_count"] = semantic_count
        scenario_config["activity_count"] = activity_count
        scenario_config["relationship_count"] = relationship_count
        scenario_config["machine_config_count"] = machine_config_count

        # Set up truth record counts
        scenario_config["storage_truth_count"] = truth_records
        scenario_config["semantic_truth_count"] = truth_records if "semantic" in metadata_types else 0
        scenario_config["activity_truth_count"] = truth_records if "activity" in metadata_types else 0
        scenario_config["machine_config_truth_count"] = min(3, truth_records) if "machine_config" in metadata_types else 0

        # Initialize the controller
        from agents.data_gen.core.controller import GenerationController

        logging.info("Initializing generation controller")
        controller = GenerationController(config)

        # Generate the dataset
        logging.info("Generating dataset")
        stats = controller.generate_dataset()

        # Generate truth dataset if testing is enabled
        if args.run_tests:
            logging.info("Generating truth dataset for testing")
            truth_stats = controller.generate_truth_dataset()

            # Export truth dataset if requested
            if args.export_truth:
                controller.export_truth_dataset(args.export_truth)

            # Run tests on the generated data
            logging.info("Running tests on generated data")
            try:
                from testing.test_runner import ModelBasedTestRunner

                # Create report directory
                report_path = Path(args.report_path)
                os.makedirs(report_path, exist_ok=True)

                # Initialize test runner
                test_runner = ModelBasedTestRunner(config, controller.truth_records)

                # Run tests
                test_results = test_runner.run_tests()

                # Generate report
                report_file = report_path / f"test_report.{args.report_format}"
                test_runner.save_results(report_path / "test_results.json")
                test_runner.generate_report(report_file, args.report_format)

                # Log summary
                summary = test_results.get("summary", {})
                if summary:
                    logging.info("Test Results Summary:")
                    logging.info(f"  Total Tests: {summary.get('total_tests', 0)}")
                    logging.info(f"  Passed Tests: {summary.get('passed_tests', 0)}")
                    logging.info(f"  Failed Tests: {summary.get('failed_tests', 0)}")
                    logging.info(f"  Average Precision: {summary.get('avg_precision', 0)}%")
                    logging.info(f"  Average Recall: {summary.get('avg_recall', 0)}%")
                    logging.info(f"  Average F1 Score: {summary.get('avg_f1_score', 0)}%")

                logging.info(f"Test report saved to {report_file}")

            except ImportError as e:
                logging.error(f"Error importing test runner: {e}")
                logging.error("Tests cannot be run")
            except Exception as e:
                logging.error(f"Error running tests: {e}", exc_info=True)

        # Export statistics if requested
        if args.export_statistics:
            controller.export_statistics(args.export_statistics)

        # Output summary statistics
        logging.info("Generation complete!")
        logging.info(f"Generated {stats['counts']['total']} total records")
        for category, count in stats["counts"].items():
            if category != "total":
                logging.info(f"  - {category}: {count} records")

        logging.info(f"Elapsed time: {stats['elapsed_time']:.2f} seconds")

    @staticmethod
    def performance_recording(kwargs: Dict[str, Any]) -> None:
        """Hook for recording performance after run()."""
        # Record total execution time and other metrics
        pass

    @staticmethod
    def cleanup(kwargs: Dict[str, Any]) -> None:
        """Cleanup hook (e.g., close resources)."""
        logging.info("Data generator execution completed")
