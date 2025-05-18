"""
Analyzer for ablation test results.

This module analyzes and summarizes the results of ablation tests,
providing insights into how different metadata types affect query precision and recall.

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

import os
import sys
import json
import glob
import logging
import argparse
from typing import Dict, List, Any, Tuple, Set
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime


class AblationResultAnalyzer:
    """Analyzes and summarizes ablation test results."""

    def __init__(self, results_dir: str):
        """
        Initialize the analyzer with a directory of test results.

        Args:
            results_dir: Directory containing ablation test result JSON files
        """
        self.results_dir = results_dir
        self.result_files = []
        self.results = []
        self.summary = {}

        # Find all result files
        self._load_result_files()

    def _load_result_files(self) -> None:
        """Load all result files from the specified directory."""
        pattern = os.path.join(self.results_dir, "ablation_test_*.json")
        self.result_files = glob.glob(pattern)

        if not self.result_files:
            logging.warning(f"No result files found matching pattern: {pattern}")

        logging.info(f"Found {len(self.result_files)} result files")

    def load_results(self) -> None:
        """Load and parse all result files."""
        self.results = []

        for file_path in self.result_files:
            try:
                with open(file_path, 'r') as f:
                    result = json.load(f)
                    self.results.append(result)
                    logging.info(f"Loaded result file: {os.path.basename(file_path)}")
            except Exception as e:
                logging.error(f"Error loading {file_path}: {e}")

        logging.info(f"Loaded {len(self.results)} result sets")

    def analyze_results(self) -> Dict[str, Any]:
        """
        Analyze the loaded results and generate summary statistics.

        Returns:
            Dictionary with summary statistics
        """
        if not self.results:
            logging.warning("No results to analyze")
            return {}

        # Prepare summary structure
        summary = {
            "queries": [],
            "metadata_impact": {},
            "collection_usage": {},
            "query_complexity": {},
            "aql_changes": {},
            "timestamp": datetime.now().isoformat()
        }

        # Collect unique queries and analyze each
        queries = set()
        for result in self.results:
            query = result.get("query")
            if query:
                queries.add(query)

        # Analyze each query
        for query in queries:
            query_results = [r for r in self.results if r.get("query") == query]
            query_summary = self._analyze_query_results(query, query_results)
            summary["queries"].append(query_summary)

        # Calculate metadata impact across all queries
        metadata_types = set()
        for query_summary in summary["queries"]:
            for metadata_type in query_summary.get("metadata_impact", {}).keys():
                metadata_types.add(metadata_type)

        # Combine metadata impact data
        for metadata_type in metadata_types:
            impacts = []
            for query_summary in summary["queries"]:
                if metadata_type in query_summary.get("metadata_impact", {}):
                    impacts.append(query_summary["metadata_impact"][metadata_type])

            if impacts:
                avg_impact = sum(impacts) / len(impacts)
                summary["metadata_impact"][metadata_type] = avg_impact

        # Add overall statistics
        collection_usage = {}
        for query_summary in summary["queries"]:
            for collection, count in query_summary.get("collection_usage", {}).items():
                if collection not in collection_usage:
                    collection_usage[collection] = 0
                collection_usage[collection] += 1

        summary["collection_usage"] = {
            k: v / len(summary["queries"]) for k, v in collection_usage.items()
        }

        self.summary = summary
        return summary

    def _analyze_query_results(self, query: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze results for a specific query.

        Args:
            query: The query string
            results: List of results for this query

        Returns:
            Dictionary with query-specific analysis
        """
        query_summary = {
            "query": query,
            "baseline_results": 0,
            "metadata_impact": {},
            "collection_usage": {},
            "aql_changes": {}
        }

        # Get baseline result count
        baseline_results = None
        for result in results:
            if "baseline" in result:
                baseline_results = result["baseline"].get("result_count", 0)
                query_summary["baseline_results"] = baseline_results

                # Extract collections from baseline AQL
                aql = result["baseline"].get("aql", "")
                collections = self._extract_collections_from_aql(aql)
                query_summary["collection_usage"] = {
                    c: 1 for c in collections
                }
                break

        if baseline_results is None:
            logging.warning(f"No baseline results found for query: {query}")
            return query_summary

        # Analyze collection ablation impact
        for result in results:
            if "results" not in result:
                continue

            for group_name, group_result in result.get("results", {}).items():
                metrics = group_result.get("metrics", {})
                ablated_collections = group_result.get("ablated_collections", [])

                # Calculate impact as change in F1 score
                baseline_f1 = 1.0  # Perfect score for baseline
                ablated_f1 = metrics.get("f1", 0)
                impact = baseline_f1 - ablated_f1

                query_summary["metadata_impact"][group_name] = impact

                # Analyze AQL changes
                aql_analysis = group_result.get("aql_analysis", {})
                missing_collections = aql_analysis.get("missing_collections", [])
                query_summary["aql_changes"][group_name] = len(missing_collections)

        return query_summary

    def _extract_collections_from_aql(self, aql: str) -> List[str]:
        """
        Extract collection names from an AQL query.

        Args:
            aql: The AQL query string

        Returns:
            List of collection names
        """
        import re
        pattern = r'FOR\s+\w+\s+IN\s+([a-zA-Z0-9_]+)'
        return re.findall(pattern, aql)

    def generate_report(self, output_file: str = None) -> str:
        """
        Generate a human-readable report of the analysis.

        Args:
            output_file: Optional file to write the report to

        Returns:
            The report as a string
        """
        if not self.summary:
            self.analyze_results()

        if not self.summary:
            return "No results to report"

        # Generate the report
        report = []
        report.append("# Indaleko Ablation Test Results")
        report.append("")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        report.append("## Metadata Impact Summary")
        report.append("")
        report.append("The impact of each metadata type is measured as the reduction in F1 score when that metadata is ablated.")
        report.append("Higher numbers indicate more important metadata types for query effectiveness.")
        report.append("")

        # Sort metadata types by impact
        sorted_impacts = sorted(
            self.summary.get("metadata_impact", {}).items(),
            key=lambda x: x[1],
            reverse=True
        )

        if sorted_impacts:
            report.append("| Metadata Type | Impact |")
            report.append("|-------------|--------|")
            for metadata_type, impact in sorted_impacts:
                report.append(f"| {metadata_type} | {impact:.2f} |")
        else:
            report.append("No metadata impact data available")

        report.append("")
        report.append("## Collection Usage")
        report.append("")
        report.append("The frequency with which each collection appears in baseline queries.")
        report.append("")

        # Sort collections by usage
        sorted_usage = sorted(
            self.summary.get("collection_usage", {}).items(),
            key=lambda x: x[1],
            reverse=True
        )

        if sorted_usage:
            report.append("| Collection | Usage |")
            report.append("|------------|-------|")
            for collection, usage in sorted_usage:
                report.append(f"| {collection} | {usage:.2f} |")
        else:
            report.append("No collection usage data available")

        report.append("")
        report.append("## Query Results")
        report.append("")

        # Add details for each query
        for query_summary in self.summary.get("queries", []):
            query = query_summary.get("query", "Unknown query")
            report.append(f"### Query: \"{query}\"")
            report.append("")
            report.append(f"Baseline result count: {query_summary.get('baseline_results', 0)}")
            report.append("")
            report.append("#### Metadata Impact")

            # Sort metadata types by impact
            sorted_impacts = sorted(
                query_summary.get("metadata_impact", {}).items(),
                key=lambda x: x[1],
                reverse=True
            )

            if sorted_impacts:
                report.append("| Metadata Type | Impact |")
                report.append("|-------------|--------|")
                for metadata_type, impact in sorted_impacts:
                    report.append(f"| {metadata_type} | {impact:.2f} |")
            else:
                report.append("No metadata impact data available for this query")

            report.append("")
            report.append("#### Collections Used")
            collections = query_summary.get("collection_usage", {}).keys()
            if collections:
                for collection in collections:
                    report.append(f"- {collection}")
            else:
                report.append("No collection usage data available for this query")

            report.append("")

        # Write report to file if requested
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write("\n".join(report))
                logging.info(f"Report written to {output_file}")
            except Exception as e:
                logging.error(f"Error writing report to {output_file}: {e}")

        return "\n".join(report)

    def generate_visualizations(self, output_dir: str = None) -> None:
        """
        Generate visualizations of the analysis results.

        Args:
            output_dir: Directory to save visualizations to (default: results_dir)
        """
        if not self.summary:
            self.analyze_results()

        if not self.summary:
            logging.warning("No results to visualize")
            return

        if not output_dir:
            output_dir = self.results_dir

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Generate metadata impact bar chart
        self._generate_metadata_impact_chart(output_dir)

        # Generate collection usage chart
        self._generate_collection_usage_chart(output_dir)

        # Generate per-query impact matrix
        self._generate_query_impact_matrix(output_dir)

    def _generate_metadata_impact_chart(self, output_dir: str) -> None:
        """Generate a bar chart of metadata impact."""
        metadata_impact = self.summary.get("metadata_impact", {})
        if not metadata_impact:
            return

        # Sort by impact
        sorted_impacts = sorted(
            metadata_impact.items(),
            key=lambda x: x[1],
            reverse=True
        )

        labels = [item[0] for item in sorted_impacts]
        values = [item[1] for item in sorted_impacts]

        plt.figure(figsize=(10, 6))
        plt.bar(labels, values, color='skyblue')
        plt.xlabel('Metadata Type')
        plt.ylabel('Impact (F1 Score Reduction)')
        plt.title('Impact of Metadata Types on Query Effectiveness')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        output_path = os.path.join(output_dir, "metadata_impact.png")
        plt.savefig(output_path)
        plt.close()
        logging.info(f"Generated metadata impact chart: {output_path}")

    def _generate_collection_usage_chart(self, output_dir: str) -> None:
        """Generate a pie chart of collection usage."""
        collection_usage = self.summary.get("collection_usage", {})
        if not collection_usage:
            return

        # Sort by usage
        sorted_usage = sorted(
            collection_usage.items(),
            key=lambda x: x[1],
            reverse=True
        )

        labels = [item[0] for item in sorted_usage]
        values = [item[1] for item in sorted_usage]

        plt.figure(figsize=(10, 8))
        plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
        plt.axis('equal')
        plt.title('Collection Usage in Queries')
        plt.tight_layout()

        output_path = os.path.join(output_dir, "collection_usage.png")
        plt.savefig(output_path)
        plt.close()
        logging.info(f"Generated collection usage chart: {output_path}")

    def _generate_query_impact_matrix(self, output_dir: str) -> None:
        """Generate a heatmap of metadata impact per query."""
        queries = self.summary.get("queries", [])
        if not queries:
            return

        # Collect all metadata types and query labels
        metadata_types = set()
        query_labels = []

        for query_summary in queries:
            query_labels.append(query_summary.get("query", "Unknown"))
            for metadata_type in query_summary.get("metadata_impact", {}).keys():
                metadata_types.add(metadata_type)

        metadata_types = sorted(list(metadata_types))

        # Create impact matrix
        impact_matrix = np.zeros((len(query_labels), len(metadata_types)))

        for i, query_summary in enumerate(queries):
            for j, metadata_type in enumerate(metadata_types):
                impact = query_summary.get("metadata_impact", {}).get(metadata_type, 0)
                impact_matrix[i, j] = impact

        # Create the heatmap
        plt.figure(figsize=(12, 8))
        plt.imshow(impact_matrix, cmap='viridis', aspect='auto')
        plt.colorbar(label='Impact (F1 Score Reduction)')
        plt.xlabel('Metadata Type')
        plt.ylabel('Query')
        plt.title('Impact of Metadata Types on Different Queries')
        plt.xticks(np.arange(len(metadata_types)), metadata_types, rotation=45, ha='right')
        plt.yticks(np.arange(len(query_labels)), query_labels)
        plt.tight_layout()

        output_path = os.path.join(output_dir, "query_impact_matrix.png")
        plt.savefig(output_path)
        plt.close()
        logging.info(f"Generated query impact matrix: {output_path}")


def main():
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Analyze ablation test results")
    parser.add_argument(
        "results_dir",
        help="Directory containing ablation test results"
    )
    parser.add_argument(
        "--output", "-o",
        help="Path to write the report to"
    )
    parser.add_argument(
        "--visualize", "-v",
        action="store_true",
        help="Generate visualizations"
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Create analyzer and generate report
    analyzer = AblationResultAnalyzer(args.results_dir)
    analyzer.load_results()
    analyzer.analyze_results()

    # Determine output file path
    output_file = args.output
    if not output_file:
        output_file = os.path.join(args.results_dir, "ablation_report.md")

    # Generate report
    report = analyzer.generate_report(output_file)

    # Generate visualizations if requested
    if args.visualize:
        analyzer.generate_visualizations(args.results_dir)

    print(f"Analysis complete. Report written to {output_file}")
    if args.visualize:
        print(f"Visualizations saved to {args.results_dir}")


if __name__ == "__main__":
    main()
