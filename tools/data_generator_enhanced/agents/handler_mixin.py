#!/usr/bin/env python3
"""Handler Mixin for the Enhanced Data Generator CLI tool.

This mixin defines the data generator's CLI arguments and handles execution.
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from utils.cli.handlermixin import IndalekoHandlermixin

# Local imports that will be available once the file is in the correct location
try:
    from data_gen.core.controller import GenerationController
    from data_gen.config.defaults import DEFAULT_CONFIG
    from data_gen.config.scenarios import SCENARIOS
except ImportError:
    # We'll need to handle this in load_configuration
    pass


class DataGeneratorHandlerMixin(IndalekoHandlermixin):
    """Handler Mixin for the Enhanced Data Generator CLI."""

    @staticmethod
    def get_pre_parser() -> Optional[argparse.ArgumentParser]:
        """Define initial arguments (before the main parser)."""
        pre_parser = argparse.ArgumentParser(add_help=False)
        pre_parser.add_argument(
            "--verbose", "-v", 
            action="count", 
            default=0,
            help="Increase verbosity level"
        )
        pre_parser.add_argument(
            "--list-scenarios", 
            action="store_true",
            help="List available generation scenarios"
        )
        return pre_parser

    @staticmethod
    def setup_logging(args: argparse.Namespace, **kwargs: Dict[str, Any]) -> None:
        """Configure logging based on parsed args."""
        log_level = logging.WARNING
        if args.verbose == 1:
            log_level = logging.INFO
        elif args.verbose >= 2:
            log_level = logging.DEBUG
        
        # Configure root logger
        logger = logging.getLogger()
        logger.setLevel(log_level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Configure handlers
        for handler in logger.handlers:
            handler.setLevel(log_level)
            handler.setFormatter(formatter)
        
        # Suppress excessive logging from third-party libraries
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('openai').setLevel(logging.WARNING)

    @staticmethod
    def load_configuration(kwargs: Dict[str, Any]) -> None:
        """Load tool-specific configuration (e.g., from file or env)."""
        args = kwargs.get("args")
        
        # Try to import required modules here if they weren't available at import time
        try:
            from data_gen.core.controller import GenerationController
            from data_gen.config.defaults import DEFAULT_CONFIG
            from data_gen.config.scenarios import SCENARIOS
            kwargs["modules_loaded"] = True
        except ImportError as e:
            logging.error(f"Failed to import required modules: {e}")
            print(f"Error: Failed to load required modules. Make sure the data_generator_enhanced module is properly installed.")
            kwargs["modules_loaded"] = False
            return
            
        # Handle list-scenarios command
        if args.list_scenarios:
            DataGeneratorHandlerMixin._list_scenarios()
            sys.exit(0)
            
        # Load configuration from file
        config = DEFAULT_CONFIG.copy()
        if args.config and os.path.exists(args.config):
            try:
                with open(args.config, 'r') as f:
                    user_config = json.load(f)
                    config.update(user_config)
            except Exception as e:
                logging.error(f"Error loading config file {args.config}: {e}")
                print(f"Error: Failed to load configuration from {args.config}")
                sys.exit(1)
        
        kwargs["config"] = config

    @staticmethod
    def _list_scenarios():
        """Print available scenarios."""
        print("Available generation scenarios:")
        print("-" * 30)
        
        for name, details in SCENARIOS.items():
            print(f"{name}:")
            print(f"  Description: {details.get('description', 'No description')}")
            print(f"  Storage count: {details.get('storage_count', 'default')}")
            print(f"  Semantic count: {details.get('semantic_count', 'default')}")
            print(f"  Activity count: {details.get('activity_count', 'default')}")
            print(f"  Relationship count: {details.get('relationship_count', 'default')}")
            print(f"  Machine configurations: {details.get('machine_config_count', 'default')}")
            print()

    @staticmethod
    def add_parameters(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        """Add tool-specific CLI arguments to the parser."""
        # Basic options
        parser.add_argument(
            "--config", 
            help="Path to configuration file"
        )
        parser.add_argument(
            "--scenario", 
            help="Scenario to generate data for", 
            default="basic"
        )
        parser.add_argument(
            "--output", 
            help="Output path for generation report", 
            default="./generation_report.json"
        )
        
        # Generation options
        generation_group = parser.add_argument_group("Generation Options")
        generation_group.add_argument(
            "--storage-count", 
            type=int, 
            help="Number of storage records to generate"
        )
        generation_group.add_argument(
            "--semantic-count", 
            type=int, 
            help="Number of semantic records to generate"
        )
        generation_group.add_argument(
            "--activity-count", 
            type=int, 
            help="Number of activity records to generate"
        )
        generation_group.add_argument(
            "--relationship-count", 
            type=int, 
            help="Number of relationship records to generate"
        )
        generation_group.add_argument(
            "--machine-count", 
            type=int, 
            help="Number of machine configurations to generate"
        )
        
        # Truth dataset options
        truth_group = parser.add_argument_group("Truth Dataset Options")
        truth_group.add_argument(
            "--truth-only", 
            action="store_true", 
            help="Generate only truth records"
        )
        truth_group.add_argument(
            "--truth-query", 
            help="Natural language query for truth data generation"
        )
        truth_group.add_argument(
            "--truth-count", 
            type=int, 
            default=10, 
            help="Number of truth records to generate"
        )
        
        # LLM options
        llm_group = parser.add_argument_group("LLM Options")
        llm_group.add_argument(
            "--llm-provider", 
            choices=["openai", "anthropic", "mock"], 
            default="openai", 
            help="LLM provider to use"
        )
        llm_group.add_argument(
            "--direct-generation", 
            action="store_true", 
            help="Use direct generation instead of LLM"
        )
        
        # Execution options
        exec_group = parser.add_argument_group("Execution Options")
        exec_group.add_argument(
            "--dry-run", 
            action="store_true", 
            help="Simulate generation without database writes"
        )
        
        return parser

    @staticmethod
    def performance_configuration(_kwargs: Dict[str, Any]) -> bool:
        """Configure performance recording; return False to skip."""
        return True

    @staticmethod
    def run(kwargs: Dict[str, Any]) -> None:
        """Main entry point for CLI execution."""
        args = kwargs.get("args")
        config = kwargs.get("config", {})
        
        # Check if modules were loaded successfully
        if not kwargs.get("modules_loaded", False):
            return
            
        logging.info(f"Running data generator with scenario: {args.scenario}")
        
        # Set up controller with args and config
        try:
            controller = DataGeneratorHandlerMixin._setup_controller(args, config)
            logging.info("Generation controller initialized")
        except Exception as e:
            logging.error(f"Failed to initialize controller: {e}")
            print(f"Error: {e}")
            return
        
        # Run generation
        try:
            print(f"Starting data generation for scenario: {args.scenario}")
            start_time = time.time()
            
            if args.truth_only:
                print(f"Generating {args.truth_count} truth records for query: {config['truth']['query']}")
                result = controller.generate_truth_dataset(
                    query=config['truth']['query'],
                    count=config['truth']['count']
                )
            else:
                print(f"Generating dataset using scenario: {args.scenario}")
                result = controller.generate_dataset(scenario=args.scenario)
            
            elapsed = time.time() - start_time
            print(f"Generation completed in {elapsed:.2f} seconds")
            
            # Summarize results
            DataGeneratorHandlerMixin._print_summary(result)
            
            # Save report
            DataGeneratorHandlerMixin._save_report(result, args.output)
            
        except KeyboardInterrupt:
            print("\nGeneration interrupted by user")
        except Exception as e:
            logging.error(f"Generation failed: {e}")
            print(f"Error: Generation failed - {e}")

    @staticmethod
    def _setup_controller(args, config: Dict[str, Any]) -> "GenerationController":
        """Set up the generation controller with command line arguments and config."""
        # Override config with command line arguments
        if args.storage_count:
            config["generation"]["storage_count"] = args.storage_count
        if args.semantic_count:
            config["generation"]["semantic_count"] = args.semantic_count
        if args.activity_count:
            config["generation"]["activity_count"] = args.activity_count
        if args.relationship_count:
            config["generation"]["relationship_count"] = args.relationship_count
        if args.machine_count:
            config["generation"]["machine_config_count"] = args.machine_count
        
        # Set LLM provider
        config["llm"]["provider"] = args.llm_provider
        config["generation"]["direct_generation"] = args.direct_generation
        
        # Configure truth dataset generation
        if args.truth_only or args.truth_query:
            config["truth"]["enabled"] = True
            if args.truth_query:
                config["truth"]["query"] = args.truth_query
            if args.truth_count:
                config["truth"]["count"] = args.truth_count
        
        # Set dry run mode
        config["execution"]["dry_run"] = args.dry_run
        
        # Create controller
        from data_gen.core.controller import GenerationController
        return GenerationController(config)
        
    @staticmethod
    def _print_summary(result: Dict[str, Any]) -> None:
        """Print summary of generation results."""
        print("\nGeneration Summary:")
        print(f"  Storage records: {result.get('storage_count', 0)}")
        print(f"  Semantic records: {result.get('semantic_count', 0)}")
        print(f"  Activity records: {result.get('activity_count', 0)}")
        print(f"  Relationship records: {result.get('relationship_count', 0)}")
        print(f"  Machine configurations: {result.get('machine_config_count', 0)}")
        
        if result.get('truth_generated'):
            print(f"\nTruth Dataset:")
            print(f"  Query: {result.get('truth_query', 'N/A')}")
            print(f"  Records: {result.get('truth_count', 0)}")
    
    @staticmethod
    def _save_report(report: Dict[str, Any], output_path: str) -> None:
        """Save generation report to a file."""
        try:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"Generation report saved to {output_path}")
        except Exception as e:
            logging.error(f"Error saving report to {output_path}: {e}")
            print(f"Error: Failed to save report to {output_path}")

    @staticmethod
    def performance_recording(kwargs: Dict[str, Any]) -> None:
        """Hook for recording performance after run()."""
        # Can capture performance metrics here if needed
        pass

    @staticmethod
    def cleanup(kwargs: Dict[str, Any]) -> None:
        """Cleanup hook (e.g., close resources)."""
        # Close any open resources, connections, etc.
        pass