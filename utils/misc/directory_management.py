"""
This module handles directories for Indaleko.

Indaleko Windows Local Indexer
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

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from constants.values import IndalekoConstants

# pylint: enable=wrong-import-position

indaleko_default_data_dir = IndalekoConstants.default_data_dir
indaleko_default_config_dir = IndalekoConstants.default_config_dir
indaleko_default_log_dir = IndalekoConstants.default_log_dir


def indaleko_create_secure_directories(directories: list = None) -> None:
    """Create secure directories for Indaleko."""
    if directories is None:
        directories = [
            indaleko_default_data_dir,
            indaleko_default_config_dir,
            indaleko_default_log_dir,
        ]
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
        os.chmod(directory, 0o700)
