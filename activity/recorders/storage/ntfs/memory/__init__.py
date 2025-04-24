"""
NTFS Cognitive Memory System for Indaleko.

This package implements the cognitive memory system for NTFS file system activities,
providing a four-tier architecture inspired by human memory:

1. Sensory Memory: Short-term, high-detail raw activity data (milliseconds to seconds)
2. Short-Term Memory: Processed activity data with entity resolution (seconds to minutes)
3. Long-Term Memory: Consolidated entities with semantic enrichment (minutes to days)
4. Archival Memory: Permanent knowledge store with rich semantic relationships (days to years)

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

# Import tier implementations
try:
    from activity.recorders.storage.ntfs.memory.archival.recorder import (
        NtfsArchivalMemoryRecorder,
    )
    from activity.recorders.storage.ntfs.memory.long_term.recorder import (
        NtfsLongTermMemoryRecorder,
    )
    from activity.recorders.storage.ntfs.memory.sensory.recorder import (
        NtfsSensoryMemoryRecorder,
    )
    from activity.recorders.storage.ntfs.memory.short_term.recorder import (
        NtfsShortTermMemoryRecorder,
    )
except ImportError:
    # Some modules might not be available, which is ok
    pass
