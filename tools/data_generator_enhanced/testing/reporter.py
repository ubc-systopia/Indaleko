#!/usr/bin/env python3
"""Test result reporter for model-based data generation.

This module provides utilities for generating reports on test results
in various formats (Markdown, JSON, CSV, etc.).
"""

import csv
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    HAS_PLOTTING = True
except ImportError:
    HAS_PLOTTING = False


class TestReporter:
    """Reporter for test results."""

    def __init__(self, results: Dict[str, Any]):
        """Initialize a test reporter.

        Args:
            results: Test results
        """
        self.results = results
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate_report(self, output_path: Union[str, Path], format: str = "md") -> None:
        """Generate a report from test results.

        Args:
            output_path: Path to save report to
            format: Report format (md, json, csv, html, or pdf)
        """
        output_path = Path(output_path)
        os.makedirs(output_path.parent, exist_ok=True)

        if format == "json":
            self._generate_json_report(output_path)
        elif format == "csv":
            self._generate_csv_report(output_path)
        elif format == "html":
            self._generate_html_report(output_path)
        elif format == "pdf":
            self._generate_pdf_report(output_path)
        else:
            # Default to Markdown
            self._generate_markdown_report(output_path)

    def _generate_json_report(self, output_path: Path) -> None:
        """Generate a JSON report.

        Args:
            output_path: Path to save report to
        """
        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2)

        self.logger.info(f"JSON report saved to {output_path}")

    def _generate_csv_report(self, output_path: Path) -> None:
        """Generate a CSV report.

        Args:
            output_path: Path to save report to
        """
        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)

            # Write header
            writer.writerow(["Query", "Precision", "Recall", "F1 Score", "Result Count", "Expected Truth", "Passed"])

            # Write rows
            for test in self.results.get("tests", []):
                metrics = test.get("metrics", {})
                writer.writerow([
                    test.get("query", ""),
                    metrics.get("precision", 0),
                    metrics.get("recall", 0),
                    metrics.get("f1_score", 0),
                    test.get("result_count", 0),
                    test.get("expected_truth", 0),
                    test.get("passed", False)
                ])

        self.logger.info(f"CSV report saved to {output_path}")

    def _generate_markdown_report(self, output_path: Path) -> None:
        """Generate a Markdown report.

        Args:
            output_path: Path to save report to
        """
        summary = self.results.get("summary", {})
        tests = self.results.get("tests", [])

        lines = [
            "# Model-Based Data Generation Test Report",
            "",
            f"Generated: {self.results.get('timestamp', datetime.now().isoformat())}",
            "",
            "## Summary",
            "",
            f"- **Total Tests**: {summary.get('total_tests', 0)}",
            f"- **Passed Tests**: {summary.get('passed_tests', 0)}",
            f"- **Failed Tests**: {summary.get('failed_tests', 0)}",
            f"- **Average Precision**: {summary.get('avg_precision', 0)}%",
            f"- **Average Recall**: {summary.get('avg_recall', 0)}%",
            f"- **Average F1 Score**: {summary.get('avg_f1_score', 0)}%",
            "",
            "## Truth Dataset",
            "",
        ]

        # Add truth dataset statistics
        truth_counts = self.results.get("truth_record_counts", {})
        for category, count in truth_counts.items():
            if category != "all":
                lines.append(f"- **{category}**: {count} records")

        lines.append("")
        lines.append("## Test Results")
        lines.append("")

        # Add individual test results
        for i, test in enumerate(tests):
            lines.append(f"### Test {i+1}: {test.get('query', 'Unknown query')}")
            lines.append("")

            if "error" in test:
                lines.append(f"**Error**: {test['error']}")
                lines.append("")
                continue

            metrics = test.get("metrics", {})
            lines.append(f"- **Precision**: {metrics.get('precision', 0):.4f}")
            lines.append(f"- **Recall**: {metrics.get('recall', 0):.4f}")
            lines.append(f"- **F1 Score**: {metrics.get('f1_score', 0):.4f}")
            lines.append(f"- **Result Count**: {test.get('result_count', 0)}")
            lines.append(f"- **Expected Truth**: {test.get('expected_truth', 0)}")
            lines.append(f"- **Passed**: {'Yes' if test.get('passed', False) else 'No'}")
            lines.append("")

            # Add query generation time
            if "query_generation_time" in test:
                lines.append(f"- **Query Generation Time**: {test['query_generation_time']:.4f} seconds")

            # Add query execution time
            if "query_execution_time" in test:
                lines.append(f"- **Query Execution Time**: {test['query_execution_time']:.4f} seconds")

            lines.append("")

            # Add AQL query
            lines.append("#### AQL Query")
            lines.append("```aql")
            lines.append(test.get("aql_query", "No query available"))
            lines.append("```")
            lines.append("")

            # Add top results
            lines.append("#### Top Results")
            top_results = test.get("top_results", [])
            if top_results:
                lines.append("```json")
                lines.append(json.dumps(top_results, indent=2))
                lines.append("```")
            else:
                lines.append("No results available")

            lines.append("")

        with open(output_path, "w") as f:
            f.write("\n".join(lines))

        self.logger.info(f"Markdown report saved to {output_path}")

        # Generate charts if available
        if HAS_PLOTTING:
            charts_dir = output_path.parent / "charts"
            os.makedirs(charts_dir, exist_ok=True)

            self._generate_charts(charts_dir)

            # Add charts to the report
            with open(output_path, "a") as f:
                f.write("\n\n## Charts\n\n")
                f.write(f"![Precision and Recall](charts/precision_recall.png)\n\n")
                f.write(f"![F1 Scores](charts/f1_scores.png)\n\n")
                f.write(f"![Query Execution Times](charts/execution_times.png)\n\n")

    def _generate_html_report(self, output_path: Path) -> None:
        """Generate an HTML report.

        Args:
            output_path: Path to save report to
        """
        try:
            import markdown

            # First generate the Markdown report
            md_path = output_path.with_suffix(".md")
            self._generate_markdown_report(md_path)

            # Convert to HTML
            with open(md_path, "r") as f:
                md_content = f.read()

            html_content = markdown.markdown(md_content, extensions=["tables", "fenced_code"])

            # Add some basic styling
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Model-Based Data Generation Test Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 1200px; margin: 0 auto; }}
                    h1 {{ color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
                    h2 {{ color: #444; margin-top: 20px; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
                    h3 {{ color: #555; }}
                    pre {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; overflow: auto; }}
                    code {{ font-family: Consolas, Monaco, 'Andale Mono', monospace; }}
                    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                    tr:nth-child(even) {{ background-color: #f9f9f9; }}
                    .passed {{ color: green; }}
                    .failed {{ color: red; }}
                    img {{ max-width: 100%; height: auto; }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """

            with open(output_path, "w") as f:
                f.write(html)

            self.logger.info(f"HTML report saved to {output_path}")

        except ImportError:
            self.logger.warning("markdown package not available, falling back to Markdown report")
            self._generate_markdown_report(output_path.with_suffix(".md"))

    def _generate_pdf_report(self, output_path: Path) -> None:
        """Generate a PDF report.

        Args:
            output_path: Path to save report to
        """
        try:
            import weasyprint

            # First generate the HTML report
            html_path = output_path.with_suffix(".html")
            self._generate_html_report(html_path)

            # Convert to PDF
            html = weasyprint.HTML(filename=str(html_path))
            html.write_pdf(str(output_path))

            self.logger.info(f"PDF report saved to {output_path}")

        except ImportError:
            self.logger.warning("weasyprint package not available, falling back to HTML report")
            self._generate_html_report(output_path.with_suffix(".html"))

    def _generate_charts(self, output_dir: Path) -> None:
        """Generate charts for test results.

        Args:
            output_dir: Directory to save charts to
        """
        if not HAS_PLOTTING:
            self.logger.warning("matplotlib or pandas not available, skipping chart generation")
            return

        tests = self.results.get("tests", [])

        # Extract data
        queries = []
        precision = []
        recall = []
        f1_scores = []
        execution_times = []

        for test in tests:
            queries.append(test.get("query", "")[:30] + "..." if len(test.get("query", "")) > 30 else test.get("query", ""))

            metrics = test.get("metrics", {})
            precision.append(metrics.get("precision", 0))
            recall.append(metrics.get("recall", 0))
            f1_scores.append(metrics.get("f1_score", 0))

            execution_times.append(test.get("query_execution_time", 0))

        # Create precision and recall chart
        plt.figure(figsize=(10, 6))
        x = np.arange(len(queries))
        width = 0.35

        plt.bar(x - width/2, precision, width, label='Precision')
        plt.bar(x + width/2, recall, width, label='Recall')

        plt.xlabel('Queries')
        plt.ylabel('Score')
        plt.title('Precision and Recall by Query')
        plt.xticks(x, queries, rotation=45, ha='right')
        plt.ylim(0, 1.1)
        plt.tight_layout()
        plt.legend()

        plt.savefig(output_dir / "precision_recall.png")
        plt.close()

        # Create F1 score chart
        plt.figure(figsize=(10, 6))
        plt.bar(x, f1_scores, 0.7)

        plt.xlabel('Queries')
        plt.ylabel('F1 Score')
        plt.title('F1 Scores by Query')
        plt.xticks(x, queries, rotation=45, ha='right')
        plt.ylim(0, 1.1)
        plt.tight_layout()

        plt.savefig(output_dir / "f1_scores.png")
        plt.close()

        # Create execution time chart
        plt.figure(figsize=(10, 6))
        plt.bar(x, execution_times, 0.7)

        plt.xlabel('Queries')
        plt.ylabel('Execution Time (s)')
        plt.title('Query Execution Times')
        plt.xticks(x, queries, rotation=45, ha='right')
        plt.tight_layout()

        plt.savefig(output_dir / "execution_times.png")
        plt.close()
