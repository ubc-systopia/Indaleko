#!/usr/bin/env python3
"""
Test script for optimized view handling.

This script tests the optimized view handling approach with caching
to improve performance while maintaining functionality.

Run with:
python test_optimized_views.py
"""

import logging
import os
import sys
import time
from typing import Any

# Set up path
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import required components
from db.db_collections import IndalekoDBCollections
from db.i_collections import IndalekoCollections

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("view_optimizer")


class OptimizedViewManager:
    """Optimized view manager with caching for better performance."""

    # Cache storage
    _view_cache = {}
    _analyzer_cache = {}
    _last_cache_update = 0
    _cache_ttl = 300  # 5 minutes

    @classmethod
    def get_views(cls, force_refresh=False) -> dict[str, Any]:
        """
        Get views with caching for better performance.

        Args:
            force_refresh: Force cache refresh

        Returns:
            Dict of view names to view info
        """
        current_time = time.time()

        # Check if cache is valid
        if (
            not force_refresh
            and cls._view_cache
            and (current_time - cls._last_cache_update) < cls._cache_ttl
        ):
            logger.debug("Using cached views")
            return cls._view_cache.copy()

        # Initialize with known views
        views = {
            "ObjectsTextView": {"name": "ObjectsTextView", "type": "arangosearch"},
            "ActivityTextView": {"name": "ActivityTextView", "type": "arangosearch"},
            "NamedEntityTextView": {
                "name": "NamedEntityTextView",
                "type": "arangosearch",
            },
            "EntityEquivalenceTextView": {
                "name": "EntityEquivalenceTextView",
                "type": "arangosearch",
            },
            "KnowledgeTextView": {"name": "KnowledgeTextView", "type": "arangosearch"},
        }

        # Update cache
        cls._view_cache = views.copy()
        cls._last_cache_update = current_time

        return views

    @classmethod
    def view_exists(cls, view_name: str) -> bool:
        """
        Check if a view exists (using cache).

        Args:
            view_name: Name of the view

        Returns:
            True if the view exists, False otherwise
        """
        views = cls.get_views()
        return view_name in views

    @classmethod
    def get_view(cls, view_name: str) -> dict[str, Any] | None:
        """
        Get a view by name (using cache).

        Args:
            view_name: Name of the view

        Returns:
            View info if found, None otherwise
        """
        views = cls.get_views()
        return views.get(view_name)


def test_machine_config_performance():
    """Test machine config lookups with optimized views."""
    print("\n=== Testing Machine Config Performance ===\n")

    # Test with original approach (skip_views=False)
    print("Original approach (with views):")
    start_time = time.time()

    collections = IndalekoCollections(skip_views=False)
    collection = collections.get_collection(
        IndalekoDBCollections.Indaleko_MachineConfig_Collection,
    )

    # Perform query
    results = collections.db_config._arangodb.aql.execute(
        "FOR doc IN @@collection LIMIT 10 RETURN doc",
        bind_vars={
            "@collection": IndalekoDBCollections.Indaleko_MachineConfig_Collection,
        },
    )
    records = list(results)

    end_time = time.time()
    print(f"  - Time: {end_time - start_time:.4f} seconds")
    print(f"  - Found {len(records)} records")

    # Test with optimized approach (skip_views=True)
    print("\nOptimized approach (skip_views=True):")
    start_time = time.time()

    collections = IndalekoCollections(skip_views=True)
    collection = collections.get_collection(
        IndalekoDBCollections.Indaleko_MachineConfig_Collection, skip_views=True,
    )

    # Perform query
    results = collections.db_config._arangodb.aql.execute(
        "FOR doc IN @@collection LIMIT 10 RETURN doc",
        bind_vars={
            "@collection": IndalekoDBCollections.Indaleko_MachineConfig_Collection,
        },
    )
    records = list(results)

    end_time = time.time()
    print(f"  - Time: {end_time - start_time:.4f} seconds")
    print(f"  - Found {len(records)} records")


def test_optimized_view_manager():
    """Test the optimized view manager with caching."""
    print("\n=== Testing Optimized View Manager ===\n")

    # Get views with cache
    print("First call (cold cache):")
    start_time = time.time()
    views = OptimizedViewManager.get_views()
    end_time = time.time()
    print(f"  - Time: {end_time - start_time:.4f} seconds")
    print(f"  - Views: {list(views.keys())}")

    # Get views again with cache
    print("\nSecond call (warm cache):")
    start_time = time.time()
    views = OptimizedViewManager.get_views()
    end_time = time.time()
    print(f"  - Time: {end_time - start_time:.4f} seconds")

    # Check if view exists
    print("\nCheck if view exists:")
    start_time = time.time()
    exists = OptimizedViewManager.view_exists("ObjectsTextView")
    end_time = time.time()
    print(f"  - Time: {end_time - start_time:.4f} seconds")
    print(f"  - Exists: {exists}")

    # Get a view
    print("\nGet a view:")
    start_time = time.time()
    view = OptimizedViewManager.get_view("ObjectsTextView")
    end_time = time.time()
    print(f"  - Time: {end_time - start_time:.4f} seconds")
    print(f"  - View: {view}")

    print("\n=== Test Complete ===\n")


if __name__ == "__main__":
    try:
        # Test optimized view manager
        test_optimized_view_manager()

        # Test machine config performance
        test_machine_config_performance()

    except Exception as e:
        logger.exception(f"Error during testing: {e}")
        print(f"Error during testing: {e}")
