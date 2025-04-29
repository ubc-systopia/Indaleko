#!/usr/bin/env python3
"""
Pre-commit hook to check for direct pip usage in Python files.

This script scans Python files for direct pip imports or pip.main() calls,
enforcing the project standard of using uv instead.
"""
import argparse
import re
import sys
from collections.abc import Sequence


def check_file(filename: str) -> list[str]:
    """Check file for pip imports or usage patterns.

    Args:
        filename: The file to check

    Returns:
        List of error messages if violations found
    """
    errors = []
    with open(filename, encoding="utf-8") as f:
        content = f.read()

    # Check for pip imports
    if re.search(r"import\s+pip", content) or re.search(
        r"from\s+pip\s+import",
        content,
    ):
        errors.append(f"{filename}: Direct pip import found. Use uv instead.")

    # Check for pip.main() calls
    if re.search(r"pip\.main\(", content) and "check_no_pip_usage.py" not in filename:
        errors.append(f"{filename}: pip.main() call found. Use uv instead.")

    # Check for subprocess calls to pip
    pip_patterns = [
        r"subprocess\.(?:call|run|check_call|Popen)\(.*[\"'].*pip",
        r"os\.system\(.*[\"'].*pip",
        r"-m\s*[\"']pip[\"']",
        r"!pip install",  # For Jupyter notebooks
    ]

    for pattern in pip_patterns:
        if re.search(pattern, content):
            errors.append(
                f"{filename}: Direct pip install command found. "
                "Use 'uv pip install -e .' or edit pyproject.toml instead.",
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
        if filename.endswith(".py"):
            errors.extend(check_file(filename))

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(
            "\nPlease use 'uv' for package management instead of pip.\n"
            "- To install dependencies: uv pip install -e .\n"
            "- To add new packages: Edit pyproject.toml and run uv pip install -e .\n",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
