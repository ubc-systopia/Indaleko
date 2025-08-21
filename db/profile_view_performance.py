#!/usr/bin/env python3
"""
ArangoDB View Performance Profiler.

This script profiles the performance of various approaches to working with
ArangoDB views to help diagnose and optimize the slow operations.

Run with:
python profile_view_performance.py
"""

import logging
import os
import statistics
import sys
import time

from collections.abc import Callable


# Set up path
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import required components
from db.collection_view import IndalekoCollectionView
from db.db_collections import IndalekoDBCollections
from db.db_config import IndalekoDBConfig
from db.i_collections import IndalekoCollections


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
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


def profile_view_operations() -> None:
    """Profile various view operations to identify performance bottlenecks."""
    # Initialize database connection
    time.perf_counter()
    db_config = IndalekoDBConfig()
    db_config.start()
    time.perf_counter()

    # Test 1: Initialize view manager
    for _i in range(3):
        _, duration = time_execution(IndalekoCollectionView, db_config=db_config)

    # Test 2: Get existing views using AQL
    view_manager = IndalekoCollectionView(db_config=db_config)

    def _get_views_with_aql():
        try:
            cursor = db_config._arangodb.aql.execute("FOR v IN _views RETURN v")
            return list(cursor)
        except Exception as e:
            return {"error": str(e)}

    for _i in range(3):
        _, duration = time_execution(_get_views_with_aql)

    # Test 3: Get views using API directly

    def _get_views_with_api():
        try:
            return list(db_config._arangodb.views())
        except Exception as e:
            return {"error": str(e)}

    for _i in range(3):
        _, duration = time_execution(_get_views_with_api)

    # Test 4: Initialize IndalekoCollections with and without skip_views

    def _init_collections_with_views():
        return IndalekoCollections(skip_views=False)

    def _init_collections_without_views():
        return IndalekoCollections(skip_views=True)

    for _i in range(3):
        _, duration = time_execution(_init_collections_with_views)

    for _i in range(3):
        _, duration = time_execution(_init_collections_without_views)

    # Test 5: Get collection with and without skip_views
    collection_name = IndalekoDBCollections.Indaleko_MachineConfig_Collection

    def _get_collection_with_views():
        return IndalekoCollections.get_collection(collection_name, skip_views=False)

    def _get_collection_without_views():
        return IndalekoCollections.get_collection(collection_name, skip_views=True)

    for _i in range(3):
        _, duration = time_execution(_get_collection_with_views)

    for _i in range(3):
        _, duration = time_execution(_get_collection_without_views)

    # Test 6: Profile individual view operations
    view_manager = IndalekoCollectionView(db_config=db_config)

    operations = [
        ("get_analyzers", lambda: view_manager.get_analyzers()),
        ("get_views", lambda: view_manager.get_views()),
        ("view_exists", lambda: view_manager.view_exists("ObjectsTextView")),
        ("get_view", lambda: view_manager.get_view("ObjectsTextView")),
    ]

    for _name, operation in operations:
        times = []
        for _i in range(3):
            _, duration = time_execution(operation)
            times.append(duration)
        statistics.mean(times)



def analyze_results() -> None:
    """Analyze profiling results and suggest optimizations."""


if __name__ == "__main__":
    try:
        profile_view_operations()
        analyze_results()
    except Exception as e:
        logger.exception(f"Error during profiling: {e}")
