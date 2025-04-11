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

import os
import sys
import argparse
import json
from datetime import datetime, timezone, timedelta
import logging

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from query.memory.cross_source_patterns import (
    CrossSourcePatternDetector,
    CrossSourceEvent,
    DataSourceType,
    CrossSourcePatternsData
)
from query.memory.proactive_archivist import ProactiveArchivist
from query.memory.archivist_memory import ArchivistMemory
from db import IndalekoDBConfig
# pylint: enable=wrong-import-position


def setup_logging(debug=False):
    """Set up logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )


def test_event_collection(detector, args):
    """Test collecting events from different sources."""
    print("\nTesting event collection...")
    
    # Collect events from all sources
    event_count = detector.collect_events(max_events_per_source=args.max_events)
    
    if event_count == 0:
        print("No events collected. This could be because:")
        print("- No events exist in the database")
        print("- The collections don't exist or are empty")
        print("- The last_update timestamps in the detector are set to recent times")
        
        # Reset timestamps and try again if requested
        if args.reset_timestamps:
            print("\nResetting timestamps and trying again...")
            for source_type in DataSourceType:
                detector.data.last_update[source_type] = datetime.now(timezone.utc) - timedelta(days=365)
            
            # Try collecting again
            event_count = detector.collect_events(max_events_per_source=args.max_events)
            print(f"After resetting timestamps: Collected {event_count} events")
    else:
        print(f"Successfully collected {event_count} events")
    
    # Print event statistics
    print("\nEvent statistics by source type:")
    for source_type, stats in detector.data.source_statistics.items():
        event_count = stats["event_count"]
        if event_count > 0:
            first_event = stats["first_event"].strftime('%Y-%m-%d %H:%M:%S') if stats["first_event"] else "N/A"
            last_event = stats["last_event"].strftime('%Y-%m-%d %H:%M:%S') if stats["last_event"] else "N/A"
            event_types = ", ".join(stats["event_types"]) if stats["event_types"] else "None"
            
            print(f"- {source_type.value}: {event_count} events")
            print(f"  First event: {first_event}")
            print(f"  Last event: {last_event}")
            print(f"  Event types: {event_types}")
    
    # Print the first few events from each source type
    if args.verbose and event_count > 0:
        print("\nSample events by source type:")
        for source_type in DataSourceType:
            source_events = [
                event for event_id, event in detector.data.events.items() 
                if event.source_type == source_type
            ]
            
            if source_events:
                print(f"\n{source_type.value} events (showing up to 3):")
                for event in source_events[:3]:
                    print(f"- ID: {event.event_id}")
                    print(f"  Timestamp: {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"  Event type: {event.event_type}")
                    if event.entities:
                        print(f"  Entities: {', '.join(event.entities[:3])}")
                    
                    # Show a few attributes
                    if event.attributes and args.verbose:
                        print("  Attributes:")
                        for i, (key, value) in enumerate(event.attributes.items()):
                            if i < 3:  # Limit to 3 attributes
                                print(f"    {key}: {value}")
    
    return event_count


def test_pattern_detection(detector, args):
    """Test pattern detection capabilities."""
    print("\nTesting pattern detection...")
    
    # Detect patterns
    patterns = detector.detect_patterns(
        window_size=args.window_size,
        min_occurrences=args.min_occurrences
    )
    
    print(f"Detected {len(patterns)} new patterns")
    
    # Show detected patterns
    if patterns:
        print("\nDetected patterns:")
        for i, pattern in enumerate(patterns, 1):
            print(f"{i}. {pattern.pattern_name}")
            print(f"   Description: {pattern.description}")
            print(f"   Confidence: {pattern.confidence:.2f}")
            print(f"   Source types: {', '.join([s.value for s in pattern.source_types])}")
            print(f"   Observation count: {pattern.observation_count}")
            
            if pattern.temporal_constraints and args.verbose:
                print(f"   Temporal constraints: {pattern.temporal_constraints}")
            
            if pattern.entities_involved and args.verbose:
                print(f"   Entities involved: {', '.join(pattern.entities_involved[:3])}")
                if len(pattern.entities_involved) > 3:
                    print(f"   ... and {len(pattern.entities_involved) - 3} more entities")
    
    return patterns


def test_correlation_detection(detector, args):
    """Test correlation detection capabilities."""
    print("\nTesting correlation detection...")
    
    # Detect correlations
    correlations = detector.detect_correlations(
        time_window_minutes=args.time_window,
        min_confidence=args.min_confidence
    )
    
    print(f"Detected {len(correlations)} new correlations")
    
    # Show detected correlations
    if correlations:
        print("\nDetected correlations:")
        for i, correlation in enumerate(correlations, 1):
            print(f"{i}. {correlation.description}")
            print(f"   Confidence: {correlation.confidence:.2f}")
            print(f"   Relationship type: {correlation.relationship_type}")
            print(f"   Source types: {', '.join([s.value for s in correlation.source_types])}")
            
            if correlation.entities_involved and args.verbose:
                print(f"   Entities involved: {', '.join(correlation.entities_involved[:3])}")
                if len(correlation.entities_involved) > 3:
                    print(f"   ... and {len(correlation.entities_involved) - 3} more entities")
    
    return correlations


def test_suggestion_generation(detector, args):
    """Test suggestion generation capabilities."""
    print("\nTesting suggestion generation...")
    
    # Generate suggestions
    suggestions = detector.generate_suggestions(max_suggestions=args.max_suggestions)
    
    print(f"Generated {len(suggestions)} suggestions")
    
    # Show generated suggestions
    if suggestions:
        print("\nGenerated suggestions:")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. [{suggestion.priority}] {suggestion.title}")
            print(f"   Type: {suggestion.suggestion_type}")
            print(f"   Confidence: {suggestion.confidence:.2f}")
            print(f"   Content: {suggestion.content}")
            
            if args.verbose:
                expiry = suggestion.expires_at.strftime('%Y-%m-%d %H:%M:%S') if suggestion.expires_at else "Never"
                print(f"   Expires: {expiry}")
                
                if suggestion.context:
                    print(f"   Context: {suggestion.context}")
    
    return suggestions


def test_proactive_archivist_integration(args):
    """Test integration with the Proactive Archivist."""
    print("\nTesting Proactive Archivist integration...")
    
    # Initialize Archivist and Proactive Archivist
    archivist = ArchivistMemory()
    proactive = ProactiveArchivist(archivist)
    
    # Check if cross-source pattern detection is enabled
    print(f"Cross-source pattern detection enabled: {proactive.data.cross_source_enabled}")
    
    # Run cross-source analysis
    try:
        print("Running cross-source pattern analysis...")
        proactive.analyze_cross_source_patterns()
        
        # Check when it was last run
        last_analysis = proactive.data.last_cross_source_analysis
        if last_analysis:
            print(f"Last analysis: {last_analysis.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Generate suggestions
        suggestions = proactive.generate_suggestions()
        print(f"\nGenerated {len(suggestions)} proactive suggestions")
        
        # Show suggestions
        if suggestions:
            print("\nProactive suggestions:")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"{i}. [{suggestion.priority}] {suggestion.title}")
                print(f"   Type: {suggestion.suggestion_type}")
                print(f"   Confidence: {suggestion.confidence:.2f}")
                print(f"   Content: {suggestion.content}")
                
                if args.verbose:
                    expiry = suggestion.expires_at.strftime('%Y-%m-%d %H:%M:%S') if suggestion.expires_at else "Never"
                    print(f"   Expires: {expiry}")
        
        # Check for insights added to the Archivist
        insights = [i for i in archivist.memory.insights 
                     if i.category in ("cross_source_pattern", "cross_source_correlation")]
        
        print(f"\nAdded {len(insights)} cross-source insights to Archivist memory")
        
        if insights and args.verbose:
            print("\nCross-source insights:")
            for i, insight in enumerate(insights, 1):
                print(f"{i}. {insight.insight}")
                print(f"   Category: {insight.category}")
                print(f"   Confidence: {insight.confidence:.2f}")
        
        return True
    except Exception as e:
        print(f"Error in Proactive Archivist integration: {e}")
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
    with open(path, 'w') as f:
        json.dump(data_dict, f, default=convert_to_json, indent=2)
    
    print(f"Detector state saved to {path}")


def main():
    """Main function for the test script."""
    parser = argparse.ArgumentParser(description="Test the cross-source pattern detection system")
    parser.add_argument("--collect", action="store_true", help="Test event collection")
    parser.add_argument("--patterns", action="store_true", help="Test pattern detection")
    parser.add_argument("--correlations", action="store_true", help="Test correlation detection")
    parser.add_argument("--suggestions", action="store_true", help="Test suggestion generation")
    parser.add_argument("--integration", action="store_true", help="Test Proactive Archivist integration")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--max-events", type=int, default=100, help="Maximum events to collect per source")
    parser.add_argument("--window-size", type=int, default=10, help="Window size for pattern detection")
    parser.add_argument("--min-occurrences", type=int, default=2, help="Minimum occurrences for pattern detection")
    parser.add_argument("--time-window", type=int, default=15, help="Time window in minutes for correlation detection")
    parser.add_argument("--min-confidence", type=float, default=0.6, help="Minimum confidence for correlations")
    parser.add_argument("--max-suggestions", type=int, default=5, help="Maximum suggestions to generate")
    parser.add_argument("--reset-timestamps", action="store_true", help="Reset timestamps to collect more events")
    parser.add_argument("--save-state", type=str, help="Save detector state to file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.debug)
    
    # If no specific test is specified, run all tests
    if not any([args.collect, args.patterns, args.correlations, args.suggestions, args.integration, args.all]):
        args.all = True
    
    # Create detector
    db_config = IndalekoDBConfig()
    detector = CrossSourcePatternDetector(db_config)
    
    # Run tests
    if args.all or args.collect:
        event_count = test_event_collection(detector, args)
        
        # Only proceed with other tests if we have events
        if event_count == 0 and not args.reset_timestamps:
            print("\nNo events collected. Skipping pattern and correlation detection.")
            print("Hint: Use --reset-timestamps to reset timestamp filters and try collecting more events.")
            return
    
    if args.all or args.patterns:
        patterns = test_pattern_detection(detector, args)
    
    if args.all or args.correlations:
        correlations = test_correlation_detection(detector, args)
    
    if args.all or args.suggestions:
        suggestions = test_suggestion_generation(detector, args)
    
    if args.all or args.integration:
        test_proactive_archivist_integration(args)
    
    # Save detector state if requested
    if args.save_state:
        save_detector_state(detector, args.save_state)
    
    print("\nAll tests completed.")


if __name__ == "__main__":
    main()