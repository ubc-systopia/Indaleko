#!/usr/bin/env python
"""
USN Bridge for Indaleko.

This script serves as a bridge between direct_usn_test.py and foo.py.
It calls foo.py as a subprocess to retrieve USN journal records and captures the output.

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

import argparse
import os
import subprocess
import sys


def main() -> int | None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="USN Bridge - Run foo.py as a subprocess",
    )
    parser.add_argument("--volume", required=True, help="Volume to query (e.g., 'C:')")
    parser.add_argument("--start-usn", type=int, help="Starting USN to query from")
    parser.add_argument("--output", required=True, help="Output file for USN records")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    # Standardize volume path
    volume = args.volume
    if not volume.endswith(":"):
        volume = f"{volume}:"

    # Get the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    foo_path = os.path.join(script_dir, "foo.py")

    if not os.path.exists(foo_path):
        return 1

    if args.verbose:
        pass

    # Build the command to run foo.py
    cmd = [sys.executable, foo_path, "--volume", volume]

    if args.start_usn is not None:
        cmd.extend(["--start-usn", str(args.start_usn)])

    if args.verbose:
        cmd.append("--verbose")

    # Run foo.py and capture its output
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            return 1

        # Parse the output
        records_found = False
        with open(args.output, "w") as outfile:
            for line in result.stdout.splitlines():
                if "USN:" in line:
                    # Start of a record
                    current_record = line + "\n"
                    records_found = True
                elif records_found and line.strip() and ":" in line:
                    # Continuation of the record
                    current_record += line + "\n"
                elif records_found and current_record:
                    # End of a record, write it and reset
                    outfile.write(current_record + "\n")
                    current_record = ""

            # Write the last record if there is one
            if records_found and current_record:
                outfile.write(current_record + "\n")

        if args.verbose:
            pass

        # Print stdout for debugging in verbose mode
        if args.verbose:
            pass

        return 0

    except Exception:
        return 1


if __name__ == "__main__":
    sys.exit(main())
