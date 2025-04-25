#!/usr/bin/env python3
"""
picker.py

Background file picker CLI for Indaleko.
"""

import argparse
import logging
import os
import signal
import sys
import time

from utils.db.db_file_picker import IndalekoFilePicker

# Attempt to import unstructured processor if available
try:
    from semantic.collectors.unstructured.IndalekoUnstructured_Main import (
        process_file as process_unstructured,
    )

    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False


def start(args):
    """
    Start the background file picker.
    """
    # Lower process priority
    try:
        if sys.platform != "win32":
            os.nice(10)
    except Exception as e:
        logging.warning(f"Failed to set low priority: {e}")

    # Initialize file picker, ensure database connectivity
    try:
        picker = IndalekoFilePicker()
    except Exception as e:
        logging.exception(f"Failed to initialize file picker (DB connection issue): {e}")
        sys.exit(1)

    # Graceful shutdown handler
    def shutdown(signum, frame):
        logging.info("Shutting down file picker...")
        picker.stop_background_processing(wait=True)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Prepare extension filter
    extensions = set(ext.lower() for ext in args.extensions) if args.extensions else None

    # Main loop
    while True:
        # Pick random files
        files = picker.pick_random_files(count=args.batch_size, local_only=args.local_only)
        # Filter by extension if provided
        if extensions:
            filtered = []
            for file in files:
                uri = file.serialize().get("URI", "")
                _, ext = os.path.splitext(uri)
                if ext.lower() in extensions:
                    filtered.append(file)
            files = filtered
        if files:
            # Select processing function
            if args.unstructured and UNSTRUCTURED_AVAILABLE:
                func = process_unstructured
            else:
                # Default: log the picked file paths
                func = lambda f, p: logging.info(f"Picked file: {p}")
            queued = picker.queue_for_background_processing(files, func, priority=args.priority)
            logging.info(f"Queued {queued} files for background processing.")
        else:
            logging.info("No files selected this round.")
        time.sleep(args.interval)


def batch_export(args):
    """
    Batch export files for remote processing (not yet implemented).
    """
    raise NotImplementedError("batch-export is not yet implemented")


def batch_import(args):
    """
    Batch import files from a processing bundle (not yet implemented).
    """
    raise NotImplementedError("batch-import is not yet implemented")


def main():
    parser = argparse.ArgumentParser(prog="picker", description="Indaleko file picker utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # start subcommand
    start_parser = subparsers.add_parser("start", help="Start background file picker")
    start_parser.add_argument("--batch-size", type=int, default=1, help="Number of files to pick per batch")
    start_parser.add_argument("--interval", type=int, default=300, help="Interval between batches in seconds")
    start_parser.add_argument("--local-only", action="store_true", help="Only pick locally accessible files")
    start_parser.add_argument("--extensions", nargs="*", help="List of file extensions to include (e.g. .txt .md)")
    start_parser.add_argument("--unstructured", action="store_true", help="Use unstructured processor if available")
    start_parser.add_argument(
        "--priority", type=int, default=1, help="Processing priority (lower number = higher priority)",
    )
    start_parser.set_defaults(func=start)

    # batch-export subcommand (TODO)
    export_parser = subparsers.add_parser("batch-export", help="Batch export files for remote processing")
    export_parser.set_defaults(func=batch_export)

    # batch-import subcommand (TODO)
    import_parser = subparsers.add_parser("batch-import", help="Batch import files from processing bundle")
    import_parser.set_defaults(func=batch_import)

    args = parser.parse_args()
    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        args.func(args)
    except NotImplementedError as e:
        logging.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
