#!/usr/bin/env python3
"""
Incremental File System Indexer CLI.

Walks configured directories, emits new or modified files since last run,
and records them to a JSONL file.
"""
import argparse
import logging
import sys
from pathlib import Path

from activity.collectors.storage.fs_incremental import FsIncrementalCollector
from activity.recorders.storage.fs_incremental_recorder import FsIncrementalRecorder


def main() -> None:
    """CLI entry point for the incremental file system indexer.

    Walk volumes, collect new/modified files, and record them.
    """
    parser = argparse.ArgumentParser(description="Incremental File System Indexer")
    parser.add_argument(
        "--volumes",
        nargs="+",
        required=True,
        help="Volumes or directories to index",
    )
    parser.add_argument(
        "--state-file",
        type=str,
        default="data/fs_indexer_state.json",
        help="JSON file tracking last run timestamp",
    )
    parser.add_argument(
        "--patterns",
        nargs="*",
        default=["*"],
        help="Glob patterns to include (default: all files)",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="data/fs_incremental_records.jsonl",
        help="JSONL file to append new file records",
    )
    parser.add_argument(
        "--full-scan",
        action="store_true",
        help="Ignore last run state and scan all files",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--db-records",
        action="store_true",
        help="Upsert incremental records into the database instead of JSONL file",
    )
    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        stream=sys.stdout,
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("FsIndexer")

    # Handle full scan by removing state file
    if args.full_scan:
        # Remove existing state file for a full scan
        Path(args.state_file).unlink(missing_ok=True)
        logger.info("Removed state file for full scan: %s", args.state_file)

    # Collect
    collector = FsIncrementalCollector(
        volumes=args.volumes,
        state_file=args.state_file,
        patterns=args.patterns,
    )
    activities = collector.collect_activities()
    logger.info(
        "Collected %d new/modified files since last run",
        len(activities),
    )

    # Record
    if args.db_records:
        from activity.recorders.storage.fs_incremental_db import FsIncrementalDbRecorder

        recorder = FsIncrementalDbRecorder()
        count = recorder.store_activities(activities)
        logger.info(
            "Upserted %d file records to database",
            count,
        )
    else:
        recorder = FsIncrementalRecorder(output_file=args.output_file)
        count = recorder.store_activities(activities)
        logger.info(
            "Recorded %d file events to %s",
            count,
            args.output_file,
        )


if __name__ == "__main__":
    main()
