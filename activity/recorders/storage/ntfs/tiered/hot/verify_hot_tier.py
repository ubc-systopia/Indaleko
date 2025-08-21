#!/usr/bin/env python3
"""
Verification script for NtfsHotTierRecorder implementation.

This script provides a comprehensive verification of the NtfsHotTierRecorder by:
1. Setting up a database connection
2. Loading real NTFS activity data
3. Verifying entity mapping functionality
4. Testing TTL expiration
5. Running performance benchmarks
6. Testing query capabilities

Usage:
    python verify_hot_tier.py --database-url http://localhost:8529 --database indaleko
    python verify_hot_tier.py --find-files --path /path/to/search
    python verify_hot_tier.py --verify-entities
    python verify_hot_tier.py --test-ttl
    python verify_hot_tier.py --benchmark
    python verify_hot_tier.py --full-verification

Author: Indaleko Team
"""

import argparse
import datetime
import glob
import json
import os
import sys
import time
import uuid

from datetime import timedelta
from typing import Any


# Add parent directory to path to ensure imports work correctly
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../../..")),
)

from activity.recorders.storage.ntfs.tiered.hot.recorder import NtfsHotTierRecorder
from data_models import timestamp
from data_models.db_config import IndalekoDBConfig


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Verify NtfsHotTierRecorder implementation",
    )

    # Database connection options
    parser.add_argument(
        "--database-url",
        type=str,
        default="http://localhost:8529",
        help="URL for ArangoDB server",
    )
    parser.add_argument(
        "--database",
        type=str,
        default="indaleko",
        help="Database name",
    )
    parser.add_argument(
        "--username",
        type=str,
        default="root",
        help="Database username",
    )
    parser.add_argument("--password", type=str, default="", help="Database password")

    # Verification modes
    parser.add_argument(
        "--find-files",
        action="store_true",
        help="Find JSONL files with NTFS activity data",
    )
    parser.add_argument(
        "--path",
        type=str,
        default=None,
        help="Path to search for JSONL files",
    )
    parser.add_argument(
        "--verify-connection",
        action="store_true",
        help="Verify database connection",
    )
    parser.add_argument(
        "--load-data",
        action="store_true",
        help="Load activity data to database",
    )
    parser.add_argument(
        "--verify-entities",
        action="store_true",
        help="Verify entity mapping functionality",
    )
    parser.add_argument("--test-ttl", action="store_true", help="Test TTL expiration")
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run performance benchmarks",
    )
    parser.add_argument(
        "--query-test",
        action="store_true",
        help="Test query capabilities",
    )
    parser.add_argument(
        "--full-verification",
        action="store_true",
        help="Run all verification steps",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Specific JSONL file to process",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate operations without affecting database",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit the number of records to process",
    )

    return parser.parse_args()


def find_jsonl_files(path: str | None = None) -> list[str]:
    """
    Find JSONL files that contain NTFS activity data.

    Args:
        path: Directory to search (defaults to system-specific locations if None)

    Returns:
        List of file paths
    """
    files = []

    # Default search paths based on platform
    if path is None:
        if sys.platform == "win32":
            # Windows default paths
            paths = [
                os.path.join(os.environ.get("APPDATA", ""), "Indaleko", "ntfs"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Indaleko", "ntfs"),
                os.path.join(os.getcwd(), "activity", "collectors", "storage", "ntfs"),
            ]
        else:
            # Linux/macOS default paths
            home = os.environ.get("HOME", "")
            paths = [
                os.path.join(home, ".indaleko", "ntfs"),
                os.path.join(home, ".local", "share", "indaleko", "ntfs"),
                os.path.join(os.getcwd(), "activity", "collectors", "storage", "ntfs"),
            ]
    else:
        paths = [path]

    # Search all paths
    for search_path in paths:
        if os.path.exists(search_path):
            # Look for .jsonl files
            for pattern in ["*.jsonl", "**/*.jsonl", "activities/*.jsonl"]:
                jsonl_pattern = os.path.join(search_path, pattern)
                files.extend(glob.glob(jsonl_pattern, recursive=True))

    return sorted(files)


def create_recorder(args) -> NtfsHotTierRecorder:
    """
    Create a NtfsHotTierRecorder instance with the specified configuration.

    Args:
        args: Command line arguments

    Returns:
        Configured NtfsHotTierRecorder instance
    """
    # Create with no_db if this is a dry run
    if args.dry_run:
        return NtfsHotTierRecorder(no_db=True)

    # Create with database connection
    db_config = IndalekoDBConfig(
        url=args.database_url,
        database=args.database,
        username=args.username,
        password=args.password,
    )

    return NtfsHotTierRecorder(db_config=db_config)


def verify_database_connection(recorder: NtfsHotTierRecorder) -> bool:
    """
    Verify that the recorder can connect to the database.

    Args:
        recorder: NtfsHotTierRecorder instance

    Returns:
        True if connection is successful, False otherwise
    """
    if getattr(recorder, "_no_db", False):
        return True

    try:
        # Check if we have a connection
        if not hasattr(recorder, "_db") or recorder._db is None:
            return False

        # Verify connection by checking database version
        version = recorder._db.properties()
        return bool(version and "version" in version)
    except Exception:
        return False


def count_activities_in_jsonl(file_path: str) -> dict[str, Any]:
    """
    Count the number of activities in a JSONL file and categorize them.

    Args:
        file_path: Path to JSONL file

    Returns:
        Dictionary with activity statistics
    """
    total_lines = 0
    activity_counts = {}

    try:
        with open(file_path, encoding="utf-8") as f:
            for line in f:
                total_lines += 1
                try:
                    activity = json.loads(line.strip())
                    activity_type = activity.get("Activity", {}).get(
                        "activity_type",
                        "unknown",
                    )

                    if activity_type in activity_counts:
                        activity_counts[activity_type] += 1
                    else:
                        activity_counts[activity_type] = 1
                except json.JSONDecodeError:
                    if "invalid_json" in activity_counts:
                        activity_counts["invalid_json"] += 1
                    else:
                        activity_counts["invalid_json"] = 1
    except Exception as e:
        return {"total_lines": 0, "activity_counts": {"error": str(e)}}

    return {"total_lines": total_lines, "activity_counts": activity_counts}


def load_data_to_database(
    recorder: NtfsHotTierRecorder,
    files: list[str],
    args,
) -> dict[str, Any]:
    """
    Load NTFS activity data from JSONL files into the database.

    Args:
        recorder: NtfsHotTierRecorder instance
        files: List of JSONL file paths
        args: Command line arguments

    Returns:
        Dictionary with loading statistics
    """
    start_time = time.time()
    results = {
        "total_files": len(files),
        "processed_files": 0,
        "total_activities": 0,
        "loaded_activities": 0,
        "errors": 0,
        "processing_time": 0,
        "file_results": [],
    }

    for file_path in files:
        file_start_time = time.time()
        os.path.basename(file_path)

        # Get activity counts from file
        activity_counts = count_activities_in_jsonl(file_path)

        results["total_activities"] += activity_counts["total_lines"]

        # Handle simulation mode (dry run)
        if args.dry_run or getattr(recorder, "_no_db", False):
            success = activity_counts["total_lines"]

            # Generate some fake IDs
            activity_ids = []
            for _ in range(min(10, success)):
                activity_ids.append(uuid.uuid4())

            # Simulate processing time
            time.sleep(0.05)

            file_result = {
                "file_path": file_path,
                "total_activities": activity_counts["total_lines"],
                "loaded_activities": success,
                "processing_time": time.time() - file_start_time,
                "activity_ids": [str(id) for id in activity_ids[:5]],
                "activity_counts": activity_counts["activity_counts"],
                "simulated": True,
            }

            results["loaded_activities"] += success
        else:
            # Process with real database connection
            try:
                # Apply limit if specified
                process_options = {}
                if args.limit:
                    process_options["limit"] = args.limit

                # Process the file
                activity_ids = recorder.process_jsonl_file(file_path, **process_options)
                success = len(activity_ids) if activity_ids else 0

                file_result = {
                    "file_path": file_path,
                    "total_activities": activity_counts["total_lines"],
                    "loaded_activities": success,
                    "processing_time": time.time() - file_start_time,
                    "activity_ids": ([str(id) for id in activity_ids[:5]] if activity_ids else []),
                    "activity_counts": activity_counts["activity_counts"],
                }

                results["loaded_activities"] += success
            except Exception as e:
                import traceback

                traceback.print_exc()

                file_result = {
                    "file_path": file_path,
                    "error": str(e),
                    "total_activities": activity_counts["total_lines"],
                    "loaded_activities": 0,
                    "processing_time": time.time() - file_start_time,
                    "activity_counts": activity_counts["activity_counts"],
                }

                results["errors"] += 1

        # Add to results
        results["file_results"].append(file_result)
        results["processed_files"] += 1

        # Print processing rate
        processing_time = file_result["processing_time"]
        loaded = file_result["loaded_activities"]

        if processing_time > 0 and loaded > 0:
            pass


    # Calculate overall statistics
    results["processing_time"] = time.time() - start_time

    if results["processing_time"] > 0 and results["loaded_activities"] > 0:
        results["activities_per_second"] = results["loaded_activities"] / results["processing_time"]
    else:
        results["activities_per_second"] = 0

    return results


def verify_entity_mapping(recorder: NtfsHotTierRecorder, args) -> dict[str, Any]:
    """
    Verify that the entity mapping functionality works correctly.

    Args:
        recorder: NtfsHotTierRecorder instance
        args: Command line arguments

    Returns:
        Dictionary with verification results
    """
    if args.dry_run or getattr(recorder, "_no_db", False):
        return {
            "success": True,
            "message": "Dry run mode - entity mapping would be verified",
            "entities_verified": 0,
            "mapping_verified": False,
        }

    try:
        # Find entities with multiple FRNs mapped to the same UUID
        query = """
        FOR doc IN @@collection
        COLLECT entity_id = doc.entity_id
        WITH COUNT INTO frn_count
        FILTER frn_count > 1
        RETURN {
            entity_id: entity_id,
            frn_count: frn_count
        }
        """

        bind_vars = {"@collection": recorder._entity_map_collection.name}

        result = recorder._db.aql.execute(query, bind_vars=bind_vars)
        mapped_entities = list(result)

        # If we found mapped entities, verify the mapping works
        if mapped_entities:
            # Sample one entity to verify
            entity = mapped_entities[0]
            entity_id = entity["entity_id"]

            # Get all FRNs for this entity
            query = """
            FOR doc IN @@collection
            FILTER doc.entity_id == @entity_id
            RETURN doc
            """

            bind_vars = {
                "@collection": recorder._entity_map_collection.name,
                "entity_id": entity_id,
            }

            frn_docs = list(recorder._db.aql.execute(query, bind_vars=bind_vars))

            # Verify that entity lookup works for each FRN
            verification_results = []
            for frn_doc in frn_docs:
                frn = frn_doc["frn"]
                volume = frn_doc["volume_path"]

                # Test the entity lookup
                try:
                    lookup_result = recorder._get_entity_uuid(volume, frn)
                    verification_results.append(
                        {
                            "frn": frn,
                            "volume": volume,
                            "expected_entity_id": entity_id,
                            "actual_entity_id": str(lookup_result),
                            "success": str(lookup_result) == entity_id,
                        },
                    )
                except Exception as e:
                    verification_results.append(
                        {
                            "frn": frn,
                            "volume": volume,
                            "expected_entity_id": entity_id,
                            "error": str(e),
                            "success": False,
                        },
                    )

            # Check if all verifications succeeded
            all_succeeded = all(v["success"] for v in verification_results)

            return {
                "success": all_succeeded,
                "message": "Entity mapping verification completed",
                "entities_verified": len(mapped_entities),
                "entity_samples": mapped_entities[:5],
                "verification_results": verification_results,
                "mapping_verified": all_succeeded,
            }
        return {
            "success": False,
            "message": "No entities with multiple FRNs found - cannot verify mapping",
            "entities_verified": 0,
            "mapping_verified": False,
        }
    except Exception as e:
        import traceback

        traceback.print_exc()

        return {
            "success": False,
            "message": f"Error verifying entity mapping: {e}",
            "entities_verified": 0,
            "mapping_verified": False,
        }


def test_ttl_expiration(recorder: NtfsHotTierRecorder, args) -> dict[str, Any]:
    """
    Test the TTL expiration functionality.

    Args:
        recorder: NtfsHotTierRecorder instance
        args: Command line arguments

    Returns:
        Dictionary with test results
    """
    if args.dry_run or getattr(recorder, "_no_db", False):
        return {
            "success": True,
            "message": "Dry run mode - TTL expiration would be tested",
            "ttl_verified": False,
        }

    try:
        # Check if TTL index exists
        ttl_indices = []

        for index in recorder._activities_collection.indexes():
            if index.get("type") == "ttl":
                ttl_indices.append(index)

        if not ttl_indices:
            return {
                "success": False,
                "message": "No TTL index found on activities collection",
                "ttl_verified": False,
            }

        # Create a test activity with expiration
        now = datetime.datetime.now(datetime.UTC)

        # Set expiration 30 seconds in the future
        expiration = now + timedelta(seconds=30)

        # Create a test activity
        test_activity = {
            "_key": str(uuid.uuid4()),
            "entity_id": str(uuid.uuid4()),
            "activity_type": "TTL_TEST",
            "timestamp": timestamp.format_timestamp(now),
            "expiration": timestamp.format_timestamp(expiration),
            "importance": 0.5,
            "test_ttl": True,
        }

        # Insert the test activity
        recorder._activities_collection.insert(test_activity)

        # Verify the activity was inserted
        inserted = recorder._activities_collection.get(test_activity["_key"])

        if not inserted:
            return {
                "success": False,
                "message": "Failed to insert test activity for TTL verification",
                "ttl_verified": False,
            }


        # Wait for expiration (with a bit of buffer)
        max_wait = 65  # seconds
        ttl_verified = False

        for i in range(max_wait):
            time.sleep(1)

            # Check if activity is still there
            try:
                still_exists = recorder._activities_collection.get(
                    test_activity["_key"],
                )

                # If more than 30 seconds have passed, the document should be deleted
                if i >= 30 and not still_exists:
                    ttl_verified = True
                    break

                if i % 5 == 0:
                    pass
            except Exception:
                break

        return {
            "success": ttl_verified,
            "message": "TTL expiration test completed",
            "ttl_verified": ttl_verified,
            "ttl_indices": ttl_indices,
            "test_activity": test_activity,
            "wait_time": i + 1 if "i" in locals() else 0,
        }
    except Exception as e:
        import traceback

        traceback.print_exc()

        return {
            "success": False,
            "message": f"Error testing TTL expiration: {e}",
            "ttl_verified": False,
        }


def run_performance_benchmark(recorder: NtfsHotTierRecorder, args) -> dict[str, Any]:
    """
    Run performance benchmarks on the NtfsHotTierRecorder.

    Args:
        recorder: NtfsHotTierRecorder instance
        args: Command line arguments

    Returns:
        Dictionary with benchmark results
    """
    if args.dry_run or getattr(recorder, "_no_db", False):
        return {
            "success": True,
            "message": "Dry run mode - performance benchmarks would be run",
            "benchmarks": {},
        }

    benchmarks = {}

    try:
        # Benchmark 1: Query recent activities
        try:
            start_time = time.time()
            activities = recorder.get_recent_activities(limit=100)
            query_time = time.time() - start_time

            benchmarks["recent_activities"] = {
                "success": True,
                "time": query_time,
                "count": len(activities) if activities else 0,
                "query": "get_recent_activities(limit=100)",
            }

        except Exception as e:
            benchmarks["recent_activities"] = {
                "success": False,
                "error": str(e),
                "query": "get_recent_activities(limit=100)",
            }

        # Benchmark 2: Query by entity
        # First, find an entity with activities
        try:
            query = """
            FOR doc IN @@collection
            LIMIT 1
            RETURN doc.entity_id
            """

            bind_vars = {"@collection": recorder._activities_collection.name}

            result = recorder._db.aql.execute(query, bind_vars=bind_vars)
            entity_ids = list(result)

            if entity_ids:
                entity_id = entity_ids[0]

                start_time = time.time()
                activities = recorder.get_activities_by_entity(entity_id, limit=100)
                query_time = time.time() - start_time

                benchmarks["entity_activities"] = {
                    "success": True,
                    "time": query_time,
                    "count": len(activities) if activities else 0,
                    "entity_id": entity_id,
                    "query": f"get_activities_by_entity('{entity_id}', limit=100)",
                }

            else:
                benchmarks["entity_activities"] = {
                    "success": False,
                    "error": "No entities found for benchmark",
                    "query": "get_activities_by_entity",
                }
        except Exception as e:
            benchmarks["entity_activities"] = {
                "success": False,
                "error": str(e),
                "query": "get_activities_by_entity",
            }

        # Benchmark 3: Query by time range
        try:
            # Get activities from the last 24 hours
            end_time = datetime.datetime.now(datetime.UTC)
            start_time_dt = end_time - timedelta(hours=24)

            query_start_time = time.time()
            activities = recorder.get_activities_by_time_range(
                start_time_dt,
                end_time,
                limit=100,
            )
            query_time = time.time() - query_start_time

            benchmarks["time_range_activities"] = {
                "success": True,
                "time": query_time,
                "count": len(activities) if activities else 0,
                "start_time": timestamp.format_timestamp(start_time_dt),
                "end_time": timestamp.format_timestamp(end_time),
                "query": f"get_activities_by_time_range(start={start_time_dt}, end={end_time}, limit=100)",
            }

        except Exception as e:
            benchmarks["time_range_activities"] = {
                "success": False,
                "error": str(e),
                "query": "get_activities_by_time_range",
            }

        # Overall benchmark results
        successful_benchmarks = sum(1 for b in benchmarks.values() if b.get("success", False))
        total_benchmarks = len(benchmarks)

        return {
            "success": successful_benchmarks == total_benchmarks,
            "message": f"Performance benchmarks completed: {successful_benchmarks}/{total_benchmarks} successful",
            "benchmarks": benchmarks,
        }
    except Exception as e:
        import traceback

        traceback.print_exc()

        return {
            "success": False,
            "message": f"Error running performance benchmarks: {e}",
            "benchmarks": benchmarks,
        }


def test_query_capabilities(recorder: NtfsHotTierRecorder, args) -> dict[str, Any]:
    """
    Test the query capabilities of the NtfsHotTierRecorder.

    Args:
        recorder: NtfsHotTierRecorder instance
        args: Command line arguments

    Returns:
        Dictionary with test results
    """
    if args.dry_run or getattr(recorder, "_no_db", False):
        return {
            "success": True,
            "message": "Dry run mode - query capabilities would be tested",
            "query_tests": {},
        }

    query_tests = {}

    try:
        # Test 1: Query recent activities
        try:
            activities = recorder.get_recent_activities(limit=5)

            query_tests["recent_activities"] = {
                "success": True,
                "count": len(activities) if activities else 0,
                "samples": activities[:2] if activities else [],
            }

        except Exception as e:
            query_tests["recent_activities"] = {"success": False, "error": str(e)}

        # Test 2: Query by activity type
        try:
            # First, find available activity types
            query = """
            FOR doc IN @@collection
            COLLECT activity_type = doc.activity_type
            RETURN activity_type
            """

            bind_vars = {"@collection": recorder._activities_collection.name}

            result = recorder._db.aql.execute(query, bind_vars=bind_vars)
            activity_types = list(result)

            if activity_types:
                test_type = activity_types[0]

                activities = recorder.get_activities_by_type(test_type, limit=5)

                query_tests["activity_type"] = {
                    "success": True,
                    "activity_type": test_type,
                    "count": len(activities) if activities else 0,
                    "samples": activities[:2] if activities else [],
                }

            else:
                query_tests["activity_type"] = {
                    "success": False,
                    "error": "No activity types found for test",
                }
        except Exception as e:
            query_tests["activity_type"] = {"success": False, "error": str(e)}

        # Test 3: Query by path
        try:
            # First, find a path to query
            query = """
            FOR doc IN @@collection
            FILTER doc.path != null
            LIMIT 1
            RETURN doc.path
            """

            bind_vars = {"@collection": recorder._activities_collection.name}

            result = recorder._db.aql.execute(query, bind_vars=bind_vars)
            paths = list(result)

            if paths:
                test_path = paths[0]

                # Extract directory part of the path
                import os

                dir_path = os.path.dirname(test_path)

                activities = recorder.get_activities_by_path(dir_path, limit=5)

                query_tests["path"] = {
                    "success": True,
                    "path": dir_path,
                    "count": len(activities) if activities else 0,
                    "samples": activities[:2] if activities else [],
                }

            else:
                query_tests["path"] = {
                    "success": False,
                    "error": "No paths found for test",
                }
        except Exception as e:
            query_tests["path"] = {"success": False, "error": str(e)}

        # Overall test results
        successful_tests = sum(1 for t in query_tests.values() if t.get("success", False))
        total_tests = len(query_tests)

        return {
            "success": successful_tests > 0,
            "message": f"Query capability tests completed: {successful_tests}/{total_tests} successful",
            "query_tests": query_tests,
        }
    except Exception as e:
        import traceback

        traceback.print_exc()

        return {
            "success": False,
            "message": f"Error testing query capabilities: {e}",
            "query_tests": query_tests,
        }


def run_full_verification(
    recorder: NtfsHotTierRecorder,
    files: list[str],
    args,
) -> dict[str, Any]:
    """
    Run a full verification of the NtfsHotTierRecorder.

    Args:
        recorder: NtfsHotTierRecorder instance
        files: List of JSONL file paths
        args: Command line arguments

    Returns:
        Dictionary with verification results
    """
    results = {
        "verification_started": datetime.datetime.now(datetime.UTC).isoformat(),
        "steps": {},
    }

    # Step 1: Verify database connection
    connection_result = verify_database_connection(recorder)
    results["steps"]["connection"] = {
        "success": connection_result,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    }

    if not connection_result and not args.dry_run:
        results["success"] = False
        results["message"] = "Database connection verification failed"
        return results

    # Step 2: Load data to database
    if files:
        load_results = load_data_to_database(recorder, files, args)
        results["steps"]["load_data"] = {
            "success": load_results["loaded_activities"] > 0,
            "details": load_results,
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        }
    else:
        results["steps"]["load_data"] = {
            "success": False,
            "message": "No JSONL files found",
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        }

    # Step 3: Verify entity mapping
    entity_results = verify_entity_mapping(recorder, args)
    results["steps"]["entity_mapping"] = {
        "success": entity_results["success"],
        "details": entity_results,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    }

    # Step 4: Test TTL expiration
    ttl_results = test_ttl_expiration(recorder, args)
    results["steps"]["ttl_expiration"] = {
        "success": ttl_results["success"],
        "details": ttl_results,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    }

    # Step 5: Run performance benchmarks
    benchmark_results = run_performance_benchmark(recorder, args)
    results["steps"]["benchmarks"] = {
        "success": benchmark_results["success"],
        "details": benchmark_results,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    }

    # Step 6: Test query capabilities
    query_results = test_query_capabilities(recorder, args)
    results["steps"]["query_tests"] = {
        "success": query_results["success"],
        "details": query_results,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    }

    # Calculate overall success
    successful_steps = sum(1 for step in results["steps"].values() if step.get("success", False))
    total_steps = len(results["steps"])
    results["success"] = successful_steps > 0
    results["success_ratio"] = f"{successful_steps}/{total_steps}"
    results["message"] = f"Verification completed: {successful_steps}/{total_steps} steps successful"
    results["verification_completed"] = datetime.datetime.now(datetime.UTC).isoformat()

    return results


def main() -> int:
    """Main function for verifying NtfsHotTierRecorder implementation."""
    args = parse_arguments()

    # Find JSONL files
    if args.find_files or args.full_verification:
        files = find_jsonl_files(args.path)

        for _i, _file_path in enumerate(files):
            pass

        if not files and args.full_verification:
            return 1
    elif args.file:
        files = [args.file]
    else:
        files = []

    # Create recorder
    recorder = create_recorder(args)

    # Run requested verification steps
    results = {}

    if args.verify_connection:
        connection_result = verify_database_connection(recorder)
        results["connection"] = {
            "success": connection_result,
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        }

    if args.load_data and files:
        load_results = load_data_to_database(recorder, files, args)
        results["load_data"] = load_results

    if args.verify_entities:
        entity_results = verify_entity_mapping(recorder, args)
        results["entity_mapping"] = entity_results

    if args.test_ttl:
        ttl_results = test_ttl_expiration(recorder, args)
        results["ttl_expiration"] = ttl_results

    if args.benchmark:
        benchmark_results = run_performance_benchmark(recorder, args)
        results["benchmarks"] = benchmark_results

    if args.query_test:
        query_results = test_query_capabilities(recorder, args)
        results["query_tests"] = query_results

    if args.full_verification:
        results = run_full_verification(recorder, files, args)

    # Print summary

    if "steps" in results:
        # Full verification summary
        for result in results["steps"].values():
            result.get("success", False)

    else:
        # Individual steps summary
        for result in results.values():
            if isinstance(result, dict) and "success" in result:
                result["success"]

    # Save results to file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"hot_tier_verification_{timestamp}.json"

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


    return 0 if results.get("success", True) else 1


if __name__ == "__main__":
    sys.exit(main())
