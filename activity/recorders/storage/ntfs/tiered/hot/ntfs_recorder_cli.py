#!/usr/bin/env python
"""
Command-line interface for recording NTFS activities to the hot tier database.

This module provides a command-line interface for processing NTFS activities from
JSONL files and recording them to the hot tier database. It maintains a proper
separation of concerns by focusing exclusively on the recording functionality,
leaving data collection to separate components.

Usage:
    # Process a JSONL file with default settings
    python ntfs_recorder_cli.py --input activities.jsonl

    # Process with custom TTL and debug logging
    python ntfs_recorder_cli.py --input activities.jsonl --ttl-days 7 --debug

    # Show statistics after processing
    python ntfs_recorder_cli.py --input activities.jsonl --statistics

    # Display help message
    python ntfs_recorder_cli.py --help

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).resolve().parent
    while not Path.exists(Path(current_path) / "Indaleko.py"):
        current_path = current_path.parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.append(str(current_path))

# pylint: disable=wrong-import-position
from activity.recorders.storage.ntfs.tiered.hot.recorder import NtfsHotTierRecorder
from constants.values import IndalekoConstants

# Create default DB config path using pathlib.Path
DEFAULT_DB_CONFIG_PATH = (
    Path(IndalekoConstants.default_config_dir)
    / IndalekoConstants.default_db_config_file_name
)
# pylint: enable=wrong-import-position


def process_jsonl_file(
    input_file: str,
    db_config_path: str | None = None,
    ttl_days: int = 4,
    debug: bool = False,
    statistics: bool = False,
    show_activities: bool = False,
    activity_limit: int = 10,
) -> dict[str, Any]:
    """
    Process a JSONL file containing NTFS activities and record to hot tier database.

    Args:
        input_file: Path to the JSONL file containing activities
        db_config_path: Path to the database configuration file
        ttl_days: Number of days to keep data in hot tier before expiration
        debug: Whether to enable debug logging
        statistics: Whether to generate and return statistics
        show_activities: Whether to include recent activities in the result
        activity_limit: Maximum number of activities to include in result

    Returns:
        Dictionary containing results and statistics
    """
    logger = logging.getLogger("NtfsRecorderCLI")

    # Check if input file exists
    if not Path(input_file).exists():
        error_msg = f"Input file not found: {input_file}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

    # Configure recorder
    try:
        logger.info("Initializing hot tier recorder...")
        recorder = NtfsHotTierRecorder(
            ttl_days=ttl_days,
            debug=debug,
            db_config_path=db_config_path,
            # Let registration service handle collection name
        )
        logger.info("Hot tier recorder initialized successfully")
    except Exception as e:
        error_msg = f"Failed to initialize recorder: {e!s}"
        logger.error(error_msg, exc_info=True)
        return {"success": False, "error": error_msg}

    # Process the JSONL file
    try:
        logger.info(f"Processing activities from {input_file}...")
        start_time = time.time()
        activity_ids = recorder.process_jsonl_file(input_file)
        end_time = time.time()
        processing_time = end_time - start_time

        result = {
            "success": True,
            "file": input_file,
            "activities_processed": len(activity_ids),
            "processing_time_seconds": processing_time,
            "ttl_days": ttl_days,
        }

        logger.info(
            f"Successfully processed {len(activity_ids)} activities in {processing_time:.2f} seconds",
        )

        # Add statistics if requested
        if statistics:
            try:
                stats = recorder.get_hot_tier_statistics()
                result["statistics"] = stats
                logger.info(f"Generated statistics: {len(stats)} metrics")
            except Exception as e:
                logger.warning(f"Failed to generate statistics: {e!s}")
                result["statistics_error"] = str(e)

        # Add recent activities if requested
        if show_activities and len(activity_ids) > 0:
            try:
                recent = recorder.get_recent_activities(hours=24, limit=activity_limit)
                # Clean up activities for display (remove large/complex fields)
                simplified_activities = []
                for activity in recent[:activity_limit]:
                    data = activity.get("Record", {}).get("Data", {})
                    simple_activity = {
                        "activity_id": data.get("activity_id"),
                        "timestamp": data.get("timestamp"),
                        "activity_type": data.get("activity_type"),
                        "file_path": data.get("file_path"),
                        "entity_id": data.get("entity_id"),
                        "importance_score": data.get("importance_score"),
                    }
                    simplified_activities.append(simple_activity)

                result["recent_activities"] = simplified_activities
                logger.info(
                    f"Added {len(simplified_activities)} recent activities to result",
                )
            except Exception as e:
                logger.warning(f"Failed to retrieve recent activities: {e!s}")
                result["activities_error"] = str(e)

        return result

    except Exception as e:
        error_msg = f"Error processing activities: {e!s}"
        logger.error(error_msg, exc_info=True)
        return {"success": False, "error": error_msg}


def main() -> None:
    """Main entry point for CLI."""
    # Configure error handling for timezone issues
    try:
        # Force timezone-aware handling for all datetime operations
        # This prevents "can't subtract offset-naive and offset-aware datetimes" errors
        datetime.now(timezone.utc)  # Force timezone awareness in this module
    except Exception:
        pass

    # Configure command-line interface
    parser = argparse.ArgumentParser(
        description="Record NTFS activities from JSONL files to the hot tier database",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Input configuration
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to input JSONL file with NTFS activities",
    )

    # Database configuration
    parser.add_argument(
        "--db-config",
        type=str,
        help="Path to database configuration file",
        default=str(DEFAULT_DB_CONFIG_PATH),
    )

    # Recorder configuration
    parser.add_argument(
        "--ttl-days",
        type=int,
        default=4,
        help="Number of days to keep data in hot tier",
    )

    # Output and display options
    parser.add_argument(
        "--statistics", action="store_true", help="Display statistics after processing",
    )
    parser.add_argument(
        "--show-activities",
        action="store_true",
        help="Display recent activities after processing",
    )
    parser.add_argument(
        "--limit", type=int, default=10, help="Maximum number of activities to display",
    )

    # Logging options
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress all output except errors",
    )
    parser.add_argument(
        "--json-output", action="store_true", help="Output results as JSON",
    )

    # Parse arguments
    args = parser.parse_args()

    # Configure logging
    log_level = (
        logging.ERROR if args.quiet else (logging.DEBUG if args.debug else logging.INFO)
    )
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("NtfsRecorderCLI")

    # Process the JSONL file
    result = process_jsonl_file(
        input_file=args.input,
        db_config_path=args.db_config,
        ttl_days=args.ttl_days,
        debug=args.debug,
        statistics=args.statistics,
        show_activities=args.show_activities,
        activity_limit=args.limit,
    )

    # Display results
    if args.json_output:
        # Format JSON output for better readability
        print(json.dumps(result, indent=2))
    elif result["success"]:
        print(f"\nSuccessfully processed activities from {args.input}")
        print(f"  - Activities processed: {result['activities_processed']}")
        print(
            f"  - Processing time: {result['processing_time_seconds']:.2f} seconds",
        )
        print(f"  - TTL: {result['ttl_days']} days")

        if args.statistics and "statistics" in result:
            stats = result["statistics"]
            print("\nHot Tier Statistics:")
            print(f"  - Total activities: {stats.get('total_count', 'N/A')}")

            if "by_type" in stats:
                print("\n  Activity Types:")
                for activity_type, count in stats["by_type"].items():
                    print(f"    - {activity_type}: {count}")

            if "by_importance" in stats:
                print("\n  Importance Score Distribution:")
                for score, count in stats["by_importance"].items():
                    print(f"    - Score {score}: {count}")

            if "by_time" in stats:
                print("\n  Time Distribution:")
                for time_range, count in stats["by_time"].items():
                    print(f"    - {time_range}: {count}")

        if args.show_activities and "recent_activities" in result:
            print("\nRecent Activities:")
            for i, activity in enumerate(result["recent_activities"], 1):
                print(f"\n  Activity {i}:")
                print(f"    - ID: {activity.get('activity_id', 'N/A')}")
                print(f"    - Time: {activity.get('timestamp', 'N/A')}")
                print(f"    - Type: {activity.get('activity_type', 'N/A')}")
                print(f"    - Path: {activity.get('file_path', 'N/A')}")
                print(
                    f"    - Importance: {activity.get('importance_score', 'N/A')}",
                )
    else:
        print(f"\nERROR: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
