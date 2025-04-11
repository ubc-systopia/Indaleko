"""
Test script for the MIME type recorder.

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
import json
import unittest
import tempfile
import uuid
from pathlib import Path

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from semantic.recorders.mime.recorder import MimeTypeRecorder
# pylint: enable=wrong-import-position


class TestMimeTypeRecorder(unittest.TestCase):
    """Tests for the MIME type recorder"""

    def setUp(self):
        """Create test files with different types"""
        self.test_dir = tempfile.mkdtemp()
        
        # Create a text file
        self.text_file = os.path.join(self.test_dir, "test.txt")
        with open(self.text_file, "w", encoding="utf-8") as f:
            f.write("This is a text file for MIME type detection testing.")
            
        # Create an HTML file
        self.html_file = os.path.join(self.test_dir, "test.html")
        with open(self.html_file, "w", encoding="utf-8") as f:
            f.write("<html><head><title>Test</title></head><body><h1>HTML Test</h1></body></html>")
            
        # Create a JSON file
        self.json_file = os.path.join(self.test_dir, "test.json")
        with open(self.json_file, "w", encoding="utf-8") as f:
            f.write('{"test": "This is a JSON file"}')
            
        # Create a binary file
        self.bin_file = os.path.join(self.test_dir, "test.bin")
        with open(self.bin_file, "wb") as f:
            f.write(os.urandom(1024))  # 1KB of random data
            
        # Create a Python script
        self.py_file = os.path.join(self.test_dir, "test.py")
        with open(self.py_file, "w", encoding="utf-8") as f:
            f.write('print("Hello, world!")')
            
        # Create a subdirectory with more files
        self.subdir = os.path.join(self.test_dir, "subdir")
        os.makedirs(self.subdir, exist_ok=True)
        
        self.sub_text_file = os.path.join(self.subdir, "subdir_test.txt")
        with open(self.sub_text_file, "w", encoding="utf-8") as f:
            f.write("This is a text file in a subdirectory.")
            
        # Initialize recorder
        self.mime_recorder = MimeTypeRecorder()
        
    def tearDown(self):
        """Remove test files"""
        for file_path in [self.text_file, self.html_file, self.json_file, 
                        self.bin_file, self.py_file, self.sub_text_file]:
            if os.path.exists(file_path):
                os.remove(file_path)
                
        if os.path.exists(self.subdir):
            os.rmdir(self.subdir)
                
        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)
            
    def test_process_file(self):
        """Test processing a single file"""
        # Process a text file
        result = self.mime_recorder.process_file(self.text_file)
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertIn("mime_type", result)
        self.assertIn("confidence", result)
        self.assertTrue(result["mime_type"].startswith("text/"))
        
        # Process a binary file
        result = self.mime_recorder.process_file(self.bin_file)
        self.assertIsNotNone(result)
        
        # Process a non-existent file
        result = self.mime_recorder.process_file("non_existent_file.txt")
        self.assertIsNone(result)
        
    def test_batch_process(self):
        """Test batch processing multiple files"""
        # Create a list of files
        file_list = [self.text_file, self.html_file, self.json_file, self.bin_file, self.py_file]
        
        # Process the batch
        results = self.mime_recorder.batch_process_files(file_list)
        
        # Verify results
        self.assertEqual(len(results), len(file_list))
        
        # Verify each result has correct structure
        for result in results:
            self.assertIn("mime_type", result)
            self.assertIn("confidence", result)
            self.assertIn("mime_type_from_extension", result)
            
    def test_process_directory(self):
        """Test processing a directory"""
        # Process the main directory without recursion
        results = self.mime_recorder.process_directory(self.test_dir, recursive=False)
        self.assertEqual(len(results), 5)  # 5 files in the main directory
        
        # Process with recursion
        results = self.mime_recorder.process_directory(self.test_dir, recursive=True)
        self.assertEqual(len(results), 6)  # 5 files + 1 file in subdirectory
        
        # Process with extension filter
        results = self.mime_recorder.process_directory(self.test_dir, 
                                                    recursive=True, 
                                                    file_extensions=[".txt"])
        self.assertEqual(len(results), 2)  # 2 .txt files in total
        
    def test_export_results(self):
        """Test exporting results to JSON"""
        # Process some files
        file_list = [self.text_file, self.html_file]
        results = self.mime_recorder.batch_process_files(file_list)
        
        # Export results
        output_file = os.path.join(self.test_dir, "test_results.json")
        self.mime_recorder.export_results_to_json(results, output_file)
        
        # Verify output file exists
        self.assertTrue(os.path.exists(output_file))
        
        # Read the file and verify it contains valid JSON
        with open(output_file, "r", encoding="utf-8") as f:
            exported_data = json.load(f)
            
        self.assertEqual(len(exported_data), len(results))
        self.assertIn("mime_type", exported_data[0])
        
        # Clean up
        os.remove(output_file)
        
    def test_summarize_results(self):
        """Test generating a summary of results"""
        # Process some files
        file_list = [self.text_file, self.html_file, self.json_file, self.bin_file, self.py_file]
        results = self.mime_recorder.batch_process_files(file_list)
        
        # Generate summary
        summary = self.mime_recorder.summarize_results(results)
        
        # Verify summary structure
        self.assertIn("total_files", summary)
        self.assertIn("mime_type_counts", summary)
        self.assertIn("avg_confidence", summary)
        self.assertIn("extension_match_percentage", summary)
        
        # Verify counts
        self.assertEqual(summary["total_files"], len(file_list))
        
        # Verify the MIME type counts sum to the total files
        total_mime_count = sum(summary["mime_type_counts"].values())
        self.assertEqual(total_mime_count, summary["total_files"])


def main():
    """Run the test suite"""
    unittest.main()
    

if __name__ == "__main__":
    main()