"""
This module defines known characteristics for MIME type data.

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

# Primary MIME type identifier
SEMANTIC_MIME_TYPE = "d9c34d8a-bc9e-4e21-b67a-6c5b3958cbf7"

# Confidence level for the MIME type detection
SEMANTIC_MIME_CONFIDENCE = "a72f9d32-8eb3-4b0c-aef1-0fc5dfb9173e"

# MIME type based on file extension (for comparison)
SEMANTIC_MIME_TYPE_FROM_EXTENSION = "16e4cd15-7d2c-4d30-9c72-69482301b59a"

# Character encoding for text files
SEMANTIC_MIME_ENCODING = "f4ed5a2b-9f17-4c8e-a6db-1089c9e3d7c1"

# Specific MIME category indicators
SEMANTIC_MIME_IS_TEXT = "c3ebd94f-1a95-4e2a-a5a5-e2ef984e9c2b"
SEMANTIC_MIME_IS_IMAGE = "76a8f7c2-5e0d-4b59-9f0a-fcc1d2e1b9de"
SEMANTIC_MIME_IS_AUDIO = "e5c2d81f-6b47-4ae3-8b8a-d7f89e3c6a9e"
SEMANTIC_MIME_IS_VIDEO = "b0a6f7c4-9d5e-4a3b-9c8d-2e1f0b7a9c3d"
SEMANTIC_MIME_IS_APPLICATION = "1d7e9a2f-5c3b-4e8d-9f7a-6b3c1d0e5a8f"

# Format-specific markers
SEMANTIC_MIME_IS_CONTAINER = (
    "9c3d5a7e-1f4b-8a2e-6d9c-5b7a3f1e8d2c"  # For formats that contain other formats
)
SEMANTIC_MIME_IS_COMPRESSED = (
    "3e8d1c5a-7f9b-2e6d-4a1c-9f5e3d7b8a2c"  # For compressed formats
)
SEMANTIC_MIME_IS_ENCRYPTED = (
    "5a9c3e7d-1b8f-4e2d-7a9c-3e5d1b8f4a2e"  # For encrypted formats
)
