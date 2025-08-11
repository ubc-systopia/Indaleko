"""
This module defines the data model for the WiFi based location
activity data provider.

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

import importlib
import os
import sys

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


class KnownSemanticAttributes:
    """
    This class dynamically constructs definitions of the known semantic
    attributes from each of the provider types.  In this way, we can distribute
    the definition process, yet end up with a unified list.
    """

    _initialized = False
    _attributes_by_provider_type = {}
    _attributes_by_uuid = {}
    _short_prefix = "ADP_"
    full_prefix = "ACTIVITY_DATA"

    _modules_to_load = {
        "collaboration": "activity.collectors.collaboration.semantic_attributes",
        "location": "activity.collectors.location.semantic_attributes",
        "network": "activity.collectors.network.semantic_attributes",
        "storage": "activity.collectors.storage.semantic_attributes",
        "ambient": "activity.collectors.ambient.semantic_attributes",
    }

    @classmethod
    def _initialize(cls) -> None:
        """Dynamically construct the list of known activity data provider
        semantic attributes.
        """
        if cls._initialized:
            return
        cls._initialized = True
        for label, name in cls._modules_to_load.items():
            module = KnownSemanticAttributes.safe_import(name, quiet=True)
            if not module:
                continue
            for label, value in module.__dict__.items():
                if label.startswith(KnownSemanticAttributes._short_prefix):
                    full_label = KnownSemanticAttributes.full_prefix + label[3:]
                    assert not hasattr(
                        cls,
                        full_label,
                    ), f"Duplicate definition of {full_label}"
                    setattr(cls, full_label, value)
                    provider_type = label.rsplit("_", maxsplit=2)[-2]
                    if provider_type not in cls._attributes_by_provider_type:
                        cls._attributes_by_provider_type[provider_type] = {}
                    cls._attributes_by_provider_type[provider_type][full_label] = value
                    cls._attributes_by_uuid[value] = full_label

    @staticmethod
    def safe_import(name: str, quiet: bool = False):
        """Given a module name, load it and then extract the important data from it."""
        module = None
        try:
            module = importlib.import_module(name)
        except ImportError as e:
            if not quiet:
                ic(f"Import module {name} failed {e}")
        return module

    def __init__(self) -> None:
        if not self._initialized:
            self._initialize()
        ic(dir(self))

    @staticmethod
    def get_attribute_by_uuid(uuid_value):
        """Get the attribute by the UUID."""
        return KnownSemanticAttributes._attributes_by_uuid.get(uuid_value)

    @staticmethod
    def get_all_attributes() -> dict[str, dict[str, str]]:
        """Get all of the known attributes."""
        return KnownSemanticAttributes._attributes_by_provider_type


KnownSemanticAttributes._initialize()


def main() -> None:
    """Main function for the module."""
    ic("Starting")
    ic(dir(KnownSemanticAttributes))
    ic(KnownSemanticAttributes._attributes_by_uuid)


if __name__ == "__main__":
    main()
