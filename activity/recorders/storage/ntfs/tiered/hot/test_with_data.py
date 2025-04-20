#!/usr/bin/env python
"""
Testing script for the NTFS Hot Tier Recorder using real NTFS activity data.

This script processes existing NTFS activity data from JSONL files using
the NTFS Hot Tier Recorder and prints statistics about the processed activities.

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

import os
import sys
import json
import logging
import argparse
from collections import Counter
from typing import Dict, List, Any

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import the recorder class to test
from activity.recorders.storage.ntfs.tiered.hot.recorder import NtfsHotTierRecorder


def find_ntfs_jsonl_files() -> List[str]:
    """Find all NTFS JSONL files in the repository."""
    ntfs_files = []
    data_dir = os.path.join(os.environ["INDALEKO_ROOT"], "data")
    
    # Check if data directory exists
    if os.path.exists(data_dir):
        for filename in os.listdir(data_dir):
            if "ntfs" in filename.lower() and filename.endswith(".jsonl"):
                ntfs_files.append(os.path.join(data_dir, filename))
    
    # Also check the activity collectors directory
    activity_dir = os.path.join(os.environ["INDALEKO_ROOT"], "activity", "collectors", "storage", "ntfs")
    if os.path.exists(activity_dir):
        for filename in os.listdir(activity_dir):
            if filename.endswith(".jsonl"):
                ntfs_files.append(os.path.join(activity_dir, filename))
    
    return ntfs_files


def count_activities_in_jsonl(file_path: str) -> Dict[str, int]:
    """Count the number of activities by type in a JSONL file."""
    activity_types = Counter()
    line_count = 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line_count += 1
                try:
                    activity = json.loads(line)
                    activity_type = activity.get("activity_type", "unknown")
                    activity_types[activity_type] += 1
                except json.JSONDecodeError:
                    # Skip invalid lines
                    pass
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return {
        "total_lines": line_count,
        "activity_counts": dict(activity_types)
    }


def analyze_importance_scores(activities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze the importance scores assigned to activities."""
    if not activities:
        return {"error": "No activities to analyze"}
    
    scores = [activity.get("importance_score", 0) for activity in activities]
    
    # Count by ranges
    ranges = {
        "0.0-0.2": 0,
        "0.2-0.4": 0,
        "0.4-0.6": 0,
        "0.6-0.8": 0,
        "0.8-1.0": 0
    }
    
    for score in scores:
        if 0.0 <= score < 0.2:
            ranges["0.0-0.2"] += 1
        elif 0.2 <= score < 0.4:
            ranges["0.2-0.4"] += 1
        elif 0.4 <= score < 0.6:
            ranges["0.4-0.6"] += 1
        elif 0.6 <= score < 0.8:
            ranges["0.6-0.8"] += 1
        else:
            ranges["0.8-1.0"] += 1
    
    # Calculate statistics
    if scores:
        avg_score = sum(scores) / len(scores)
        min_score = min(scores)
        max_score = max(scores)
    else:
        avg_score = min_score = max_score = 0
        
    return {
        "count": len(scores),
        "average": avg_score,
        "min": min_score,
        "max": max_score,
        "ranges": ranges
    }


def analyze_entity_mapping(activities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze entity mapping statistics."""
    if not activities:
        return {"error": "No activities to analyze"}
    
    entity_counts = Counter()
    frn_counts = Counter()
    
    for activity in activities:
        entity_id = activity.get("entity_id")
        frn = activity.get("file_reference_number")
        
        if entity_id:
            entity_counts[entity_id] += 1
        if frn:
            frn_counts[frn] += 1
    
    return {
        "unique_entities": len(entity_counts),
        "unique_frns": len(frn_counts),
        "most_common_entities": entity_counts.most_common(5),
        "most_common_frns": frn_counts.most_common(5)
    }


def process_with_recorder(file_path: str, debug: bool = False, stats_only: bool = True) -> Dict[str, Any]:
    """Process a JSONL file with the NTFS Hot Tier Recorder and return statistics."""
    print(f"Processing {file_path}...")
    
    # Create recorder in mock mode (no database)
    recorder = NtfsHotTierRecorder(
        no_db=True,  # Don't connect to database
        debug=debug,
        register_service=False,  # Don't register with service manager
        ttl_days=3  # Shorter TTL for testing
    )
    
    # Patch the get_semantic_attributes_for_activity function to avoid UUID validation issues
    from unittest.mock import patch
    import activity.collectors.storage.semantic_attributes
    
    def mock_get_semantic_attributes(*args, **kwargs):
        return []  # Return empty list to bypass semantic attributes processing
        
    # Apply the patch
    original_func = activity.collectors.storage.semantic_attributes.get_semantic_attributes_for_activity
    activity.collectors.storage.semantic_attributes.get_semantic_attributes_for_activity = mock_get_semantic_attributes
    
    # Track processed activities
    processed_activities = []
    
    # Override store_activity to capture processed activities
    original_store_activity = recorder.store_activity
    
    def mock_store_activity(activity_data):
        if hasattr(activity_data, 'model_dump'):
            # For Pydantic models, convert to dict
            activity_dict = activity_data.model_dump()
        else:
            # Already a dict
            activity_dict = activity_data
            
        # Process the activity as normal
        processed_activities.append(activity_dict)
        
        # Call original method but with no_db=True it won't store in database
        return original_store_activity(activity_data)
    
    # Replace the method with our mock
    recorder.store_activity = mock_store_activity
    
    try:
        # Precalculate activity counts
        activity_counts = count_activities_in_jsonl(file_path)
        
        # Process the file
        start_time = __import__('time').time()
        
        try:
            # The real store_activity won't be called because no_db=True
            recorder.process_jsonl_file(file_path)
        except Exception as e:
            print(f"Error processing file: {e}")
            if debug:
                import traceback
                traceback.print_exc()
        
        end_time = __import__('time').time()
        
        # Calculate processing time
        processing_time = end_time - start_time
        
        # Analyze processed activities
        importance_stats = analyze_importance_scores(processed_activities)
        entity_stats = analyze_entity_mapping(processed_activities)
        
        activity_types = Counter()
        for activity in processed_activities:
            activity_type = activity.get("activity_type", "unknown")
            activity_types[activity_type] += 1
        
        stats = {
            "file_path": file_path,
            "file_size": os.path.getsize(file_path),
            "raw_activity_count": activity_counts["total_lines"],
            "processed_activity_count": len(processed_activities),
            "processing_time_seconds": processing_time,
            "activities_per_second": len(processed_activities) / processing_time if processing_time > 0 else 0,
            "activity_types": dict(activity_types),
            "importance_stats": importance_stats,
            "entity_stats": entity_stats
        }
        
        # Print statistics if requested
        if stats_only:
            print(f"File: {file_path}")
            print(f"  Size: {stats['file_size']:,} bytes")
            print(f"  Raw activities: {stats['raw_activity_count']:,}")
            print(f"  Processed activities: {stats['processed_activity_count']:,}")
            print(f"  Processing time: {stats['processing_time_seconds']:.2f} seconds")
            print(f"  Activities per second: {stats['activities_per_second']:.2f}")
            print("  Activity types:")
            for activity_type, count in stats["activity_types"].items():
                print(f"    {activity_type}: {count:,}")
            print("  Importance scores:")
            print(f"    Average: {stats['importance_stats']['average']:.2f}")
            print(f"    Min: {stats['importance_stats']['min']:.2f}")
            print(f"    Max: {stats['importance_stats']['max']:.2f}")
            print("    Distribution:")
            for range_name, count in stats["importance_stats"]["ranges"].items():
                print(f"      {range_name}: {count:,}")
            print("  Entity mapping:")
            print(f"    Unique entities: {stats['entity_stats']['unique_entities']:,}")
            print(f"    Unique FRNs: {stats['entity_stats']['unique_frns']:,}")
        
        return stats
    
    finally:
        # Restore original method
        recorder.store_activity = original_store_activity


def process_file_directly(file_path: str) -> None:
    """Process a JSONL file directly without using the recorder."""
    print(f"Directly processing {file_path}...")
    
    try:
        activities = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                try:
                    activity = json.loads(line)
                    activities.append(activity)
                except json.JSONDecodeError as e:
                    print(f"Error parsing line {i+1}: {e}")
                    
        print(f"Successfully parsed {len(activities)} activities")
        
        # Analyze activity types
        activity_types = {}
        for activity in activities:
            activity_type = activity.get("activity_type", "unknown")
            if activity_type in activity_types:
                activity_types[activity_type] += 1
            else:
                activity_types[activity_type] = 1
                
        print("Activity types:")
        for activity_type, count in activity_types.items():
            print(f"  {activity_type}: {count}")
            
        # Calculate importance scores manually
        scores = []
        for activity in activities:
            # Basic importance scoring algorithm
            base_score = 0.3  # Start with modest importance
            
            # Factor 1: Activity type importance
            activity_type = activity.get("activity_type", "")
            if activity_type in ["create", "security_change"]:
                base_score += 0.2  # Creation events matter more
            elif activity_type in ["delete", "rename"]:
                base_score += 0.15  # Structural changes matter too
            
            # Factor 2: File type importance (basic version)
            file_path = activity.get("file_path", "")
            if any(file_path.lower().endswith(ext) for ext in [".docx", ".xlsx", ".pdf", ".py", ".md"]):
                base_score += 0.1  # Document types matter more
            
            # Factor 3: Path significance
            if any(segment in file_path for segment in ["\\Documents\\", "\\Projects\\", "\\src\\", "\\source\\"]):
                base_score += 0.1  # User document areas matter more
            elif any(segment in file_path for segment in ["\\Temp\\", "\\tmp\\", "\\Cache\\", "\\Downloaded\\"]):
                base_score -= 0.1  # Temporary areas matter less
            
            # Factor 4: Is directory
            if activity.get("is_directory", False):
                base_score += 0.05  # Directories slightly more important than files
                
            # Cap between 0.1 and 1.0
            importance = min(1.0, max(0.1, base_score))
            scores.append(importance)
            
        # Calculate statistics
        avg_score = sum(scores) / len(scores) if scores else 0
        min_score = min(scores) if scores else 0
        max_score = max(scores) if scores else 0
            
        print("Importance scores:")
        print(f"  Average: {avg_score:.2f}")
        print(f"  Min: {min_score:.2f}")
        print(f"  Max: {max_score:.2f}")
        
        # Count files vs directories
        files = sum(1 for a in activities if not a.get("is_directory", False))
        directories = sum(1 for a in activities if a.get("is_directory", False))
        print(f"Files: {files}, Directories: {directories}")
        
    except Exception as e:
        print(f"Error directly processing file: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point for the test script."""
    parser = argparse.ArgumentParser(description="Test NTFS Hot Tier Recorder with existing data")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--file", type=str, help="Specific JSONL file to process")
    parser.add_argument("--all", action="store_true", help="Process all found JSONL files")
    parser.add_argument("--stats-only", action="store_true", help="Show only statistics, no processed activities")
    parser.add_argument("--direct", action="store_true", help="Process file directly without the recorder")
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Find JSONL files
    if args.file:
        if not os.path.exists(args.file):
            print(f"File not found: {args.file}")
            return
        files_to_process = [args.file]
    else:
        files_to_process = find_ntfs_jsonl_files()
        print(f"Found {len(files_to_process)} NTFS JSONL files")
    
    # Process all files or just the first one
    if args.direct:
        # Use direct processing instead of recorder
        if args.file:
            process_file_directly(args.file)
        elif files_to_process:
            process_file_directly(files_to_process[0])
        else:
            print("No NTFS JSONL files found")
    elif args.all:
        results = []
        for file_path in files_to_process:
            results.append(process_with_recorder(file_path, args.debug, args.stats_only))
        
        # Print summary
        print("\nSummary:")
        total_activities = sum(r["processed_activity_count"] for r in results)
        total_time = sum(r["processing_time_seconds"] for r in results)
        print(f"Processed {len(results)} files with {total_activities:,} activities in {total_time:.2f} seconds")
        print(f"Overall performance: {total_activities / total_time:.2f} activities per second")
    else:
        # Process the first file
        if files_to_process:
            process_with_recorder(files_to_process[0], args.debug, args.stats_only)
        else:
            print("No NTFS JSONL files found")


if __name__ == "__main__":
    main()