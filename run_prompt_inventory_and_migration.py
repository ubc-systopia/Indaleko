#!/usr/bin/env python
"""
Run the prompt inventory and migration planning tools.

This script runs both tools in sequence to generate a complete inventory
and migration plan for all prompts in the codebase.
"""

import argparse
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_results_dir() -> str:
    """Create results directory with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path(f"./results/prompt_migration_{timestamp}")
    results_dir.mkdir(parents=True, exist_ok=True)
    return str(results_dir)


def run_inventory(root_dir: str, output_dir: str, verbose: bool) -> str:
    """Run the prompt inventory tool."""
    logger.info("Running prompt inventory tool...")

    cmd = [
        "python",
        "-m",
        "query.utils.prompt_management.tools.prompt_inventory",
        "--root-dir",
        root_dir,
        "--output-dir",
        output_dir,
    ]

    if verbose:
        cmd.append("--verbose")

    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    logger.info(f"Inventory completed: {result.stdout}")

    # Find the generated JSON file
    inventory_files = list(Path(output_dir).glob("prompt_inventory_*.json"))
    if not inventory_files:
        raise FileNotFoundError("No inventory JSON file was generated")

    # Return the most recent one
    return str(sorted(inventory_files)[-1])


def run_migration_planner(inventory_path: str, output_dir: str) -> str:
    """Run the migration planner tool."""
    logger.info("Running migration planner tool...")

    cmd = [
        "python",
        "-m",
        "query.utils.prompt_management.tools.migration_planner",
        "--inventory",
        inventory_path,
        "--output-dir",
        output_dir,
    ]

    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    logger.info(f"Migration planning completed: {result.stdout}")

    # Find the generated markdown report
    report_files = list(Path(output_dir).glob("migration_plan_report_*.md"))
    if not report_files:
        raise FileNotFoundError("No migration plan report was generated")

    # Return the most recent one
    return str(sorted(report_files)[-1])


def main() -> None:
    """Run the main script."""
    parser = argparse.ArgumentParser(description="Run prompt inventory and migration planning")
    parser.add_argument(
        "--root-dir",
        type=str,
        default=".",
        help="Root directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Create results directory
    results_dir = create_results_dir()
    logger.info(f"Results will be saved to: {results_dir}")

    try:
        # Run inventory tool
        inventory_path = run_inventory(args.root_dir, results_dir, args.verbose)
        logger.info(f"Inventory saved to: {inventory_path}")

        # Run migration planner
        migration_report = run_migration_planner(inventory_path, results_dir)
        logger.info(f"Migration plan report saved to: {migration_report}")

        # Print summary
        logger.info("\n" + "=" * 50)
        logger.info("Prompt inventory and migration planning completed successfully!")
        logger.info(f"Results directory: {results_dir}")
        logger.info(f"Migration report: {migration_report}")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"Error running tools: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    main()
