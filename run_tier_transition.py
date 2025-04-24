#!/usr/bin/env python
"""
NTFS Tier Transition CLI for Indaleko.

This script provides a command-line interface for managing the tiered memory system
in Indaleko, focusing on transitions between tiers for NTFS activity data.

Features:
- Run transitions from hot tier to warm tier
- Configure transition parameters (age threshold, batch size)
- View statistics about the current state of each tier
- Schedule regular transitions with configurable intervals
- Monitor storage efficiency and tier health

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
from datetime import datetime, timezone
from typing import Dict, Any

# Import tier management components
from activity.recorders.storage.ntfs.tiered.hot.recorder import NtfsHotTierRecorder
from activity.recorders.storage.ntfs.tiered.warm.recorder import NtfsWarmTierRecorder
from activity.recorders.storage.ntfs.tiered.tier_transition import TierTransitionManager


def configure_logging(level=logging.INFO):
    """Configure logging for the application."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                os.path.join(
                    os.environ.get("INDALEKO_ROOT", "."),
                    "logs",
                    f"tier_transition_{datetime.now(timezone.utc).strftime('%Y%m%d')}.log"
                )
            )
        ]
    )


def format_byte_size(size_bytes):
    """Format byte size to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.2f} MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.2f} GB"


def print_storage_efficiency(hot_tier_stats, warm_tier_stats):
    """Print storage efficiency metrics."""
    # Calculate storage metrics (estimation based on record counts and sizes)
    hot_count = hot_tier_stats.get("total_count", 0)
    warm_count = warm_tier_stats.get("total_count", 0)
    
    # Estimate average record sizes (in bytes)
    avg_hot_record_size = 2048  # Estimated size of a hot tier record
    avg_warm_record_size = 1024  # Estimated size of a warm tier record
    
    # Count of original activities in warm tier
    original_activities = 0
    aggregated_count = warm_tier_stats.get("by_aggregation", {}).get("aggregated", 0)
    if "aggregation_stats" in warm_tier_stats and aggregated_count > 0:
        agg_stats = warm_tier_stats["aggregation_stats"]
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
    
    # Print formatted metrics
    print("\nStorage Efficiency:")
    print(f"  Hot tier storage: {format_byte_size(hot_storage)}")
    print(f"  Warm tier storage: {format_byte_size(warm_storage)}")
    print(f"  Equivalent hot tier storage: {format_byte_size(equivalent_hot_storage)}")
    print(f"  Compression ratio: {compression_ratio:.2f}x")
    print(f"  Space saved: {format_byte_size(space_saved)} ({percent_saved:.1f}%)")
    
    # Print aggregation metrics
    if aggregated_count > 0 and original_activities > 0:
        aggregation_ratio = original_activities / aggregated_count
        print(f"  Aggregation ratio: {aggregation_ratio:.2f} activities per record")
        print(f"  Original activities represented: {original_activities:,}")
        print(f"  Aggregated records: {aggregated_count:,}")


def run_single_transition(args):
    """Run a single tier transition operation."""
    logger = logging.getLogger("run_tier_transition")
    
    try:
        # Create recorders
        hot_tier = NtfsHotTierRecorder(
            debug=args.debug,
            db_config_path=args.db_config
        )
        
        warm_tier = NtfsWarmTierRecorder(
            debug=args.debug,
            db_config_path=args.db_config,
            transition_enabled=True
        )
        
        # Create transition manager
        manager = TierTransitionManager(
            hot_tier_recorder=hot_tier,
            warm_tier_recorder=warm_tier,
            age_threshold_hours=args.age_hours,
            batch_size=args.batch_size,
            debug=args.debug
        )
        
        # Check if manager is ready
        if not manager.check_readiness():
            logger.error("Transition manager is not ready for operation")
            return 1
        
        # Show initial stats if requested
        if args.stats or args.verbose:
            print("\nInitial State:")
            stats = manager.get_transition_stats()
            
            # Print hot tier stats
            if "hot_tier" in stats:
                hot = stats["hot_tier"]
                print("\nHot Tier:")
                print(f"  Total activities: {hot.get('total_activities', 0):,}")
                print(f"  Ready for transition: {hot.get('transition_ready', 0):,}")
                print(f"  Already transitioned: {hot.get('already_transitioned', 0):,}")
                print(f"  Remaining hot: {hot.get('remaining_hot', 0):,}")
            
            # Print warm tier stats
            if "warm_tier" in stats:
                warm = stats["warm_tier"]
                print("\nWarm Tier:")
                print(f"  Total activities: {warm.get('total_activities', 0):,}")
                print(f"  Aggregated activities: {warm.get('aggregated_activities', 0):,}")
                print(f"  Individual activities: {warm.get('individual_activities', 0):,}")
        
        # Run transition if requested
        if args.run:
            print("\nRunning tier transition...")
            start_time = time.time()
            
            results = manager.run_transition(
                max_batches=args.max_batches,
                pause_seconds=args.pause_seconds
            )
            
            end_time = time.time()
            
            # Print results
            print(f"\nTransition completed in {end_time - start_time:.2f} seconds")
            print(f"Status: {results.get('status', 'unknown')}")
            
            if results.get("status") == "error":
                print(f"Error: {results.get('error', 'unknown error')}")
                return 1
            else:
                print(f"Total activities found: {results.get('total_activities_found', 0):,}")
                print(f"Total activities transitioned: {results.get('total_activities_transitioned', 0):,}")
                
                # Print batch results if verbose
                if args.verbose and "batches" in results:
                    print("\nBatch results:")
                    for i, batch in enumerate(results["batches"]):
                        print(f"  Batch {i+1}:")
                        print(f"    Activities found: {batch.get('activities_found', 0):,}")
                        print(f"    Activities transitioned: {batch.get('activities_transitioned', 0):,}")
                        print(f"    Duration: {batch.get('duration_seconds', 0):.2f} seconds")
        
        # Show final stats if requested
        if args.stats or args.verbose:
            print("\nFinal State:")
            stats = manager.get_transition_stats()
            
            # Get hot tier stats
            hot_tier_stats = {}
            if "hot_tier" in stats:
                hot = stats["hot_tier"]
                hot_tier_stats = hot
                print("\nHot Tier:")
                print(f"  Total activities: {hot.get('total_activities', 0):,}")
                print(f"  Ready for transition: {hot.get('transition_ready', 0):,}")
                print(f"  Already transitioned: {hot.get('already_transitioned', 0):,}")
                print(f"  Remaining hot: {hot.get('remaining_hot', 0):,}")
            
            # Get warm tier stats
            warm_tier_stats = {}
            if "warm_tier" in stats:
                warm = stats["warm_tier"]
                warm_tier_stats = warm
                print("\nWarm Tier:")
                print(f"  Total activities: {warm.get('total_activities', 0):,}")
                print(f"  Aggregated activities: {warm.get('aggregated_activities', 0):,}")
                print(f"  Individual activities: {warm.get('individual_activities', 0):,}")
            
            # Get detailed warm tier stats
            if args.verbose and hasattr(manager._warm_tier, "get_warm_tier_statistics"):
                warm_tier_detailed = manager._warm_tier.get_warm_tier_statistics()
                
                # Print importance distribution
                if "by_importance" in warm_tier_detailed:
                    print("\nImportance Distribution:")
                    for importance, count in warm_tier_detailed["by_importance"].items():
                        print(f"  Score {importance}: {count:,}")
                
                # Print activity type distribution
                if "by_type" in warm_tier_detailed:
                    print("\nActivity Type Distribution:")
                    for activity_type, count in warm_tier_detailed["by_type"].items():
                        print(f"  {activity_type}: {count:,}")
                
                # Print time distribution
                if "by_time" in warm_tier_detailed:
                    print("\nTime Distribution:")
                    for time_range, count in warm_tier_detailed["by_time"].items():
                        print(f"  {time_range}: {count:,}")
                
                # Print aggregation statistics
                if "aggregation_stats" in warm_tier_detailed:
                    agg_stats = warm_tier_detailed["aggregation_stats"]
                    print("\nAggregation Statistics:")
                    print(f"  Total original activities: {agg_stats.get('count_sum', 0):,}")
                    print(f"  Average aggregation size: {agg_stats.get('count_avg', 0):.1f}")
                    print(f"  Max aggregation size: {agg_stats.get('count_max', 0):,}")
                    print(f"  Min aggregation size: {agg_stats.get('count_min', 0):,}")
                
                # Print storage efficiency metrics
                print_storage_efficiency(hot_tier_stats, warm_tier_detailed)
        
        return 0
    
    except Exception as e:
        logger.error(f"Error running tier transition: {e}", exc_info=args.debug)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


def run_scheduled_transitions(args):
    """Run scheduled tier transitions at regular intervals."""
    logger = logging.getLogger("run_tier_transition")
    logger.info(f"Starting scheduled transitions every {args.interval} minutes")
    
    # Print schedule information
    print(f"Running scheduled transitions every {args.interval} minutes")
    print(f"Press Ctrl+C to stop")
    
    # Set up loop variables
    run_count = 0
    start_time = time.time()
    
    try:
        while True:
            # Run a transition
            run_count += 1
            print(f"\n=== Run {run_count} at {datetime.now(timezone.utc).isoformat()} ===")
            
            # Create a modified args object for this run
            run_args = argparse.Namespace(**vars(args))
            run_args.verbose = False  # Reduce output for scheduled runs
            
            # Run the transition
            status = run_single_transition(run_args)
            
            # Calculate elapsed time and next run time
            elapsed = time.time() - start_time
            elapsed_minutes = elapsed / 60
            next_run = (run_count * args.interval) - elapsed_minutes
            
            if next_run <= 0:
                # We're already behind schedule, run again immediately
                logger.warning(f"Behind schedule by {-next_run:.1f} minutes")
                continue
            
            # Print next run info
            next_run_time = datetime.now(timezone.utc) + timedelta(minutes=next_run)
            print(f"\nNext run in {next_run:.1f} minutes (at {next_run_time.isoformat()})")
            
            # Sleep until next run
            time.sleep(next_run * 60)
    
    except KeyboardInterrupt:
        print("\nScheduled transitions stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Error in scheduled transitions: {e}", exc_info=args.debug)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="NTFS Tier Transition CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Add general arguments
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run tier transition"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show tier statistics"
    )
    
    # Add transition parameters
    parser.add_argument(
        "--age-hours",
        type=int,
        default=12,
        help="Age threshold in hours for transition"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Number of activities to process in each batch"
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=10,
        help="Maximum number of batches to process"
    )
    parser.add_argument(
        "--pause-seconds",
        type=int,
        default=5,
        help="Seconds to pause between batches"
    )
    
    # Add scheduling options
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run scheduled transitions"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Interval in minutes for scheduled transitions"
    )
    
    # Add database options
    parser.add_argument(
        "--db-config",
        type=str,
        help="Path to database configuration file"
    )
    
    # Add output options
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show more detailed output"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    configure_logging(logging.DEBUG if args.debug else logging.INFO)
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.environ.get("INDALEKO_ROOT", "."), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Print banner
    print("\n=== Indaleko NTFS Tier Transition ===")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    
    # Run appropriate mode
    if args.schedule:
        return run_scheduled_transitions(args)
    else:
        return run_single_transition(args)


if __name__ == "__main__":
    from datetime import timedelta
    sys.exit(main())