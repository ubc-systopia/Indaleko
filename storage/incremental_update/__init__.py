"""
Incremental Update Module for Entity Resolution.

This module provides a queue-based system for resolving entities that are
detected in activity streams but don't yet exist in the database. It follows
Indaleko's collector/recorder pattern while providing coordination between them.
"""

__version__ = "0.1.0"
