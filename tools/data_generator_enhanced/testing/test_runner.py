#!/usr/bin/env python3
"""Test runner for model-based data generation.

This module provides a test runner that executes queries against the
generated data and reports metrics on the results.
"""

import logging
import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .metrics import SearchMetrics, RankedSearchMetrics
from .query_generator import QueryGenerator
from .enhanced_query_generator import ModelBasedQueryGenerator

try:
    from query.query_processing.nl_parser import NLParser
    from query.query_processing.query_translator.aql_translator import AQLTranslator
    from query.search_execution.query_executor.aql_executor import AQLExecutor
    from db.db_config import IndalekoDBConfig
except ImportError:
    logging.warning("Could not import query processing modules, using simplified test runner")
    NLParser = None
    AQLTranslator = None
    AQLExecutor = None
    IndalekoDBConfig = None


class ModelBasedTestRunner:
    """Test runner for model-based data generation."""

    def __init__(self, config: Dict[str, Any], truth_dataset: Dict[str, List[Dict[str, Any]]]):
        """Initialize a test runner.

        Args:
            config: Test configuration
            truth_dataset: Dictionary mapping categories to lists of truth records
        """
        self.config = config
        self.truth_dataset = truth_dataset
        self.logger = logging.getLogger(self.__class__.__name__)

        # Extract truth IDs by category
        self.truth_ids = self._extract_truth_ids()

        # Initialize components
        self.db_config = IndalekoDBConfig() if IndalekoDBConfig else None
        # Use model-based query generator by default
        self.query_generator = ModelBasedQueryGenerator(use_model_templates=True)

        if NLParser and AQLTranslator:
            self.nl_parser = NLParser()
            self.aql_translator = AQLTranslator()
        else:
            self.nl_parser = None
            self.aql_translator = None

        if AQLExecutor and self.db_config:
            self.aql_executor = AQLExecutor(self.db_config)
        else:
            self.aql_executor = None

        self.results = {}

    def _extract_truth_ids(self) -> Dict[str, Set[str]]:
        """Extract truth record IDs from the truth dataset.

        Returns:
            Dictionary mapping categories to sets of truth record IDs
        """
        truth_ids = {}

        for category, records in self.truth_dataset.items():
            id_field = self._get_id_field_for_category(category)

            truth_ids[category] = {
                record.get(id_field, "") for record in records if id_field in record
            }

        # Create a combined set of all truth IDs
        all_ids = set()
        for ids in truth_ids.values():
            all_ids.update(ids)

        truth_ids["all"] = all_ids

        return truth_ids

    def _get_id_field_for_category(self, category: str) -> str:
        """Get the ID field name for a category.

        Args:
            category: Category name

        Returns:
            ID field name
        """
        category_to_id_field = {
            "storage": "ObjectIdentifier",
            "semantic": "ObjectIdentifier",
            "activity": "Handle",
            "relationship": "_key",
            "machine_config": "MachineID"
        }

        return category_to_id_field.get(category, "ObjectIdentifier")

    def run_tests(self) -> Dict[str, Any]:
        """Run all tests defined in the configuration.

        Returns:
            Dictionary of test results
        """
        # Get test queries from configuration
        test_queries = self.config.get("query_patterns", [])
        if not test_queries:
            self.logger.warning("No test queries found in configuration")
            return {"error": "No test queries found in configuration"}

        results = {
            "tests": [],
            "timestamp": datetime.now().isoformat(),
            "truth_record_counts": {cat: len(ids) for cat, ids in self.truth_ids.items()},
            "summary": {}
        }

        # Run each test query
        for i, test_query in enumerate(test_queries):
            self.logger.info(f"Running test {i+1}/{len(test_queries)}: {test_query.get('description', 'Unknown test')}")

            test_result = self._run_test_query(test_query)
            results["tests"].append(test_result)

        # Compute summary metrics
        all_metrics = []
        for test in results["tests"]:
            if "metrics" in test:
                all_metrics.append(test["metrics"])

        if all_metrics:
            summary = {
                "avg_precision": sum(m.get("precision", 0) for m in all_metrics) / len(all_metrics),
                "avg_recall": sum(m.get("recall", 0) for m in all_metrics) / len(all_metrics),
                "avg_f1_score": sum(m.get("f1_score", 0) for m in all_metrics) / len(all_metrics),
                "total_tests": len(all_metrics),
                "passed_tests": sum(1 for m in all_metrics if m.get("f1_score", 0) > 0.5),
                "failed_tests": sum(1 for m in all_metrics if m.get("f1_score", 0) <= 0.5),
            }

            # Format as percentages
            summary["avg_precision"] = round(summary["avg_precision"] * 100, 2)
            summary["avg_recall"] = round(summary["avg_recall"] * 100, 2)
            summary["avg_f1_score"] = round(summary["avg_f1_score"] * 100, 2)

            results["summary"] = summary

        return results

    def _run_test_query(self, test_query: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test query.

        Args:
            test_query: Test query configuration

        Returns:
            Dictionary of test results
        """
        nl_query = test_query.get("nl_query", "")
        expected_truth = test_query.get("expected_truth", 0)
        tags = test_query.get("tags", [])

        if not nl_query:
            self.logger.warning("Empty query in test configuration")
            return {"error": "Empty query in test configuration"}

        result = {
            "query": nl_query,
            "expected_truth": expected_truth,
            "tags": tags,
        }

        try:
            # Generate AQL query
            start_time = time.time()
            aql_query = self._generate_aql_query(nl_query, tags)
            query_gen_time = time.time() - start_time

            result["aql_query"] = aql_query
            result["query_generation_time"] = query_gen_time

            # Execute query if we have an executor
            if self.aql_executor:
                start_time = time.time()
                query_results = self._execute_query(aql_query)
                query_exec_time = time.time() - start_time

                result["query_execution_time"] = query_exec_time
                result["result_count"] = len(query_results)

                # Extract result IDs
                result_ids = self._extract_result_ids(query_results)

                # Calculate metrics
                metrics = SearchMetrics(self.truth_ids["all"], result_ids)
                result["metrics"] = metrics.get_metrics()

                # Include top 5 results (truncated for readability)
                top_results = []
                for res in query_results[:5]:
                    # Create a simplified result view
                    simple_result = {}
                    for key in ["_key", "ObjectIdentifier", "Handle", "Label", "Name", "MachineID"]:
                        if key in res:
                            simple_result[key] = res[key]
                    top_results.append(simple_result)

                result["top_results"] = top_results

                # Record if the test passed (arbitrary threshold of F1 > 0.5)
                result["passed"] = metrics.f1_score > 0.5
            else:
                result["error"] = "Query executor not available"
        except Exception as e:
            self.logger.error(f"Error running test query: {e}", exc_info=True)
            result["error"] = str(e)
            result["passed"] = False

        return result

    def _generate_aql_query(self, nl_query: str, tags: List[str]) -> str:
        """Generate an AQL query from a natural language query.

        Args:
            nl_query: Natural language query
            tags: Query tags

        Returns:
            Generated AQL query
        """
        # If we have the NL parser and AQL translator, use them
        if self.nl_parser and self.aql_translator:
            try:
                # Parse the natural language query
                parsed_data = self.nl_parser.parse(nl_query)

                # Translate to AQL
                aql_query = self.aql_translator.translate(parsed_data)

                return aql_query
            except Exception as e:
                self.logger.error(f"Error generating AQL query with NL parser: {e}", exc_info=True)
                # Fall back to basic generator

        # Use basic query generator
        metadata_context = self._get_metadata_context_for_tags(tags)
        return self.query_generator.generate_from_nl(nl_query, metadata_context)

    def _get_metadata_context_for_tags(self, tags: List[str]) -> Dict[str, Any]:
        """Get metadata context based on query tags.

        Args:
            tags: Query tags

        Returns:
            Metadata context
        """
        context = {}

        # Set up context based on the first tag
        primary_tag = tags[0] if tags else "unknown"

        if primary_tag in ["time", "temporal", "temporal_fuzzy"]:
            context["start_time"] = (datetime.now() - datetime.timedelta(days=7)).timestamp()
            context["end_time"] = datetime.now().timestamp()

        elif primary_tag in ["geo_activity", "geolocation"]:
            context["latitude"] = 37.7749
            context["longitude"] = -122.4194
            context["radius"] = 10000

        elif primary_tag in ["posix", "filetype"]:
            context["extension"] = ".pdf"

        elif primary_tag in ["device", "machine_config"]:
            context["device_type"] = "laptop"

        return context

    def _execute_query(self, aql_query: str) -> List[Dict[str, Any]]:
        """Execute an AQL query.

        Args:
            aql_query: AQL query string

        Returns:
            List of query results
        """
        if not self.aql_executor:
            self.logger.warning("No AQL executor available")
            return []

        try:
            results = self.aql_executor.execute(aql_query)
            return results
        except Exception as e:
            self.logger.error(f"Error executing AQL query: {e}", exc_info=True)
            raise

    def _extract_result_ids(self, results: List[Dict[str, Any]]) -> Set[str]:
        """Extract IDs from query results.

        Args:
            results: Query results

        Returns:
            Set of result IDs
        """
        id_fields = ["ObjectIdentifier", "Handle", "_key", "MachineID"]
        result_ids = set()

        for result in results:
            # Try each ID field
            for field in id_fields:
                if field in result:
                    result_ids.add(result[field])
                    break

        return result_ids

    def save_results(self, output_path: Union[str, Path]) -> None:
        """Save test results to a file.

        Args:
            output_path: Path to save results to
        """
        output_path = Path(output_path)
        os.makedirs(output_path.parent, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2)

        self.logger.info(f"Test results saved to {output_path}")

    def generate_report(self, output_path: Union[str, Path], format: str = "md") -> None:
        """Generate a report from test results.

        Args:
            output_path: Path to save report to
            format: Report format (md, json, or csv)
        """
        from .reporter import TestReporter

        reporter = TestReporter(self.results)
        reporter.generate_report(output_path, format)


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
            format: Report format (md, json, or csv)
        """
        output_path = Path(output_path)
        os.makedirs(output_path.parent, exist_ok=True)

        if format == "json":
            self._generate_json_report(output_path)
        elif format == "csv":
            self._generate_csv_report(output_path)
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
        import csv

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
