"""
Test file for the ArangoDB command wrapper utility.

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
import sys
import argparse
from typing import List

# Handle imports for when the module is run directly
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db.utils.arango_commands import (
    ArangoImportGenerator,
    ArangoRestoreGenerator,
    ArangoDumpGenerator,
    ArangoShellGenerator
)
from utils.misc.file_name_management import generate_file_name
# pylint: enable=wrong-import-position


def test_import_command(args: argparse.Namespace) -> None:
    """Test the ArangoImportGenerator."""
    logging.info("Testing ArangoImportGenerator")

    import_gen = ArangoImportGenerator()
    import_cmd = import_gen.with_file(args.file or "example.jsonl") \
                          .with_collection(args.collection or "TestCollection") \
                          .build_command()

    print("=== Import Command ===")
    print(import_cmd)

    if args.execute:
        logging.info("Executing import command")
        result = import_gen.execute()
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")


def test_restore_command(args: argparse.Namespace) -> None:
    """Test the ArangoRestoreGenerator."""
    logging.info("Testing ArangoRestoreGenerator")

    restore_gen = ArangoRestoreGenerator()
    restore_cmd = restore_gen.with_input_directory(args.directory or "/tmp/backup") \
                            .with_create(True)

    if args.collection:
        if "," in args.collection:
            collections = args.collection.split(",")
            restore_cmd = restore_cmd.with_collections(collections)
        else:
            restore_cmd = restore_cmd.with_collections(args.collection)

    cmd_string = restore_cmd.build_command()
    print("=== Restore Command ===")
    print(cmd_string)

    if args.execute:
        logging.info("Executing restore command")
        print("This may take a long time for large databases...")
        result = restore_gen.execute()
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")


def test_dump_command(args: argparse.Namespace) -> None:
    """Test the ArangoDumpGenerator."""
    logging.info("Testing ArangoDumpGenerator")

    dump_gen = ArangoDumpGenerator()
    dump_cmd = dump_gen.with_output_directory(args.directory or "/tmp/backup") \
                      .with_compress(True)

    if args.collection:
        if "," in args.collection:
            collections = args.collection.split(",")
            dump_cmd = dump_cmd.with_collections(collections)
        else:
            dump_cmd = dump_cmd.with_collections(args.collection)

    cmd_string = dump_cmd.build_command()
    print("=== Dump Command ===")
    print(cmd_string)

    if args.execute:
        logging.info("Executing dump command")
        result = dump_gen.execute()
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")


def test_shell_command(args: argparse.Namespace) -> None:
    """Test the ArangoShellGenerator."""
    logging.info("Testing ArangoShellGenerator")

    shell_gen = ArangoShellGenerator()
    shell_cmd = shell_gen.with_command(args.command or "db._collections()") \
                        .with_quiet(True)

    cmd_string = shell_cmd.build_command()
    print("=== Shell Command ===")
    print(cmd_string)

    if args.execute:
        logging.info("Executing shell command")
        result = shell_gen.execute()
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")


def main() -> None:
    """Main function for testing the ArangoDB command generators."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test ArangoDB command generators")
    parser.add_argument(
        "--command",
        type=str,
        help="Command type to test (import, restore, dump, shell)"
    )
    parser.add_argument("--file", type=str, help="File path for import")
    parser.add_argument("--directory", type=str, help="Directory path for restore/dump")
    parser.add_argument("--collection", type=str, help="Collection name(s), comma separated")
    parser.add_argument("--js-command", type=str, dest="command", help="JavaScript command for shell")
    parser.add_argument("--execute", action="store_true", help="Actually execute the command")

    args = parser.parse_args()

    if not args.command or args.command == "import":
        test_import_command(args)
        print()

    if not args.command or args.command == "restore":
        test_restore_command(args)
        print()

    if not args.command or args.command == "dump":
        test_dump_command(args)
        print()

    if not args.command or args.command == "shell":
        test_shell_command(args)
        print()

    logging.info("Test completed")


if __name__ == "__main__":
    main()
