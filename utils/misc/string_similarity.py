"""
String similarity utilities for identity resolution in Indaleko.

This module provides functions for comparing strings using various
similarity metrics, with a focus on the Jaro-Winkler algorithm for
filename comparisons in identity resolution tasks.

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
from typing import Dict, List, Optional, Tuple, Union

try:
    import jellyfish
    JELLYFISH_AVAILABLE = True
except ImportError:
    JELLYFISH_AVAILABLE = False


def jaro_winkler_similarity(s1: str, s2: str, prefix_weight: float = 0.1) -> float:
    """
    Calculate the Jaro-Winkler similarity between two strings.

    The Jaro-Winkler similarity is a string metric for measuring the edit distance
    between two sequences. It is a variant of the Jaro distance that gives higher
    scores to strings that match from the beginning.

    Args:
        s1: First string to compare
        s2: Second string to compare
        prefix_weight: Weight given to common prefix (default: 0.1)

    Returns:
        A similarity score between 0 (completely different) and 1 (identical)
    """
    if JELLYFISH_AVAILABLE:
        # Use the jellyfish library if available
        return jellyfish.jaro_winkler_similarity(s1, s2)
    else:
        # Fallback to a pure Python implementation
        return _jaro_winkler_similarity_pure_python(s1, s2, prefix_weight)


def _jaro_winkler_similarity_pure_python(s1: str, s2: str, prefix_weight: float = 0.1) -> float:
    """
    Pure Python implementation of Jaro-Winkler similarity.
    Used as a fallback if jellyfish is not available.

    Args:
        s1: First string to compare
        s2: Second string to compare
        prefix_weight: Weight given to common prefix (default: 0.1)

    Returns:
        A similarity score between 0 (completely different) and 1 (identical)
    """
    # Handle edge cases
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    
    # Calculate Jaro similarity first
    jaro_sim = _jaro_similarity(s1, s2)
    
    # Find common prefix length (up to 4 characters)
    prefix_len = 0
    for i in range(min(len(s1), len(s2), 4)):
        if s1[i] == s2[i]:
            prefix_len += 1
        else:
            break
    
    # Apply Winkler modification with stronger prefix boost
    # The standard formula is: jaro_sim + (prefix_len * prefix_weight * (1 - jaro_sim))
    # We add a slight boost to ensure prefix matching has more impact
    winkler_boost = prefix_len * prefix_weight * (1 - jaro_sim)
    
    # When strings start with the same prefix but differ later,
    # we give more weight to the prefix similarity
    if prefix_len > 0:
        # Scale the boost based on the length of the matching prefix
        prefix_ratio = prefix_len / min(len(s1), len(s2))
        winkler_boost *= (1.0 + 0.1 * prefix_ratio)
    
    return min(1.0, jaro_sim + winkler_boost)


def _jaro_similarity(s1: str, s2: str) -> float:
    """
    Calculate the Jaro similarity between two strings.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Jaro similarity score between 0 and 1
    """
    # If strings are identical, return 1.0
    if s1 == s2:
        return 1.0
    
    # Get lengths of strings
    len1 = len(s1)
    len2 = len(s2)
    
    # Maximum distance for matching characters
    match_distance = max(len1, len2) // 2 - 1
    match_distance = max(0, match_distance)  # Ensure it's not negative
    
    # Initialize match arrays
    s1_matches = [False] * len1
    s2_matches = [False] * len2
    
    # Count matching characters
    matches = 0
    for i in range(len1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len2)
        
        for j in range(start, end):
            if not s2_matches[j] and s1[i] == s2[j]:
                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break
    
    # If no matches, return 0
    if matches == 0:
        return 0.0
    
    # Count transpositions
    transpositions = 0
    k = 0
    for i in range(len1):
        if s1_matches[i]:
            while not s2_matches[k]:
                k += 1
            if s1[i] != s2[k]:
                transpositions += 1
            k += 1
    
    # Calculate Jaro similarity
    transpositions = transpositions // 2
    jaro = (matches / len1 + matches / len2 + (matches - transpositions) / matches) / 3
    return jaro


def weighted_filename_similarity(file1: str, file2: str, 
                                 weights: Optional[Dict[str, float]] = None) -> float:
    """
    Calculate a weighted similarity score between two filenames using multiple
    similarity metrics and file attributes.

    Args:
        file1: First filename to compare
        file2: Second filename to compare
        weights: Dictionary of weights for different comparison factors.
                 Default weights are:
                 - name: 0.6 (Jaro-Winkler similarity of base filenames)
                 - extension: 0.2 (exact match of file extensions)
                 - name_tokens: 0.2 (shared token ratio)

    Returns:
        A weighted similarity score between 0 (completely different) and 1 (identical)
    """
    # Default weights if not provided
    if weights is None:
        weights = {
            "name": 0.6,  # Base filename similarity
            "extension": 0.2,  # File extension similarity
            "name_tokens": 0.2,  # Common tokens in filenames
        }
    
    # Extract base filenames and extensions
    base1, ext1 = os.path.splitext(os.path.basename(file1))
    base2, ext2 = os.path.splitext(os.path.basename(file2))
    
    # Remove leading dot from extensions
    ext1 = ext1[1:] if ext1.startswith('.') else ext1
    ext2 = ext2[1:] if ext2.startswith('.') else ext2
    
    # Calculate Jaro-Winkler similarity for base filenames
    name_similarity = jaro_winkler_similarity(base1.lower(), base2.lower())
    
    # Calculate extension similarity (exact match for now)
    extension_similarity = 1.0 if ext1.lower() == ext2.lower() else 0.0
    
    # Calculate token similarity
    tokens1 = set(_tokenize_filename(base1.lower()))
    tokens2 = set(_tokenize_filename(base2.lower()))
    
    # Jaccard similarity for tokens
    if not tokens1 and not tokens2:
        token_similarity = 1.0
    elif not tokens1 or not tokens2:
        token_similarity = 0.0
    else:
        common_tokens = len(tokens1.intersection(tokens2))
        all_tokens = len(tokens1.union(tokens2))
        token_similarity = common_tokens / all_tokens if all_tokens > 0 else 0.0
    
    # Calculate weighted similarity
    weighted_similarity = (
        weights["name"] * name_similarity +
        weights["extension"] * extension_similarity +
        weights["name_tokens"] * token_similarity
    )
    
    return weighted_similarity


def _tokenize_filename(filename: str) -> List[str]:
    """
    Simple tokenization of a filename by splitting on non-alphanumeric characters
    and extracting meaningful parts.

    Args:
        filename: The filename to tokenize

    Returns:
        List of tokens
    """
    # Split by common separators and filter out empty strings
    import re
    tokens = re.split(r'[^a-zA-Z0-9]', filename)
    return [token for token in tokens if token]


def multi_attribute_identity_resolution(
    file1_attrs: Dict[str, Union[str, int, float]], 
    file2_attrs: Dict[str, Union[str, int, float]],
    weights: Optional[Dict[str, float]] = None,
    threshold: float = 0.85
) -> Tuple[bool, float]:
    """
    Determine if two files are likely the same entity based on multiple attributes.
    
    Uses a weighted scoring system across multiple file attributes, including:
    - Filename (using Jaro-Winkler similarity)
    - File size
    - File type/extension
    - Content checksum (if available)
    - Modification time proximity (if available)
    
    Args:
        file1_attrs: Dictionary of attributes for first file
        file2_attrs: Dictionary of attributes for second file
        weights: Dictionary of weights for different attributes.
                 Default weights are:
                 - filename: 0.4
                 - size: 0.1
                 - extension: 0.1
                 - checksum: 0.3
                 - modified: 0.1
        threshold: Minimum similarity score to consider files as the same entity
    
    Returns:
        Tuple of (is_same_entity: bool, similarity_score: float)
    """
    # Default weights if not provided
    if weights is None:
        weights = {
            "filename": 0.3,
            "size": 0.1,
            "extension": 0.1,
            "checksum": 0.4,  # Increased weight for checksum
            "modified": 0.1
        }
    
    scores = {}
    total_weight = 0.0
    
    # Filename similarity (required)
    if "filename" in file1_attrs and "filename" in file2_attrs:
        scores["filename"] = weighted_filename_similarity(
            str(file1_attrs["filename"]), 
            str(file2_attrs["filename"])
        )
        total_weight += weights["filename"]
    
    # File size similarity
    if "size" in file1_attrs and "size" in file2_attrs:
        size1 = int(file1_attrs["size"])
        size2 = int(file2_attrs["size"])
        
        if size1 == size2:
            scores["size"] = 1.0
        elif size1 == 0 or size2 == 0:
            scores["size"] = 0.0
        else:
            # Relative size difference
            ratio = min(size1, size2) / max(size1, size2)
            scores["size"] = ratio
        
        total_weight += weights["size"]
    
    # Extension similarity
    if "extension" in file1_attrs and "extension" in file2_attrs:
        ext1 = str(file1_attrs["extension"]).lower()
        ext2 = str(file2_attrs["extension"]).lower()
        scores["extension"] = 1.0 if ext1 == ext2 else 0.0
        total_weight += weights["extension"]
    
    # Checksum similarity (exact match)
    if "checksum" in file1_attrs and "checksum" in file2_attrs:
        checksum1 = str(file1_attrs["checksum"])
        checksum2 = str(file2_attrs["checksum"])
        scores["checksum"] = 1.0 if checksum1 == checksum2 else 0.0
        total_weight += weights["checksum"]
    
    # Modification time similarity
    if "modified" in file1_attrs and "modified" in file2_attrs:
        mod1 = float(file1_attrs["modified"])
        mod2 = float(file2_attrs["modified"])
        
        # Time difference in seconds
        time_diff = abs(mod1 - mod2)
        
        # Consider times within 1 hour similar, with decreasing similarity
        if time_diff <= 3600:
            scores["modified"] = 1.0 - (time_diff / 3600)
        else:
            scores["modified"] = 0.0
            
        total_weight += weights["modified"]
    
    # Calculate weighted average score
    if total_weight == 0:
        return False, 0.0
    
    weighted_score = sum(scores[attr] * weights[attr] for attr in scores) / total_weight
    
    # Special case: files with same checksum are highly likely to be the same entity
    # This handles cases where filenames differ but content is identical
    if "checksum" in scores and scores["checksum"] == 1.0 and "size" in scores and scores["size"] == 1.0:
        # If checksums match exactly, boost the overall score to ensure they're recognized as same
        checksum_boost = 0.15 * (1.0 - weighted_score)
        weighted_score = min(1.0, weighted_score + checksum_boost)
    
    # Determine if files are the same entity based on threshold
    is_same_entity = weighted_score >= threshold
    
    return is_same_entity, weighted_score


def main():
    """Test the string similarity functions with sample filenames."""
    test_pairs = [
        # Similar filenames
        ("IndalekoObjectDataModel.py", "IndalekoObjectDataModel.py"),
        ("thesis-draft-v1.docx", "thesis-draft-v2.docx"),
        ("quarterly_report_2023.pdf", "quarterly_report_2023_final.pdf"),
        ("project-notes-jan.txt", "project_notes_jan.txt"),
        ("Mason_Tony_CV.pdf", "Mason-Tony-CV.pdf"),
        
        # Different filenames
        ("IndalekoObjectDataModel.py", "IndalekoRecordSchema.py"),
        ("thesis-draft-v1.docx", "project-proposal.docx"),
        ("quarterly_report_2023.pdf", "annual_report_2022.pdf"),
        
        # Edge cases
        ("", ""),
        ("short.txt", "completely_different_long_filename.txt"),
    ]
    
    print("Jaro-Winkler Similarity Tests:")
    print("=============================")
    
    for file1, file2 in test_pairs:
        similarity = jaro_winkler_similarity(file1, file2)
        print(f"'{file1}' <-> '{file2}': {similarity:.4f}")
    
    print("\nWeighted Filename Similarity Tests:")
    print("=================================")
    
    for file1, file2 in test_pairs:
        similarity = weighted_filename_similarity(file1, file2)
        print(f"'{file1}' <-> '{file2}': {similarity:.4f}")
    
    print("\nMulti-Attribute Identity Resolution Tests:")
    print("=======================================")
    
    # Test with different attribute combinations
    test_files = [
        # Identical files
        (
            {"filename": "document.pdf", "size": 1024, "checksum": "abcdef", "modified": 1649152000},
            {"filename": "document.pdf", "size": 1024, "checksum": "abcdef", "modified": 1649152000}
        ),
        # Same file, different location
        (
            {"filename": "/home/user/document.pdf", "size": 1024, "checksum": "abcdef"},
            {"filename": "C:\\Users\\Tony\\document.pdf", "size": 1024, "checksum": "abcdef"}
        ),
        # Similar filename, same size, different content
        (
            {"filename": "thesis-draft-v1.docx", "size": 2048, "checksum": "abcdef"},
            {"filename": "thesis-draft-v2.docx", "size": 2048, "checksum": "123456"}
        ),
        # Different filename, same content
        (
            {"filename": "document.pdf", "size": 1024, "checksum": "abcdef"},
            {"filename": "backup_document.pdf", "size": 1024, "checksum": "abcdef"}
        ),
        # Different files
        (
            {"filename": "document.pdf", "size": 1024, "checksum": "abcdef"},
            {"filename": "spreadsheet.xlsx", "size": 5120, "checksum": "xyz123"}
        ),
    ]
    
    for file1_attrs, file2_attrs in test_files:
        is_same, score = multi_attribute_identity_resolution(file1_attrs, file2_attrs)
        file1_name = file1_attrs.get("filename", "unknown")
        file2_name = file2_attrs.get("filename", "unknown")
        result = "SAME" if is_same else "DIFFERENT"
        print(f"'{file1_name}' <-> '{file2_name}': {score:.4f} ({result})")


if __name__ == "__main__":
    main()