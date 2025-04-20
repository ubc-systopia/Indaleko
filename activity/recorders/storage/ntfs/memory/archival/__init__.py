#!/usr/bin/env python
"""
Archival Memory module for NTFS Cognitive Memory System.

This module implements the "Archival Memory" component of the cognitive memory system,
providing long-term, permanent storage of the most significant file system activities.

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

# Make recorder available at the module level
try:
    from .recorder import NtfsArchivalMemoryRecorder
except ImportError:
    # Recorder implementation not available yet
    pass