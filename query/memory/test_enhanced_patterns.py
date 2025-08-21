"""
Enhanced test script for the improved cross-source pattern detection system.

This script provides additional testing capabilities for the enhanced
pattern detection algorithms and statistical analysis.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason and contributors

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
import random
import sys
import time

from datetime import UTC, datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np


try:
    from icecream import ic
except ImportError:

    def ic(*args):
        """Fallback for icecream if not installed."""
        if args:
            pass


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.memory.cross_source_patterns import (
    CrossSourceEvent,
    CrossSourcePatternDetector,
)
from query.memory.pattern_types import DataSourceType


# pylint: enable=wrong-import-position


def setup_logging(debug=False):
    """Set up logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def generate_synthetic_events(count=1000, time_span_days=30, correlation_ratio=0.3):
    """
    Generate synthetic events for testing pattern detection algorithms.

    Args:
        count: Number of events to generate
        time_span_days: Time span for events (days)
        correlation_ratio: Ratio of events that should be correlated

    Returns:
        Dictionary of events
    """
    events = {}

    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(days=time_span_days)

    # Define some common entities
    common_entities = [
        "project_indaleko",
        "database_schema",
        "query_system",
        "documentation",
        "file_analyzer",
        "performance_tests",
        "user_interface",
        "api_gateway",
        "config_manager",
    ]

    # Generate base events (uncorrelated)
    uncorrelated_count = int(count * (1 - correlation_ratio))

    for i in range(uncorrelated_count):
        # Random timestamp within the time span
        random_seconds = random.randint(0, time_span_days * 86400)
        timestamp = start_time + timedelta(seconds=random_seconds)

        # Random source type
        source_type = random.choice(list(DataSourceType))

        # Random event type based on source type
        event_type = f"{source_type.value}_activity"

        # Random entities (0-3)
        entity_count = random.randint(0, 3)
        entities = random.sample(
            common_entities,
            min(entity_count, len(common_entities)),
        )

        # Create event
        event_id = f"event_{i}"
        event = CrossSourceEvent(
            event_id=event_id,
            source_type=source_type,
            source_name=f"{source_type.value}_source",
            timestamp=timestamp,
            event_type=event_type,
            entities=entities,
            importance=random.uniform(0.1, 0.9),
        )

        events[event_id] = event

    # Generate correlated events
    correlated_count = count - uncorrelated_count
    correlation_groups = correlated_count // 4  # Each correlation has ~4 events

    # Fixed patterns to inject
    patterns = [
        # NTFS -> QUERY pattern (file access followed by query)
        {
            "source_types": [DataSourceType.NTFS, DataSourceType.QUERY],
            "time_gap": 1200,  # 20 minutes in seconds
            "shared_entities": True,
        },
        # LOCATION -> COLLABORATION pattern
        {
            "source_types": [DataSourceType.LOCATION, DataSourceType.COLLABORATION],
            "time_gap": 3600,  # 1 hour in seconds
            "shared_entities": True,
        },
        # AMBIENT -> NTFS pattern
        {
            "source_types": [DataSourceType.AMBIENT, DataSourceType.NTFS],
            "time_gap": 1800,  # 30 minutes in seconds
            "shared_entities": False,
        },
    ]

    # Add some random patterns too
    for _ in range(2):
        source_types = random.sample(list(DataSourceType), 2)
        patterns.append(
            {
                "source_types": source_types,
                "time_gap": random.randint(300, 7200),  # 5 min to 2 hours
                "shared_entities": random.choice([True, False]),
            },
        )

    event_id_start = uncorrelated_count
    for _group in range(correlation_groups):
        # Pick a random pattern
        pattern = random.choice(patterns)

        # Random timestamp for the first event
        random_seconds = random.randint(
            0,
            (time_span_days - 1) * 86400,
        )  # Leave room for correlated events
        base_timestamp = start_time + timedelta(seconds=random_seconds)

        # Random entities for this correlation group
        if pattern["shared_entities"]:
            group_entities = random.sample(
                common_entities,
                min(3, len(common_entities)),
            )
        else:
            group_entities = []

        # Create events for this correlation group
        for i, source_type in enumerate(pattern["source_types"]):
            # Add some time gap between events
            if i == 0:
                timestamp = base_timestamp
            else:
                # Add the defined gap plus some random variation
                variation = random.uniform(0.8, 1.2)  # ±20% variation
                gap_seconds = pattern["time_gap"] * variation
                timestamp = base_timestamp + timedelta(seconds=gap_seconds)

            # Random event type based on source type
            event_type = f"{source_type.value}_activity"

            # Entities: either shared or random
            if pattern["shared_entities"]:
                entities = group_entities.copy()
                # Add some source-specific entities
                if random.random() < 0.5:
                    entities.append(f"{source_type.value}_specific_entity")
            else:
                entity_count = random.randint(0, 2)
                entities = random.sample(
                    common_entities,
                    min(entity_count, len(common_entities)),
                )

            # Create event
            event_id = f"event_{event_id_start}"
            event_id_start += 1

            event = CrossSourceEvent(
                event_id=event_id,
                source_type=source_type,
                source_name=f"{source_type.value}_source",
                timestamp=timestamp,
                event_type=event_type,
                entities=entities,
                importance=random.uniform(
                    0.3,
                    0.9,
                ),  # Correlated events tend to be more important
            )

            events[event_id] = event

    return events


def test_with_synthetic_data(args):
    """Test the pattern detection with synthetic data."""

    # Create detector
    detector = CrossSourcePatternDetector(None)  # No DB needed for synthetic data

    # Generate synthetic events
    events = generate_synthetic_events(
        count=args.event_count,
        time_span_days=args.time_span,
        correlation_ratio=args.correlation_ratio,
    )

    # Add events to detector
    detector.data.events = events

    # Create timeline (sort by timestamp)
    timeline = sorted(events.keys(), key=lambda k: events[k].timestamp)
    detector.data.event_timeline = timeline

    # Update source statistics
    for event in events.values():
        source_type = event.source_type
        stats = detector.data.source_statistics[source_type]
        stats["event_count"] += 1
        stats["event_types"].add(event.event_type)

        if not stats["first_event"] or event.timestamp < stats["first_event"]:
            stats["first_event"] = event.timestamp
        if not stats["last_event"] or event.timestamp > stats["last_event"]:
            stats["last_event"] = event.timestamp

    # Print event statistics
    for source_type, stats in detector.data.source_statistics.items():
        event_count = stats["event_count"]
        if event_count > 0:
            pass

    # Test pattern detection
    start_time = time.time()

    patterns = detector.detect_patterns(
        window_size=args.window_size,
        min_occurrences=args.min_occurrences,
    )

    time.time() - start_time

    # Test correlation detection
    start_time = time.time()

    correlations = detector.detect_correlations(
        time_window_minutes=args.time_window,
        min_confidence=args.min_confidence,
        min_entity_overlap=args.min_entity_overlap,
        adaptive_window=args.adaptive_window,
    )

    time.time() - start_time

    # Show detected patterns
    if patterns:
        for _i, pattern in enumerate(patterns[: min(5, len(patterns))], 1):

            if pattern.attributes and args.verbose:
                for _key, _value in pattern.attributes.items():
                    pass

        if len(patterns) > 5:
            pass

    # Show detected correlations
    if correlations:
        for _i, correlation in enumerate(correlations[: min(5, len(correlations))], 1):

            if correlation.attributes and args.verbose:
                for _key, _value in correlation.attributes.items():
                    pass

        if len(correlations) > 5:
            pass

    # Visualize results if requested
    if args.visualize:
        visualize_results(detector, patterns, correlations)

    return patterns, correlations


def visualize_results(detector, patterns, correlations):
    """Visualize the pattern and correlation detection results."""
    try:
        plt.figure(figsize=(10, 8))

        # Create subplots
        plt.subplot(2, 1, 1)

        # Plot pattern confidences by source type combinations
        if patterns:
            source_combinations = ["+".join(s.value for s in p.source_types) for p in patterns]
            confidences = [p.confidence for p in patterns]

            # Sort by confidence
            sorted_indices = np.argsort(confidences)[::-1]
            sorted_combinations = [source_combinations[i] for i in sorted_indices]
            sorted_confidences = [confidences[i] for i in sorted_indices]

            # Limit to top 10 for readability
            if len(sorted_combinations) > 10:
                sorted_combinations = sorted_combinations[:10]
                sorted_confidences = sorted_confidences[:10]

            plt.barh(sorted_combinations, sorted_confidences, color="blue", alpha=0.7)
            plt.xlabel("Confidence")
            plt.title("Pattern Confidence by Source Type Combination")
            plt.xlim(0, 1)
            plt.grid(axis="x", linestyle="--", alpha=0.7)

        # Plot correlation confidences
        plt.subplot(2, 1, 2)

        if correlations:
            source_combinations = ["+".join(s.value for s in c.source_types) for c in correlations]
            confidences = [c.confidence for c in correlations]

            # Sort by confidence
            sorted_indices = np.argsort(confidences)[::-1]
            sorted_combinations = [source_combinations[i] for i in sorted_indices]
            sorted_confidences = [confidences[i] for i in sorted_indices]

            # Limit to top 10 for readability
            if len(sorted_combinations) > 10:
                sorted_combinations = sorted_combinations[:10]
                sorted_confidences = sorted_confidences[:10]

            plt.barh(sorted_combinations, sorted_confidences, color="green", alpha=0.7)
            plt.xlabel("Confidence")
            plt.title("Correlation Confidence by Source Type Combination")
            plt.xlim(0, 1)
            plt.grid(axis="x", linestyle="--", alpha=0.7)

        plt.tight_layout()
        plt.savefig("pattern_correlation_analysis.png")

        # Event timeline visualization
        plt.figure(figsize=(12, 6))

        # Plot events by source type
        source_types = list(DataSourceType)
        colors = plt.cm.tab10(np.linspace(0, 1, len(source_types)))

        for i, source_type in enumerate(source_types):
            # Get events for this source type
            events = [e for e in detector.data.events.values() if e.source_type == source_type]

            if events:
                # Get timestamps
                timestamps = [e.timestamp.timestamp() for e in events]
                y_values = [i] * len(timestamps)

                plt.scatter(
                    timestamps,
                    y_values,
                    color=colors[i],
                    alpha=0.7,
                    label=source_type.value,
                )

        # Format x-axis as dates
        plt.gca().xaxis.set_major_formatter(
            plt.matplotlib.dates.DateFormatter("%Y-%m-%d"),
        )
        plt.gcf().autofmt_xdate()

        plt.yticks(range(len(source_types)), [s.value for s in source_types])
        plt.title("Event Timeline by Source Type")
        plt.xlabel("Time")
        plt.ylabel("Source Type")
        plt.grid(axis="y", linestyle="--", alpha=0.3)

        plt.tight_layout()
        plt.savefig("event_timeline.png")

    except Exception:
        pass


def benchmark_performance(args):
    """Benchmark pattern and correlation detection performance."""

    # Create detector
    detector = CrossSourcePatternDetector(None)  # No DB needed for synthetic data

    # Test with different event counts
    event_counts = [100, 500, 1000, 5000, 10000]
    if args.event_count > 10000:
        event_counts.append(args.event_count)

    pattern_times = []
    correlation_times = []

    for count in event_counts:

        # Generate synthetic events
        events = generate_synthetic_events(
            count=count,
            time_span_days=args.time_span,
            correlation_ratio=args.correlation_ratio,
        )

        # Add events to detector
        detector.data.events = events

        # Create timeline (sort by timestamp)
        timeline = sorted(events.keys(), key=lambda k: events[k].timestamp)
        detector.data.event_timeline = timeline

        # Update source statistics
        for event in events.values():
            source_type = event.source_type
            stats = detector.data.source_statistics[source_type]
            stats["event_count"] += 1
            stats["event_types"].add(event.event_type)

            if not stats["first_event"] or event.timestamp < stats["first_event"]:
                stats["first_event"] = event.timestamp
            if not stats["last_event"] or event.timestamp > stats["last_event"]:
                stats["last_event"] = event.timestamp

        # Test pattern detection
        start_time = time.time()
        detector.detect_patterns(
            window_size=args.window_size,
            min_occurrences=args.min_occurrences,
        )
        pattern_time = time.time() - start_time
        pattern_times.append(pattern_time)

        # Test correlation detection
        start_time = time.time()
        detector.detect_correlations(
            time_window_minutes=args.time_window,
            min_confidence=args.min_confidence,
            min_entity_overlap=args.min_entity_overlap,
            adaptive_window=args.adaptive_window,
        )
        correlation_time = time.time() - start_time
        correlation_times.append(correlation_time)


    # Visualize benchmark results
    try:
        plt.figure(figsize=(10, 6))

        plt.plot(event_counts, pattern_times, "o-", label="Pattern Detection")
        plt.plot(event_counts, correlation_times, "s-", label="Correlation Detection")

        plt.xlabel("Number of Events")
        plt.ylabel("Execution Time (seconds)")
        plt.title("Performance Scaling")
        plt.legend()
        plt.grid(linestyle="--", alpha=0.7)

        # Log scale for x-axis if large range
        if max(event_counts) / min(event_counts) > 100:
            plt.xscale("log")

        plt.tight_layout()
        plt.savefig("performance_benchmark.png")

    except Exception:
        pass


def main():
    """Main function for the enhanced test script."""
    parser = argparse.ArgumentParser(
        description="Test the enhanced cross-source pattern detection system",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Test with synthetic data",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Benchmark performance with different event counts",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Visualize detection results",
    )
    parser.add_argument(
        "--event-count",
        type=int,
        default=1000,
        help="Number of synthetic events to generate",
    )
    parser.add_argument(
        "--time-span",
        type=int,
        default=30,
        help="Time span for synthetic events (days)",
    )
    parser.add_argument(
        "--correlation-ratio",
        type=float,
        default=0.3,
        help="Ratio of correlated events",
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=10,
        help="Window size for pattern detection",
    )
    parser.add_argument(
        "--min-occurrences",
        type=int,
        default=2,
        help="Minimum occurrences for pattern detection",
    )
    parser.add_argument(
        "--time-window",
        type=int,
        default=15,
        help="Time window in minutes for correlation detection",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.6,
        help="Minimum confidence for correlations",
    )
    parser.add_argument(
        "--min-entity-overlap",
        type=float,
        default=0.0,
        help="Minimum entity overlap for correlations",
    )
    parser.add_argument(
        "--adaptive-window",
        action="store_true",
        help="Use adaptive time windows for correlations",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.debug)

    # If no specific test is specified, use synthetic data
    if not any([args.synthetic, args.benchmark]):
        args.synthetic = True

    if args.synthetic:
        patterns, correlations = test_with_synthetic_data(args)

    if args.benchmark:
        benchmark_performance(args)



if __name__ == "__main__":
    main()
