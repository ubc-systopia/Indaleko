#!/usr/bin/env python3
"""
Pre-commit hook to check for unauthorized 'create_collection' calls.

This script scans Python files to ensure create_collection is only called from
approved locations:
1. db/db_collections.py - For static collections
2. utils/registration_service.py - For dynamic collections

All other direct create_collection calls are unauthorized.
"""
import argparse
import re
import sys
from collections.abc import Sequence

# List of files/directories allowed to use create_collection
AUTHORIZED_FILES = [
    "db/collection.py",
    "utils/registration_service.py",
]

# Directories to skip completely (old code, test data, etc.)
SKIP_DIRS = [
    "old/",
    "scratch/",
    "__pycache__",
    "testing/",
    "test_",        # Files starting with test_
    "tests/",
    "ablation_",    # Ablation test files
    "tools/data_generator_enhanced/testing/",  # Ablation testing directory
]


def is_authorized_file(filepath: str) -> bool:
    """Check if this is an authorized file for create_collection calls.

    Args:
        filepath: The file path to check

    Returns:
        True if this file is authorized, False otherwise
    """
    # Convert to Unix-style path for consistent comparison
    filepath = filepath.replace("\\", "/")

    # Check if this is an explicitly authorized file
    for auth_file in AUTHORIZED_FILES:
        if filepath.endswith(auth_file):
            return True

    # Check if this file is in a directory that should be skipped
    for skip_dir in SKIP_DIRS:
        if skip_dir in filepath:
            return True

    return False


def check_file(filename: str) -> list[str]:
    """Check file for unauthorized create_collection calls.

    Args:
        filename: The file to check

    Returns:
        List of error messages if violations found
    """
    errors = []

    # Skip authorized files
    if is_authorized_file(filename):
        return errors

    # Skip non-Python files
    if not filename.endswith(".py"):
        return errors

    with open(filename, encoding="utf-8") as f:
        content = f.read()

    # Pattern to detect create_collection calls
    # This pattern looks for .create_collection( with optional whitespace
    pattern = r"\.create_collection\s*\("

    matches = re.findall(pattern, content)
    if matches:
        # Report the unauthorized usage
        errors.append(
            f"{filename}: Unauthorized create_collection call found. "
            "Only use create_collection in db/db_collections.py or utils/registration_service.py.",
        )

    return errors


def main(argv: Sequence[str] = None) -> int:
    """Run the pre-commit hook.

    Args:
        argv: Command line arguments

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", nargs="*")
    args = parser.parse_args(argv)

    errors = []
    for filename in args.filenames:
        errors.extend(check_file(filename))

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(
            "\nDirect create_collection calls are only allowed in:\n"
            "1. db/db_collections.py - For static collections\n"
            "2. utils/registration_service.py - For dynamic collections\n\n"
            "For other cases, use IndalekoCollections.get_collection() or the registration service.\n",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
