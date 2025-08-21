"""
Test script for the tokenization module.

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


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from storage.recorders.tokenization import tokenize_filename


def test_tokenize_filename() -> None:
    """Test the tokenize_filename function."""
    test_cases = [
        # CamelCase
        (
            "IndalekoObject",
            {
                "CamelCaseTokenizedName": "Indaleko Object",
                "SnakeCaseTokenizedName": "IndalekoObject",
            },
        ),
        # snake_case
        (
            "indaleko_object",
            {
                "CamelCaseTokenizedName": "indaleko_object",
                "SnakeCaseTokenizedName": "indaleko object",
            },
        ),
        # Mixed case with numbers and special chars
        (
            "MyFile-v1.2_FINAL.txt",
            {
                "CamelCaseTokenizedName": "My File-v1.2_FINAL.txt",
                "SnakeCaseTokenizedName": "MyFile-v1.2 FINAL.txt",  # Note space instead of underscore
            },
        ),
        # Windows path
        (
            "C:\\Users\\TonyMason\\Documents\\Project Report.docx",
            {
                "CamelCaseTokenizedName": "Project Report.docx",
                "SnakeCaseTokenizedName": "Project Report.docx",
            },
        ),
        # Linux path
        (
            "/home/tony/Documents/ProjectReport.md",
            {
                "CamelCaseTokenizedName": "Project Report.md",
                "SnakeCaseTokenizedName": "ProjectReport.md",
            },
        ),
    ]

    for filename, expected_partial in test_cases:
        result = tokenize_filename(filename)

        # Check that the expected results are in the output
        for key, expected_value in expected_partial.items():
            assert key in result, f"Key {key} missing from result"
            assert result[key] == expected_value, f"For {key}, expected {expected_value}, got {result[key]}"

        # Check that n-grams and space tokenization are working
        assert "NgramTokenizedName" in result, "NgramTokenizedName missing"
        assert "SpaceTokenizedName" in result, "SpaceTokenizedName missing"

        # For longer names, we should have n-grams
        base_name = os.path.basename(filename)
        name_part = os.path.splitext(base_name)[0]
        if len(name_part) >= 3:
            assert len(result["NgramTokenizedName"]) > 0, "Expected n-grams for name length >= 3"



if __name__ == "__main__":
    test_tokenize_filename()
