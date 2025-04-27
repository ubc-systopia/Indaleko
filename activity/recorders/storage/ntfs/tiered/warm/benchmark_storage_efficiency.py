#!/usr/bin/env python
"""
Storage Efficiency Benchmark for NTFS Warm Tier.

This script benchmarks the storage efficiency of the warm tier implementation,
providing metrics on compression ratio, aggregation effectiveness, and query performance.

Features:
- Measures storage size reduction from hot tier to warm tier
- Evaluates aggregation effectiveness for different activity types
- Tests query performance across tiers
- Generates visual reports of efficiency metrics

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
import csv
import json
import logging
import os
import sys
import time

from datetime import UTC, datetime


# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import tier components
from activity.recorders.storage.ntfs.tiered.hot.recorder import NtfsHotTierRecorder
from activity.recorders.storage.ntfs.tiered.tier_transition import TierTransitionManager
from activity.recorders.storage.ntfs.tiered.warm.recorder import NtfsWarmTierRecorder


class StorageEfficiencyBenchmark:
    """Benchmark for evaluating the storage efficiency of the warm tier implementation."""

    def __init__(self, db_config=None, debug=False):
        """
        Initialize the benchmark.

        Args:
            db_config: Path to database configuration file
            debug: Whether to enable debug logging
        """
        # Configure logging
        self.debug = debug
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
        self.logger = logging.getLogger("StorageEfficiencyBenchmark")

        # Initialize recorders
        self.hot_tier = NtfsHotTierRecorder(
            debug=debug,
            db_config_path=db_config,
        )

        self.warm_tier = NtfsWarmTierRecorder(
            debug=debug,
            db_config_path=db_config,
            transition_enabled=True,
        )

        # Initialize transition manager
        self.transition_manager = TierTransitionManager(
            hot_tier_recorder=self.hot_tier,
            warm_tier_recorder=self.warm_tier,
            debug=debug,
        )

        # Check readiness
        if not self.transition_manager.check_readiness():
            self.logger.error("Benchmark not ready: transition manager initialization failed")
            self.ready = False
        else:
            self.ready = True

    def measure_storage_efficiency(self):
        """
        Measure storage efficiency metrics between hot and warm tiers.

        Returns:
            Dictionary of storage efficiency metrics
        """
        metrics = {
            "timestamp": datetime.now(UTC).isoformat(),
            "hot_tier": {},
            "warm_tier": {},
            "efficiency": {},
        }

        try:
            # Get hot tier statistics
            hot_stats = self.hot_tier.get_hot_tier_statistics()
            metrics["hot_tier"] = hot_stats

            # Get warm tier statistics
            warm_stats = self.warm_tier.get_warm_tier_statistics()
            metrics["warm_tier"] = warm_stats

            # Calculate storage metrics (estimation based on record counts and sizes)
            hot_count = hot_stats.get("total_count", 0)
            warm_count = warm_stats.get("total_count", 0)

            # Estimate average record sizes (in bytes)
            avg_hot_record_size = 2048  # Estimated size of a hot tier record
            avg_warm_record_size = 1024  # Estimated size of a warm tier record

            # Count of original activities represented in warm tier
            original_activities = 0
            aggregated_count = warm_stats.get("by_aggregation", {}).get("aggregated", 0)
            if "aggregation_stats" in warm_stats and aggregated_count > 0:
                agg_stats = warm_stats["aggregation_stats"]
                original_activities = agg_stats.get("count_sum", 0)

            # Calculate estimated storage sizes
            hot_storage = hot_count * avg_hot_record_size
            warm_storage = warm_count * avg_warm_record_size
            equivalent_hot_storage = (warm_count + original_activities) * avg_hot_record_size

            # Calculate efficiency metrics
            if equivalent_hot_storage > 0:
                compression_ratio = equivalent_hot_storage / warm_storage
                space_saved = equivalent_hot_storage - warm_storage
                percent_saved = (space_saved / equivalent_hot_storage) * 100
            else:
                compression_ratio = 1.0
                space_saved = 0
                percent_saved = 0

            # Add metrics
            metrics["efficiency"] = {
                "hot_tier_size_bytes": hot_storage,
                "warm_tier_size_bytes": warm_storage,
                "equivalent_hot_tier_size_bytes": equivalent_hot_storage,
                "compression_ratio": compression_ratio,
                "space_saved_bytes": space_saved,
                "percent_saved": percent_saved,
                "original_activities": original_activities,
                "aggregated_activities": aggregated_count,
            }

            # Add aggregation metrics if available
            if aggregated_count > 0 and original_activities > 0:
                metrics["efficiency"]["aggregation_ratio"] = original_activities / aggregated_count

            return metrics

        except Exception as e:
            self.logger.error(f"Error measuring storage efficiency: {e}")
            metrics["error"] = str(e)
            return metrics

    def measure_importance_distribution(self):
        """
        Measure the distribution of importance scores in both tiers.

        Returns:
            Dictionary with importance score distributions
        """
        metrics = {
            "timestamp": datetime.now(UTC).isoformat(),
            "hot_tier": {},
            "warm_tier": {},
        }

        try:
            # Get hot tier statistics
            hot_stats = self.hot_tier.get_hot_tier_statistics()
            if "importance_distribution" in hot_stats:
                metrics["hot_tier"]["importance_distribution"] = hot_stats[
                    "importance_distribution"
                ]

            # Get warm tier statistics
            warm_stats = self.warm_tier.get_warm_tier_statistics()
            if "by_importance" in warm_stats:
                metrics["warm_tier"]["importance_distribution"] = warm_stats["by_importance"]

            return metrics

        except Exception as e:
            self.logger.error(f"Error measuring importance distribution: {e}")
            metrics["error"] = str(e)
            return metrics

    def measure_aggregation_by_type(self):
        """
        Measure aggregation effectiveness by activity type.

        Returns:
            Dictionary with aggregation metrics by activity type
        """
        metrics = {
            "timestamp": datetime.now(UTC).isoformat(),
            "activity_types": {},
        }

        try:
            # Get warm tier statistics
            warm_stats = self.warm_tier.get_warm_tier_statistics()

            # Get aggregated records by type
            if self.warm_tier._db and hasattr(self.warm_tier._db, "_arangodb"):
                query = """
                    FOR doc IN @@collection
                    FILTER doc.Record.Data.is_aggregated == true
                    COLLECT type = doc.Record.Data.activity_type WITH COUNT INTO count_agg
                    RETURN {
                        "activity_type": type,
                        "aggregated_count": count_agg,
                        "original_count": SUM(
                            FOR d IN @@collection
                            FILTER d.Record.Data.is_aggregated == true
                            FILTER d.Record.Data.activity_type == type
                            RETURN d.Record.Data.count
                        )
                    }
                """

                cursor = self.warm_tier._db._arangodb.aql.execute(
                    query,
                    bind_vars={"@collection": self.warm_tier._collection_name},
                )

                for item in cursor:
                    activity_type = item["activity_type"]
                    aggregated_count = item["aggregated_count"]
                    original_count = item["original_count"]

                    if aggregated_count > 0 and original_count > 0:
                        metrics["activity_types"][activity_type] = {
                            "aggregated_count": aggregated_count,
                            "original_count": original_count,
                            "aggregation_ratio": original_count / aggregated_count,
                        }

            return metrics

        except Exception as e:
            self.logger.error(f"Error measuring aggregation by type: {e}")
            metrics["error"] = str(e)
            return metrics

    def run_benchmark(self, output_file=None):
        """
        Run a complete storage efficiency benchmark.

        Args:
            output_file: Path to write results to (JSON format)

        Returns:
            Dictionary with all benchmark results
        """
        if not self.ready:
            self.logger.error("Cannot run benchmark: not ready")
            return {"error": "Benchmark not ready"}

        self.logger.info("Running storage efficiency benchmark...")

        results = {
            "timestamp": datetime.now(UTC).isoformat(),
            "system_info": {},
            "storage_efficiency": {},
            "importance_distribution": {},
            "aggregation_by_type": {},
            "transition_metrics": {},
        }

        try:
            # Get system info
            results["system_info"] = {
                "platform": sys.platform,
                "python_version": sys.version,
                "hot_tier_ttl_days": self.hot_tier._ttl_days
                if hasattr(self.hot_tier, "_ttl_days")
                else None,
                "warm_tier_ttl_days": self.warm_tier._ttl_days
                if hasattr(self.warm_tier, "_ttl_days")
                else None,
            }

            # Measure storage efficiency
            start_time = time.time()
            results["storage_efficiency"] = self.measure_storage_efficiency()
            results["storage_efficiency"]["measurement_time_seconds"] = time.time() - start_time

            # Measure importance distribution
            start_time = time.time()
            results["importance_distribution"] = self.measure_importance_distribution()
            results["importance_distribution"]["measurement_time_seconds"] = (
                time.time() - start_time
            )

            # Measure aggregation by type
            start_time = time.time()
            results["aggregation_by_type"] = self.measure_aggregation_by_type()
            results["aggregation_by_type"]["measurement_time_seconds"] = time.time() - start_time

            # Get transition manager stats
            start_time = time.time()
            results["transition_metrics"] = self.transition_manager.get_transition_stats()
            results["transition_metrics"]["measurement_time_seconds"] = time.time() - start_time

            # Write results to file if requested
            if output_file:
                output_dir = os.path.dirname(output_file)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir)

                with open(output_file, "w") as f:
                    json.dump(results, f, indent=2)
                self.logger.info(f"Benchmark results written to {output_file}")

            # Generate CSV summary if results include storage efficiency metrics
            if output_file and "efficiency" in results["storage_efficiency"]:
                csv_file = os.path.splitext(output_file)[0] + ".csv"

                with open(csv_file, "w", newline="") as f:
                    writer = csv.writer(f)

                    # Write header
                    writer.writerow(["Metric", "Value"])

                    # Write efficiency metrics
                    eff = results["storage_efficiency"]["efficiency"]
                    writer.writerow(["Timestamp", results["timestamp"]])
                    writer.writerow(["Hot Tier Size (bytes)", eff.get("hot_tier_size_bytes", 0)])
                    writer.writerow(["Warm Tier Size (bytes)", eff.get("warm_tier_size_bytes", 0)])
                    writer.writerow(
                        [
                            "Equivalent Hot Tier Size (bytes)",
                            eff.get("equivalent_hot_tier_size_bytes", 0),
                        ]
                    )
                    writer.writerow(["Compression Ratio", eff.get("compression_ratio", 1.0)])
                    writer.writerow(["Space Saved (bytes)", eff.get("space_saved_bytes", 0)])
                    writer.writerow(["Percent Saved", eff.get("percent_saved", 0.0)])
                    writer.writerow(
                        ["Original Activities Count", eff.get("original_activities", 0)]
                    )
                    writer.writerow(
                        ["Aggregated Activities Count", eff.get("aggregated_activities", 0)]
                    )

                    if "aggregation_ratio" in eff:
                        writer.writerow(["Aggregation Ratio", eff["aggregation_ratio"]])

                self.logger.info(f"CSV summary written to {csv_file}")

            return results

        except Exception as e:
            self.logger.error(f"Error running benchmark: {e}")
            results["error"] = str(e)
            return results


def format_byte_size(size_bytes):
    """Format byte size to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Storage Efficiency Benchmark for NTFS Warm Tier",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Add arguments
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="benchmark_results.json",
        help="Output file for benchmark results (JSON format)",
    )
    parser.add_argument(
        "--db-config",
        type=str,
        help="Path to database configuration file",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Run benchmark
    benchmark = StorageEfficiencyBenchmark(
        db_config=args.db_config,
        debug=args.debug,
    )

    if not benchmark.ready:
        print("Benchmark not ready. Please check database connection.")
        return 1

    results = benchmark.run_benchmark(output_file=args.output)

    # Print summary
    print("\n=== Storage Efficiency Benchmark Results ===\n")

    if "error" in results:
        print(f"Error: {results['error']}")
        return 1

    if "efficiency" in results["storage_efficiency"]:
        eff = results["storage_efficiency"]["efficiency"]
        print("Storage Efficiency Metrics:")
        print(f"  Hot Tier Size: {format_byte_size(eff.get('hot_tier_size_bytes', 0))}")
        print(f"  Warm Tier Size: {format_byte_size(eff.get('warm_tier_size_bytes', 0))}")
        print(
            f"  Equivalent Hot Tier Size: {format_byte_size(eff.get('equivalent_hot_tier_size_bytes', 0))}"
        )
        print(f"  Compression Ratio: {eff.get('compression_ratio', 1.0):.2f}x")
        print(
            f"  Space Saved: {format_byte_size(eff.get('space_saved_bytes', 0))} ({eff.get('percent_saved', 0.0):.1f}%)",
        )
        print(f"  Original Activities: {eff.get('original_activities', 0):,}")
        print(f"  Aggregated Activities: {eff.get('aggregated_activities', 0):,}")

        if "aggregation_ratio" in eff:
            print(f"  Aggregation Ratio: {eff['aggregation_ratio']:.2f} activities per record")

    if "activity_types" in results["aggregation_by_type"]:
        types = results["aggregation_by_type"]["activity_types"]
        if types:
            print("\nAggregation by Activity Type:")
            for activity_type, metrics in types.items():
                print(f"  {activity_type}:")
                print(f"    Aggregated Count: {metrics.get('aggregated_count', 0):,}")
                print(f"    Original Count: {metrics.get('original_count', 0):,}")
                print(f"    Aggregation Ratio: {metrics.get('aggregation_ratio', 0):.2f}x")

    if "hot_tier" in results["transition_metrics"]:
        hot = results["transition_metrics"]["hot_tier"]
        print("\nTransition Status:")
        print(f"  Ready for Transition: {hot.get('transition_ready', 0):,}")
        print(f"  Already Transitioned: {hot.get('already_transitioned', 0):,}")

    print(f"\nDetailed results saved to: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
