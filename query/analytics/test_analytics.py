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
from query.analytics.file_statistics import FileStatistics, display_report


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

    # Initialize database connection
    if args.db_config:
        db_config = IndalekoDBConfig(config_file=args.db_config)
    else:
        db_config = IndalekoDBConfig()

    # Create statistics object
    stats = FileStatistics(db_config)

    # Run the requested tests
    if args.all or args.counts:
        stats.count_total_objects()
        stats.count_files()
        stats.count_directories()


    if args.all or args.types:
        file_types = stats.get_file_type_distribution()

        if file_types:
            sorted_types = sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:5]
            for _ext, _count in sorted_types:
                pass
        else:
            pass

    if args.all or args.sizes:
        size_stats = stats.get_file_size_statistics()

        if size_stats:
            pass
        else:
            pass

    if args.all or args.ages:
        age_distribution = stats.get_file_age_distribution()

        if age_distribution:
            for _item in age_distribution:
                pass
        else:
            pass

    if args.all or args.report:
        output_dir = args.output or "."

        # Generate the report
        report = stats.generate_report(output_dir, args.visualize)

        # Display the report
        display_report(report)

        if args.visualize:
            pass


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
