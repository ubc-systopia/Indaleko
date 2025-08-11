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
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
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
        if not force_refresh and cls._view_cache and (current_time - cls._last_cache_update) < cls._cache_ttl:
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

    # Test with original approach (skip_views=False)
    time.time()

    collections = IndalekoCollections(skip_views=False)
    collections.get_collection(
        IndalekoDBCollections.Indaleko_MachineConfig_Collection,
    )

    # Perform query
    results = collections.db_config._arangodb.aql.execute(
        "FOR doc IN @@collection LIMIT 10 RETURN doc",
        bind_vars={
            "@collection": IndalekoDBCollections.Indaleko_MachineConfig_Collection,
        },
    )
    list(results)

    time.time()

    # Test with optimized approach (skip_views=True)
    time.time()

    collections = IndalekoCollections(skip_views=True)
    collections.get_collection(
        IndalekoDBCollections.Indaleko_MachineConfig_Collection,
        skip_views=True,
    )

    # Perform query
    results = collections.db_config._arangodb.aql.execute(
        "FOR doc IN @@collection LIMIT 10 RETURN doc",
        bind_vars={
            "@collection": IndalekoDBCollections.Indaleko_MachineConfig_Collection,
        },
    )
    list(results)

    time.time()


def test_optimized_view_manager():
    """Test the optimized view manager with caching."""

    # Get views with cache
    time.time()
    OptimizedViewManager.get_views()
    time.time()

    # Get views again with cache
    time.time()
    OptimizedViewManager.get_views()
    time.time()

    # Check if view exists
    time.time()
    OptimizedViewManager.view_exists("ObjectsTextView")
    time.time()

    # Get a view
    time.time()
    OptimizedViewManager.get_view("ObjectsTextView")
    time.time()



if __name__ == "__main__":
    try:
        # Test optimized view manager
        test_optimized_view_manager()

        # Test machine config performance
        test_machine_config_performance()

    except Exception as e:
        logger.exception(f"Error during testing: {e}")
