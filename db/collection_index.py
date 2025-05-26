"""
IndalekoCollectionIndex.

This module is used to manage index creation for
IndalekoCollection objects.

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

from arango.collection import StandardCollection
from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from utils.singleton import IndalekoSingleton


# pylint: enable=wrong-import-position


class IndalekoCollectionIndex(IndalekoSingleton):
    """Manages an index for an IndalekoCollection object."""

    index_args = {  # noqa: RUF012
        "hash": {
            "fields": str,
            "name": str,
            "unique": bool,
            "sparse": bool,
            "deduplicate": bool,
            "in_background": bool,
        },
        "skip_list": {
            "fields": str,
            "name": str,
            "unique": bool,
            "sparse": bool,
            "deduplicate": bool,
            "in_background": bool,
        },
        "geo_index": {
            "fields": str,
            "name": str,
            "geo_json": bool,
            "in_background": bool,
            "legacyPolygons": bool,
        },
        "fulltext": {
            "fields": str,
            "name": str,
            "min_length": int,
            "in_background": bool,
        },
        "persistent": {
            "fields": str,
            "name": str,
            "unique": bool,
            "sparse": bool,
            "in_background": bool,
            "storedValues": list,
            "cacheEnabled": bool,
        },
        "ttl": {"fields": str, "name": str, "expiry_time": int, "in_background": bool},
        "inverted": {
            "fields": str,
            "name": str,
            "inBackground": bool,
            "parallelism": int,
            "primarySort": list,
            "storedValues": list,
            "analyzer": str,
            "features": list,
            "includeAllFields": bool,
            "trackListPositions": bool,
            "searchField": str,
            "primaryKeyCache": bool,
            "cache": bool,
        },
        "zkd": {
            "fields": str,
            "name": str,
            "field_value_types": list,
            "unique": bool,
            "in_background": bool,
        },
        "mdi": {
            "fields": str,
            "name": str,
            "field_value_types": list,
            "unique": bool,
            "in_background": bool,
        },
    }

    def __init__(self, collection: str | StandardCollection, **kwargs: dict) -> None:
        """
        This class is used to create indices for IndalekoCollection objects.

        Args:
        collection: this points to the ArangoDB collection object to use for
                    this index (not a string - just avoiding init issues.)
        kwargs: the parameters to pass to the add_index method of the collection.
            Note: these vary by index type.
        """
        self.collection: StandardCollection = collection
        if kwargs.get("type") is None:
            raise ValueError("type is a required parameter")
        if kwargs.get("fields") is None:
            raise ValueError("fields is a required parameter")
        if "inBackground" not in kwargs:
            kwargs["inBackground"] = True # build async
        self.index = self.collection.add_index(data=kwargs, formatter=False)
        self.debug = kwargs.get("debug", False)
        if self.debug:
            ic(f"Created index for collection {self.collection}: {self.index}")


def main() -> None:
    """Test the IndalekoCollectionIndex class."""


if __name__ == "__main__":
    main()
