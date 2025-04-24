"""
Test script for Indaleko Analytics module.

This script provides a simple way to test the analytics functionality.

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

# Set up environment variables
current_path = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_path))
os.environ["INDALEKO_ROOT"] = root_dir
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Import Indaleko components
from db.db_config import IndalekoDBConfig
from query.analytics.file_statistics import FileStatistics, display_report, format_size

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_file_stats_test(args):
    """
    Run file statistics tests.

    Args:
        args: Command line arguments
    """
    print("\n=== Testing File Statistics Analytics ===\n")

    # Initialize database connection
    if args.db_config:
        db_config = IndalekoDBConfig(config_file=args.db_config)
    else:
        db_config = IndalekoDBConfig()

    # Create statistics object
    stats = FileStatistics(db_config)

    # Run the requested tests
    if args.all or args.counts:
        print("\n=== Testing Basic Counts ===")
        total_objects = stats.count_total_objects()
        file_count = stats.count_files()
        directory_count = stats.count_directories()

        print(f"Total Objects: {total_objects:,}")
        print(f"Files: {file_count:,}")
        print(f"Directories: {directory_count:,}")

    if args.all or args.types:
        print("\n=== Testing File Type Distribution ===")
        file_types = stats.get_file_type_distribution()

        if file_types:
            print(f"Found {len(file_types)} different file types")
            print("\nTop 5 file types:")
            sorted_types = sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:5]
            for ext, count in sorted_types:
                print(f".{ext}: {count:,} files")
        else:
            print("No file type distribution found")

    if args.all or args.sizes:
        print("\n=== Testing File Size Statistics ===")
        size_stats = stats.get_file_size_statistics()

        if size_stats:
            print(f"Total Size: {format_size(size_stats['total_size'])}")
            print(f"Average Size: {format_size(size_stats['average_size'])}")
            print(f"Median Size: {format_size(size_stats['median_size'])}")
            print(f"Smallest File: {format_size(size_stats['min_size'])}")
            print(f"Largest File: {format_size(size_stats['max_size'])}")
        else:
            print("No size statistics found")

    if args.all or args.ages:
        print("\n=== Testing File Age Distribution ===")
        age_distribution = stats.get_file_age_distribution()

        if age_distribution:
            print(f"Found {len(age_distribution)} age ranges")
            for item in age_distribution:
                print(
                    f"{item['age_range']}: {item['count']:,} files, {format_size(item['total_size'])}",
                )
        else:
            print("No age distribution found")

    if args.all or args.report:
        print("\n=== Testing Full Report Generation ===")
        output_dir = args.output or "."

        # Generate the report
        report = stats.generate_report(output_dir, args.visualize)

        # Display the report
        display_report(report)

        print(f"\nReport saved to: {os.path.abspath(output_dir)}")
        if args.visualize:
            print("Visualizations generated:")
            print(f"  - {os.path.join(output_dir, 'files_vs_directories.png')}")
            print(f"  - {os.path.join(output_dir, 'file_types.png')}")
            print(f"  - {os.path.join(output_dir, 'file_age_distribution.png')}")
            print(f"  - {os.path.join(output_dir, 'file_size_by_age.png')}")


def main():
    """Main entry point for the analytics test script."""
    parser = argparse.ArgumentParser(description="Indaleko Analytics Test Tool")
    parser.add_argument("--all", "-a", action="store_true", help="Run all tests")
    parser.add_argument("--counts", "-c", action="store_true", help="Test file counts")
    parser.add_argument(
        "--types",
        "-t",
        action="store_true",
        help="Test file type distribution",
    )
    parser.add_argument(
        "--sizes",
        "-s",
        action="store_true",
        help="Test file size statistics",
    )
    parser.add_argument(
        "--ages",
        action="store_true",
        help="Test file age distribution",
    )
    parser.add_argument(
        "--report",
        "-r",
        action="store_true",
        help="Test comprehensive report generation",
    )
    parser.add_argument(
        "--visualize",
        "-v",
        action="store_true",
        help="Generate visualizations",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=".",
        help="Output directory for report and visualizations",
    )
    parser.add_argument(
        "--db-config",
        type=str,
        help="Path to database configuration file",
    )
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode")

    args = parser.parse_args()

    # If no specific test is selected, run all tests
    if not (args.counts or args.types or args.sizes or args.ages or args.report):
        args.all = True

    # If debug mode is enabled, set logging level to DEBUG
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run the tests
    run_file_stats_test(args)


if __name__ == "__main__":
    main()
