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

import os
import sys
from enum import Enum

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
    STORAGE_ATTRIBUTES_REPARSE_TAG = "7ebf1a92-94f9-40b0-8887-349c24f0e354"  # windows specific - move?
    STORAGE_ATTRIBUTES_UID = "1bd30cfc-9320-427d-bdde-60d9e8aa4400"  # st_uid
    STORAGE_ATTRIBUTES_INODE = "882d75c6-a424-4d8b-a938-c264a281204c"  # st_ino

    STORAGE_ATTRIBUTES_LOWERCASE_FILE_NAME = "c6724410-a717-44a7-b9d3-6b276e250c1d"
    STORAGE_ATTRIBUTES_SUFFIX = "f980b0c8-3d24-4a77-b985-5e945803991f"

    STORAGE_ATTRIBUTES_MIMETYPE_FROM_SUFFIX = "8aeb9b5a-3d08-4d1f-9921-0795343d9eb3"
    STORAGE_ATTRIBUTES_MIMETYPE_FROM_STORAGE_PROVIDER = "c391fbee-6c40-42d6-a7db-dcf33d45e1a9"
    STORAGE_ATTRIBUTES_MIMETYPE_FROM_CONTENT = "bce15d05-d4fd-4d37-933f-ff6b4e5dde9d"

    STORAGE_ATTRIBUTES_CHECKSUM_MD5 = "c2c8c8e2-56ec-48c0-aba8-3a739bd30f82"
    STORAGE_ATTRIBUTES_CHECKSUM_SHA1 = "5820f1b4-dc98-4297-b7a3-7d1845fcca3d"
    STORAGE_ATTRIBUTES_CHECKSUM_SHA256 = "0743c70b-1f82-420c-a8b7-774ca60b18fb"
    STORAGE_ATTRIBUTES_CHECKSUM_SHA512 = "abb04b9f-da69-4694-b3fc-e5b03ad2e87b"
    STORAGE_ATTRIBUTES_CHECKSUM_DROPBOX = "653002f3-6b12-4d7b-a4c6-6efa2ab1e5f3"
    STORAGE_ATTRIBUTES_CHECKSUM_BLAKE2 = "2a2f4ac7-2a7d-476f-8fa7-53fc43d6b1c6"
    STORAGE_ATTRIBUTES_CHECKSUM_S3_ETAG = "45aae76e-3d50-4185-9795-122f730ad8cc"

    STORAGE_ATTRIBUTES_GDRIVE_SHARED = "697cde3a-e2d2-466f-b317-828c79b722a3"
    STORAGE_ATTRIBUTES_GDRIVE_ID = "7d9293cf-b7a3-4458-b977-2cf110d2da3c"
