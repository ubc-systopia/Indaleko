#!/usr/bin/env python3
"""Run data sanity checks for the ablation framework.

This script allows running sanity checks independently to verify data integrity
before running ablation tests. It implements a fail-fast approach by default.
"""

import logging
import os
import sys
from pathlib import Path

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

from research.ablation.data_sanity_checker import DataSanityChecker


def setup_logging():
    """Set up logging for the script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def main():
    """Run data sanity checks from the command line."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting data sanity checks for ablation framework")
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Run data sanity checks for ablation framework")
    parser.add_argument("--no-fail-fast", action="store_true", help="Continue checks after first failure")
    parser.add_argument("--check", choices=[
        "collections", 
        "truth-data", 
        "truth-entities", 
        "query-execution", 
        "cross-collection", 
        "query-ids"
    ], action="append", help="Specific checks to run (default: all)")
    parser.add_argument("--query-id", action="append", help="Verify specific query IDs")
    args = parser.parse_args()
    
    try:
        # Create checker
        checker = DataSanityChecker(fail_fast=not args.no_fail_fast)
        
        # Run specific checks or all checks
        if args.check:
            logger.info(f"Running specific checks: {args.check}")
            all_passed = True
            
            # Map command line options to checker methods
            check_map = {
                "collections": checker.verify_collections_exist,
                "truth-data": checker.verify_truth_data_integrity,
                "truth-entities": checker.verify_truth_entities_exist,
                "query-execution": checker.verify_query_execution,
                "cross-collection": checker.verify_cross_collection_ids,
                "query-ids": checker.verify_truth_query_ids,
            }
            
            for check_name in args.check:
                check_func = check_map.get(check_name)
                if check_func:
                    logger.info(f"Running check: {check_name}")
                    try:
                        if not check_func():
                            all_passed = False
                            if not args.no_fail_fast:
                                break
                    except Exception as e:
                        logger.error(f"Check {check_name} failed with exception: {e}")
                        all_passed = False
                        if not args.no_fail_fast:
                            break
                else:
                    logger.warning(f"Unknown check: {check_name}")
        else:
            # Run all checks
            logger.info("Running all checks")
            all_passed = checker.run_all_checks()
        
        # Run additional query-specific checks if requested
        if args.query_id:
            logger.info(f"Verifying specific query IDs: {args.query_id}")
            if not checker.verify_query_execution(args.query_id):
                all_passed = False
        
        # Set exit code based on check results
        if not all_passed:
            logger.error("Data sanity checks failed!")
            sys.exit(1)
        else:
            logger.info("All data sanity checks passed!")
            sys.exit(0)
    except Exception as e:
        logger.error(f"Error running data sanity checks: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()