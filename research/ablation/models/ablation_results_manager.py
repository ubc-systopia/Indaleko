"""
Ablation Results Manager for the experimental ablation framework.

This module handles the storage, analysis, and visualization of ablation test results.
It supports the experimental design with control/test groups and generates publication-quality
insights and visualizations for comprehensive analysis.
"""

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure

from research.ablation.models.ablation_results import MetricType


class AblationResultsManager:
    """
    Manager for ablation test results.

    This class handles:
    1. Storing and retrieving test results
    2. Analyzing results to compute metrics
    3. Generating visualizations and reports
    4. Comparing results across different ablation configurations
    5. Supporting the experimental design with control/test groups
    """

    def __init__(self, output_dir: str = "ablation_results"):
        """
        Initialize the results manager.

        Args:
            output_dir: Directory to store results and visualizations
        """
        self.logger = logging.getLogger(__name__)
        self.output_dir = output_dir

        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(exist_ok=True, parents=True)

        # Initialize SQLite database for results
        self.db_path = os.path.join(output_dir, "ablation_results.db")
        self.initialize_database()

        # Track active experiments
        self.active_experiments = {}
        self.experiment_configurations = {}

    def initialize_database(self):
        """Initialize the SQLite database for storing results."""
        self.logger.info(f"Initializing results database at {self.db_path}")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create tables if they don't exist
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS ablation_results (
            id TEXT PRIMARY KEY,
            test_id TEXT,
            experiment_id TEXT,
            ablation_id TEXT,
            query_id TEXT,
            query_text TEXT,
            ablated_collection TEXT,
            timestamp TEXT,
            baseline_precision REAL,
            baseline_recall REAL,
            baseline_f1 REAL,
            ablated_precision REAL,
            ablated_recall REAL,
            ablated_f1 REAL,
            impact_precision REAL,
            impact_recall REAL,
            impact_f1 REAL,
            baseline_result_count INTEGER,
            ablated_result_count INTEGER,
            execution_time_ms REAL,
            metadata TEXT
        )
        """,
        )

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS experiment_metadata (
            id TEXT PRIMARY KEY,
            experiment_id TEXT,
            iteration_id TEXT,
            control_group TEXT,
            test_group TEXT,
            timestamp TEXT,
            description TEXT,
            configuration TEXT
        )
        """,
        )

        # Commit and close
        conn.commit()
        conn.close()

    def record_experiment_configuration(
        self, iteration_id: str, control_group: list[str], test_group: list[str], description: str = "",
    ):
        """
        Record the configuration of an experiment.

        Args:
            iteration_id: Identifier for the experiment iteration
            control_group: List of activity types in the control group
            test_group: List of activity types in the test group
            description: Optional description of the experiment
        """
        experiment_id = str(uuid.uuid4())
        self.experiment_configurations[experiment_id] = {
            "iteration_id": iteration_id,
            "control_group": control_group,
            "test_group": test_group,
            "timestamp": datetime.now().isoformat(),
            "description": description,
        }

        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO experiment_metadata (
                id, experiment_id, iteration_id, control_group, test_group,
                timestamp, description, configuration
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                experiment_id,
                iteration_id,
                json.dumps(control_group),
                json.dumps(test_group),
                datetime.now().isoformat(),
                description,
                json.dumps(self.experiment_configurations[experiment_id]),
            ),
        )

        conn.commit()
        conn.close()

        return experiment_id

    def store_ablation_result(
        self,
        experiment_id: str,
        ablation_id: str,
        query_id: str,
        query_text: str,
        ablated_collection: str,
        baseline_metrics: dict[str, float],
        ablated_metrics: dict[str, float],
        impact_metrics: dict[str, float],
        baseline_result_count: int,
        ablated_result_count: int,
        execution_time_ms: float,
        metadata: dict[str, Any] = None,
    ):
        """
        Store the result of an ablation test.

        Args:
            experiment_id: Identifier for the experiment
            ablation_id: Identifier for the ablation configuration
            query_id: Identifier for the query
            query_text: Text of the query
            ablated_collection: Name of the ablated collection
            baseline_metrics: Performance metrics before ablation
            ablated_metrics: Performance metrics after ablation
            impact_metrics: Impact of ablation (difference between baseline and ablated)
            baseline_result_count: Number of results returned before ablation
            ablated_result_count: Number of results returned after ablation
            execution_time_ms: Execution time in milliseconds
            metadata: Additional metadata
        """
        if metadata is None:
            metadata = {}

        result_id = str(uuid.uuid4())
        test_id = str(uuid.uuid4())

        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO ablation_results (
                id, test_id, experiment_id, ablation_id, query_id, query_text, ablated_collection,
                timestamp, baseline_precision, baseline_recall, baseline_f1,
                ablated_precision, ablated_recall, ablated_f1,
                impact_precision, impact_recall, impact_f1,
                baseline_result_count, ablated_result_count, execution_time_ms, metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result_id,
                test_id,
                experiment_id,
                ablation_id,
                query_id,
                query_text,
                ablated_collection,
                datetime.now().isoformat(),
                baseline_metrics.get(MetricType.PRECISION, 0.0),
                baseline_metrics.get(MetricType.RECALL, 0.0),
                baseline_metrics.get(MetricType.F1_SCORE, 0.0),
                ablated_metrics.get(MetricType.PRECISION, 0.0),
                ablated_metrics.get(MetricType.RECALL, 0.0),
                ablated_metrics.get(MetricType.F1_SCORE, 0.0),
                impact_metrics.get(MetricType.PRECISION, 0.0),
                impact_metrics.get(MetricType.RECALL, 0.0),
                impact_metrics.get(MetricType.F1_SCORE, 0.0),
                baseline_result_count,
                ablated_result_count,
                execution_time_ms,
                json.dumps(metadata),
            ),
        )

        conn.commit()
        conn.close()

        return result_id

    def get_results_for_experiment(self, experiment_id: str) -> pd.DataFrame:
        """
        Get all results for a specific experiment.

        Args:
            experiment_id: Identifier for the experiment

        Returns:
            DataFrame containing the results
        """
        conn = sqlite3.connect(self.db_path)

        query = f"""
        SELECT * FROM ablation_results
        WHERE experiment_id = '{experiment_id}'
        """

        df = pd.read_sql_query(query, conn)
        conn.close()

        return df

    def get_experiment_configuration(self, experiment_id: str) -> dict:
        """
        Get the configuration for a specific experiment.

        Args:
            experiment_id: Identifier for the experiment

        Returns:
            Dictionary containing the experiment configuration
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT configuration FROM experiment_metadata
            WHERE experiment_id = ?
            """,
            (experiment_id,),
        )

        result = cursor.fetchone()
        conn.close()

        if result:
            return json.loads(result[0])

        return {}

    def generate_precision_recall_plot(self, experiment_id: str = None) -> Figure:
        """
        Generate a precision-recall plot for the experiment.

        Args:
            experiment_id: Identifier for the experiment (if None, use all experiments)

        Returns:
            Matplotlib figure
        """
        conn = sqlite3.connect(self.db_path)

        if experiment_id:
            query = f"""
            SELECT ablated_collection, AVG(ablated_precision) as precision,
                   AVG(ablated_recall) as recall, AVG(ablated_f1) as f1
            FROM ablation_results
            WHERE experiment_id = '{experiment_id}'
            GROUP BY ablated_collection
            """
        else:
            query = """
            SELECT ablated_collection, AVG(ablated_precision) as precision,
                   AVG(ablated_recall) as recall, AVG(ablated_f1) as f1
            FROM ablation_results
            GROUP BY ablated_collection
            """

        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            self.logger.warning("No data available for precision-recall plot")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, "No data available", ha="center", va="center", fontsize=12)
            return fig

        # Create the plot
        fig, ax = plt.subplots(figsize=(10, 6))

        # Extract collection names without the prefix
        df["collection_name"] = df["ablated_collection"].apply(
            lambda x: x.replace("Indaleko_Ablation_", "").replace("_Activity_Collection", ""),
        )

        # Plot each point
        scatter = ax.scatter(df["recall"], df["precision"], s=100, c=df.index, cmap="viridis", alpha=0.7)

        # Add labels for each point
        for i, row in df.iterrows():
            ax.annotate(
                row["collection_name"],
                (row["recall"], row["precision"]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=10,
            )

        # Add baseline (no ablation) if available
        baseline_query = """
        SELECT AVG(baseline_precision) as precision, AVG(baseline_recall) as recall
        FROM ablation_results
        """
        if experiment_id:
            baseline_query += f" WHERE experiment_id = '{experiment_id}'"

        baseline_df = pd.read_sql_query(baseline_query, conn)

        if not baseline_df.empty and baseline_df["precision"].iloc[0] is not None:
            ax.scatter(
                baseline_df["recall"],
                baseline_df["precision"],
                s=150,
                c="red",
                marker="*",
                label="Baseline (No Ablation)",
            )
            ax.annotate(
                "Baseline",
                (baseline_df["recall"].iloc[0], baseline_df["precision"].iloc[0]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=10,
                fontweight="bold",
            )

        # Set plot aesthetics
        ax.set_xlabel("Recall", fontsize=12)
        ax.set_ylabel("Precision", fontsize=12)
        ax.set_xlim(0, 1.05)
        ax.set_ylim(0, 1.05)
        ax.grid(True, alpha=0.3)

        title = "Precision-Recall Performance by Ablated Collection"
        if experiment_id:
            config = self.get_experiment_configuration(experiment_id)
            if config and "iteration_id" in config:
                title += f" - Iteration {config['iteration_id']}"

        ax.set_title(title, fontsize=14)

        # Add F1 score contours
        f1_levels = [0.2, 0.4, 0.6, 0.8, 0.9]
        x = np.linspace(0.01, 1, 100)

        for f1 in f1_levels:
            y = (f1 * x) / (2 * x - f1)
            valid_mask = (y >= 0) & (y <= 1)
            ax.plot(x[valid_mask], y[valid_mask], "--", color="gray", alpha=0.5)
            # Find a suitable point to place the label
            mid_idx = np.where(valid_mask)[0][len(np.where(valid_mask)[0]) // 2]
            ax.annotate(f"F1={f1}", (x[mid_idx], y[mid_idx]), fontsize=8, color="gray")

        # Save the figure
        plt.tight_layout()
        fig.savefig(os.path.join(self.output_dir, "precision_recall.png"), dpi=300)

        return fig

    def generate_impact_heatmap(self, experiment_id: str = None) -> Figure:
        """
        Generate a heatmap showing the impact of ablating each collection.

        Args:
            experiment_id: Identifier for the experiment (if None, use all experiments)

        Returns:
            Matplotlib figure
        """
        conn = sqlite3.connect(self.db_path)

        if experiment_id:
            query = f"""
            SELECT ablated_collection,
                   AVG(impact_precision) as impact_precision,
                   AVG(impact_recall) as impact_recall,
                   AVG(impact_f1) as impact_f1
            FROM ablation_results
            WHERE experiment_id = '{experiment_id}'
            GROUP BY ablated_collection
            """
        else:
            query = """
            SELECT ablated_collection,
                   AVG(impact_precision) as impact_precision,
                   AVG(impact_recall) as impact_recall,
                   AVG(impact_f1) as impact_f1
            FROM ablation_results
            GROUP BY ablated_collection
            """

        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            self.logger.warning("No data available for impact heatmap")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, "No data available", ha="center", va="center", fontsize=12)
            return fig

        # Extract collection names without the prefix
        df["collection_name"] = df["ablated_collection"].apply(
            lambda x: x.replace("Indaleko_Ablation_", "").replace("_Activity_Collection", ""),
        )

        # Prepare data for heatmap
        pivot_df = df.set_index("collection_name")
        impact_df = pivot_df[["impact_precision", "impact_recall", "impact_f1"]]

        # Rename columns for readability
        impact_df.columns = ["Precision Impact", "Recall Impact", "F1 Impact"]

        # Create heatmap
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(impact_df, cmap="RdBu_r", center=0, annot=True, fmt=".3f", linewidths=0.5, ax=ax)

        title = "Impact of Ablating Collections on Performance Metrics"
        if experiment_id:
            config = self.get_experiment_configuration(experiment_id)
            if config and "iteration_id" in config:
                title += f" - Iteration {config['iteration_id']}"

        ax.set_title(title, fontsize=14)

        # Save the figure
        plt.tight_layout()
        fig.savefig(os.path.join(self.output_dir, "impact_heatmap.png"), dpi=300)

        return fig

    def generate_f1_by_collection(self, experiment_id: str = None) -> Figure:
        """
        Generate a bar chart showing F1 scores by collection.

        Args:
            experiment_id: Identifier for the experiment (if None, use all experiments)

        Returns:
            Matplotlib figure
        """
        conn = sqlite3.connect(self.db_path)

        if experiment_id:
            query = f"""
            SELECT ablated_collection, AVG(ablated_f1) as f1
            FROM ablation_results
            WHERE experiment_id = '{experiment_id}'
            GROUP BY ablated_collection
            """

            # Also get baseline F1
            baseline_query = f"""
            SELECT AVG(baseline_f1) as baseline_f1
            FROM ablation_results
            WHERE experiment_id = '{experiment_id}'
            """
        else:
            query = """
            SELECT ablated_collection, AVG(ablated_f1) as f1
            FROM ablation_results
            GROUP BY ablated_collection
            """

            # Also get baseline F1
            baseline_query = """
            SELECT AVG(baseline_f1) as baseline_f1
            FROM ablation_results
            """

        df = pd.read_sql_query(query, conn)
        baseline_df = pd.read_sql_query(baseline_query, conn)
        conn.close()

        if df.empty:
            self.logger.warning("No data available for F1 by collection plot")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, "No data available", ha="center", va="center", fontsize=12)
            return fig

        # Extract collection names without the prefix
        df["collection_name"] = df["ablated_collection"].apply(
            lambda x: x.replace("Indaleko_Ablation_", "").replace("_Activity_Collection", ""),
        )

        # Sort by F1 score
        df = df.sort_values("f1")

        # Create bar chart
        fig, ax = plt.subplots(figsize=(12, 6))

        bars = ax.barh(df["collection_name"], df["f1"], color="skyblue")

        # Add baseline line if available
        if not baseline_df.empty and baseline_df["baseline_f1"].iloc[0] is not None:
            baseline_f1 = baseline_df["baseline_f1"].iloc[0]
            ax.axvline(x=baseline_f1, color="red", linestyle="--", label=f"Baseline F1: {baseline_f1:.3f}")
            ax.legend()

        # Add value labels
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.text(width + 0.01, bar.get_y() + bar.get_height() / 2, f"{width:.3f}", ha="left", va="center")

        title = "F1 Score by Ablated Collection"
        if experiment_id:
            config = self.get_experiment_configuration(experiment_id)
            if config and "iteration_id" in config:
                title += f" - Iteration {config['iteration_id']}"

        ax.set_title(title, fontsize=14)
        ax.set_xlabel("F1 Score", fontsize=12)
        ax.set_ylabel("Ablated Collection", fontsize=12)
        ax.set_xlim(0, 1.05)
        ax.grid(True, axis="x", alpha=0.3)

        # Save the figure
        plt.tight_layout()
        fig.savefig(os.path.join(self.output_dir, "f1_by_collection.png"), dpi=300)

        return fig

    def generate_impact_by_collection(self, experiment_id: str = None) -> Figure:
        """
        Generate a bar chart showing the impact on F1 score by collection.

        Args:
            experiment_id: Identifier for the experiment (if None, use all experiments)

        Returns:
            Matplotlib figure
        """
        conn = sqlite3.connect(self.db_path)

        if experiment_id:
            query = f"""
            SELECT ablated_collection, AVG(impact_f1) as impact_f1
            FROM ablation_results
            WHERE experiment_id = '{experiment_id}'
            GROUP BY ablated_collection
            ORDER BY impact_f1 DESC
            """
        else:
            query = """
            SELECT ablated_collection, AVG(impact_f1) as impact_f1
            FROM ablation_results
            GROUP BY ablated_collection
            ORDER BY impact_f1 DESC
            """

        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            self.logger.warning("No data available for impact by collection plot")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, "No data available", ha="center", va="center", fontsize=12)
            return fig

        # Extract collection names without the prefix
        df["collection_name"] = df["ablated_collection"].apply(
            lambda x: x.replace("Indaleko_Ablation_", "").replace("_Activity_Collection", ""),
        )

        # Create bar chart
        fig, ax = plt.subplots(figsize=(12, 6))

        # Use different colors based on whether impact is positive or negative
        colors = ["red" if x < 0 else "green" for x in df["impact_f1"]]

        bars = ax.barh(df["collection_name"], df["impact_f1"], color=colors)

        # Add reference line at 0
        ax.axvline(x=0, color="black", linestyle="-", linewidth=0.5)

        # Add value labels
        for i, bar in enumerate(bars):
            width = bar.get_width()
            label_x = width + 0.01 if width >= 0 else width - 0.01
            ha = "left" if width >= 0 else "right"
            ax.text(label_x, bar.get_y() + bar.get_height() / 2, f"{width:.3f}", ha=ha, va="center")

        title = "Impact on F1 Score by Ablated Collection"
        if experiment_id:
            config = self.get_experiment_configuration(experiment_id)
            if config and "iteration_id" in config:
                title += f" - Iteration {config['iteration_id']}"

        ax.set_title(title, fontsize=14)
        ax.set_xlabel("Impact on F1 Score (Negative = Worse Performance)", fontsize=12)
        ax.set_ylabel("Ablated Collection", fontsize=12)
        ax.grid(True, axis="x", alpha=0.3)

        # Find appropriate limits
        max_abs = max(abs(df["impact_f1"].max()), abs(df["impact_f1"].min()))
        ax.set_xlim(-max_abs * 1.1, max_abs * 1.1)

        # Save the figure
        plt.tight_layout()
        fig.savefig(os.path.join(self.output_dir, "impact_by_collection.png"), dpi=300)

        return fig

    def get_summary_statistics(self, experiment_id: str = None) -> dict:
        """
        Get summary statistics for an experiment.

        Args:
            experiment_id: Identifier for the experiment (if None, use all experiments)

        Returns:
            Dictionary with summary statistics
        """
        conn = sqlite3.connect(self.db_path)

        # Get overall baseline metrics
        if experiment_id:
            baseline_query = f"""
            SELECT AVG(baseline_precision) as precision,
                   AVG(baseline_recall) as recall,
                   AVG(baseline_f1) as f1
            FROM ablation_results
            WHERE experiment_id = '{experiment_id}'
            """

            # Get metrics by ablated collection
            collection_query = f"""
            SELECT ablated_collection,
                   AVG(ablated_precision) as precision,
                   AVG(ablated_recall) as recall,
                   AVG(ablated_f1) as f1,
                   AVG(impact_precision) as impact_precision,
                   AVG(impact_recall) as impact_recall,
                   AVG(impact_f1) as impact_f1
            FROM ablation_results
            WHERE experiment_id = '{experiment_id}'
            GROUP BY ablated_collection
            ORDER BY AVG(impact_f1) DESC
            """
        else:
            baseline_query = """
            SELECT AVG(baseline_precision) as precision,
                   AVG(baseline_recall) as recall,
                   AVG(baseline_f1) as f1
            FROM ablation_results
            """

            # Get metrics by ablated collection
            collection_query = """
            SELECT ablated_collection,
                   AVG(ablated_precision) as precision,
                   AVG(ablated_recall) as recall,
                   AVG(ablated_f1) as f1,
                   AVG(impact_precision) as impact_precision,
                   AVG(impact_recall) as impact_recall,
                   AVG(impact_f1) as impact_f1
            FROM ablation_results
            GROUP BY ablated_collection
            ORDER BY AVG(impact_f1) DESC
            """

        baseline_df = pd.read_sql_query(baseline_query, conn)
        collection_df = pd.read_sql_query(collection_query, conn)
        conn.close()

        # Prepare summary
        summary = {
            "baseline": {},
            "collections": [],
            "most_impactful_collection": None,
            "least_impactful_collection": None,
        }

        if not baseline_df.empty:
            summary["baseline"] = {
                "precision": float(baseline_df["precision"].iloc[0]),
                "recall": float(baseline_df["recall"].iloc[0]),
                "f1": float(baseline_df["f1"].iloc[0]),
            }

        if not collection_df.empty:
            # Extract collection names without the prefix
            collection_df["collection_name"] = collection_df["ablated_collection"].apply(
                lambda x: x.replace("Indaleko_Ablation_", "").replace("_Activity_Collection", ""),
            )

            for _, row in collection_df.iterrows():
                collection_summary = {
                    "name": row["collection_name"],
                    "precision": float(row["precision"]),
                    "recall": float(row["recall"]),
                    "f1": float(row["f1"]),
                    "impact_precision": float(row["impact_precision"]),
                    "impact_recall": float(row["impact_recall"]),
                    "impact_f1": float(row["impact_f1"]),
                }
                summary["collections"].append(collection_summary)

            # Get most and least impactful collections
            most_impactful_idx = collection_df["impact_f1"].abs().idxmax()
            least_impactful_idx = collection_df["impact_f1"].abs().idxmin()

            summary["most_impactful_collection"] = {
                "name": collection_df.loc[most_impactful_idx, "collection_name"],
                "impact_f1": float(collection_df.loc[most_impactful_idx, "impact_f1"]),
            }

            summary["least_impactful_collection"] = {
                "name": collection_df.loc[least_impactful_idx, "collection_name"],
                "impact_f1": float(collection_df.loc[least_impactful_idx, "impact_f1"]),
            }

        return summary

    def generate_report(self):
        """Generate a comprehensive report of the ablation results."""
        self.logger.info("Generating ablation summary report")

        # Connect to database
        conn = sqlite3.connect(self.db_path)

        # Get all experiment IDs
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT experiment_id FROM experiment_metadata")
        experiment_ids = [row[0] for row in cursor.fetchall()]

        if not experiment_ids:
            self.logger.warning("No experiments found in database")
            return

        # Generate report markdown
        report_path = os.path.join(self.output_dir, "ablation_summary.md")

        with open(report_path, "w") as f:
            f.write("# Ablation Study Results Summary\n\n")
            f.write(f"Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Overall summary
            f.write("## Overall Summary\n\n")

            overall_summary = self.get_summary_statistics()

            if overall_summary["baseline"]:
                f.write("### Baseline Performance (No Ablation)\n\n")
                f.write("| Metric | Value |\n")
                f.write("| ------ | ----- |\n")
                f.write(f"| Precision | {overall_summary['baseline']['precision']:.3f} |\n")
                f.write(f"| Recall | {overall_summary['baseline']['recall']:.3f} |\n")
                f.write(f"| F1 Score | {overall_summary['baseline']['f1']:.3f} |\n\n")

            f.write("### Collection Impact Ranking\n\n")
            f.write("Collections ranked by absolute impact on F1 score:\n\n")
            f.write("| Collection | Impact on F1 |\n")
            f.write("| ---------- | ------------ |\n")

            for collection in sorted(overall_summary["collections"], key=lambda x: abs(x["impact_f1"]), reverse=True):
                impact_str = f"{collection['impact_f1']:.3f}"
                if collection["impact_f1"] < 0:
                    impact_str += " 🔻"  # Red triangle down for negative impact
                else:
                    impact_str += " 🔼"  # Green triangle up for positive impact

                f.write(f"| {collection['name']} | {impact_str} |\n")

            f.write("\n")

            # Per-experiment results
            for experiment_id in experiment_ids:
                config = self.get_experiment_configuration(experiment_id)
                iteration_id = config.get("iteration_id", experiment_id)

                f.write(f"## Experiment: {iteration_id}\n\n")

                if "control_group" in config and "test_group" in config:
                    f.write("### Configuration\n\n")
                    f.write(f"- Control Group: {', '.join(config['control_group'])}\n")
                    f.write(f"- Test Group: {', '.join(config['test_group'])}\n\n")

                # Get summary for this experiment
                experiment_summary = self.get_summary_statistics(experiment_id)

                if experiment_summary["baseline"]:
                    f.write("### Baseline Performance\n\n")
                    f.write("| Metric | Value |\n")
                    f.write("| ------ | ----- |\n")
                    f.write(f"| Precision | {experiment_summary['baseline']['precision']:.3f} |\n")
                    f.write(f"| Recall | {experiment_summary['baseline']['recall']:.3f} |\n")
                    f.write(f"| F1 Score | {experiment_summary['baseline']['f1']:.3f} |\n\n")

                f.write("### Results by Ablated Collection\n\n")
                f.write("| Collection | Precision | Recall | F1 Score | Impact on F1 |\n")
                f.write("| ---------- | --------- | ------ | -------- | ------------ |\n")

                for collection in experiment_summary["collections"]:
                    impact_str = f"{collection['impact_f1']:.3f}"
                    if collection["impact_f1"] < 0:
                        impact_str += " 🔻"
                    else:
                        impact_str += " 🔼"

                    f.write(
                        f"| {collection['name']} | {collection['precision']:.3f} | "
                        f"{collection['recall']:.3f} | {collection['f1']:.3f} | {impact_str} |\n",
                    )

                f.write("\n")

                # Generate and include visualizations
                f.write("### Visualizations\n\n")

                # Generate visualizations
                self.generate_precision_recall_plot(experiment_id)
                self.generate_impact_heatmap(experiment_id)
                self.generate_f1_by_collection(experiment_id)
                self.generate_impact_by_collection(experiment_id)

                # Add visualization references
                f.write("#### Precision-Recall Plot\n\n")
                f.write("![Precision-Recall Plot](precision_recall.png)\n\n")

                f.write("#### Impact Heatmap\n\n")
                f.write("![Impact Heatmap](impact_heatmap.png)\n\n")

                f.write("#### F1 Score by Collection\n\n")
                f.write("![F1 by Collection](f1_by_collection.png)\n\n")

                f.write("#### Impact on F1 Score by Collection\n\n")
                f.write("![Impact by Collection](impact_by_collection.png)\n\n")

                f.write("---\n\n")

            # Conclusion
            f.write("## Conclusion\n\n")

            if overall_summary.get("most_impactful_collection"):
                most_impactful = overall_summary["most_impactful_collection"]
                least_impactful = overall_summary["least_impactful_collection"]

                f.write(f"The most impactful collection was **{most_impactful['name']}** ")
                f.write(f"with an impact of {most_impactful['impact_f1']:.3f} on F1 score. ")

                f.write(f"The least impactful collection was **{least_impactful['name']}** ")
                f.write(f"with an impact of {least_impactful['impact_f1']:.3f} on F1 score.\n\n")

                f.write("### Key Findings\n\n")

                # List collections with negative impact (reduced performance)
                negative_impact = [c for c in overall_summary["collections"] if c["impact_f1"] < 0]
                if negative_impact:
                    f.write("Collections that reduced performance when ablated (indicating importance):\n\n")
                    for collection in sorted(negative_impact, key=lambda x: x["impact_f1"]):
                        f.write(f"- **{collection['name']}**: {collection['impact_f1']:.3f}\n")
                    f.write("\n")

                # List collections with positive impact (improved performance)
                positive_impact = [c for c in overall_summary["collections"] if c["impact_f1"] > 0]
                if positive_impact:
                    f.write("Collections that improved performance when ablated (indicating potential noise):\n\n")
                    for collection in sorted(positive_impact, key=lambda x: x["impact_f1"], reverse=True):
                        f.write(f"- **{collection['name']}**: {collection['impact_f1']:.3f}\n")
                    f.write("\n")

            f.write("\n*This report was automatically generated by the Ablation Results Manager.*\n")

        self.logger.info(f"Report saved to {report_path}")

        # Close database connection
        conn.close()
