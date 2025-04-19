#!/usr/bin/env python3
"""
ArangoDB View Performance Profiler

This script profiles the performance of various approaches to working with
ArangoDB views to help diagnose and optimize the slow operations.

Run with:
python profile_view_performance.py
"""

import os
import sys
import time
import logging
import statistics
from typing import Dict, List, Any, Callable

# Set up path
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import required components
from db.db_config import IndalekoDBConfig
from db.collection_view import IndalekoCollectionView
from db.i_collections import IndalekoCollections
from db.db_collections import IndalekoDBCollections

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("view_profiler")


def time_execution(func: Callable, *args, **kwargs) -> tuple:
    """
    Measure execution time of a function.
    
    Args:
        func: Function to time
        *args, **kwargs: Arguments to pass to the function
        
    Returns:
        Tuple of (result, execution_time_seconds)
    """
    start_time = time.perf_counter()
    result = func(*args, **kwargs)
    end_time = time.perf_counter()
    execution_time = end_time - start_time
    return result, execution_time


def profile_view_operations():
    """Profile various view operations to identify performance bottlenecks."""
    print("\n=== ArangoDB View Performance Profiler ===\n")
    
    # Initialize database connection
    print("Initializing database connection...")
    start_time = time.perf_counter()
    db_config = IndalekoDBConfig()
    db_config.start()
    end_time = time.perf_counter()
    print(f"Database connection initialized in {end_time - start_time:.4f} seconds")
    
    # Test 1: Initialize view manager
    print("\nTest 1: Initialize view manager")
    for i in range(3):
        _, duration = time_execution(IndalekoCollectionView, db_config=db_config)
        print(f"  Run {i+1}: {duration:.4f} seconds")
        
    # Test 2: Get existing views using AQL
    print("\nTest 2: Get views using AQL")
    view_manager = IndalekoCollectionView(db_config=db_config)
    
    def _get_views_with_aql():
        try:
            cursor = db_config.db.aql.execute("FOR v IN _views RETURN v")
            return list(cursor)
        except Exception as e:
            return {"error": str(e)}
    
    for i in range(3):
        _, duration = time_execution(_get_views_with_aql)
        print(f"  Run {i+1}: {duration:.4f} seconds")
        
    # Test 3: Get views using API directly
    print("\nTest 3: Get views using API directly")
    
    def _get_views_with_api():
        try:
            return list(db_config.db.views())
        except Exception as e:
            return {"error": str(e)}
    
    for i in range(3):
        _, duration = time_execution(_get_views_with_api)
        print(f"  Run {i+1}: {duration:.4f} seconds")
    
    # Test 4: Initialize IndalekoCollections with and without skip_views
    print("\nTest 4: Initialize IndalekoCollections with and without skip_views")
    
    def _init_collections_with_views():
        return IndalekoCollections(skip_views=False)
    
    def _init_collections_without_views():
        return IndalekoCollections(skip_views=True)
    
    print("  With views:")
    for i in range(3):
        _, duration = time_execution(_init_collections_with_views)
        print(f"    Run {i+1}: {duration:.4f} seconds")
        
    print("  Without views:")
    for i in range(3):
        _, duration = time_execution(_init_collections_without_views)
        print(f"    Run {i+1}: {duration:.4f} seconds")
    
    # Test 5: Get collection with and without skip_views
    print("\nTest 5: Get collection with and without skip_views")
    collection_name = IndalekoDBCollections.Indaleko_MachineConfig_Collection
    
    def _get_collection_with_views():
        return IndalekoCollections.get_collection(collection_name, skip_views=False)
    
    def _get_collection_without_views():
        return IndalekoCollections.get_collection(collection_name, skip_views=True)
    
    print("  With views:")
    for i in range(3):
        _, duration = time_execution(_get_collection_with_views)
        print(f"    Run {i+1}: {duration:.4f} seconds")
        
    print("  Without views:")
    for i in range(3):
        _, duration = time_execution(_get_collection_without_views)
        print(f"    Run {i+1}: {duration:.4f} seconds")
    
    # Test 6: Profile individual view operations
    print("\nTest 6: Profile individual view operations")
    view_manager = IndalekoCollectionView(db_config=db_config)
    
    operations = [
        ("get_analyzers", lambda: view_manager.get_analyzers()),
        ("get_views", lambda: view_manager.get_views()),
        ("view_exists", lambda: view_manager.view_exists("ObjectsTextView")),
        ("get_view", lambda: view_manager.get_view("ObjectsTextView")),
    ]
    
    for name, operation in operations:
        print(f"  Operation: {name}")
        times = []
        for i in range(3):
            _, duration = time_execution(operation)
            times.append(duration)
            print(f"    Run {i+1}: {duration:.4f} seconds")
        avg = statistics.mean(times)
        print(f"    Average: {avg:.4f} seconds")
    
    print("\n=== Profiling Complete ===\n")


def analyze_results():
    """Analyze profiling results and suggest optimizations."""
    print("\n=== Optimization Suggestions ===\n")
    
    print("1. Add caching for view information")
    print("   - Cache view and analyzer information with TTL")
    print("   - Use environment variables to control caching behavior")
    
    print("2. Skip view operations when not needed")
    print("   - Add skip_views parameter to relevant functions")
    print("   - Create specialized variants of functions for performance-sensitive operations")
    
    print("3. Optimize ArangoDB connection")
    print("   - Review connection pooling settings")
    print("   - Consider server-side view optimizations")
    
    print("4. Add instrumentation")
    print("   - Implement detailed logging for view operations")
    print("   - Consider adding performance monitoring hooks")
    
    print("5. Architectural improvements")
    print("   - Consider lazy loading of view functionality")
    print("   - Decouple view management from core database operations")


if __name__ == "__main__":
    try:
        profile_view_operations()
        analyze_results()
    except Exception as e:
        logger.exception(f"Error during profiling: {e}")
        print(f"Error during profiling: {e}")