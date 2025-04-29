"""
Example script showing how to use the analytics functions directly from Python code.

This script demonstrates how to use the file statistics analytics capabilities
directly from Python without using the CLI integration.

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
from query.analytics.file_statistics import FileStatistics, format_size

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_analytics_examples(db_config: IndalekoDBConfig | None = None):
    """
    Run examples of different analytics capabilities.

    Args:
        db_config: Optional database configuration
    """
    print("\n=== Indaleko Analytics Examples ===\n")

    # Create file statistics object
    stats = FileStatistics(db_config)

    # Example 1: Basic counts
    print("\n=== Example 1: Basic File Counts ===")
    total_objects = stats.count_total_objects()
    file_count = stats.count_files()
    directory_count = stats.count_directories()

    print(f"Total Objects: {total_objects:,}")
    print(f"Files: {file_count:,}")
    print(f"Directories: {directory_count:,}")

    # Example 2: File type distribution
    print("\n=== Example 2: File Type Distribution ===")
    file_types = stats.get_file_type_distribution()

    if file_types:
        print(f"Found {len(file_types)} different file types")
        print("\nTop 5 file types:")
        sorted_types = sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:5]
        for ext, count in sorted_types:
            print(f".{ext}: {count:,} files")

    # Example 3: File size statistics
    print("\n=== Example 3: File Size Analysis ===")
    size_stats = stats.get_file_size_statistics()

    if size_stats:
        print(f"File Count: {size_stats['count']:,}")
        print(f"Total Size: {format_size(size_stats['total_size'])}")
        print(f"Average Size: {format_size(size_stats['average_size'])}")
        print(f"Median Size: {format_size(size_stats['median_size'])}")
        print(f"Smallest File: {format_size(size_stats['min_size'])}")
        print(f"Largest File: {format_size(size_stats['max_size'])}")

    # Example 4: File age distribution
    print("\n=== Example 4: File Age Distribution ===")
    age_distribution = stats.get_file_age_distribution()

    if age_distribution:
        print(f"Found {len(age_distribution)} age ranges")
        for item in age_distribution:
            print(
                f"{item['age_range']}: {item['count']:,} files, {format_size(item['total_size'])}",
            )

    # Example 5: Generate an analytical dashboard
    print("\n=== Example 5: Calculating Data for Analytics Dashboard ===")

    # Create a simple dashboard dictionary
    dashboard = {
        "counts": {
            "total": total_objects,
            "files": file_count,
            "directories": directory_count,
        },
        "storage": {
            "total": size_stats.get("total_size", 0),
            "avg_file_size": size_stats.get("average_size", 0),
        },
        "types": {
            ext: count
            for ext, count in sorted(
                file_types.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10]
        },
        "age_profile": {
            item["age_range"]: {"count": item["count"], "size": item["total_size"]} for item in age_distribution
        },
    }

    # Display the dashboard structure (in production, this would feed a UI)
    print("\nAnalytics Dashboard Data Structure:")
    for section, data in dashboard.items():
        print(f"- {section.capitalize()}: {len(data)} metrics")
    print(
        "\nThis data structure can be used to power web dashboards, reports, or visualizations.",
    )

    # Example 6: Compute analytics-based indicators and insights
    print("\n=== Example 6: Computing System Insights ===")

    # This demonstrates how the analytics data can be used to generate insights
    insights = []

    # Growth trend insight (simplified for illustration)
    recent_files = 0
    for age_range, data in dashboard["age_profile"].items():
        if "Last week" in age_range or "Last month" in age_range:
            recent_files += data["count"]

    if file_count > 0:
        recent_ratio = recent_files / file_count
        if recent_ratio > 0.2:
            insights.append(
                "High recent activity: Consider increasing backup frequency",
            )
        elif recent_ratio < 0.05:
            insights.append(
                "Low recent activity: Consider archive/backup storage for older data",
            )

    # File type insights
    if file_types:
        # Check for document-heavy usage
        document_extensions = ["pdf", "doc", "docx", "txt", "md", "rtf"]
        doc_files = sum(file_types.get(ext, 0) for ext in document_extensions)

        if file_count > 0 and doc_files / file_count > 0.5:
            insights.append(
                "Document-heavy usage: Consider document management optimizations",
            )

        # Check for image/video heavy usage
        media_extensions = ["jpg", "jpeg", "png", "gif", "mp4", "mov", "avi"]
        media_files = sum(file_types.get(ext, 0) for ext in media_extensions)

        if file_count > 0 and media_files / file_count > 0.5:
            insights.append(
                "Media-heavy usage: Consider media management optimizations",
            )

    # Storage insights
    if size_stats and size_stats["total_size"] > 500 * 1024 * 1024 * 1024:  # 500 GB
        insights.append(
            "Large storage footprint: Consider storage optimization strategies",
        )

    # Display insights
    print("\nSystem Insights:")
    if insights:
        for i, insight in enumerate(insights, 1):
            print(f"{i}. {insight}")
    else:
        print("No significant insights found from current analytics data.")


def main():
    """Main entry point for the analytics examples."""
    parser = argparse.ArgumentParser(description="Indaleko Analytics Examples")
    parser.add_argument(
        "--db-config",
        type=str,
        help="Path to database configuration file",
    )
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode")

    args = parser.parse_args()

    # Initialize database configuration
    if args.db_config:
        db_config = IndalekoDBConfig(config_file=args.db_config)
    else:
        db_config = IndalekoDBConfig()

    # If debug mode is enabled, set logging level to DEBUG
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run examples
    run_analytics_examples(db_config)

    print("\n=== Completed Analytics Examples ===")
    print("To use analytics in the CLI, run: python -m query.cli --analytics")
    print("Then use the /analytics command to access file statistics.")


if __name__ == "__main__":
    main()
