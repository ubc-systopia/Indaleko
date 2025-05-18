"""
Metrics calculation for the ablation study framework.

This module provides functionality for calculating precision, recall, F1,
and other metrics for evaluating query performance with and without ablation.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Union

class MetricsCalculator:
    """Calculator for ablation test metrics.

    This class calculates precision, recall, F1, and other metrics
    for evaluating query performance with and without ablation.
    """

    def __init__(self):
        """Initialize the metrics calculator."""
        self.logger = logging.getLogger(__name__)

    def calculate_query_metrics(self, truth_ids: List[str], result_ids: List[str]) -> Dict[str, float]:
        """Calculate metrics for a single query.

        Args:
            truth_ids: List of identifiers that should match the query
            result_ids: List of identifiers returned by the query

        Returns:
            Dictionary with precision, recall, and F1 scores
        """
        truth_set = set(truth_ids)
        result_set = set(result_ids)

        # Calculate true positives, false positives, and false negatives
        true_positives = len(truth_set.intersection(result_set))
        false_positives = len(result_set - truth_set)
        false_negatives = len(truth_set - result_set)

        # Calculate precision, recall, and F1
        precision = true_positives / (true_positives + false_positives) if true_positives + false_positives > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if true_positives + false_negatives > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "truth_count": len(truth_set),
            "result_count": len(result_set)
        }

    def calculate_impact_score(self, baseline_metrics: Dict[str, float],
                              ablated_metrics: Dict[str, float]) -> float:
        """Calculate the impact score of ablation on query performance.

        The impact score is the percentage decrease in F1 score when a
        collection is ablated compared to the baseline.

        Args:
            baseline_metrics: Metrics with all collections available
            ablated_metrics: Metrics with a collection ablated

        Returns:
            Impact score as a percentage (0-100)
        """
        baseline_f1 = baseline_metrics.get("f1", 0.0)
        ablated_f1 = ablated_metrics.get("f1", 0.0)

        if baseline_f1 == 0.0:
            return 0.0

        # Calculate percentage decrease in F1 score
        impact = (baseline_f1 - ablated_f1) / baseline_f1 * 100.0

        # Ensure impact is not negative
        return max(0.0, impact)

    def create_metrics_record(self, query_id: str, query_text: str,
                             baseline_metrics: Dict[str, float],
                             ablated_metrics: Dict[str, float],
                             ablated_collection: str) -> Dict[str, Any]:
        """Create a metrics record for a query with and without ablation.

        Args:
            query_id: The identifier for the query
            query_text: The natural language query
            baseline_metrics: Metrics with all collections available
            ablated_metrics: Metrics with a collection ablated
            ablated_collection: The name of the ablated collection

        Returns:
            Metrics record dictionary
        """
        impact_score = self.calculate_impact_score(baseline_metrics, ablated_metrics)

        return {
            "query_id": query_id,
            "query_text": query_text,
            "baseline_precision": baseline_metrics.get("precision", 0.0),
            "baseline_recall": baseline_metrics.get("recall", 0.0),
            "baseline_f1": baseline_metrics.get("f1", 0.0),
            "ablated_precision": ablated_metrics.get("precision", 0.0),
            "ablated_recall": ablated_metrics.get("recall", 0.0),
            "ablated_f1": ablated_metrics.get("f1", 0.0),
            "ablated_collection": ablated_collection,
            "impact_score": impact_score,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def calculate_aggregate_metrics(self, metrics_records: List[Dict[str, Any]],
                                  group_by: str = "ablated_collection") -> Dict[str, Any]:
        """Calculate aggregate metrics across multiple queries.

        Args:
            metrics_records: List of metrics records
            group_by: Field to group records by (e.g., "ablated_collection")

        Returns:
            Dictionary with aggregate metrics grouped by the specified field
        """
        if not metrics_records:
            return {}

        # Group records by the specified field
        groups = {}
        for record in metrics_records:
            group_key = record.get(group_by)
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(record)

        # Calculate aggregate metrics for each group
        aggregate_metrics = {}
        for group_key, group_records in groups.items():
            avg_baseline_precision = sum(r.get("baseline_precision", 0.0) for r in group_records) / len(group_records)
            avg_baseline_recall = sum(r.get("baseline_recall", 0.0) for r in group_records) / len(group_records)
            avg_baseline_f1 = sum(r.get("baseline_f1", 0.0) for r in group_records) / len(group_records)
            avg_ablated_precision = sum(r.get("ablated_precision", 0.0) for r in group_records) / len(group_records)
            avg_ablated_recall = sum(r.get("ablated_recall", 0.0) for r in group_records) / len(group_records)
            avg_ablated_f1 = sum(r.get("ablated_f1", 0.0) for r in group_records) / len(group_records)
            avg_impact_score = sum(r.get("impact_score", 0.0) for r in group_records) / len(group_records)

            aggregate_metrics[group_key] = {
                "avg_baseline_precision": avg_baseline_precision,
                "avg_baseline_recall": avg_baseline_recall,
                "avg_baseline_f1": avg_baseline_f1,
                "avg_ablated_precision": avg_ablated_precision,
                "avg_ablated_recall": avg_ablated_recall,
                "avg_ablated_f1": avg_ablated_f1,
                "avg_impact_score": avg_impact_score,
                "query_count": len(group_records)
            }

        return aggregate_metrics

    def save_metrics(self, metrics_records: List[Dict[str, Any]], output_path: Path) -> None:
        """Save metrics records to a file.

        Args:
            metrics_records: List of metrics records
            output_path: Path to save the metrics to
        """
        try:
            with open(output_path, 'w') as f:
                json.dump(metrics_records, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving metrics: {e}")

    def load_metrics(self, input_path: Path) -> List[Dict[str, Any]]:
        """Load metrics records from a file.

        Args:
            input_path: Path to load the metrics from

        Returns:
            List of metrics records
        """
        try:
            with open(input_path, 'r') as f:
                metrics_records = json.load(f)
            return metrics_records
        except Exception as e:
            self.logger.error(f"Error loading metrics: {e}")
            return []

    def generate_metrics_report(self, metrics_records: List[Dict[str, Any]],
                               output_path: Optional[Path] = None) -> str:
        """Generate a human-readable report of metrics.

        Args:
            metrics_records: List of metrics records
            output_path: Optional path to save the report to

        Returns:
            Report string
        """
        if not metrics_records:
            return "No metrics records available."

        # Calculate aggregate metrics by ablated collection
        aggregate_metrics = self.calculate_aggregate_metrics(metrics_records)

        # Generate report
        report = "# Ablation Study Metrics Report\n\n"
        report += f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n"

        report += "## Aggregate Metrics by Collection\n\n"
        report += "| Collection | Avg Impact | Baseline F1 | Ablated F1 | Queries |\n"
        report += "|------------|------------|-------------|------------|--------|\n"

        # Sort collections by average impact score
        sorted_collections = sorted(aggregate_metrics.keys(),
                                   key=lambda k: aggregate_metrics[k]["avg_impact_score"],
                                   reverse=True)

        for collection in sorted_collections:
            metrics = aggregate_metrics[collection]
            report += f"| {collection} | {metrics['avg_impact_score']:.2f}% | "
            report += f"{metrics['avg_baseline_f1']:.4f} | {metrics['avg_ablated_f1']:.4f} | "
            report += f"{metrics['query_count']} |\n"

        report += "\n## Detailed Query Metrics\n\n"

        # Group queries by ablated collection
        queries_by_collection = {}
        for record in metrics_records:
            collection = record.get("ablated_collection")
            if collection not in queries_by_collection:
                queries_by_collection[collection] = []
            queries_by_collection[collection].append(record)

        for collection in sorted_collections:
            report += f"### Collection: {collection}\n\n"
            report += "| Query | Impact | Baseline F1 | Ablated F1 |\n"
            report += "|-------|--------|-------------|------------|\n"

            # Sort queries by impact score
            sorted_queries = sorted(queries_by_collection[collection],
                                   key=lambda q: q.get("impact_score", 0.0),
                                   reverse=True)

            for record in sorted_queries:
                query_text = record.get("query_text", "Unknown")
                if len(query_text) > 60:
                    query_text = query_text[:57] + "..."

                report += f"| {query_text} | {record.get('impact_score', 0.0):.2f}% | "
                report += f"{record.get('baseline_f1', 0.0):.4f} | {record.get('ablated_f1', 0.0):.4f} |\n"

            report += "\n"

        # Save report if output path is provided
        if output_path:
            try:
                with open(output_path, 'w') as f:
                    f.write(report)
            except Exception as e:
                self.logger.error(f"Error saving report: {e}")

        return report
