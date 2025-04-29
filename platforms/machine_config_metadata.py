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
from textwrap import dedent

# from typing import Any

# from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.collection_metadata_data_model import (
    IndalekoCollectionMetadataDataModel,
)
from db import IndalekoDBCollections
from platforms.linux.machine_config import IndalekoLinuxMachineConfig
from platforms.mac.machine_config import IndalekoMacOSMachineConfig
from platforms.windows.machine_config import IndalekoWindowsMachineConfig
from utils import IndalekoSingleton

# pylint: enable=wrong-import-position


class MachineConfigCollectionMetadata(IndalekoSingleton):
    """This class provides a basic (default) implementation of the machine config collection metadata."""

    default_metadata = IndalekoCollectionMetadataDataModel(
        key=IndalekoDBCollections.Indaleko_MachineConfig_Collection,
        Description=dedent(
            "Indaleko is a cross-platform system that implements a unified personal indexing system. "
            "It uses an ArangoDB database, with collections for relevant metadata."
            f"The {IndalekoDBCollections.Indaleko_MachineConfig_Collection} collection is used to store "
            "metadata about the distinctive machines in the system. "
            "Currently, the system support Windows, Mac, and, Linux platforms. "
            "The metadata in this collection has been normalized, to the extent possible, to "
            "provide a consistent view of the metadata for these machines, regardless of the "
            "underlying platform. Note this is a difficult task, because the platforms themselves "
            "are quite different from one another in how they represent resources. "
            "For example, Windows explicitly surfaces the concept of volumes, while Linux and Mac "
            "obfuscate this concept in the hierarchy of the file system. "
            'Thus, this prototype does contain "volume" information for Windows platforms but not for '
            "Linux or Mac platforms. ",
        ),
        QueryGuidelines=[
            dedent(
                "The Record field is included in most Indaleko schema as a common format for "
                "storing captured metadata. "
                "This includes the component that captured the metadata, when the metadata was "
                "captured, and an encoding of "
                "all the captured metadata."
                "This field could be used to filter for platform specific data, if useful. "
                f"The UUID {IndalekoLinuxMachineConfig.linux_machine_config_uuid_str} is used to identify the "
                "Linux machine configuration agent as the source. "
                f"The UUID {IndalekoMacOSMachineConfig.macos_machine_config_uuid_str} is used to identify the "
                "Mac machine configuration agent as the source. "
                f"The UUID {IndalekoWindowsMachineConfig.windows_machine_config_uuid_str} is used to identify the "
                "Windows machine configuration agent as the source. ",
            ),
            dedent(
                "The Captured field is a timestamp of when the data was captured. "
                "It could be used to filter for machine configuration data captured within a specific time frame. "
                "It could also be used to sort multiple instances of the machine configuration data "
                "for time series analysis. This timestamp is in ISO8601 format, with a time zone specifier. ",
            ),
            dedent(
                "The Hardware field contains information about the hardware of the machine. "
                "The Software field contains information about the software of the machine. ",
            ),
            dedent(
                "The MachineUUID field that used to "
                "uniquely identify the machine. Two documents with the same MachineUUID should represent "
                "machine configuration state at different points in time. ",
            ),
            dedent(
                "This collection is expected to be small, so it is acceptable to scan the entire collection. "
                "None of the document fields are indexed at the present time. ",
            ),
            dedent(
                'If the user were to ask "Find all machine configurations captured in the last 7 days." You could '
                "use the Captured field to filter the data. For example: "
                "FOR doc IN MachineConfig FILTER DATE_DIFF(doc.Captured.Value, DATE_NOW(), 'days') <= 7 RETURN doc\n"
                "Similarly, for a query like 'List all machines running Windows 11.' you could use the Software field: "
                "FOR doc IN MachineConfig FILTER doc.Software.OS == "
                "'Windows' AND doc.Software.Version STARTS WITH '11' RETURN doc",
            ),
        ],
        Schema=IndalekoDBCollections.Collections[IndalekoDBCollections.Indaleko_MachineConfig_Collection]["schema"],
    )


def main():
    """Main entry point for the module."""
    metadata = MachineConfigCollectionMetadata()
    print(metadata.default_metadata.model_dump_json(indent=4))


if __name__ == "__main__":
    main()
