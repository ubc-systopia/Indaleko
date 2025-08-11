"""
Long-Term Memory module for NTFS Cognitive Memory System.

This module contains the implementation of the long-term memory component
of the cognitive memory system, which stores significant file system activities
for extended periods with rich semantic understanding.

Components:
- NtfsLongTermMemoryRecorder: Records significant file system activities in long-term memory
"""

from ntfs.memory.long_term.recorder import NtfsLongTermMemoryRecorder


__all__ = ["NtfsLongTermMemoryRecorder"]
