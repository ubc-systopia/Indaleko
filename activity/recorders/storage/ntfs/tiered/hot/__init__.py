"""
Hot tier recorder for NTFS storage activities in Indaleko.

The hot tier recorder is responsible for:
1. Receiving raw activity data from the NTFS USN journal collector
2. Processing, enhancing, and storing this data in the database
3. Providing efficient query capabilities for recent activities
4. Supporting eventual transition of data to the Warm tier

This module provides high-fidelity, detailed storage of recent file system
activities with full attribute preservation and entity relationship tracking.
"""

__version__ = "0.1.0"