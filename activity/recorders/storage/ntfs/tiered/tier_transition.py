#!/usr/bin/env python
"""
NTFS Tier Transition Utility for Indaleko.

This utility manages transitions between tiers in the Indaleko tiered memory
system, with a focus on transferring activities from the hot tier to the
warm tier based on age, importance, and other factors.

Features:
- Automated transition of activities from hot to warm tier
- Importance-based retention decisions
- Configurable transition timing and thresholds
- Detailed reporting and monitoring
- Support for manual and scheduled transitions

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
import time

from datetime import UTC, datetime, timedelta
from typing import Any


# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import tier recorders
from activity.recorders.storage.ntfs.tiered.hot.recorder import NtfsHotTierRecorder
from activity.recorders.storage.ntfs.tiered.importance_scorer import ImportanceScorer
from activity.recorders.storage.ntfs.tiered.warm.recorder import NtfsWarmTierRecorder


class TierTransitionManager:
    """
    Manages transitions between tiers in the Indaleko tiered memory system.

    This class provides utilities for transitioning activities from the hot tier
    to the warm tier based on age, importance, and other factors.
    """

    def __init__(self, **kwargs) -> None:
        """
        Initialize the tier transition manager.

        Args:
            hot_tier_recorder: NtfsHotTierRecorder instance
            warm_tier_recorder: NtfsWarmTierRecorder instance
            age_threshold_hours: Age in hours at which to transition (default: 12)
            high_importance_age_multiplier: Age multiplier for high importance (default: 2.0)
            low_importance_age_multiplier: Age multiplier for low importance (default: 0.5)
            batch_size: Number of activities to process in each batch (default: 1000)
            debug: Whether to enable debug logging (default: False)
        """
        # Configure logging
        self._debug = kwargs.get("debug", False)
        logging.basicConfig(level=logging.DEBUG if self._debug else logging.INFO)
        self._logger = logging.getLogger("TierTransitionManager")

        # Store tier recorders
        self._hot_tier = kwargs.get("hot_tier_recorder")
        self._warm_tier = kwargs.get("warm_tier_recorder")

        # Configure transition parameters
        self._age_threshold_hours = kwargs.get("age_threshold_hours", 12)
        self._high_importance_age = kwargs.get("high_importance_age_multiplier", 2.0)
        self._low_importance_age = kwargs.get("low_importance_age_multiplier", 0.5)
        self._batch_size = kwargs.get("batch_size", 1000)

        # Initialize importance scorer for evaluating activities
        self._scorer = ImportanceScorer(debug=self._debug)

        # Default importance thresholds
        self._high_importance = 0.7
        self._low_importance = 0.3

        # Create recorders if not provided
        if self._hot_tier is None:
            self._logger.info("Creating hot tier recorder")
            try:
                self._hot_tier = NtfsHotTierRecorder(debug=self._debug)
            except Exception as e:
                self._logger.exception(f"Error creating hot tier recorder: {e}")
                self._hot_tier = None

        if self._warm_tier is None:
            self._logger.info("Creating warm tier recorder")
            try:
                self._warm_tier = NtfsWarmTierRecorder(
                    debug=self._debug,
                    transition_enabled=True,
                )
            except Exception as e:
                self._logger.exception(f"Error creating warm tier recorder: {e}")
                self._warm_tier = None

    def check_readiness(self) -> bool:
        """
        Check if the transition manager is ready for operation.

        Returns:
            True if ready, False otherwise
        """
        if not self._hot_tier:
            self._logger.error("Hot tier recorder not available")
            return False

        if not self._warm_tier:
            self._logger.error("Warm tier recorder not available")
            return False

        # Check DB connection on hot tier
        if not hasattr(self._hot_tier, "_db") or self._hot_tier._db is None:
            self._logger.error("Hot tier not connected to database")
            return False

        # Check DB connection on warm tier
        if not hasattr(self._warm_tier, "_db") or self._warm_tier._db is None:
            self._logger.error("Warm tier not connected to database")
            return False

        return True

    def get_transition_stats(self) -> dict[str, Any]:
        """
        Get statistics about the current transition state.

        Returns:
            Dictionary of transition statistics
        """
        stats = {
            "timestamp": datetime.now(UTC).isoformat(),
            "configuration": {
                "age_threshold_hours": self._age_threshold_hours,
                "high_importance_age_multiplier": self._high_importance_age,
                "low_importance_age_multiplier": self._low_importance_age,
                "batch_size": self._batch_size,
            },
        }

        # Skip if not ready
        if not self.check_readiness():
            stats["status"] = "not_ready"
            return stats

        try:
            # Get hot tier statistics
            hot_stats = self._hot_tier.get_hot_tier_statistics()

            # Calculate transition metrics
            transition_ready = 0
            already_transitioned = 0

            # Query for transition-ready activities
            threshold_time = datetime.now(UTC) - timedelta(
                hours=self._age_threshold_hours,
            )
            threshold_str = threshold_time.isoformat()

            # Count transition-ready
            ready_query = """
                RETURN COUNT(
                    FOR doc IN @@collection
                    FILTER doc.Record.Data.timestamp <= @threshold
                    FILTER doc.Record.Data.transitioned != true
                    RETURN 1
                )
            """

            cursor = self._hot_tier._db._arangodb.aql.execute(
                ready_query,
                bind_vars={
                    "@collection": self._hot_tier._collection_name,
                    "threshold": threshold_str,
                },
            )

            for count in cursor:
                transition_ready = count
                break

            # Count already transitioned
            transitioned_query = """
                RETURN COUNT(
                    FOR doc IN @@collection
                    FILTER doc.Record.Data.transitioned == true
                    RETURN 1
                )
            """

            cursor = self._hot_tier._db._arangodb.aql.execute(
                transitioned_query,
                bind_vars={"@collection": self._hot_tier._collection_name},
            )

            for count in cursor:
                already_transitioned = count
                break

            # Add to stats
            stats["hot_tier"] = {
                "total_activities": hot_stats.get("total_count", 0),
                "transition_ready": transition_ready,
                "already_transitioned": already_transitioned,
                "remaining_hot": hot_stats.get("total_count", 0) - transition_ready - already_transitioned,
            }

            # Get warm tier statistics
            warm_stats = self._warm_tier.get_warm_tier_statistics()

            # Add to stats
            stats["warm_tier"] = {
                "total_activities": warm_stats.get("total_count", 0),
                "aggregated_activities": warm_stats.get("by_aggregation", {}).get(
                    "aggregated",
                    0,
                ),
                "individual_activities": warm_stats.get("by_aggregation", {}).get(
                    "individual",
                    0,
                ),
            }

            # Add status
            stats["status"] = "ready"
            if transition_ready > 0:
                stats["status"] = "pending_transition"

            return stats

        except Exception as e:
            self._logger.exception(f"Error getting transition stats: {e}")
            stats["status"] = "error"
            stats["error"] = str(e)
            return stats

    def transition_batch(
        self,
        age_threshold_hours: int | None = None,
        batch_size: int | None = None,
    ) -> tuple[int, int]:
        """
        Transition a batch of activities from hot tier to warm tier.

        Args:
            age_threshold_hours: Optional override for age threshold
            batch_size: Optional override for batch size

        Returns:
            Tuple of (activities_found, activities_transitioned)
        """
        # Skip if not ready
        if not self.check_readiness():
            return (0, 0)

        # Use provided parameters or defaults
        age_threshold = age_threshold_hours if age_threshold_hours is not None else self._age_threshold_hours
        size = batch_size if batch_size is not None else self._batch_size

        try:
            # Find activities to transition
            hot_activities = self._hot_tier.find_hot_tier_activities_to_transition(
                age_threshold_hours=age_threshold,
                batch_size=size,
            )

            if not hot_activities:
                self._logger.info("No activities found ready for transition")
                return (0, 0)

            # Process activities for warm tier
            self._logger.info(
                f"Processing {len(hot_activities)} activities for warm tier",
            )

            # Use warm tier to process and store activities
            transitioned = self._warm_tier.transition_from_hot_tier()

            # Report results
            self._logger.info(f"Transitioned {transitioned} activities to warm tier")

            # Mark as transitioned in hot tier if not already done by warm tier
            if transitioned > 0 and transitioned < len(hot_activities):
                self._hot_tier.mark_hot_tier_activities_transitioned(hot_activities)

            return (len(hot_activities), transitioned)

        except Exception as e:
            self._logger.exception(f"Error in transition batch: {e}")
            return (0, 0)

    def run_transition(
        self,
        max_batches: int = 10,
        pause_seconds: int = 5,
    ) -> dict[str, Any]:
        """
        Run a full transition operation with multiple batches.

        Args:
            max_batches: Maximum number of batches to process
            pause_seconds: Seconds to pause between batches

        Returns:
            Dictionary of transition results
        """
        # Skip if not ready
        if not self.check_readiness():
            return {
                "status": "not_ready",
                "error": "Transition manager not ready for operation",
            }

        results = {
            "start_time": datetime.now(UTC).isoformat(),
            "batches": [],
            "total_activities_found": 0,
            "total_activities_transitioned": 0,
        }

        try:
            # Process batches
            for batch in range(max_batches):
                self._logger.info(f"Processing batch {batch+1}/{max_batches}")

                # Get transition stats before batch
                self.get_transition_stats()

                # Transition batch
                start_time = time.time()
                found, transitioned = self.transition_batch()
                end_time = time.time()

                # Get transition stats after batch
                self.get_transition_stats()

                # Add batch results
                batch_result = {
                    "batch_number": batch + 1,
                    "activities_found": found,
                    "activities_transitioned": transitioned,
                    "duration_seconds": end_time - start_time,
                }
                results["batches"].append(batch_result)

                # Update totals
                results["total_activities_found"] += found
                results["total_activities_transitioned"] += transitioned

                # Stop if no more activities found
                if found == 0:
                    self._logger.info(
                        "No more activities found for transition, stopping",
                    )
                    break

                # Pause between batches
                if batch < max_batches - 1 and found > 0:
                    self._logger.info(
                        f"Pausing for {pause_seconds} seconds before next batch",
                    )
                    time.sleep(pause_seconds)

            # Add final stats
            results["end_time"] = datetime.now(UTC).isoformat()
            results["duration_seconds"] = (
                datetime.fromisoformat(results["end_time"]) - datetime.fromisoformat(results["start_time"])
            ).total_seconds()

            # Get final transition stats
            results["final_stats"] = self.get_transition_stats()

            # Add success status
            results["status"] = "success"

            return results

        except Exception as e:
            self._logger.exception(f"Error in run_transition: {e}")
            results["status"] = "error"
            results["error"] = str(e)
            results["end_time"] = datetime.now(UTC).isoformat()
            return results


def create_recorders(args):
    """
    Create hot and warm tier recorders based on command line arguments.

    Args:
        args: Command line arguments

    Returns:
        Tuple of (hot_tier, warm_tier) recorders
    """
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("tier_transition")

    # Create hot tier recorder
    try:
        hot_tier = NtfsHotTierRecorder(
            debug=args.debug,
            db_config_path=args.db_config,
            no_db=args.no_db,
        )
    except Exception as e:
        logger.exception(f"Error creating hot tier recorder: {e}")
        hot_tier = None

    # Create warm tier recorder
    try:
        warm_tier = NtfsWarmTierRecorder(
            debug=args.debug,
            db_config_path=args.db_config,
            no_db=args.no_db,
            transition_enabled=True,
        )
    except Exception as e:
        logger.exception(f"Error creating warm tier recorder: {e}")
        warm_tier = None

    return (hot_tier, warm_tier)


def main() -> int | None:
    """Main function for command line operation."""
    parser = argparse.ArgumentParser(
        description="NTFS Tier Transition Manager",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Add general arguments
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show transition statistics",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run transition from hot to warm tier",
    )

    # Add transition parameters
    parser.add_argument(
        "--age-hours",
        type=int,
        default=12,
        help="Age threshold in hours for transition",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Number of activities to process in each batch",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=10,
        help="Maximum number of batches to process",
    )

    # Add mode-related arguments
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--no-db",
        action="store_true",
        help="Run without database connection",
    )
    mode_group.add_argument(
        "--db-config",
        type=str,
        default=None,
        help="Path to database configuration file",
    )

    # Add output options
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show more detailed output",
    )

    # Parse arguments
    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("tier_transition")

    # Show header

    try:
        # Create recorders
        hot_tier, warm_tier = create_recorders(args)

        # Create transition manager
        manager = TierTransitionManager(
            hot_tier_recorder=hot_tier,
            warm_tier_recorder=warm_tier,
            age_threshold_hours=args.age_hours,
            batch_size=args.batch_size,
            debug=args.debug,
        )

        # Check if manager is ready
        if not manager.check_readiness():
            return None

        # Show stats if requested
        if args.stats:
            stats = manager.get_transition_stats()

            # Print status

            # Print hot tier stats
            if "hot_tier" in stats:
                stats["hot_tier"]

            # Print warm tier stats
            if "warm_tier" in stats:
                stats["warm_tier"]

            # Print configuration
            if args.verbose and "configuration" in stats:
                config = stats["configuration"]
                for _key, _value in config.items():
                    pass

        # Run transition if requested
        if args.run:
            time.time()

            results = manager.run_transition(max_batches=args.max_batches)

            time.time()

            # Print results

            if results.get("status") == "error":
                pass

            # Print batch results
            elif args.verbose and "batches" in results:
                for _i, _batch in enumerate(results["batches"]):
                    pass


    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
