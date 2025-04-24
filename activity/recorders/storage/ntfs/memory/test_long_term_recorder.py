#!/usr/bin/env python
"""
Test script for the NTFS Long-Term Memory Recorder.

This script provides a simple test for the NtfsLongTermMemoryRecorder, verifying that
it can correctly consolidate data from short-term memory and extract semantic concepts.

Usage:
    python test_long_term_recorder.py [--db-config=path/to/config] [--test-only] [--verbose]

Project Indaleko
Copyright (C) 2024-2025 Tony Mason
"""

import argparse
import logging
import os
import sys
from datetime import UTC, datetime, timedelta

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.recorders.storage.ntfs.memory.long_term.recorder import (
    NtfsLongTermMemoryRecorder,
)

# pylint: enable=wrong-import-position


def run_tests(verbose: bool = False, db_config_path: str = None) -> bool:
    """
    Run tests for the NtfsLongTermMemoryRecorder.

    Args:
        verbose: Whether to enable verbose logging
        db_config_path: Optional path to database configuration

    Returns:
        True if all tests passed, False otherwise
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=log_level)
    logger = logging.getLogger("test_long_term_recorder")

    logger.info("Testing Long-Term Memory Recorder")

    # Create recorder with test mode (no DB)
    try:
        recorder = NtfsLongTermMemoryRecorder(
            no_db=db_config_path is None,
            db_config_path=db_config_path,
            debug=verbose,
        )
        logger.info("Successfully created Long-Term Memory Recorder")
    except Exception as e:
        logger.error(f"Failed to create Long-Term Memory Recorder: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test semantic concept extraction
    logger.info("Testing semantic concept extraction...")
    test_data = {
        "Record": {
            "Data": {
                "file_path": "C:\\Users\\Documents\\Project\\Report.docx",
                "search_hits": 5,
            },
        },
    }

    concepts = recorder._extract_semantic_concepts(test_data)
    logger.info(f"Extracted concepts: {concepts}")

    if "document" not in concepts or "report" not in concepts:
        logger.error("Failed to extract expected concepts")
        return False

    # Test activity pattern extraction
    logger.info("Testing activity pattern extraction...")
    test_activity_data = {
        "Record": {
            "Data": {
                "activity_summary": {
                    "first_activity_date": (datetime.now(UTC) - timedelta(days=30)).isoformat(),
                    "last_activity_date": datetime.now(UTC).isoformat(),
                    "activity_count": 20,
                    "activity_types": {"create": 1, "modify": 15, "read": 4},
                    "access_frequency": 10,
                    "modification_frequency": 15,
                },
            },
        },
    }

    patterns = recorder._extract_activity_patterns(test_activity_data)
    logger.info(f"Extracted patterns: {patterns}")

    if "usage" not in patterns or "access" not in patterns or "lifecycle" not in patterns:
        logger.error("Failed to extract expected activity patterns")
        return False

    # If we get here, all tests passed
    logger.info("All tests passed!")
    return True


def main():
    """Main function for test script."""
    parser = argparse.ArgumentParser(
        description="Test Long-Term Memory Recorder",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--db-config",
        type=str,
        default=None,
        help="Path to database configuration file",
    )
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="Run tests without connecting to database",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # If test-only, force no_db
    if args.test_only:
        args.db_config = None

    # Run tests
    success = run_tests(verbose=args.verbose, db_config_path=args.db_config)

    # Return exit code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
