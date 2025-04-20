#!/usr/bin/env python
"""
Load NTFS activities into the database using the Hot Tier Recorder.

This script loads real NTFS activity data from JSONL files into ArangoDB
through the NTFS Hot Tier Recorder, allowing you to see your actual 
file system activities in the database.

Features:
- Loads NTFS activity data from JSONL files into ArangoDB
- Supports loading multiple files with filtering options
- Provides detailed statistics on loaded activities
- Includes comprehensive test queries to verify data loading
- Generates various reports on activity patterns and importance scores
- Can simulate loading without affecting the database

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
import time
import argparse
import logging
import textwrap
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from collections import Counter

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import the recorder and database components
from activity.recorders.storage.ntfs.tiered.hot.recorder import NtfsHotTierRecorder
from db.db_config import IndalekoDBConfig


def find_ntfs_jsonl_files(newest_first: bool = True) -> List[str]:
    """
    Find all NTFS JSONL files in the repository.
    
    Args:
        newest_first: Sort files by modification time, newest first
        
    Returns:
        List of paths to NTFS JSONL files
    """
    ntfs_files = []
    data_dir = os.path.join(os.environ["INDALEKO_ROOT"], "data")
    
    # Check if data directory exists
    if os.path.exists(data_dir):
        for filename in os.listdir(data_dir):
            if ("ntfs" in filename.lower() or "collector" in filename.lower()) and filename.endswith(".jsonl"):
                file_path = os.path.join(data_dir, filename)
                ntfs_files.append(file_path)
    
    # Also check the activity collectors directory
    activity_dir = os.path.join(os.environ["INDALEKO_ROOT"], "activity", "collectors", "storage", "ntfs")
    if os.path.exists(activity_dir):
        for filename in os.listdir(activity_dir):
            if filename.endswith(".jsonl"):
                file_path = os.path.join(activity_dir, filename)
                ntfs_files.append(file_path)
    
    if newest_first:
        # Sort by modification time, newest first
        ntfs_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    return ntfs_files


def filter_jsonl_files(files: List[str], 
                      min_size: Optional[int] = None, 
                      max_size: Optional[int] = None,
                      pattern: Optional[str] = None,
                      max_age_days: Optional[int] = None) -> List[str]:
    """
    Filter JSONL files based on criteria.
    
    Args:
        files: List of file paths
        min_size: Minimum file size in bytes
        max_size: Maximum file size in bytes
        pattern: Pattern that must be in filename
        max_age_days: Maximum age in days
        
    Returns:
        Filtered list of file paths
    """
    filtered_files = []
    
    for file_path in files:
        # Skip if file doesn't exist
        if not os.path.exists(file_path):
            continue
            
        # Check file size
        file_size = os.path.getsize(file_path)
        if min_size is not None and file_size < min_size:
            continue
        if max_size is not None and file_size > max_size:
            continue
            
        # Check filename pattern
        if pattern is not None and pattern not in os.path.basename(file_path):
            continue
            
        # Check file age
        if max_age_days is not None:
            file_time = os.path.getmtime(file_path)
            file_age = (time.time() - file_time) / (24 * 60 * 60)  # Convert to days
            if file_age > max_age_days:
                continue
                
        filtered_files.append(file_path)
    
    return filtered_files


def analyze_jsonl_file(file_path: str) -> Dict[str, Any]:
    """
    Analyze a JSONL file to extract metadata.
    
    Args:
        file_path: Path to JSONL file
        
    Returns:
        Dictionary with file metadata
    """
    activity_types = Counter()
    line_count = 0
    file_paths = set()
    directories = set()
    volumes = set()
    earliest_time = None
    latest_time = None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line_count += 1
                try:
                    activity = json.loads(line)
                    
                    # Count activity types
                    activity_type = activity.get("activity_type", "unknown")
                    activity_types[activity_type] += 1
                    
                    # Track paths and directories
                    file_path = activity.get("file_path", "")
                    if file_path:
                        file_paths.add(file_path)
                        # Add directory path
                        directory = os.path.dirname(file_path)
                        if directory:
                            directories.add(directory)
                    
                    # Track volumes
                    volume = activity.get("volume_name", "")
                    if volume:
                        volumes.add(volume)
                    
                    # Track timestamps
                    if "timestamp" in activity:
                        try:
                            timestamp = activity["timestamp"]
                            if isinstance(timestamp, str):
                                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                if earliest_time is None or dt < earliest_time:
                                    earliest_time = dt
                                if latest_time is None or dt > latest_time:
                                    latest_time = dt
                        except (ValueError, TypeError):
                            pass
                    
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        return {
            "error": str(e),
            "file_path": file_path,
            "file_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
        }
    
    return {
        "file_path": file_path,
        "file_size": os.path.getsize(file_path),
        "line_count": line_count,
        "activity_types": dict(activity_types),
        "unique_paths": len(file_paths),
        "unique_directories": len(directories),
        "volumes": list(volumes),
        "earliest_time": earliest_time.isoformat() if earliest_time else None,
        "latest_time": latest_time.isoformat() if latest_time else None,
        "time_span_hours": ((latest_time - earliest_time).total_seconds() / 3600) if earliest_time and latest_time else None
    }


def count_activities_in_jsonl(file_path: str) -> Dict[str, int]:
    """
    Count the number of activities by type in a JSONL file.
    
    Args:
        file_path: Path to JSONL file
        
    Returns:
        Dictionary with activity counts
    """
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
                    pass
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    
    return {
        "total_lines": line_count,
        "activity_counts": dict(activity_types)
    }


def setup_database(db_config_path: Optional[str] = None, 
                  simulate: bool = False, 
                  dry_run: bool = False,
                  connection_timeout: int = 30) -> Optional[IndalekoDBConfig]:
    """
    Set up database connection.
    
    Args:
        db_config_path: Optional path to database configuration file
        simulate: If True, don't actually connect to the database
        dry_run: If True, perform a dry run without database modifications
        connection_timeout: Timeout in seconds for database connection
        
    Returns:
        IndalekoDBConfig instance connected to the database or None if simulated
    """
    if simulate:
        print("Database connection simulation mode enabled (no actual connection)")
        return None
        
    if dry_run:
        print("Dry run mode - performing database setup but will not load data")
    
    print("Setting up database connection...")
    
    # Try to use a default config file if not specified
    if db_config_path is None:
        default_config = os.path.join(os.environ["INDALEKO_ROOT"], "db", "db_config.json")
        if os.path.exists(default_config):
            db_config_path = default_config
            print(f"Using default config file: {db_config_path}")
    
    try:
        # Create database configuration
        db_config = IndalekoDBConfig(config_file=db_config_path)
        
        # Set timeout if not None
        if connection_timeout is not None:
            db_config.connection_timeout = connection_timeout
        
        # Start the database connection
        db_config.start()
        print(f"Successfully connected to ArangoDB at {db_config.hostname}:{db_config.port}")
        print(f"Database: {db_config.database}")
        return db_config
    except Exception as e:
        print(f"Error connecting to database: {e}")
        if dry_run:
            print("Continuing with dry run despite database connection error")
            return None
        else:
            raise


def create_hot_tier_recorder(db_config: Optional[IndalekoDBConfig], 
                           ttl_days: int = 4, 
                           debug: bool = False,
                           collection_name: Optional[str] = None,
                           simulate: bool = False,
                           dry_run: bool = False) -> NtfsHotTierRecorder:
    """
    Create a hot tier recorder instance connected to the database.
    
    Args:
        db_config: Database configuration (None if simulate=True)
        ttl_days: Number of days to keep data in hot tier
        debug: Enable debug mode
        collection_name: Optional custom collection name
        simulate: If True, create recorder in simulation mode
        dry_run: If True, configure for dry run (analyze only)
        
    Returns:
        NtfsHotTierRecorder instance
    """
    print(f"Creating hot tier recorder (TTL: {ttl_days} days)...")
    
    # Create recorder with database connection
    kwargs = {
        'ttl_days': ttl_days,
        'debug': debug,
        'no_db': simulate or dry_run or (db_config is None),  # No DB if simulating or dry run
        'register_service': not (simulate or dry_run),  # Don't register in simulation modes
    }
    
    if collection_name:
        kwargs['collection_name'] = collection_name
    
    if db_config is not None and not simulate and not dry_run:
        kwargs['db_config'] = db_config
    
    # Create recorder with database connection
    try:
        recorder = NtfsHotTierRecorder(**kwargs)
        return recorder
    except Exception as e:
        if simulate or dry_run:
            print(f"Error creating recorder in simulation mode: {e}")
            print("Using basic recorder for simulation...")
            # Create with absolute minimum options for dry run
            return NtfsHotTierRecorder(
                no_db=True, 
                register_service=False,
                ttl_days=ttl_days,
                debug=debug
            )
        else:
            raise


def load_activities_to_database(recorder: NtfsHotTierRecorder, 
                             file_path: str,
                             dry_run: bool = False) -> Dict[str, Any]:
    """
    Load NTFS activities from a JSONL file into the database.
    
    Args:
        recorder: Hot tier recorder instance
        file_path: Path to JSONL file with activities
        dry_run: If True, just analyze file but don't load to database
        
    Returns:
        Dictionary with processing statistics
    """
    file_name = os.path.basename(file_path)
    print(f"Processing {file_name}...")
    
    # Get activity counts from file
    activity_counts = count_activities_in_jsonl(file_path)
    print(f"File contains {activity_counts['total_lines']} activities")
    
    # Print activity types
    print("Activity types:")
    for activity_type, count in activity_counts['activity_counts'].items():
        print(f"  {activity_type}: {count}")
        
    # Track processing time
    start_time = time.time()
    
    # Handle dry run mode
    if dry_run:
        print("\nDRY RUN: Not loading activities to database")
        return {
            "file_path": file_path,
            "total_activities": activity_counts["total_lines"],
            "dry_run": True,
            "activity_counts": activity_counts['activity_counts']
        }
    
    # Handle simulation mode (no database connection) or if the recorder is set up for no_db
    if getattr(recorder, "_no_db", False) or not hasattr(recorder, "_db") or recorder._db is None:
        print(f"Simulation mode: Would have processed {activity_counts['total_lines']} activities")
        success = activity_counts['total_lines']
        # Generate some fake IDs
        activity_ids = []
        for _ in range(min(10, success)):
            activity_ids.append(uuid.uuid4())
        
        # Simulate processing time 
        time.sleep(0.05)  # Add a small delay to simulate processing
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"Simulated loading {success} activities in {processing_time:.2f} seconds")
        if processing_time > 0:
            print(f"Simulated processing rate: {success / processing_time:.2f} activities/second")
        
        return {
            "file_path": file_path,
            "total_activities": activity_counts["total_lines"],
            "loaded_activities": success,
            "processing_time": processing_time,
            "activity_ids": activity_ids,
            "activity_counts": activity_counts['activity_counts'],
            "simulated": True
        }
    
    # Process the file with real database connection
    try:
        # Process the file
        activity_ids = recorder.process_jsonl_file(file_path)
        success = len(activity_ids) if activity_ids else 0
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"Successfully loaded {success} activities in {processing_time:.2f} seconds")
        if processing_time > 0:
            print(f"Processing rate: {success / processing_time:.2f} activities/second")
        
        return {
            "file_path": file_path,
            "total_activities": activity_counts["total_lines"],
            "loaded_activities": success,
            "processing_time": processing_time,
            "activity_ids": activity_ids,
            "activity_counts": activity_counts['activity_counts']
        }
    except Exception as e:
        print(f"Error processing file: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "file_path": file_path,
            "error": str(e),
            "total_activities": activity_counts["total_lines"],
            "loaded_activities": 0,
            "activity_counts": activity_counts['activity_counts']
        }


def run_test_queries(recorder: NtfsHotTierRecorder, 
                    query_types: List[str] = None,
                    verbose: bool = False) -> Dict[str, Any]:
    """
    Run test queries to verify data was loaded correctly.
    
    Args:
        recorder: Hot tier recorder instance
        query_types: List of query types to run (None for all)
        verbose: Whether to print verbose output
        
    Returns:
        Dictionary with query results
    """
    print("\nRunning test queries...")
    results = {}
    
    if query_types is None:
        query_types = ["statistics", "recent", "creates", "renames", "entities", "popular"]
    
    # Get statistics
    if "statistics" in query_types:
        try:
            print("\nActivity Statistics:")
            stats = recorder.get_hot_tier_statistics()
            results["statistics"] = stats
            
            if "total_count" in stats:
                print(f"  Total activities: {stats['total_count']:,}")
            
            if "by_type" in stats:
                print("  Activities by type:")
                for activity_type, count in stats.get("by_type", {}).items():
                    print(f"    {activity_type}: {count:,}")
                
            if "by_importance" in stats and verbose:
                print("  Activities by importance score range:")
                for score_range, count in stats.get("by_importance", {}).items():
                    print(f"    {score_range}: {count:,}")
                
            if "by_time" in stats:
                print("  Activities by time:")
                for time_range, count in stats.get("by_time", {}).items():
                    print(f"    {time_range}: {count:,}")
                
        except Exception as e:
            print(f"Error getting statistics: {e}")
            results["statistics_error"] = str(e)
    
    # Get recent activities
    if "recent" in query_types:
        try:
            print("\nRecent activities (last 24 hours):")
            recent = recorder.get_recent_activities(hours=24, limit=5)
            results["recent_activities"] = [{
                "id": activity.get("_key"),
                "type": activity.get("Record", {}).get("Data", {}).get("activity_type"),
                "file_name": activity.get("Record", {}).get("Data", {}).get("file_name"),
                "timestamp": activity.get("Record", {}).get("Data", {}).get("timestamp"),
                "entity_id": activity.get("Record", {}).get("Data", {}).get("entity_id"),
                "importance": activity.get("Record", {}).get("Data", {}).get("importance_score")
            } for activity in recent]
            
            for i, activity in enumerate(recent):
                data = activity.get("Record", {}).get("Data", {})
                print(f"  Activity {i+1}:")
                print(f"    Type: {data.get('activity_type', 'Unknown')}")
                print(f"    File: {data.get('file_name', 'Unknown')}")
                path = data.get('file_path', 'Unknown')
                # Truncate long paths
                if len(path) > 60 and not verbose:
                    path = "..." + path[-57:]
                print(f"    Path: {path}")
                print(f"    Time: {data.get('timestamp', 'Unknown')}")
                print(f"    Importance: {data.get('importance_score', 'Unknown')}")
                if verbose:
                    print(f"    Entity ID: {data.get('entity_id', 'Unknown')}")
                print("")
        except Exception as e:
            print(f"Error getting recent activities: {e}")
            results["recent_activities_error"] = str(e)
    
    # Get activities by type
    if "creates" in query_types:
        try:
            print("\nCreate activities (top 3):")
            creates = recorder.get_activities_by_type("create", limit=3)
            results["create_activities"] = [{
                "id": activity.get("_key"),
                "file_name": activity.get("Record", {}).get("Data", {}).get("file_name"),
                "timestamp": activity.get("Record", {}).get("Data", {}).get("timestamp"),
                "entity_id": activity.get("Record", {}).get("Data", {}).get("entity_id")
            } for activity in creates]
            
            for i, activity in enumerate(creates):
                data = activity.get("Record", {}).get("Data", {})
                print(f"  Create {i+1}: {data.get('file_name', 'Unknown')} at {data.get('timestamp', 'Unknown')}")
        except Exception as e:
            print(f"Error getting create activities: {e}")
            results["create_activities_error"] = str(e)
    
    # Get rename activities
    if "renames" in query_types:
        try:
            print("\nRename activities (top 3):")
            renames = recorder.get_rename_activities(hours=72, limit=3)
            results["rename_activities"] = [{
                "id": activity.get("_key"),
                "file_name": activity.get("Record", {}).get("Data", {}).get("file_name"),
                "timestamp": activity.get("Record", {}).get("Data", {}).get("timestamp"),
                "entity_id": activity.get("Record", {}).get("Data", {}).get("entity_id")
            } for activity in renames]
            
            for i, activity in enumerate(renames):
                data = activity.get("Record", {}).get("Data", {})
                print(f"  Rename {i+1}: {data.get('file_name', 'Unknown')} at {data.get('timestamp', 'Unknown')}")
        except Exception as e:
            print(f"Error getting rename activities: {e}")
            results["rename_activities_error"] = str(e)
    
    # Get entity activities
    if "entities" in query_types and recent and len(recent) > 0:
        try:
            entity_id = recent[0].get("Record", {}).get("Data", {}).get("entity_id")
            if entity_id:
                print(f"\nAll activities for entity {entity_id} (top 3):")
                entity_activities = recorder.get_activities_by_entity(uuid.UUID(entity_id), limit=3)
                results["entity_activities"] = [{
                    "id": activity.get("_key"),
                    "type": activity.get("Record", {}).get("Data", {}).get("activity_type"),
                    "file_name": activity.get("Record", {}).get("Data", {}).get("file_name"),
                    "timestamp": activity.get("Record", {}).get("Data", {}).get("timestamp")
                } for activity in entity_activities]
                
                for i, activity in enumerate(entity_activities):
                    data = activity.get("Record", {}).get("Data", {})
                    print(f"  Activity {i+1}: {data.get('activity_type', 'Unknown')} on {data.get('file_name', 'Unknown')} at {data.get('timestamp', 'Unknown')}")
        except Exception as e:
            print(f"Error getting entity activities: {e}")
            results["entity_activities_error"] = str(e)
    
    # Get high importance activities
    if "popular" in query_types:
        try:
            print("\nHigh importance activities (top 3):")
            # Use AQL to query by importance score
            if hasattr(recorder, "_db") and recorder._db:
                query = """
                    FOR doc IN @@collection
                    FILTER doc.Record.Data.importance_score >= 0.7
                    SORT doc.Record.Data.importance_score DESC
                    LIMIT 3
                    RETURN doc
                """
                
                cursor = recorder._db.db.aql.execute(
                    query,
                    bind_vars={"@collection": recorder._collection_name}
                )
                
                high_importance = list(cursor)
                results["high_importance_activities"] = [{
                    "id": activity.get("_key"),
                    "type": activity.get("Record", {}).get("Data", {}).get("activity_type"),
                    "file_name": activity.get("Record", {}).get("Data", {}).get("file_name"),
                    "timestamp": activity.get("Record", {}).get("Data", {}).get("timestamp"),
                    "importance": activity.get("Record", {}).get("Data", {}).get("importance_score")
                } for activity in high_importance]
                
                for i, activity in enumerate(high_importance):
                    data = activity.get("Record", {}).get("Data", {})
                    print(f"  Important {i+1}: {data.get('activity_type', 'Unknown')} on {data.get('file_name', 'Unknown')} (score: {data.get('importance_score', 0):.2f})")
        except Exception as e:
            print(f"Error getting high importance activities: {e}")
            results["high_importance_activities_error"] = str(e)
    
    return results


def generate_summary_report(results: List[Dict[str, Any]], queries: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate a summary report from processing results.
    
    Args:
        results: List of processing results
        queries: Optional query results
        
    Returns:
        Formatted report text
    """
    if not results:
        return "No processing results to summarize"
        
    # Calculate totals
    total_activities = sum(r.get("total_activities", 0) for r in results)
    loaded_activities = sum(r.get("loaded_activities", 0) for r in results)
    processing_time = sum(r.get("processing_time", 0) for r in results)
    
    # Get activity counts by type
    activity_counts = Counter()
    for result in results:
        if "activity_counts" in result:
            for activity_type, count in result["activity_counts"].items():
                activity_counts[activity_type] += count
    
    # Build report
    report = []
    report.append("===== NTFS Hot Tier Recorder Summary Report =====")
    report.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    report.append("")
    report.append("Processing Summary:")
    report.append(f"- Files processed: {len(results)}")
    report.append(f"- Total activities in files: {total_activities:,}")
    report.append(f"- Activities loaded to database: {loaded_activities:,} ({loaded_activities/total_activities*100:.1f}% success)")
    report.append(f"- Total processing time: {processing_time:.2f} seconds")
    if processing_time > 0:
        report.append(f"- Average processing rate: {loaded_activities/processing_time:.1f} activities/second")
    
    report.append("")
    report.append("Activity Types:")
    for activity_type, count in sorted(activity_counts.items(), key=lambda x: x[1], reverse=True):
        report.append(f"- {activity_type}: {count:,} ({count/total_activities*100:.1f}%)")
    
    # Add database statistics if available
    if queries and "statistics" in queries:
        stats = queries["statistics"]
        report.append("")
        report.append("Database Statistics:")
        
        if "total_count" in stats:
            report.append(f"- Total activities in hot tier: {stats['total_count']:,}")
            
        if "ttl_days" in stats:
            report.append(f"- TTL expiration: {stats['ttl_days']} days")
            
        if "by_type" in stats:
            report.append("- Activities by type in database:")
            for activity_type, count in sorted(stats["by_type"].items(), key=lambda x: x[1], reverse=True):
                report.append(f"  - {activity_type}: {count:,}")
        
        if "by_importance" in stats:
            report.append("- Activities by importance score:")
            for score_range, count in sorted(stats["by_importance"].items()):
                report.append(f"  - {score_range}: {count:,}")
    
    report.append("")
    report.append("File Details:")
    for i, result in enumerate(results):
        file_path = result.get("file_path", "Unknown")
        file_name = os.path.basename(file_path)
        total = result.get("total_activities", 0)
        loaded = result.get("loaded_activities", 0)
        
        report.append(f"- File {i+1}: {file_name}")
        report.append(f"  - Activities: {total:,}")
        report.append(f"  - Loaded: {loaded:,}")
        if "error" in result:
            report.append(f"  - Error: {result['error']}")
    
    return "\n".join(report)


def save_report_to_file(report: str, output_path: Optional[str] = None) -> str:
    """
    Save report to a file.
    
    Args:
        report: Report text
        output_path: Path to save report (None for auto-generated)
        
    Returns:
        Path to saved report
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(os.environ["INDALEKO_ROOT"], 
                                 "data", 
                                 f"ntfs_hot_tier_report_{timestamp}.txt")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"Report saved to {output_path}")
    return output_path


def show_welcome_message():
    """Display a welcome message with program description."""
    welcome = """
    ╔════════════════════════════════════════════════════════════╗
    ║               NTFS Hot Tier Recorder Loader                ║
    ╠════════════════════════════════════════════════════════════╣
    ║ This tool loads real NTFS activity data into ArangoDB's    ║
    ║ hot tier, allowing you to see your actual file system      ║
    ║ activities in the database.                               ║
    ║                                                            ║
    ║ The hot tier represents recent, high-fidelity activity     ║
    ║ data before it transitions to warm/cool tiers.             ║
    ╚════════════════════════════════════════════════════════════╝
    """
    print(welcome)


def parse_arguments():
    """Parse command line arguments with detailed help text."""
    parser = argparse.ArgumentParser(
        description="Load NTFS activities into ArangoDB Hot Tier",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog=textwrap.dedent("""
        Examples:
          # Process the newest NTFS JSONL file found
          python load_to_database.py
          
          # Process a specific file with verbose output
          python load_to_database.py --file /path/to/ntfs_data.jsonl --verbose
          
          # Process all NTFS JSONL files and generate a report
          python load_to_database.py --all --report
          
          # Test loading without affecting the database
          python load_to_database.py --simulate --verbose
          
          # Find available JSONL files without processing
          python load_to_database.py --list-files
        """))
    
    # File selection options
    file_group = parser.add_argument_group('File Selection')
    file_group.add_argument("--file", type=str, help="Specific JSONL file to process")
    file_group.add_argument("--all", action="store_true", help="Process all NTFS JSONL files found")
    file_group.add_argument("--pattern", type=str, help="Only process files containing this pattern in name")
    file_group.add_argument("--list-files", action="store_true", help="List available NTFS JSONL files and exit")
    file_group.add_argument("--newest", type=int, default=1, help="Process only N newest files (0 for all)")
    file_group.add_argument("--max-age-days", type=int, help="Only process files modified within N days")
    
    # Database options
    db_group = parser.add_argument_group('Database Options')
    db_group.add_argument("--db-config", type=str, help="Path to database configuration file")
    db_group.add_argument("--ttl-days", type=int, default=4, help="Number of days to keep data in hot tier")
    db_group.add_argument("--collection", type=str, help="Custom collection name for hot tier")
    db_group.add_argument("--connection-timeout", type=int, default=30, help="Database connection timeout in seconds")
    
    # Operation modes
    mode_group = parser.add_argument_group('Operation Modes')
    mode_group.add_argument("--dry-run", action="store_true", help="Analyze files but don't load to database")
    mode_group.add_argument("--simulate", action="store_true", help="Simulate without database connection")
    mode_group.add_argument("--no-queries", action="store_true", help="Skip running test queries")
    
    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument("--debug", action="store_true", help="Enable debug logging")
    output_group.add_argument("--verbose", action="store_true", help="Show more detailed output")
    output_group.add_argument("--quiet", action="store_true", help="Minimal output")
    output_group.add_argument("--report", action="store_true", help="Generate summary report after processing")
    output_group.add_argument("--report-file", type=str, help="Path to save report (auto-generated if not specified)")
    
    args = parser.parse_args()
    
    # Handle conflicting options
    if args.simulate and args.dry_run:
        parser.error("--simulate and --dry-run cannot be used together")
        
    if args.quiet and args.verbose:
        parser.error("--quiet and --verbose cannot be used together")
    
    if args.newest <= 0:
        args.newest = None  # Process all files
        
    return args


def main():
    """Main function."""
    # Parse arguments
    args = parse_arguments()
    
    # Show welcome message if not in quiet mode
    if not args.quiet:
        show_welcome_message()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    if args.quiet:
        log_level = logging.WARNING
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    try:
        # Find JSONL files
        all_files = find_ntfs_jsonl_files()
        
        # List files and exit if requested
        if args.list_files:
            print(f"Found {len(all_files)} NTFS JSONL files:")
            for i, file_path in enumerate(all_files):
                file_stats = os.stat(file_path)
                file_size = file_stats.st_size
                mod_time = datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                print(f"{i+1}. {os.path.basename(file_path)}")
                print(f"   Path: {file_path}")
                print(f"   Size: {file_size:,} bytes")
                print(f"   Modified: {mod_time}")
                
                if args.verbose:
                    # Show quick analysis
                    try:
                        metadata = analyze_jsonl_file(file_path)
                        print(f"   Activities: {metadata.get('line_count', 'Unknown')}")
                        if 'activity_types' in metadata:
                            types_str = ", ".join(f"{t}: {c}" for t, c in metadata['activity_types'].items())
                            print(f"   Types: {types_str}")
                        if metadata.get('earliest_time') and metadata.get('latest_time'):
                            print(f"   Time span: {metadata.get('earliest_time')} to {metadata.get('latest_time')}")
                            if metadata.get('time_span_hours'):
                                print(f"   Duration: {metadata.get('time_span_hours'):.1f} hours")
                    except Exception as e:
                        print(f"   Error analyzing file: {e}")
                
                print("")
            return
        
        # Filter files based on args
        files_to_process = []
        
        if args.file:
            if not os.path.exists(args.file):
                print(f"File not found: {args.file}")
                return
            files_to_process = [args.file]
        else:
            # Filter files
            filtered_files = filter_jsonl_files(
                all_files,
                pattern=args.pattern,
                max_age_days=args.max_age_days
            )
            
            # Apply newest limit if specified
            if args.newest is not None and not args.all:
                filtered_files = filtered_files[:args.newest]
                
            files_to_process = filtered_files
            
        if not files_to_process:
            print("No matching NTFS JSONL files found")
            return
            
        print(f"Found {len(files_to_process)} files to process")
        
        # Setup database connection
        db_config = setup_database(
            args.db_config, 
            simulate=args.simulate,
            dry_run=args.dry_run,
            connection_timeout=args.connection_timeout
        )
        
        # Create hot tier recorder
        recorder = create_hot_tier_recorder(
            db_config, 
            args.ttl_days, 
            args.debug,
            collection_name=args.collection,
            simulate=args.simulate,
            dry_run=args.dry_run
        )
        
        # Process files
        results = []
        for file_path in files_to_process:
            result = load_activities_to_database(
                recorder, 
                file_path,
                dry_run=args.dry_run
            )
            results.append(result)
        
        # Run test queries if not disabled
        queries = None
        if not args.no_queries and not args.dry_run:
            queries = run_test_queries(
                recorder,
                verbose=args.verbose
            )
        
        # Generate report if requested
        if args.report:
            report = generate_summary_report(results, queries)
            if args.report_file:
                save_report_to_file(report, args.report_file)
            else:
                save_report_to_file(report)
                if args.verbose:
                    print("\n" + report)
        
        print("\nDone!")
        
    except Exception as e:
        print(f"Error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    # Import uuid here since it's not needed at module level
    import uuid
    main()