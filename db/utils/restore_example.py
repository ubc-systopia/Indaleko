"""
Example of using the ArangoRestoreGenerator for restoring an ArangoDB backup.

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
import logging
import os
import sys
import time
from pathlib import Path

# Handle imports for when the module is run directly
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from db.utils.arango_commands import ArangoRestoreGenerator
# pylint: enable=wrong-import-position


def format_time(seconds):
    """Format seconds into a human-readable time string."""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"


def main():
    """Main function for the ArangoRestore example."""
    parser = argparse.ArgumentParser(description="Restore an ArangoDB backup")
    parser.add_argument(
        "--input-directory",
        "-i",
        required=True,
        help="Path to the backup directory containing dump files"
    )
    parser.add_argument(
        "--collections",
        "-c",
        help="Optional comma-separated list of collections to restore (default: all collections)"
    )
    parser.add_argument(
        "--create",
        action="store_true",
        default=True,
        help="Create collections if they don't exist (default: true)"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite existing data (default: false)"
    )
    parser.add_argument(
        "--timeout-hours",
        type=float,
        default=5.0,
        help="Timeout in hours (default: 5.0)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the command without executing it"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Parse collections if provided
    collections = None
    if args.collections:
        collections = [c.strip() for c in args.collections.split(",")]
        if len(collections) == 1:
            collections = collections[0]  # Single collection as string

    # Create the restore command generator
    restore_gen = ArangoRestoreGenerator()
    restore_gen.with_input_directory(args.input_directory)

    if collections:
        restore_gen.with_collections(collections)

    restore_gen.with_create(args.create)
    restore_gen.with_overwrite(args.overwrite)
    restore_gen.with_timeout_hours(args.timeout_hours)

    # Build the command
    cmd_string = restore_gen.build_command()

    # Print the command
    print("\n=== ArangoDB Restore Command ===")
    print(cmd_string)
    print()

    if args.dry_run:
        print("Dry run mode - command not executed")
        return

    # Execute the command with timing
    print(f"Starting restore operation (timeout: {args.timeout_hours} hours)...")
    print("This may take a long time for large databases.")
    print("Press Ctrl+C to cancel...")

    start_time = time.time()

    try:
        result = restore_gen.execute()

        end_time = time.time()
        elapsed = end_time - start_time

        print(f"\nRestore completed in {format_time(elapsed)}")
        print(f"Exit code: {result.returncode}")

        if result.returncode != 0:
            print("Restore operation failed!")
            print(f"Error output: {result.stderr}")
        else:
            print("Restore operation successful!")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"\nError during restore: {e}")


if __name__ == "__main__":
    main()
