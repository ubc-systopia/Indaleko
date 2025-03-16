"""
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

from enum import Enum
import os
import sys


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
# pylint: enable=wrong-import-position


class StorageSemanticAttributes(str, Enum):
    """
    This class defines the data model for the Indaleko storage semantic attributes.
    """

    STORAGE_ATTRIBUTES_DEVICE = "3fa47f24-b198-434d-b440-119ec5af4f7d"  # st_dev
    STORAGE_ATTRIBUTES_GID = "64ec8b5a-78ba-4787-ba8d-cb033ec24116"  # st_gid
    STORAGE_ATTRIBUTES_MODE = "1bb62d33-0392-4ffe-af1d-5ebfc32afbb9"  # st_mode
    STORAGE_ATTRIBUTES_NLINK = "06677615-2957-4966-aab9-dde29660c334"  # st_nlink
    STORAGE_ATTRIBUTES_REPARSE_TAG = (
        "7ebf1a92-94f9-40b0-8887-349c24f0e354"  # windows specific - move?
    )
    STORAGE_ATTRIBUTES_UID = "1bd30cfc-9320-427d-bdde-60d9e8aa4400"  # st_uid
    STORAGE_ATTRIBUTES_INODE = "882d75c6-a424-4d8b-a938-c264a281204c"  # st_ino
