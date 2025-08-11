"""
Test script for the cross-source pattern detection system.

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
import json
import logging
import os
import sys

from datetime import UTC, datetime, timedelta


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db import IndalekoDBConfig
from query.memory.archivist_memory import ArchivistMemory
from query.memory.cross_source_patterns import CrossSourcePatternDetector
from query.memory.pattern_types import DataSourceType
from query.memory.proactive_archivist import ProactiveArchivist


# pylint: enable=wrong-import-position


def setup_logging(debug=False):
    """Set up logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )


def test_event_collection(detector, args):
    """Test collecting events from different sources."""

    # Collect events from all sources
    event_count = detector.collect_events(max_events_per_source=args.max_events)

    if event_count == 0:

        # Reset timestamps and try again if requested
        if args.reset_timestamps:
            for source_type in DataSourceType:
                detector.data.last_update[source_type] = datetime.now(
                    UTC,
                ) - timedelta(days=365)

            # Try collecting again
            event_count = detector.collect_events(max_events_per_source=args.max_events)
    else:
        pass

    # Print event statistics
    for source_type, stats in detector.data.source_statistics.items():
        event_count = stats["event_count"]
        if event_count > 0:
            stats["first_event"].strftime("%Y-%m-%d %H:%M:%S") if stats["first_event"] else "N/A"
            stats["last_event"].strftime("%Y-%m-%d %H:%M:%S") if stats["last_event"] else "N/A"
            ", ".join(stats["event_types"]) if stats["event_types"] else "None"


    # Print the first few events from each source type
    if args.verbose and event_count > 0:
        for source_type in DataSourceType:
            source_events = [
                event for event_id, event in detector.data.events.items() if event.source_type == source_type
            ]

            if source_events:
                for event in source_events[:3]:
                    if event.entities:
                        pass

                    # Show a few attributes
                    if event.attributes and args.verbose:
                        for i, (_key, _value) in enumerate(event.attributes.items()):
                            if i < 3:  # Limit to 3 attributes
                                pass

    return event_count


def test_pattern_detection(detector, args):
    """Test pattern detection capabilities."""

    # Detect patterns
    patterns = detector.detect_patterns(
        window_size=args.window_size,
        min_occurrences=args.min_occurrences,
    )


    # Show detected patterns
    if patterns:
        for _i, pattern in enumerate(patterns, 1):

            if pattern.temporal_constraints and args.verbose:
                pass

            if pattern.entities_involved and args.verbose:
                if len(pattern.entities_involved) > 3:
                    pass

    return patterns


def test_correlation_detection(detector, args):
    """Test correlation detection capabilities."""

    # Detect correlations
    correlations = detector.detect_correlations(
        time_window_minutes=args.time_window,
        min_confidence=args.min_confidence,
    )


    # Show detected correlations
    if correlations:
        for _i, correlation in enumerate(correlations, 1):

            if correlation.entities_involved and args.verbose:
                if len(correlation.entities_involved) > 3:
                    pass

    return correlations


def test_suggestion_generation(detector, args):
    """Test suggestion generation capabilities."""

    # Generate suggestions
    suggestions = detector.generate_suggestions(max_suggestions=args.max_suggestions)


    # Show generated suggestions
    if suggestions:
        for _i, suggestion in enumerate(suggestions, 1):

            if args.verbose:
                suggestion.expires_at.strftime("%Y-%m-%d %H:%M:%S") if suggestion.expires_at else "Never"

                if suggestion.context:
                    pass

    return suggestions


def test_proactive_archivist_integration(args):
    """Test integration with the Proactive Archivist."""

    # Initialize Archivist and Proactive Archivist
    archivist = ArchivistMemory()
    proactive = ProactiveArchivist(archivist)

    # Check if cross-source pattern detection is enabled

    # Run cross-source analysis
    try:
        proactive.analyze_cross_source_patterns()

        # Check when it was last run
        last_analysis = proactive.data.last_cross_source_analysis
        if last_analysis:
            pass

        # Generate suggestions
        suggestions = proactive.generate_suggestions()

        # Show suggestions
        if suggestions:
            for _i, suggestion in enumerate(suggestions, 1):

                if args.verbose:
                    suggestion.expires_at.strftime("%Y-%m-%d %H:%M:%S") if suggestion.expires_at else "Never"

        # Check for insights added to the Archivist
        insights = [
            i for i in archivist.memory.insights if i.category in ("cross_source_pattern", "cross_source_correlation")
        ]


        if insights and args.verbose:
            for _i, _insight in enumerate(insights, 1):
                pass

        return True
    except Exception:
        return False


def save_detector_state(detector, path):
    """Save the detector state to a file."""
    # Convert data to a serializable format
    data_dict = detector.data.model_dump(exclude_none=True)

    # Handle datetime conversions
    def convert_to_json(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)

    # Save to file
    with open(path, "w") as f:
        json.dump(data_dict, f, default=convert_to_json, indent=2)



def main():
    """Main function for the test script."""
    parser = argparse.ArgumentParser(
        description="Test the cross-source pattern detection system",
    )
    parser.add_argument("--collect", action="store_true", help="Test event collection")
    parser.add_argument(
        "--patterns",
        action="store_true",
        help="Test pattern detection",
    )
    parser.add_argument(
        "--correlations",
        action="store_true",
        help="Test correlation detection",
    )
    parser.add_argument(
        "--suggestions",
        action="store_true",
        help="Test suggestion generation",
    )
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Test Proactive Archivist integration",
    )
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument(
        "--max-events",
        type=int,
        default=100,
        help="Maximum events to collect per source",
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
        "--max-suggestions",
        type=int,
        default=5,
        help="Maximum suggestions to generate",
    )
    parser.add_argument(
        "--reset-timestamps",
        action="store_true",
        help="Reset timestamps to collect more events",
    )
    parser.add_argument("--save-state", type=str, help="Save detector state to file")
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

    # If no specific test is specified, run all tests
    if not any(
        [
            args.collect,
            args.patterns,
            args.correlations,
            args.suggestions,
            args.integration,
            args.all,
        ],
    ):
        args.all = True

    # Create detector
    db_config = IndalekoDBConfig()
    detector = CrossSourcePatternDetector(db_config)

    # Run tests
    if args.all or args.collect:
        event_count = test_event_collection(detector, args)

        # Only proceed with other tests if we have events
        if event_count == 0 and not args.reset_timestamps:
            return

    if args.all or args.patterns:
        test_pattern_detection(detector, args)

    if args.all or args.correlations:
        test_correlation_detection(detector, args)

    if args.all or args.suggestions:
        test_suggestion_generation(detector, args)

    if args.all or args.integration:
        test_proactive_archivist_integration(args)

    # Save detector state if requested
    if args.save_state:
        save_detector_state(detector, args.save_state)



if __name__ == "__main__":
    main()
