"""
Tokenization utilities for file and directory names in Indaleko.

These functions help break down file and directory names into tokenized forms
that improve search functionality when indexed in ArangoDB.

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
import re


def tokenize_filename(filename: str) -> dict[str, str | list[str]]:
    """
    Generate different tokenizations of a filename to improve search capabilities.

    Args:
        filename: The filename or directory name to tokenize

    Returns:
        A dictionary containing different tokenization results:
        - CamelCaseTokenizedName: Splits CamelCase names (e.g., "IndalekoObject" -> "Indaleko Object")
        - SnakeCaseTokenizedName: Splits snake_case names (e.g., "indaleko_object" -> "indaleko object")
        - NgramTokenizedName: List of n-grams (3-5 character sequences)
        - SpaceTokenizedName: Simple space-split tokenization
        - SearchTokenizedName: Combined tokenization for search purposes
    """
    # Strip path but keep extension for display
    base_name = os.path.basename(filename)

    # For n-grams, we use just the name part without extension
    name_part, extension = os.path.splitext(base_name)

    result = {}

    # CamelCase tokenization - preserve extension
    # This regex finds transitions from lowercase to uppercase
    camel_split = re.sub(r"([a-z])([A-Z])", r"\1 \2", base_name)
    # Also handle consecutive uppercase letters followed by lowercase
    camel_split = re.sub(r"([A-Z])([A-Z][a-z])", r"\1 \2", camel_split)
    result["CamelCaseTokenizedName"] = camel_split

    # Snake case tokenization - preserve extension
    snake_split = base_name.replace("_", " ")
    result["SnakeCaseTokenizedName"] = snake_split

    # N-gram tokenization (using 3, 4, and 5-grams) - just on name part
    ngrams = []
    # Only generate n-grams if name is long enough
    if len(name_part) >= 3:
        # 3-grams
        for i in range(len(name_part) - 2):
            ngrams.append(name_part[i : i + 3])

        # 4-grams
        if len(name_part) >= 4:
            for i in range(len(name_part) - 3):
                ngrams.append(name_part[i : i + 4])

        # 5-grams
        if len(name_part) >= 5:
            for i in range(len(name_part) - 4):
                ngrams.append(name_part[i : i + 5])

    result["NgramTokenizedName"] = ngrams

    # Space tokenization (split by spaces, dashes, dots, etc.) - on full name
    space_split = re.split(r"[ \-_\.\(\)\[\]\{\}]", base_name)
    # Remove empty strings from the list
    space_split = [token for token in space_split if token]
    result["SpaceTokenizedName"] = space_split

    # Create a combined tokenized value that incorporates CamelCase and snake_case tokenization
    # This will be indexed using the standard text_en analyzer
    combined_tokens = []
    combined_tokens.append(base_name)  # Original name
    combined_tokens.append(camel_split)  # CamelCase tokenized version
    combined_tokens.append(snake_split)  # snake_case tokenized version

    # Add individual tokens from space tokenization
    combined_tokens.extend(space_split)

    # Join everything into a single string with spaces for standard analyzer processing
    result["SearchTokenizedName"] = " ".join(combined_tokens)

    return result


def main():
    """Test the tokenization functions."""
    test_names = [
        "IndalekoObjectDataModel.py",
        "indaleko_object_data_model.py",
        "Windows10Pro-2023.tar.gz",
        "README(important).md",
        "MyProject[v2.1].zip",
        "data-science_notebook.ipynb",
        "CamelCaseExample123",
        "snake_case_example_123",
    ]

    for name in test_names:
        print(f"Tokenizing: {name}")
        tokens = tokenize_filename(name)
        for token_type, token_value in tokens.items():
            print(f"  {token_type}: {token_value}")
        print()


if __name__ == "__main__":
    main()
