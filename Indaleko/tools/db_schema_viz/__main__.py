"""
Main entry point for the Indaleko Database Schema Visualization tool.

This module provides a command-line interface for generating
visualizations of the Indaleko database schema.

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

from pathlib import Path


# Add the root directory to the path to ensure imports work correctly
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from indaleko.tools.db_schema_viz.config import DEFAULT_GROUPS, load_config, save_config
from indaleko.tools.db_schema_viz.graphviz_generator import (
    generate_dot,
    generate_output,
)
from indaleko.tools.db_schema_viz.schema_analyzer import (
    analyze_indexes,
    group_collections,
)
from indaleko.tools.db_schema_viz.schema_extractor import (
    extract_collections,
    extract_relationships,
)


# pylint: enable=wrong-import-position


def main() -> None:
    """
    Main entry point for the schema visualization tool.

    Parses command-line arguments and generates the schema visualization
    based on the specified options.
    """
    parser = argparse.ArgumentParser(description="Generate visualization of the Indaleko database schema")

    # Output options
    parser.add_argument("--output", "-o", default="schema.pdf", help="Output file path")
    parser.add_argument("--format", "-f", choices=["pdf", "png", "svg"], default="pdf", help="Output format")

    # Visualization options
    parser.add_argument("--groups", "-g", action="store_true", default=True, help="Show collection groupings")
    parser.add_argument(
        "--indexes",
        "-i",
        action="store_true",
        default=True,
        help="Show key indexes (limited to 1-2 per collection)",
    )
    parser.add_argument(
        "--relationships",
        "-r",
        action="store_true",
        default=True,
        help="Show relationships between collections",
    )
    parser.add_argument(
        "--orientation",
        choices=["portrait", "landscape"],
        default="landscape",
        help="Diagram orientation",
    )

    # Configuration options
    parser.add_argument("--config", "-c", help="Path to configuration file")
    parser.add_argument("--save-config", "-s", help="Save current configuration to file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Configure logging
    logging_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=logging_level, format="%(asctime)s - %(levelname)s - %(message)s")

    # Load configuration
    config = load_config(args.config) if args.config else {"groups": DEFAULT_GROUPS}

    # Extract schema information
    logging.info("Extracting collection information from database...")
    collections = extract_collections()

    logging.info("Detecting relationships between collections...")
    relationships = extract_relationships(collections) if args.relationships else []

    # Analyze schema
    logging.info("Grouping collections...")
    groups = group_collections(collections, config["groups"]) if args.groups else {}

    logging.info("Analyzing indexes...")
    if args.indexes:
        collections = analyze_indexes(collections)

    # Generate DOT file
    logging.info("Generating GraphViz DOT file...")
    dot = generate_dot(collections=collections, relationships=relationships, groups=groups, show_indexes=args.indexes)

    # Generate output
    logging.info(f"Generating {args.format.upper()} output to {args.output}...")
    generate_output(dot=dot, output_path=args.output, format=args.format, orientation=args.orientation)

    # Save configuration if requested
    if args.save_config:
        config = {"groups": groups}
        save_config(config, args.save_config)
        logging.info(f"Configuration saved to {args.save_config}")

    logging.info(f"Schema visualization complete: {args.output}")


if __name__ == "__main__":
    main()
