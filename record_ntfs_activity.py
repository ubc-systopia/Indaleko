#!/usr/bin/env python
"""
CLI entry point for recording NTFS activities to the hot tier database.

This script is a simple entry point for the ntfs_recorder_cli.py module,
making it easier to invoke from the command line or scripts. It follows
the architectural principle of separation of concerns by focusing only
on recording functionality.

Usage:
    # Basic usage
    python record_ntfs_activity.py --input activities.jsonl

    # Specify database configuration
    python record_ntfs_activity.py --input activities.jsonl --db-config path/to/config.json

    # Enable statistics and display
    python record_ntfs_activity.py --input activities.jsonl --statistics --show-activities

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

import os
import sys

from pathlib import Path


# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).resolve().parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.append(str(current_path))

# Import the constants for default paths
from constants.values import IndalekoConstants


# Create default DB config path using pathlib.Path
DEFAULT_DB_CONFIG_PATH = Path(IndalekoConstants.default_config_dir) / IndalekoConstants.default_db_config_file_name

# Import the recorder CLI module
from activity.recorders.storage.ntfs.tiered.hot.ntfs_recorder_cli import main


if __name__ == "__main__":
    main()
