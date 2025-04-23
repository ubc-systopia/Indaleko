"""
Google Drive collector for Indaleko.

This module provides functionality for collecting file activity data from Google Drive.
It includes a collector that interfaces with the Google Drive Activity API to gather
information about file creation, modification, sharing, and other activities.

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

# Import core functionality
from activity.collectors.storage.cloud.google_drive.data_models import (
    GDriveActivityData,
    GDriveActivityType,
    GDriveFileInfo,
    GDriveFileType,
    GDriveUserInfo,
)
from activity.collectors.storage.cloud.google_drive.google_drive_collector import (
    GoogleDriveActivityCollector,
)

# Import version info
__version__ = "0.1.0"
