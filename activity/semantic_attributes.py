"""
This module defines known semantic attributes for the activity data providers in
the Indaleko Project. The model allows an activity data provider to generate
new/unknown semantic attributes as needed, but there is no expectations that
other activity data providers will use those same semantic attributes.

Ideally, an activity data provider will use a known semantic attribute if one
exists.  This simplifies reasoning across activity data providers.

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
import uuid

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.known_semantic_attributes import KnownSemanticAttributes
from utils.singleton import IndalekoSingleton


# pylint: enable=wrong-import-position


class IndalekoActivityDataProviderKnownSemanticAttributes(IndalekoSingleton):
    """
    This class defines known semantic attributes for the activity data
    providers.
    """

    def __init__(self) -> None:
        """Initialize the known semantic attributes for the activity data
        providers.
        """
        if self._initialized:
            return
        self.uuid_to_label = {}
        ksa = KnownSemanticAttributes()
        for label, value in ksa.__dict__.items():
            if label.startswith(KnownSemanticAttributes.full_prefix):
                setattr(self, label + "_UUID", uuid.UUID(value))
                self.uuid_to_label[value] = label
        self._initialized = True

    @staticmethod
    def get_known_semantic_attributes():
        """Get the known semantic attributes for the activity data providers."""
        return {
            label: value
            for label, value in KnownSemanticAttributes.__dict__.items()
            if label.startswith("KnownSemanticAttributes.full_prefix")
        }

    @staticmethod
    def get_provider_label(identifier: uuid.UUID):
        """Get the label for the provider."""
        return IndalekoActivityDataProviderKnownSemanticAttributes().uuid_to_label.get(
            identifier,
            None,
        )


def main() -> None:
    """Test code for the known semantic attributes."""
    known_semantic_attributes = IndalekoActivityDataProviderKnownSemanticAttributes()
    ic(known_semantic_attributes.__dict__)
    ic(KnownSemanticAttributes.__dict__)


if __name__ == "__main__":
    main()
