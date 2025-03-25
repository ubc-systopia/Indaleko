"""
IndakeloRelationshipContains module defines the "contains" relationship,
e.g., a directory contains a file or directory, a volume contains files and
directories, etc.

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

from IndalekoRelationship import IndalekoRelationship
from Indaleko import Indaleko


class IndalekoRelationshipContains(IndalekoRelationship):
    """This class defines the "contains" relationship."""

    DIRECTORY_CONTAINS_RELATIONSHIP_UUID_STR = "cde81295-f171-45be-8607-8100f4611430"
    VOLUME_CONTAINS_RELATIONSHIP_UUID_STR = "db1a48c0-91d9-4f16-bd65-845433e6cba9"
    MACHINE_CONTAINS_RELATIONSHIP_UUID_STR = "f3dde8a2-cff5-41b9-bd00-0f41330895e1"

    def __init__(self: "IndalekoRelationshipContains", **kwargs: dict) -> None:
        """
        Constructor for the IndalekoRelationshipContains class. Takes a
        configuration object as a parameter. The configuration object is a
        dictionary that contains all the configuration parameters for the
        relationship.
        """
        super().__init__(**kwargs)
        self.parent = None
        if "parent" in kwargs:
            self.parent = kwargs["parent"]
        self.child = None
        if "child" in kwargs:
            self.child = kwargs["child"]
        if "relationship" not in kwargs:
            raise ValueError("Relationship UUID must be specified")
        assert Indaleko.validate_uuid_string(
            kwargs["relationship"]
        ), "relationship must be a valid UUID"
        self.relationship = kwargs["relationship"]
