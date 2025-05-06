#!/usr/bin/env python3
"""Query analysis for test query patterns.

This module provides utilities for analyzing test queries, categorizing them,
and extracting patterns that can be used to generate test data.
"""

import json
import logging
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# pandas not needed yet
# import pandas as pd


class QueryAnalyzer:
    """Analyzer for test queries to extract patterns and insights."""

    def __init__(self, queries_file: Optional[Union[str, Path]] = None):
        """Initialize a query analyzer.

        Args:
            queries_file: Optional path to a JSON file containing test queries
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.queries = []

        if queries_file:
            self.load_queries(queries_file)

    def load_queries(self, queries_file: Union[str, Path]) -> List[Dict[str, Any]]:
        """Load test queries from a file.

        Args:
            queries_file: Path to a JSON file containing test queries

        Returns:
            List of query dictionaries

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the file format is invalid
        """
        try:
            with open(queries_file, "r") as f:
                queries = json.load(f)

            if not isinstance(queries, list):
                raise ValueError(f"Expected a list of queries, got {type(queries)}")

            self.queries = queries
            self.logger.info(f"Loaded {len(queries)} test queries from {queries_file}")
            return queries

        except FileNotFoundError:
            self.logger.error(f"Query file not found: {queries_file}")
            raise

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in query file: {e}")
            raise ValueError(f"Invalid JSON in query file: {e}") from e

    def get_tag_statistics(self) -> Dict[str, int]:
        """Get statistics on query tags.

        Returns:
            Dictionary mapping tags to their frequencies
        """
        tag_counter = Counter()

        for query in self.queries:
            tags = query.get("tags", [])
            tag_counter.update(tags)

        return dict(tag_counter.most_common())

    def get_query_categories(self) -> Dict[str, List[str]]:
        """Categorize queries by their primary tag.

        Returns:
            Dictionary mapping categories to lists of queries
        """
        categories = defaultdict(list)

        for query in self.queries:
            query_text = query.get("query", "")
            tags = query.get("tags", [])

            if tags:
                # Use the first tag as the primary category
                primary_tag = tags[0]
                categories[primary_tag].append(query_text)

        return dict(categories)

    def analyze_query_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in test queries.

        Returns:
            Dictionary of analysis results
        """
        tag_stats = self.get_tag_statistics()
        categories = self.get_query_categories()

        # Analyze common patterns
        time_references = 0
        location_references = 0
        device_references = 0
        filetype_references = 0
        activity_references = 0

        for query in self.queries:
            query_text = query.get("query", "").lower()
            tags = query.get("tags", [])

            if any(tag in ["time", "temporal", "temporal_fuzzy", "temporal_linked", "temporal_ambiguity"] for tag in tags):
                time_references += 1

            if any(tag in ["geo_activity", "geolocation", "fuzzy_location"] for tag in tags):
                location_references += 1

            if any(tag in ["device", "machine_config", "device_config"] for tag in tags):
                device_references += 1

            if any(tag in ["filetype"] for tag in tags):
                filetype_references += 1

            if any(tag in ["activity_context", "music_activity", "music"] for tag in tags):
                activity_references += 1

        return {
            "tag_statistics": tag_stats,
            "categories": categories,
            "pattern_counts": {
                "time_references": time_references,
                "location_references": location_references,
                "device_references": device_references,
                "filetype_references": filetype_references,
                "activity_references": activity_references,
            },
            "total_queries": len(self.queries),
        }

    def generate_report(self, output_file: Optional[Union[str, Path]] = None) -> str:
        """Generate a report on test query analysis.

        Args:
            output_file: Optional path to write the report to

        Returns:
            Report text
        """
        analysis = self.analyze_query_patterns()

        report = [
            "# Test Query Analysis Report",
            "",
            f"Analyzed {analysis['total_queries']} test queries.",
            "",
            "## Tag Statistics",
            "",
        ]

        # Add tag statistics
        for tag, count in analysis["tag_statistics"].items():
            percentage = 100 * count / analysis["total_queries"]
            report.append(f"- {tag}: {count} ({percentage:.1f}%)")

        report.append("")
        report.append("## Pattern Counts")
        report.append("")

        # Add pattern counts
        for pattern, count in analysis["pattern_counts"].items():
            percentage = 100 * count / analysis["total_queries"]
            report.append(f"- {pattern}: {count} ({percentage:.1f}%)")

        report.append("")
        report.append("## Query Categories")
        report.append("")

        # Add sample queries for each category
        for category, queries in analysis["categories"].items():
            report.append(f"### {category}")
            report.append("")
            for query in queries[:3]:  # Show up to 3 examples
                report.append(f"- \"{query}\"")
            report.append("")

        report_text = "\n".join(report)

        if output_file:
            with open(output_file, "w") as f:
                f.write(report_text)
            self.logger.info(f"Wrote report to {output_file}")

        return report_text

    def generate_test_configurations(self, output_dir: Union[str, Path]) -> List[Dict[str, Any]]:
        """Generate test configurations based on query patterns.

        Args:
            output_dir: Directory to write the configurations to

        Returns:
            List of configuration dictionaries
        """
        output_dir = Path(output_dir)
        os.makedirs(output_dir, exist_ok=True)

        # Group queries by primary tag
        tag_groups = defaultdict(list)
        for query in self.queries:
            query_text = query.get("query", "")
            tags = query.get("tags", [])

            if tags:
                tag_groups[tags[0]].append({"query": query_text, "tags": tags})

        configurations = []

        # Generate a configuration for each major tag group
        for tag, queries in tag_groups.items():
            config = {
                "metadata": {
                    "total_records": 1000,
                    "truth_records": min(50, len(queries) * 5),  # 5 truth records per query
                    "distributions": self._get_distributions_for_tag(tag),
                },
                "query_patterns": [
                    {
                        "description": f"Test query for {tag}",
                        "nl_query": query["query"],
                        "expected_truth": 5,
                        "tags": query["tags"],
                    }
                    for query in queries[:5]  # Use up to 5 queries per tag
                ],
                "reporting": {
                    "format": "json",
                    "metrics": ["precision", "recall", "latency", "result_count"],
                },
                "database": {
                    "clear_collections": False,
                    "batch_size": 100,
                },
            }

            # Write the configuration to a file
            config_file = output_dir / f"{tag}_test_config.json"
            with open(config_file, "w") as f:
                json.dump(config, f, indent=2)

            self.logger.info(f"Wrote test configuration for {tag} to {config_file}")
            configurations.append(config)

        return configurations

    def _get_distributions_for_tag(self, tag: str) -> Dict[str, Any]:
        """Get appropriate distributions for a tag.

        Args:
            tag: Tag to get distributions for

        Returns:
            Dictionary of distributions
        """
        # Base distributions
        distributions = {
            "file_sizes": {"type": "lognormal", "mu": 8.5, "sigma": 2.0},
            "modification_times": {"type": "normal", "mean": "now-30d", "std": "15d"},
            "file_extensions": {"type": "weighted", "values": {".pdf": 0.2, ".docx": 0.3, ".txt": 0.5}},
        }

        # Customize based on tag
        if tag in ["posix", "filetype"]:
            distributions["file_extensions"] = {
                "type": "weighted",
                "values": {".pdf": 0.3, ".docx": 0.2, ".xlsx": 0.2, ".txt": 0.1, ".jpg": 0.1, ".mp3": 0.05, ".mp4": 0.05},
            }

        elif tag in ["time", "temporal", "temporal_fuzzy"]:
            distributions["modification_times"] = {
                "type": "normal",
                "mean": "now-7d",  # More recent files
                "std": "3d",  # Tighter clustering
            }
            distributions["creation_times"] = {
                "type": "normal",
                "mean": "now-14d",
                "std": "5d",
            }

        elif tag in ["geo_activity", "geolocation"]:
            distributions["geo_locations"] = {
                "type": "weighted",
                "values": {
                    "San Francisco": 0.2,
                    "New York": 0.15,
                    "London": 0.1,
                    "Tokyo": 0.1,
                    "Nairobi": 0.1,
                    "Mexico City": 0.1,
                    "Oaxaca": 0.05,
                    "BC": 0.05,
                    "Coyoacán": 0.05,
                    "Home": 0.1,
                },
            }

        elif tag in ["music_activity", "music"]:
            distributions["music_artists"] = {
                "type": "weighted",
                "values": {
                    "Taylor Swift": 0.2,
                    "Heavy Metal": 0.15,
                    "Ambient": 0.2,
                    "Classical": 0.15,
                    "Jazz": 0.1,
                    "Hip Hop": 0.1,
                    "Rock": 0.1,
                },
            }

        elif tag in ["device", "machine_config"]:
            distributions["devices"] = {
                "type": "weighted",
                "values": {
                    "Laptop": 0.4,
                    "Desktop": 0.2,
                    "iPad": 0.15,
                    "iPhone": 0.15,
                    "Android": 0.1,
                },
            }

        elif tag in ["semantic", "structured_content"]:
            distributions["content_topics"] = {
                "type": "weighted",
                "values": {
                    "widget recall": 0.1,
                    "charts": 0.1,
                    "unicorn startup": 0.1,
                    "diagrams": 0.1,
                    "buzzwords": 0.1,
                    "vendor invoices": 0.1,
                    "marketing assets": 0.1,
                    "project Zephyr": 0.1,
                    "interview": 0.1,
                    "presentation": 0.1,
                },
            }

        return distributions


def main():
    """Main function for the query analyzer."""
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Set paths
    this_dir = Path(__file__).parent
    repo_root = Path(os.environ.get("INDALEKO_ROOT", this_dir.parent.parent.parent))
    query_file = repo_root / "tools" / "data_generator_enhanced" / "config" / "test_data" / "test_queries.json"
    output_dir = repo_root / "tools" / "data_generator_enhanced" / "config" / "test_configs"

    # Create the output directory
    os.makedirs(output_dir, exist_ok=True)

    # Analyze queries
    analyzer = QueryAnalyzer(query_file)
    report = analyzer.generate_report(output_dir / "query_analysis_report.md")
    configs = analyzer.generate_test_configurations(output_dir)

    logging.info(f"Generated {len(configs)} test configurations")
    logging.info(f"Report written to {output_dir / 'query_analysis_report.md'}")


if __name__ == "__main__":
    main()
