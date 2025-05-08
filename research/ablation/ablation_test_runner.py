"""Runner for ablation experiments and results generation."""

import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

# Check for visualization dependencies
try:
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns

    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False

from .ablation_tester import AblationConfig, AblationTester
from .base import AblationResult


class AblationTestRunner:
    """Runner for executing ablation experiments and generating results.

    This class coordinates a set of ablation tests across multiple queries
    and collections, then aggregates and analyzes the results.
    """

    def __init__(self, output_dir: str = "./ablation_results"):
        """Initialize the ablation test runner.

        Args:
            output_dir: The directory to save results to.
        """
        self.logger = logging.getLogger(__name__)
        self.tester = AblationTester()
        self.output_dir = output_dir

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Results storage
        self.results: dict[str, dict[str, AblationResult]] = {}

    def run_single_test(
        self, query_id: uuid.UUID, query_text: str, config: AblationConfig,
    ) -> dict[str, AblationResult]:
        """Run a single ablation test for a specific query.

        Args:
            query_id: The UUID of the query.
            query_text: The text of the query.
            config: The ablation test configuration.

        Returns:
            Dict[str, AblationResult]: The results of the ablation test.
        """
        self.logger.info(f"Running ablation test for query: {query_text}")

        # Run the ablation test
        results = self.tester.run_ablation_test(config, query_id, query_text)

        # Store the results
        self.results[str(query_id)] = results

        return results

    def run_batch_tests(
        self,
        queries: list[dict[str, Any]],
        config: AblationConfig,
        max_queries: int = 10,
    ) -> dict[str, dict[str, AblationResult]]:
        """Run ablation tests for a batch of queries.

        Args:
            queries: List of query dicts with 'id' and 'text' keys.
            config: The ablation test configuration.
            max_queries: Maximum number of queries to test.

        Returns:
            Dict[str, Dict[str, AblationResult]]: The results of all ablation tests.
        """
        self.logger.info(f"Running batch ablation tests for {len(queries)} queries")

        # Limit the number of queries to test
        queries_to_test = queries[:max_queries]

        start_time = time.time()

        # Run tests for each query
        for i, query in enumerate(queries_to_test, 1):
            query_id = uuid.UUID(query["id"]) if isinstance(query["id"], str) else query["id"]
            query_text = query["text"]

            self.logger.info(f"Running test {i}/{len(queries_to_test)}: {query_text}")

            # Run the ablation test
            results = self.run_single_test(query_id, query_text, config)

            # Log progress
            if i % 5 == 0 or i == len(queries_to_test):
                elapsed = time.time() - start_time
                self.logger.info(f"Completed {i}/{len(queries_to_test)} tests in {elapsed:.2f} seconds")

        return self.results

    def calculate_aggregate_metrics(self) -> dict[str, dict[str, float]]:
        """Calculate aggregate metrics across all ablation tests.

        Returns:
            Dict[str, Dict[str, float]]: Aggregate metrics by collection.
        """
        if not self.results:
            self.logger.warning("No results to calculate aggregate metrics from")
            return {}

        # Initialize aggregate metrics
        aggregate_metrics: dict[str, dict[str, float]] = {}

        # Track metrics by collection
        for query_id, query_results in self.results.items():
            for collection_key, result in query_results.items():
                if collection_key not in aggregate_metrics:
                    aggregate_metrics[collection_key] = {
                        "precision_sum": 0.0,
                        "recall_sum": 0.0,
                        "f1_sum": 0.0,
                        "impact_sum": 0.0,
                        "count": 0,
                    }

                # Update metrics
                aggregate_metrics[collection_key]["precision_sum"] += result.precision
                aggregate_metrics[collection_key]["recall_sum"] += result.recall
                aggregate_metrics[collection_key]["f1_sum"] += result.f1_score
                aggregate_metrics[collection_key]["impact_sum"] += result.impact
                aggregate_metrics[collection_key]["count"] += 1

        # Calculate averages
        for collection_key, metrics in aggregate_metrics.items():
            count = metrics["count"]

            if count > 0:
                metrics["avg_precision"] = metrics["precision_sum"] / count
                metrics["avg_recall"] = metrics["recall_sum"] / count
                metrics["avg_f1"] = metrics["f1_sum"] / count
                metrics["avg_impact"] = metrics["impact_sum"] / count
            else:
                metrics["avg_precision"] = 0.0
                metrics["avg_recall"] = 0.0
                metrics["avg_f1"] = 0.0
                metrics["avg_impact"] = 0.0

        return aggregate_metrics

    def save_results_json(self, filename: str = "ablation_results.json") -> str:
        """Save raw ablation results to a JSON file.

        Args:
            filename: The name of the JSON file to save.

        Returns:
            str: The path to the saved file.
        """
        if not self.results:
            self.logger.warning("No results to save")
            return ""

        # Prepare results for serialization
        serializable_results = {}

        for query_id, query_results in self.results.items():
            serializable_results[query_id] = {}

            for collection_key, result in query_results.items():
                # Convert the result to a dict
                result_dict = result.dict()

                # Convert any UUID objects to strings
                for key, value in result_dict.items():
                    if isinstance(value, UUID):
                        result_dict[key] = str(value)

                serializable_results[query_id][collection_key] = result_dict

        # Save to file
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w") as f:
            json.dump(serializable_results, f, indent=2)

        self.logger.info(f"Saved results to {filepath}")

        return filepath

    def save_results_csv(self, filename: str = "ablation_results.csv") -> str:
        """Save ablation results to a CSV file.

        Args:
            filename: The name of the CSV file to save.

        Returns:
            str: The path to the saved file.
        """
        if not self.results:
            self.logger.warning("No results to save")
            return ""

        # Prepare data for DataFrame
        rows = []

        for query_id, query_results in self.results.items():
            for collection_key, result in query_results.items():
                row = {
                    "query_id": query_id,
                    "ablated_collection": result.ablated_collection,
                    "precision": result.precision,
                    "recall": result.recall,
                    "f1_score": result.f1_score,
                    "impact": result.impact,
                    "execution_time_ms": result.execution_time_ms,
                    "result_count": result.result_count,
                    "true_positives": result.true_positives,
                    "false_positives": result.false_positives,
                    "false_negatives": result.false_negatives,
                }

                rows.append(row)

        # Create DataFrame
        df = pd.DataFrame(rows)

        # Save to file
        filepath = os.path.join(self.output_dir, filename)

        df.to_csv(filepath, index=False)

        self.logger.info(f"Saved results to {filepath}")

        return filepath

    def generate_summary_report(self, filename: str = "ablation_summary.md") -> str:
        """Generate a summary report of ablation results.

        Args:
            filename: The name of the Markdown file to save.

        Returns:
            str: The path to the saved file.
        """
        if not self.results:
            self.logger.warning("No results to generate summary from")
            return ""

        # Calculate aggregate metrics
        aggregate_metrics = self.calculate_aggregate_metrics()

        # Generate summary report
        report = []

        # Add header
        report.append("# Ablation Study Results Summary")
        report.append("")

        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report.append(f"Generated: {timestamp}")
        report.append("")

        # Add overview
        report.append("## Overview")
        report.append("")
        report.append(f"Total Queries: {len(self.results)}")
        report.append(
            f"Collections Tested: {len({k.split('_impact_on_')[0] for k in aggregate_metrics.keys() if '_impact_on_' in k})}",
        )
        report.append("")

        # Add aggregate metrics table
        report.append("## Aggregate Metrics")
        report.append("")
        report.append("| Ablated Collection | Avg Precision | Avg Recall | Avg F1 Score | Avg Impact |")
        report.append("|-------------------|--------------|-----------|-------------|-----------|")

        # Get unique collections
        collections = set()
        for collection_key in aggregate_metrics.keys():
            if "_impact_on_" in collection_key:
                ablated_coll = collection_key.split("_impact_on_")[0]
                collections.add(ablated_coll)

        # Sort by impact
        collection_impact = {}
        for collection in collections:
            impact_sum = 0.0
            count = 0

            for collection_key, metrics in aggregate_metrics.items():
                if collection_key.startswith(f"{collection}_impact_on_"):
                    impact_sum += metrics["avg_impact"]
                    count += 1

            collection_impact[collection] = impact_sum / count if count > 0 else 0.0

        sorted_collections = sorted(collection_impact.items(), key=lambda x: x[1], reverse=True)

        # Add rows for each collection
        for collection, impact in sorted_collections:
            precision_sum = 0.0
            recall_sum = 0.0
            f1_sum = 0.0
            count = 0

            for collection_key, metrics in aggregate_metrics.items():
                if collection_key.startswith(f"{collection}_impact_on_"):
                    precision_sum += metrics["avg_precision"]
                    recall_sum += metrics["avg_recall"]
                    f1_sum += metrics["avg_f1"]
                    count += 1

            avg_precision = precision_sum / count if count > 0 else 0.0
            avg_recall = recall_sum / count if count > 0 else 0.0
            avg_f1 = f1_sum / count if count > 0 else 0.0

            report.append(f"| {collection} | {avg_precision:.4f} | {avg_recall:.4f} | {avg_f1:.4f} | {impact:.4f} |")

        report.append("")

        # Add interpretation
        report.append("## Interpretation")
        report.append("")
        report.append(
            "The **Impact** score measures how much performance degrades when a collection is ablated. Higher impact scores indicate greater importance of the collection to query results.",
        )
        report.append("")

        # Add recommendations
        report.append("## Recommendations")
        report.append("")

        # Sort collections by impact for recommendations
        if sorted_collections:
            # Highest impact collection
            highest_collection, highest_impact = sorted_collections[0]
            report.append(
                f"1. The **{highest_collection}** collection has the highest impact ({highest_impact:.4f}) on query results. This suggests this activity type provides critical context for search relevance.",
            )
            report.append("")

            # Low impact collections
            low_impact_collections = [c for c, i in sorted_collections if i < 0.1]
            if low_impact_collections:
                report.append(
                    "2. The following collections have low impact (< 0.1) and may be candidates for optimization or reduction in storage footprint:",
                )
                for collection in low_impact_collections:
                    report.append(f"   - {collection}")
                report.append("")

            # Highest precision collection
            precision_collections = [
                (c, aggregate_metrics.get(f"{c}_impact_on_AblationLocationActivity", {}).get("avg_precision", 0))
                for c, _ in sorted_collections
            ]
            precision_collections.sort(key=lambda x: x[1], reverse=True)

            if precision_collections:
                highest_precision_collection, highest_precision = precision_collections[0]
                report.append(
                    f"3. The **{highest_precision_collection}** collection contributes most to search precision ({highest_precision:.4f}), indicating it helps reduce false positives.",
                )
                report.append("")

            # Highest recall collection
            recall_collections = [
                (c, aggregate_metrics.get(f"{c}_impact_on_AblationLocationActivity", {}).get("avg_recall", 0))
                for c, _ in sorted_collections
            ]
            recall_collections.sort(key=lambda x: x[1], reverse=True)

            if recall_collections:
                highest_recall_collection, highest_recall = recall_collections[0]
                report.append(
                    f"4. The **{highest_recall_collection}** collection contributes most to search recall ({highest_recall:.4f}), indicating it helps reduce false negatives.",
                )
                report.append("")

        # Save to file
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w") as f:
            f.write("\n".join(report))

        self.logger.info(f"Generated summary report at {filepath}")

        return filepath

    def generate_visualizations(self) -> list[str]:
        """Generate visualizations of ablation results.

        Returns:
            List[str]: The paths to the saved visualizations.
        """
        if not self.results:
            self.logger.warning("No results to generate visualizations from")
            return []

        # Check if visualization dependencies are available
        if not VISUALIZATION_AVAILABLE:
            self.logger.warning("Visualization dependencies (pandas, matplotlib, seaborn) not available")
            self.logger.warning("Install with: pip install pandas matplotlib seaborn")
            return []

        # Set up seaborn
        sns.set(style="whitegrid")

        # Create a dataframe from the results
        rows = []

        for query_id, query_results in self.results.items():
            for collection_key, result in query_results.items():
                # Only include impact results
                if "_impact_on_" in collection_key:
                    ablated, target = collection_key.split("_impact_on_")

                    row = {
                        "query_id": query_id,
                        "ablated_collection": ablated,
                        "target_collection": target,
                        "precision": result.precision,
                        "recall": result.recall,
                        "f1_score": result.f1_score,
                        "impact": result.impact,
                    }

                    rows.append(row)

        df = pd.DataFrame(rows)

        # Check if we have enough data
        if len(df) == 0:
            self.logger.warning("Not enough data to generate visualizations")
            return []

        saved_files = []

        # 1. Impact by collection barplot
        try:
            plt.figure(figsize=(10, 6))
            impact_by_collection = df.groupby("ablated_collection")["impact"].mean().reset_index()
            impact_by_collection = impact_by_collection.sort_values("impact", ascending=False)

            ax = sns.barplot(x="ablated_collection", y="impact", data=impact_by_collection)
            plt.title("Average Impact by Ablated Collection")
            plt.xlabel("Ablated Collection")
            plt.ylabel("Impact Score (higher = more important)")
            plt.xticks(rotation=45)
            plt.tight_layout()

            # Save figure
            impact_plot_path = os.path.join(self.output_dir, "impact_by_collection.png")
            plt.savefig(impact_plot_path)
            plt.close()

            saved_files.append(impact_plot_path)
        except Exception as e:
            self.logger.error(f"Failed to generate impact barplot: {e}")

        # 2. Metrics heatmap
        try:
            plt.figure(figsize=(15, 8))

            # Reshape data for heatmap
            heatmap_data = df.pivot_table(
                index="ablated_collection", columns="target_collection", values="impact", aggfunc="mean",
            )

            ax = sns.heatmap(heatmap_data, annot=True, cmap="YlGnBu", fmt=".3f", linewidths=0.5)
            plt.title("Impact of Ablating One Collection on Others")
            plt.xlabel("Target Collection")
            plt.ylabel("Ablated Collection")
            plt.tight_layout()

            # Save figure
            heatmap_path = os.path.join(self.output_dir, "impact_heatmap.png")
            plt.savefig(heatmap_path)
            plt.close()

            saved_files.append(heatmap_path)
        except Exception as e:
            self.logger.error(f"Failed to generate heatmap: {e}")

        # 3. Precision-Recall scatter plot
        try:
            plt.figure(figsize=(10, 8))

            ax = sns.scatterplot(
                x="precision", y="recall", hue="ablated_collection", size="impact", sizes=(50, 200), data=df,
            )
            plt.title("Precision vs Recall by Ablated Collection")
            plt.xlabel("Precision")
            plt.ylabel("Recall")
            plt.grid(True)
            plt.tight_layout()

            # Save figure
            pr_path = os.path.join(self.output_dir, "precision_recall.png")
            plt.savefig(pr_path)
            plt.close()

            saved_files.append(pr_path)
        except Exception as e:
            self.logger.error(f"Failed to generate precision-recall plot: {e}")

        # 4. F1 score by collection
        try:
            plt.figure(figsize=(10, 6))
            f1_by_collection = df.groupby("ablated_collection")["f1_score"].mean().reset_index()
            f1_by_collection = f1_by_collection.sort_values("f1_score", ascending=True)  # Lower F1 = higher impact

            ax = sns.barplot(x="ablated_collection", y="f1_score", data=f1_by_collection)
            plt.title("Average F1 Score by Ablated Collection")
            plt.xlabel("Ablated Collection")
            plt.ylabel("F1 Score (lower = higher impact)")
            plt.xticks(rotation=45)
            plt.tight_layout()

            # Save figure
            f1_plot_path = os.path.join(self.output_dir, "f1_by_collection.png")
            plt.savefig(f1_plot_path)
            plt.close()

            saved_files.append(f1_plot_path)
        except Exception as e:
            self.logger.error(f"Failed to generate F1 barplot: {e}")

        return saved_files

    def cleanup(self) -> None:
        """Clean up resources used by the test runner."""
        self.tester.cleanup()
