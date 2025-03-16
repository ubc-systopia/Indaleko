"""
Base description of Indaleko

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

from icecream import ic

if "INDALEKO_ROOT" not in os.environ:
    os.environ["INDALEKO_ROOT"] = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.environ["INDALEKO_ROOT"])


def initialize_project():
    """Initialize the project"""
    ic("Indaleko project initialization invoked.")


# pylint: disable=wrong-import-position
# from db import IndalekoDBConfig, IndalekoCollection, IndalekoCollectionIndex, IndalekoCollections
# from utils import IndalekoDocker, IndalekoSingleton
# pylint: enable=wrong-import-position

__all__ = [
    #    'IndalekoCollection',
    #    'IndalekoCollectionIndex',
    #    'IndalekoCollections',
    #    'IndalekoDBConfig',
    #    'IndalekoDocker',
    #    'IndalekoSingleton',
]

__version__ = "2024.11.15.1"
