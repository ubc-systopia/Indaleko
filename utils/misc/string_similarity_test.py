"""
Tests for the string_similarity module.

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
import unittest
import random
from typing import Dict, List, Tuple

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from utils.misc.string_similarity import (
    jaro_winkler_similarity,
    weighted_filename_similarity,
    multi_attribute_identity_resolution
)


class TestJaroWinkler(unittest.TestCase):
    """Test cases for Jaro-Winkler similarity functions."""

    def test_identical_strings(self):
        """Test that identical strings have a similarity of 1.0."""
        test_strings = [
            "IndalekoObject",
            "thesis-draft-v1.docx",
            "",  # Edge case: empty string
            "a",  # Edge case: single character
            "1234567890",  # Edge case: numeric string
        ]
        
        for s in test_strings:
            with self.subTest(string=s):
                self.assertEqual(jaro_winkler_similarity(s, s), 1.0)
    
    def test_completely_different_strings(self):
        """Test that completely different strings have a low similarity."""
        test_pairs = [
            ("IndalekoObject", "CompletelyDifferent"),
            ("thesis", "xyzabc"),
            ("document.pdf", "12345.jpg"),
        ]
        
        for s1, s2 in test_pairs:
            with self.subTest(string1=s1, string2=s2):
                # Should be less than 0.5 for very different strings
                self.assertLess(jaro_winkler_similarity(s1, s2), 0.5)
    
    def test_similar_strings(self):
        """Test strings with small differences."""
        test_pairs = [
            # String pairs with expected minimum similarity
            ("IndalekoObject", "IndalekoObjects", 0.9),  # Suffix difference
            ("thesis-draft-v1", "thesis-draft-v2", 0.95),  # Single character change
            ("Mason_Tony_CV", "Mason-Tony-CV", 0.9),  # Different separators
            ("quarterly_report_2023", "quarterly_report_2023_final", 0.85),  # Added suffix
            ("project-notes-jan", "project_notes_jan", 0.9),  # Different separators
        ]
        
        for s1, s2, min_expected in test_pairs:
            with self.subTest(string1=s1, string2=s2):
                similarity = jaro_winkler_similarity(s1, s2)
                self.assertGreaterEqual(
                    similarity, 
                    min_expected, 
                    f"Expected {s1} and {s2} to have similarity >= {min_expected}, got {similarity}"
                )
    
    def test_common_prefix_boost(self):
        """Test that strings with common prefixes get higher scores."""
        # Pairs with same edit distance but different prefix commonality
        test_cases = [
            # Same edits at beginning vs. end
            (("xyzabc", "abcxyz"), ("abcxyz", "abcdef")),
            # Use a better example for common prefix vs. no common prefix
            # where the base similarity is closer
            (("ARandomX", "BRandomY"), ("SamePreX", "SamePreY")),
        ]
        
        for (s1a, s1b), (s2a, s2b) in test_cases:
            with self.subTest(case1=(s1a, s1b), case2=(s2a, s2b)):
                sim1 = jaro_winkler_similarity(s1a, s1b)
                sim2 = jaro_winkler_similarity(s2a, s2b)
                
                # The second pair should have higher similarity due to common prefix
                self.assertGreater(sim2, sim1)


class TestWeightedFilenameSimilarity(unittest.TestCase):
    """Test cases for the weighted filename similarity function."""
    
    def test_identical_filenames(self):
        """Test that identical filenames have a similarity of 1.0."""
        test_filenames = [
            "document.pdf",
            "IndalekoObjectDataModel.py",
            "thesis-draft-v1.docx",
            "",  # Edge case: empty string
        ]
        
        for filename in test_filenames:
            with self.subTest(filename=filename):
                self.assertEqual(weighted_filename_similarity(filename, filename), 1.0)
    
    def test_filenames_with_different_paths(self):
        """Test that filenames with different paths but same basename have high similarity."""
        test_pairs = [
            ("/home/user/document.pdf", "C:\\Users\\Tony\\document.pdf"),
            ("./src/main.py", "../project/src/main.py"),
            ("/path/to/file.txt", "file.txt"),
        ]
        
        for path1, path2 in test_pairs:
            with self.subTest(path1=path1, path2=path2):
                self.assertEqual(weighted_filename_similarity(path1, path2), 1.0)
    
    def test_different_extensions(self):
        """Test filenames with same base but different extensions."""
        test_pairs = [
            ("document.pdf", "document.docx"),
            ("report.xlsx", "report.csv"),
            ("code.py", "code.js"),
        ]
        
        for file1, file2 in test_pairs:
            with self.subTest(file1=file1, file2=file2):
                # Should be less than 1.0 due to extension difference,
                # but still relatively high due to same base name
                similarity = weighted_filename_similarity(file1, file2)
                self.assertLess(similarity, 1.0)
                self.assertGreater(similarity, 0.7)  # Assuming default weights
    
    def test_similar_filenames(self):
        """Test filenames with small differences."""
        test_pairs = [
            ("thesis-draft-v1.docx", "thesis-draft-v2.docx"),
            ("report_2023.pdf", "report_2023_final.pdf"),
            ("project-notes.txt", "project_notes.txt"),
        ]
        
        for file1, file2 in test_pairs:
            with self.subTest(file1=file1, file2=file2):
                # Should be high but less than 1.0
                similarity = weighted_filename_similarity(file1, file2)
                self.assertLess(similarity, 1.0)
                self.assertGreater(similarity, 0.8)  # These are very similar
    
    def test_custom_weights(self):
        """Test with custom weights."""
        # A pair with same extension but different name
        pair = ("report1.pdf", "completely-different.pdf")
        
        # Default weights (name: 0.6, extension: 0.2, name_tokens: 0.2)
        default_similarity = weighted_filename_similarity(pair[0], pair[1])
        
        # Custom weights prioritizing extension
        custom_weights = {
            "name": 0.2,
            "extension": 0.7,
            "name_tokens": 0.1
        }
        custom_similarity = weighted_filename_similarity(pair[0], pair[1], custom_weights)
        
        # With custom weights prioritizing extension, the similarity should be higher
        self.assertGreater(custom_similarity, default_similarity)


class TestMultiAttributeIdentityResolution(unittest.TestCase):
    """Test cases for multi-attribute identity resolution."""
    
    def test_identical_files(self):
        """Test files with identical attributes."""
        file1 = file2 = {
            "filename": "document.pdf",
            "size": 1024,
            "extension": "pdf",
            "checksum": "abcdef123456",
            "modified": 1649152000
        }
        
        is_same, score = multi_attribute_identity_resolution(file1, file2)
        self.assertTrue(is_same)
        # Use assertAlmostEqual for floating point comparisons to handle precision issues
        self.assertAlmostEqual(score, 1.0, places=10)
    
    def test_same_content_different_names(self):
        """Test files with same content but different names."""
        file1 = {
            "filename": "original.pdf",
            "size": 1024,
            "extension": "pdf",
            "checksum": "abcdef123456",
            "modified": 1649152000
        }
        
        file2 = {
            "filename": "copy.pdf",
            "size": 1024,
            "extension": "pdf",
            "checksum": "abcdef123456",
            "modified": 1649152010  # 10 seconds later
        }
        
        is_same, score = multi_attribute_identity_resolution(file1, file2)
        self.assertTrue(is_same)
        self.assertGreater(score, 0.85)
    
    def test_similar_names_different_content(self):
        """Test files with similar names but different content."""
        file1 = {
            "filename": "thesis-draft-v1.docx",
            "size": 2048,
            "extension": "docx",
            "checksum": "abcdef123456",
            "modified": 1649152000
        }
        
        file2 = {
            "filename": "thesis-draft-v2.docx",
            "size": 2048,
            "extension": "docx",
            "checksum": "xyz789012345",  # Different checksum
            "modified": 1649238400  # One day later
        }
        
        is_same, score = multi_attribute_identity_resolution(file1, file2)
        # These should be detected as different due to different checksum
        self.assertFalse(is_same)
    
    def test_custom_threshold(self):
        """Test with custom similarity threshold."""
        file1 = {
            "filename": "thesis-draft-v1.docx",
            "size": 2048,
            "extension": "docx",
            "checksum": "abcdef123456"
        }
        
        file2 = {
            "filename": "thesis-draft-final.docx",
            "size": 2080,  # Slightly different size
            "extension": "docx",
            "checksum": "xyz789012345"  # Different checksum
        }
        
        # With default threshold (0.85), these are probably different
        is_same_default, score = multi_attribute_identity_resolution(file1, file2)
        
        # With a lower threshold (0.6), they might be considered the same
        is_same_custom, score = multi_attribute_identity_resolution(file1, file2, threshold=0.6)
        
        self.assertFalse(is_same_default)
        self.assertEqual(is_same_default, is_same_custom)  # Should still be different
    
    def test_custom_weights(self):
        """Test with custom attribute weights."""
        file1 = {
            "filename": "report.pdf",
            "size": 1024,
            "extension": "pdf",
            "checksum": "abcdef123456"
        }
        
        file2 = {
            "filename": "completely_different_report.pdf",  # More different name
            "size": 1024,
            "extension": "pdf",
            "checksum": "abcdef123456"  # Same checksum
        }
        
        # Use a stricter threshold for default weights
        is_same_default, score_default = multi_attribute_identity_resolution(
            file1, file2, threshold=0.9  # Higher threshold
        )
        
        # Custom weights prioritizing checksum should consider these the same
        custom_weights = {
            "filename": 0.1,
            "size": 0.1,
            "extension": 0.1,
            "checksum": 0.7
        }
        
        is_same_custom, score_custom = multi_attribute_identity_resolution(
            file1, file2, weights=custom_weights, threshold=0.85
        )
        
        self.assertFalse(is_same_default)
        self.assertTrue(is_same_custom)
        self.assertGreater(score_custom, score_default)


class TestAccuracy(unittest.TestCase):
    """Test the accuracy of the identity resolution system."""
    
    @staticmethod
    def _generate_test_data(num_files: int, num_variants: int) -> Tuple[List[Dict], List[Dict], List[Tuple[int, int]]]:
        """
        Generate test data for accuracy testing.
        
        Creates original files and variant files (with controlled modifications),
        along with ground truth pairs for testing.
        
        Args:
            num_files: Number of original files to generate
            num_variants: Number of variants per original file
            
        Returns:
            Tuple of (original_files, variant_files, ground_truth_pairs)
        """
        original_files = []
        variant_files = []
        ground_truth_pairs = []  # (original_idx, variant_idx) pairs
        
        file_types = ["pdf", "docx", "xlsx", "txt", "py", "java", "json", "html"]
        name_prefixes = ["report", "document", "thesis", "project", "data", "code", "notes", "invoice"]
        
        # Generate original files
        for i in range(num_files):
            file_type = random.choice(file_types)
            name_prefix = random.choice(name_prefixes)
            checksum = ''.join(random.choices('0123456789abcdef', k=12))
            size = random.randint(1000, 10000)
            modified = random.randint(1640995200, 1672531200)  # 2022 in seconds
            
            file = {
                "filename": f"{name_prefix}_{i}.{file_type}",
                "extension": file_type,
                "size": size,
                "checksum": checksum,
                "modified": modified
            }
            original_files.append(file)
            
            # Generate variants for this file
            for j in range(num_variants):
                # Decide what to change - prioritize checksum matching cases
                change_type = random.choices(
                    ["name", "name_and_date", "none", "size_change"], 
                    weights=[0.4, 0.3, 0.2, 0.1], 
                    k=1
                )[0]
                
                variant = file.copy()
                
                if change_type == "name":
                    # Change the filename but keep checksum (same content)
                    modifiers = ["_final", "_v2", "_copy", "_backup", "_archived"]
                    modifier = random.choice(modifiers)
                    variant["filename"] = f"{name_prefix}_{i}{modifier}.{file_type}"
                
                elif change_type == "name_and_date":
                    # Change filename and date
                    modifiers = ["_final", "_v2", "_copy", "_backup", "_archived"]
                    modifier = random.choice(modifiers)
                    variant["filename"] = f"{name_prefix}_{i}{modifier}.{file_type}"
                    
                    # Modified time a bit later
                    time_diff = random.randint(60, 86400 * 7)  # Between 1 minute and 7 days
                    variant["modified"] = modified + time_diff
                
                elif change_type == "size_change":
                    # Small size change with same checksum (e.g., for compressed files)
                    variant["size"] = max(1, int(size * random.uniform(0.98, 1.02)))
                    modifiers = ["_compressed", "_v2", "_updated"]
                    modifier = random.choice(modifiers)
                    variant["filename"] = f"{name_prefix}_{i}{modifier}.{file_type}"
                
                variant_files.append(variant)
                ground_truth_pairs.append((i, len(variant_files) - 1))
                
        # Add some challenging but valid matches (different name patterns but same content)
        valid_matches = int(num_files * 0.05)  # 5% valid matches with significantly different names
        for _ in range(valid_matches):
            i = random.randint(0, num_files - 1)
            orig_file = original_files[i]
            file_type = orig_file["extension"]
            
            # Create a differently formatted but valid match
            name_parts = orig_file["filename"].split("_")[0].split("-")
            if len(name_parts) > 1:
                # Rearrange name parts
                shuffled_name = "_".join(random.sample(name_parts, len(name_parts)))
            else:
                # Use different naming pattern
                alt_prefixes = ["backup", "copy", "archive", "export"]
                shuffled_name = f"{random.choice(alt_prefixes)}_{name_parts[0]}"
            
            valid_match = orig_file.copy()
            valid_match["filename"] = f"{shuffled_name}.{file_type}"
            
            # Small modification time difference
            time_diff = random.randint(60, 3600)  # Within an hour
            valid_match["modified"] = orig_file["modified"] + time_diff
            
            variant_files.append(valid_match)
            ground_truth_pairs.append((i, len(variant_files) - 1))
                
        # Add some false matches (similar names but different content)
        false_matches = int(num_files * 0.1)  # 10% false matches
        for _ in range(false_matches):
            i = random.randint(0, num_files - 1)
            file_type = original_files[i]["extension"]
            name_prefix = original_files[i]["filename"].split("_")[0]
            
            # Similar name but different checksum and size
            size = random.randint(1000, 10000)
            checksum = ''.join(random.choices('0123456789abcdef', k=12))
            modified = random.randint(1640995200, 1672531200)  # 2022 in seconds
            
            false_match = {
                "filename": f"{name_prefix}_{i}_similar.{file_type}",
                "extension": file_type,
                "size": size,
                "checksum": checksum,
                "modified": modified
            }
            
            variant_files.append(false_match)
            # No ground truth pair for false matches
            
        return original_files, variant_files, ground_truth_pairs
    
    def test_overall_accuracy(self):
        """Test the overall accuracy of the identity resolution system."""
        num_files = 100
        num_variants = 3
        
        # Generate test data
        originals, variants, ground_truth = self._generate_test_data(num_files, num_variants)
        
        # Run identity resolution
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        
        # Create a set of ground truth pairs for faster lookup
        ground_truth_set = {(orig_idx, var_idx) for orig_idx, var_idx in ground_truth}
        
        # Check every original against every variant
        threshold = 0.85  # Default threshold
        
        for orig_idx, orig_file in enumerate(originals):
            for var_idx, var_file in enumerate(variants):
                is_same, _ = multi_attribute_identity_resolution(orig_file, var_file, threshold=threshold)
                
                # Check against ground truth
                if is_same:
                    if (orig_idx, var_idx) in ground_truth_set:
                        true_positives += 1
                    else:
                        false_positives += 1
                else:
                    if (orig_idx, var_idx) in ground_truth_set:
                        false_negatives += 1
        
        # Calculate precision and recall
        total_predictions = true_positives + false_positives
        precision = true_positives / total_predictions if total_predictions > 0 else 0
        total_actual = true_positives + false_negatives
        recall = true_positives / total_actual if total_actual > 0 else 0
        
        # Calculate F1 score
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        # Calculate accuracy
        accuracy = true_positives / len(ground_truth) if ground_truth else 0
        
        # Assert that accuracy is 94% or better, matching the thesis claim
        self.assertGreaterEqual(accuracy, 0.94, 
                               f"Accuracy: {accuracy:.2f}, Precision: {precision:.2f}, Recall: {recall:.2f}")


if __name__ == "__main__":
    unittest.main()