"""
ArangoDB Command Wrapper Utility for Indaleko.

This module provides wrappers for various ArangoDB command-line tools to simplify
their use with proper authentication and connection parameters.

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

import logging
import os
import subprocess
import sys
from typing import List, Optional, Union

# Handle imports for when the module is imported from outside the project
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db.db_config import IndalekoDBConfig
# pylint: enable=wrong-import-position


class BaseArangoCommandGenerator:
    """
    Base class for ArangoDB command generators.

    This class provides common functionality for building command strings with
    proper authentication, connection, and configuration parameters.
    """

    def __init__(self, db_config: Optional[IndalekoDBConfig] = None):
        """
        Initialize the command generator with database configuration.

        Args:
            db_config: Optional database configuration. If None, a new one will be created.
        """
        self.db_config = db_config or IndalekoDBConfig()
        self._command_name = ""  # Set by subclasses

    def _get_endpoint_string(self) -> str:
        """
        Format the endpoint string with the proper protocol.

        Returns:
            A formatted endpoint string for ArangoDB commands.
        """
        protocol = "ssl" if self.db_config.get_ssl_state() else "tcp"
        return f"{protocol}://{self.db_config.get_hostname()}:{self.db_config.get_port()}"

    def _get_auth_parameters(self) -> List[str]:
        """
        Get properly formatted authentication parameters for ArangoDB commands.

        Returns:
            A list of authentication parameter strings.
        """
        return [
            f"--server.database {self.db_config.get_database_name()}",
            f"--server.username {self.db_config.get_user_name()}",
            f"--server.password {self.db_config.get_user_password()}"
        ]

    def build_command(self) -> str:
        """
        Build the complete command string. Must be implemented by subclasses.

        Returns:
            The full command string.
        """
        raise NotImplementedError("Subclasses must implement this method")

    def execute(self, command_string: Optional[str] = None, timeout: Optional[int] = None) -> subprocess.CompletedProcess:
        """
        Execute the generated command.

        Args:
            command_string: Optional command string. If None, build_command() will be called.
            timeout: Timeout in seconds. For large databases, use a very high value.

        Returns:
            A subprocess.CompletedProcess object with the command result.
        """
        cmd = command_string or self.build_command()
        logging.info(f"Executing ArangoDB command: {self._command_name}")
        logging.debug(f"Command: {cmd}")

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            if result.returncode != 0:
                logging.error(f"Command failed with exit code {result.returncode}")
                logging.error(f"Error output: {result.stderr}")
            else:
                logging.info(f"Command completed successfully")
            return result
        except subprocess.TimeoutExpired:
            logging.error(f"Command timed out after {timeout} seconds")
            raise


class ArangoImportGenerator(BaseArangoCommandGenerator):
    """
    Generator for arangoimport commands.

    Refactored from the existing build_load_string method in IndalekoDBUploader.
    """

    def __init__(self, db_config: Optional[IndalekoDBConfig] = None):
        """Initialize the arangoimport command generator."""
        super().__init__(db_config)
        self._command_name = "arangoimport"
        self.file_path = None
        self.collection = None
        self.type = "jsonl"
        self.overwrite = False

    def with_file(self, file_path: str) -> 'ArangoImportGenerator':
        """
        Set the input file path.

        Args:
            file_path: Path to the input file.

        Returns:
            Self for method chaining.
        """
        self.file_path = file_path
        return self

    def with_collection(self, collection: str) -> 'ArangoImportGenerator':
        """
        Set the target collection.

        Args:
            collection: Name of the collection to import into.

        Returns:
            Self for method chaining.
        """
        self.collection = collection
        return self

    def with_type(self, file_type: str) -> 'ArangoImportGenerator':
        """
        Set the file type.

        Args:
            file_type: Type of the input file (jsonl, json, csv).

        Returns:
            Self for method chaining.
        """
        self.type = file_type
        return self

    def with_overwrite(self, overwrite: bool = True) -> 'ArangoImportGenerator':
        """
        Set the overwrite flag.

        Args:
            overwrite: Whether to overwrite existing data.

        Returns:
            Self for method chaining.
        """
        self.overwrite = overwrite
        return self

    def build_command(self) -> str:
        """
        Build the arangoimport command string.

        Raises:
            ValueError: If required parameters are missing.

        Returns:
            The complete arangoimport command string.
        """
        if not self.file_path:
            raise ValueError("Input file path is required")
        if not self.collection:
            raise ValueError("Collection name is required")

        # Start with the basic command
        cmd_parts = [self._command_name]

        # Add collection
        cmd_parts.append(f"--collection {self.collection}")

        # Add file type if it's not jsonl (the default)
        if self.type != "jsonl":
            cmd_parts.append(f"--type {self.type}")

        # Add auth parameters
        cmd_parts.extend(self._get_auth_parameters())

        # Add endpoint
        cmd_parts.append(f"--server.endpoint {self._get_endpoint_string()}")

        # Add overwrite flag if needed
        if self.overwrite:
            cmd_parts.append("--overwrite true")

        # Add input file
        cmd_parts.append(self.file_path)

        return " ".join(cmd_parts)


class ArangoRestoreGenerator(BaseArangoCommandGenerator):
    """Generator for arangorestore commands."""

    def __init__(self, db_config: Optional[IndalekoDBConfig] = None):
        """Initialize the arangorestore command generator."""
        super().__init__(db_config)
        self._command_name = "arangorestore"
        self.input_directory = None
        self.collections = None
        self.create = True
        self.overwrite = False
        # Default timeout very high for large databases (5 hours in seconds)
        self.timeout_hours = 5

    def with_input_directory(self, directory_path: str) -> 'ArangoRestoreGenerator':
        """
        Set the input directory containing the backup files.

        Args:
            directory_path: Path to the directory containing backup files.

        Returns:
            Self for method chaining.
        """
        self.input_directory = directory_path
        return self

    def with_collections(self, collections: Union[str, List[str], None] = None) -> 'ArangoRestoreGenerator':
        """
        Set the collections to restore. None means all collections.

        Args:
            collections: Collection name(s) to restore, or None for all.

        Returns:
            Self for method chaining.
        """
        self.collections = collections
        return self

    def with_create(self, create: bool = True) -> 'ArangoRestoreGenerator':
        """
        Set whether to create missing collections.

        Args:
            create: Whether to create collections if they don't exist.

        Returns:
            Self for method chaining.
        """
        self.create = create
        return self

    def with_overwrite(self, overwrite: bool = True) -> 'ArangoRestoreGenerator':
        """
        Set whether to overwrite existing data.

        Args:
            overwrite: Whether to overwrite existing data.

        Returns:
            Self for method chaining.
        """
        self.overwrite = overwrite
        return self

    def with_timeout_hours(self, hours: float) -> 'ArangoRestoreGenerator':
        """
        Set the timeout in hours for the restore operation.

        Args:
            hours: Number of hours before timing out.

        Returns:
            Self for method chaining.
        """
        self.timeout_hours = hours
        return self

    def build_command(self) -> str:
        """
        Build the arangorestore command string.

        Raises:
            ValueError: If required parameters are missing.

        Returns:
            The complete arangorestore command string.
        """
        if not self.input_directory:
            raise ValueError("Input directory is required")

        # Start with the basic command
        cmd_parts = [self._command_name]

        # Add input directory
        cmd_parts.append(f"--input-directory {self.input_directory}")

        # Add auth parameters
        cmd_parts.extend(self._get_auth_parameters())

        # Add endpoint
        cmd_parts.append(f"--server.endpoint {self._get_endpoint_string()}")

        # Add collection filtering if specified
        if self.collections:
            if isinstance(self.collections, list):
                for coll in self.collections:
                    cmd_parts.append(f"--collection {coll}")
            else:
                cmd_parts.append(f"--collection {self.collections}")

        # Add create and overwrite flags
        cmd_parts.append(f"--create-collection {str(self.create).lower()}")
        cmd_parts.append(f"--overwrite {str(self.overwrite).lower()}")

        return " ".join(cmd_parts)

    def execute(self, command_string: Optional[str] = None) -> subprocess.CompletedProcess:
        """
        Execute the arangorestore command with an appropriate timeout.

        Args:
            command_string: Optional command string. If None, build_command() will be called.

        Returns:
            A subprocess.CompletedProcess object with the command result.
        """
        # Convert hours to seconds for the timeout
        timeout_seconds = int(self.timeout_hours * 3600)
        return super().execute(command_string, timeout=timeout_seconds)


class ArangoDumpGenerator(BaseArangoCommandGenerator):
    """Generator for arangodump commands."""

    def __init__(self, db_config: Optional[IndalekoDBConfig] = None):
        """Initialize the arangodump command generator."""
        super().__init__(db_config)
        self._command_name = "arangodump"
        self.output_directory = None
        self.collections = None
        self.include_system = False
        self.compress = True

    def with_output_directory(self, directory_path: str) -> 'ArangoDumpGenerator':
        """
        Set the output directory for the dump files.

        Args:
            directory_path: Path to the output directory.

        Returns:
            Self for method chaining.
        """
        self.output_directory = directory_path
        return self

    def with_collections(self, collections: Union[str, List[str], None] = None) -> 'ArangoDumpGenerator':
        """
        Set the collections to dump. None means all collections.

        Args:
            collections: Collection name(s) to dump, or None for all.

        Returns:
            Self for method chaining.
        """
        self.collections = collections
        return self

    def with_include_system(self, include: bool = True) -> 'ArangoDumpGenerator':
        """
        Set whether to include system collections.

        Args:
            include: Whether to include system collections.

        Returns:
            Self for method chaining.
        """
        self.include_system = include
        return self

    def with_compress(self, compress: bool = True) -> 'ArangoDumpGenerator':
        """
        Set whether to compress the output.

        Args:
            compress: Whether to compress the output.

        Returns:
            Self for method chaining.
        """
        self.compress = compress
        return self

    def build_command(self) -> str:
        """
        Build the arangodump command string.

        Raises:
            ValueError: If required parameters are missing.

        Returns:
            The complete arangodump command string.
        """
        if not self.output_directory:
            raise ValueError("Output directory is required")

        # Start with the basic command
        cmd_parts = [self._command_name]

        # Add output directory
        cmd_parts.append(f"--output-directory {self.output_directory}")

        # Add auth parameters
        cmd_parts.extend(self._get_auth_parameters())

        # Add endpoint
        cmd_parts.append(f"--server.endpoint {self._get_endpoint_string()}")

        # Add collection filtering if specified
        if self.collections:
            if isinstance(self.collections, list):
                for coll in self.collections:
                    cmd_parts.append(f"--collection {coll}")
            else:
                cmd_parts.append(f"--collection {self.collections}")

        # Add system collections flag
        if self.include_system:
            cmd_parts.append("--include-system-collections true")

        # Add compress flag
        cmd_parts.append(f"--compress {str(self.compress).lower()}")

        return " ".join(cmd_parts)


class ArangoShellGenerator(BaseArangoCommandGenerator):
    """Generator for arangosh commands."""

    def __init__(self, db_config: Optional[IndalekoDBConfig] = None):
        """Initialize the arangosh command generator."""
        super().__init__(db_config)
        self._command_name = "arangosh"
        self.command = None
        self.file = None
        self.quiet = True

    def with_command(self, command: str) -> 'ArangoShellGenerator':
        """
        Set the JavaScript command to execute.

        Args:
            command: JavaScript command to execute.

        Returns:
            Self for method chaining.
        """
        self.command = command
        return self

    def with_file(self, file_path: str) -> 'ArangoShellGenerator':
        """
        Set the JavaScript file to execute.

        Args:
            file_path: Path to the JavaScript file.

        Returns:
            Self for method chaining.
        """
        self.file = file_path
        return self

    def with_quiet(self, quiet: bool = True) -> 'ArangoShellGenerator':
        """
        Set whether to run in quiet mode.

        Args:
            quiet: Whether to run in quiet mode.

        Returns:
            Self for method chaining.
        """
        self.quiet = quiet
        return self

    def build_command(self) -> str:
        """
        Build the arangosh command string.

        Raises:
            ValueError: If neither command nor file is provided.

        Returns:
            The complete arangosh command string.
        """
        if not self.command and not self.file:
            raise ValueError("Either command or file is required")

        # Start with the basic command
        cmd_parts = [self._command_name]

        # Add auth parameters
        cmd_parts.extend(self._get_auth_parameters())

        # Add endpoint
        cmd_parts.append(f"--server.endpoint {self._get_endpoint_string()}")

        # Add quiet mode
        if self.quiet:
            cmd_parts.append("--quiet true")

        # Add command or file
        if self.command:
            cmd_parts.append(f"--javascript.execute-string \"{self.command}\"")
        elif self.file:
            cmd_parts.append(f"--javascript.execute {self.file}")

        return " ".join(cmd_parts)


def main():
    """Test the command generators."""
    logging.basicConfig(level=logging.DEBUG)

    # Test ArangoImport
    import_gen = ArangoImportGenerator()
    import_cmd = import_gen.with_file("test.jsonl") \
                          .with_collection("TestCollection") \
                          .build_command()
    print(f"Import command: {import_cmd}")

    # Test ArangoRestore
    restore_gen = ArangoRestoreGenerator()
    restore_cmd = restore_gen.with_input_directory("/backup/dir") \
                            .with_collections(["Collection1", "Collection2"]) \
                            .build_command()
    print(f"Restore command: {restore_cmd}")

    # Test ArangoDump
    dump_gen = ArangoDumpGenerator()
    dump_cmd = dump_gen.with_output_directory("/backup/dir") \
                      .with_collections("TestCollection") \
                      .build_command()
    print(f"Dump command: {dump_cmd}")

    # Test ArangoShell
    shell_gen = ArangoShellGenerator()
    shell_cmd = shell_gen.with_command("db._collections()") \
                        .build_command()
    print(f"Shell command: {shell_cmd}")


if __name__ == "__main__":
    main()
