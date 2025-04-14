"""
Configuration services for Indaleko Streamlit GUI

These services handle configuration management.

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

def get_config_files():
    """
    Get a list of available database configuration files
    
    Returns:
        list: Available configuration file names
    """
    config_dir = os.path.join(os.environ.get("INDALEKO_ROOT"), "config")
    if not os.path.exists(config_dir):
        return []

    # Look for files with typical INI or config extensions
    candidates = []
    for filename in os.listdir(config_dir):
        if filename.endswith('.ini') or 'config' in filename.lower():
            candidates.append(filename)
    
    # If we didn't find any, check for any file
    if not candidates:
        for filename in os.listdir(config_dir):
            # Skip any directories or hidden files
            if not os.path.isdir(os.path.join(config_dir, filename)) and not filename.startswith('.'):
                candidates.append(filename)
    
    # Fall back to default name if we're still empty
    if not candidates:
        return ["indaleko-db-config.ini"]
        
    return candidates