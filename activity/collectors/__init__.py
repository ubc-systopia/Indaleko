"""
Init functionality for the activity data providers.

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
import importlib
import platform
import sys

# from icecream import ic

init_path = os.path.dirname(os.path.abspath(__file__))

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)
# pylint: disable=wrong-import-position
from activity.collectors.location.location_base import LocationCollector  # noqa: E402
from activity.collectors.location.ip_location import IPLocation  # noqa: E402
from activity.collectors.location.tile_location import TileLocation  # noqa: E402
from activity.collectors.location.wifi_location import WiFiLocation  # noqa: E402

if platform.system() == "Windows":
    WindowsGPSLocation = importlib.import_module(
        "activity.collectors.location.windows_gps_location"
    ).WindowsGPSLocation
# pylint: enable=wrong-import-position

__version__ = "0.1.0"

# Discover and load all plugins
# discovered_plugins = discover_plugins()
# ic(discovered_plugins)

# Make discovered plugins available when importing the package
# globals().update(discovered_plugins)

__all__ = [
    "LocationCollector",
    "IPLocation",
    "TileLocation",
    "WiFiLocation",
    "WindowsGPSLocation",
]


# You could also provide a function to get all discovered plugins
# def get_all_plugins():
#    return discovered_plugins

# print(discover_providers())
