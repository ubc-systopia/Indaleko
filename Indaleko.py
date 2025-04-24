"""
The purpose of this package is to define the core data types used in Indaleko.

Indaleko is a Unified Private Index (UPI) service that enables the indexing of
storage content (e.g., files, databases, etc.) in a way that extracts useful
metadata and then uses it for creating a rich index service that can be used in
a variety of ways, including improving search results, enabling development of
non-traditional data visualizations, and mining relationships between objects to
enable new insights.

Indaleko is not a storage engine.  Rather, it is a metadata service that relies
upon storage engines to provide the data to be indexed.  The storage engines can
be local (e.g., a local file system,) remote (e.g., a cloud storage service,) or
even non-traditional (e.g., applications that provide access to data in some
way, such as Discord, Teams, Slack, etc.)

Indaleko uses three distinct classes of metadata to enable its functionality:

* Storage metadata - this is the metadata that is provided by the storage
  services
* Semantic metadata - this is the metadata that is extracted from the objects,
  either by the storage service or by semantic transducers that act on the files
  when it is available on the local device(s).
* Activity context - this is metadata that captures information about how the
  file was used, such as when it was accessed, by what application, as well as
  ambient information, such as the location of the device, the person with whom
  the user was interacting, ambient conditions (e.g., temperature, humidity, the
  music the user is listening to, etc.) and even external events (e.g., current
  news, weather, etc.)

To do this, Indaleko stores information of various types in databases.  One of
the purposes of this package is to encapsulate the data types used in the system
as well as the schemas used to validate the data.

The general architecture of Indaleko attempts to be flexible, while still
capturing essential metadata that is used as part of the indexing functionality.
Thus, to that end, we define both a generic schema and in some cases a flexible
set of properties that can be extracted and stored.  Since this is a prototype
system, we have strived to "keep it simple" yet focus on allowing us to explore
a broad range of storage systems, semantic transducers, and activity data sources.

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

import datetime
import os
import sys

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position

# from IndalekoObjectSchema import IndalekoObjectSchema
# from IndalekoServiceSchema import IndalekoServiceSchema
# from IndalekoRelationshipSchema import IndalekoRelationshipSchema
# from IndalekoMachineConfigSchema import IndalekoMachineConfigSchema
# from IndalekoUserSchema import IndalekoUserSchema
# from IndalekoUserRelationshipSchema import IndalekoUserRelationshipSchema
# from utils.misc.file_name_management import indaleko_file_name_prefix
import utils.data_validation
import utils.misc.data_management
import utils.misc.directory_management
import utils.misc.file_name_management
import utils.misc.timestamp_management
from db.db_collections import IndalekoDBCollections
from db.db_config import IndalekoDBConfig
from utils.i_logging import IndalekoLogging
from utils.misc.directory_management import (
    indaleko_default_config_dir,
    indaleko_default_data_dir,
    indaleko_default_log_dir,
)

# pylint: enable=wrong-import-position


class Indaleko:
    """This class defines constants used by Indaleko."""

    default_data_dir = indaleko_default_data_dir
    default_config_dir = indaleko_default_config_dir
    default_log_dir = indaleko_default_log_dir

    default_db_timeout = IndalekoDBConfig.default_db_timeout

    Indaleko_Object_Collection = IndalekoDBCollections.Indaleko_Object_Collection
    Indaleko_Relationship_Collection = (
        IndalekoDBCollections.Indaleko_Relationship_Collection
    )
    Indaleko_Service_Collection = IndalekoDBCollections.Indaleko_Service_Collection
    Indaleko_MachineConfig_Collection = (
        IndalekoDBCollections.Indaleko_MachineConfig_Collection
    )
    Indaleko_ActivityDataProvider_Collection = (
        IndalekoDBCollections.Indaleko_ActivityDataProvider_Collection
    )
    Indaleko_ActivityContext_Collection = (
        IndalekoDBCollections.Indaleko_ActivityContext_Collection
    )
    Indaleko_User_Collection = IndalekoDBCollections.Indaleko_User_Collection
    Indaleko_User_Relationship_Collection = (
        IndalekoDBCollections.Indaleko_User_Relationship_Collection
    )

    Indaleko_Prefix = utils.misc.file_name_management.indaleko_file_name_prefix

    @staticmethod
    def validate_ip_address(ip: str) -> bool:
        """Given a string, verify that it is in fact a valid IP address."""
        return utils.data_validation.validate_ip_address(ip)

    @staticmethod
    def validate_hostname(hostname: str) -> bool:
        """Given a string, verify that it is in fact a valid hostname."""
        return utils.data_validation.validate_hostname(hostname)

    @staticmethod
    def create_secure_directories(directories: list = None) -> None:
        """Create secure directories for Indaleko."""
        return utils.misc.directory_management.indaleko_create_secure_directories(
            directories,
        )

    # @deprecated(reason='Use utils.validate_data.validate_uuid_string instead')
    @staticmethod
    def validate_uuid_string(uuid_string: str) -> bool:
        """Given a string, verify that it is in fact a valid uuid."""
        return utils.data_validation.validate_uuid_string(uuid_string)

    @staticmethod
    def validate_iso_timestamp(source: str) -> bool:
        """Given a string, ensure it is a valid ISO timestamp."""
        return utils.data_validation.validate_iso_timestamp(source)

    @staticmethod
    def generate_iso_timestamp(ts: datetime = None) -> str:
        """Given a timestamp, convert it to an ISO timestamp."""
        return utils.misc.timestamp_management.generate_iso_timestamp(ts)

    @staticmethod
    def generate_iso_timestamp_for_file(ts: str = None) -> str:
        """Create an ISO timestamp for the current time."""
        return utils.misc.timestamp_management.generate_iso_timestamp_for_file(ts)

    @staticmethod
    def extract_iso_timestamp_from_file_timestamp(file_timestamp: str) -> str:
        """Given a file timestamp, convert it to an ISO timestamp."""
        return (
            utils.misc.timestamp_management.extract_iso_timestamp_from_file_timestamp(
                file_timestamp,
            )
        )

    @staticmethod
    def get_logging_levels() -> list:
        """Return a list of valid logging levels."""
        return IndalekoLogging.get_logging_levels()

    @staticmethod
    def generate_final_name(args: list, **kwargs) -> str:
        """
        This is a helper function for generate_file_name, which throws
        a pylint error as having "too many branches".  An explicit args list
        threw a "too many arguments" error, so this is a compromise - send in a
        list, and then unpack it manually. Why this is better is a mystery of
        the faith.
        """
        return utils.misc.file_name_management.generate_final_name(args, **kwargs)

    @staticmethod
    def generate_file_name(**kwargs) -> str:
        """
        Given a key/value store of labels and values, this generates a file
        name in a common format.
        Special labels:
            * prefix: string to prepend to the file name
            * platform: identifies the platform from which the data originated
            * service: identifies the service that generated the data (indexer,
              ingester, etc.)
            * timestamp: timestamp to use in the file name
            * suffix: string to append to the file name
        """
        return utils.misc.file_name_management.generate_file_name(**kwargs)

    @staticmethod
    def extract_keys_from_file_name(file_name: str) -> dict:
        """
        Given a file name, extract the keys and values from the file name.
        """
        return utils.misc.file_name_management.extract_keys_from_file_name(file_name)

    @staticmethod
    def encode_binary_data(data: bytes) -> str:
        """Encode binary data as a string."""
        return utils.misc.data_management.encode_binary_data(data)

    @staticmethod
    def decode_binary_data(data: str) -> bytes:
        """Decode binary data from a string."""
        return utils.misc.data_management.decode_binary_data(data)

    @staticmethod
    def find_candidate_files(
        input_strings: list[str], directory: str,
    ) -> list[tuple[str, str]]:
        """Given a directory location, find a list of candidate files that match
        the input strings.
        """
        return utils.misc.file_name_management.find_candidate_files(
            input_strings, directory,
        )

    @staticmethod
    def print_candidate_files(candidates: list[tuple[str, str]]) -> None:
        """Print the candidate files in a nice format."""
        return utils.misc.file_name_management.print_candidate_files(candidates)


def main():
    """Test code for Indaleko.py"""
    Indaleko.create_secure_directories()
    print("Test 1: generate a file name")
    name = Indaleko.generate_file_name(platform="test", service="test")
    print(name)
    print("Test 2: extract keys from file name")
    print(Indaleko.extract_keys_from_file_name(name))


if __name__ == "__main__":
    main()
