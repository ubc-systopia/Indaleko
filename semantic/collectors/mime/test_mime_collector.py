"""
Test script for the MIME type collector.

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

import json
import os
import sys
import tempfile
import unittest
import uuid

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from semantic.collectors.mime.mime_collector import IndalekoSemanticMimeType

# pylint: enable=wrong-import-position


class IndalekoJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for Indaleko data models"""

    def default(self, obj):
        """Override default to handle UUID and datetime objects"""
        if isinstance(obj, uuid.UUID):
            return str(obj)
        from datetime import datetime

        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class TestMimeTypeCollector(unittest.TestCase):
    """Tests for the MIME type collector"""

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
            f.write(
                "<html><head><title>Test</title></head><body><h1>HTML Test</h1></body></html>",
            )

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

        # Create a mock PDF file (not a real PDF, just for testing)
        self.pdf_file = os.path.join(self.test_dir, "test.pdf")
        with open(self.pdf_file, "wb") as f:
            f.write(b"%PDF-1.7\n")
            f.write(b"Mock PDF file content")

        # Initialize collector
        self.mime_collector = IndalekoSemanticMimeType()

    def tearDown(self):
        """Remove test files"""
        for file_path in [
            self.text_file,
            self.html_file,
            self.json_file,
            self.bin_file,
            self.py_file,
            self.pdf_file,
        ]:
            if os.path.exists(file_path):
                os.remove(file_path)

        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)

    def test_mime_detection(self):
        """Test basic MIME type detection for various file types"""
        # Test text file
        text_mime = self.mime_collector.detect_mime_type(self.text_file)
        self.assertTrue(text_mime["mime_type"].startswith("text/"))
        self.assertEqual(text_mime["mime_type_from_extension"], "text/plain")

        # Test HTML file
        html_mime = self.mime_collector.detect_mime_type(self.html_file)
        self.assertTrue(
            html_mime["mime_type"].startswith("text/html")
            or html_mime["mime_type"] == "text/plain",
        )
        self.assertEqual(html_mime["mime_type_from_extension"], "text/html")

        # Test JSON file
        json_mime = self.mime_collector.detect_mime_type(self.json_file)
        self.assertTrue(
            json_mime["mime_type"].startswith("application/json")
            or json_mime["mime_type"].startswith("text/"),
        )
        self.assertEqual(json_mime["mime_type_from_extension"], "application/json")

        # Test binary file
        bin_mime = self.mime_collector.detect_mime_type(self.bin_file)
        self.assertIn(
            bin_mime["mime_type_from_extension"], ["application/octet-stream", None],
        )

        # Test Python file
        py_mime = self.mime_collector.detect_mime_type(self.py_file)
        self.assertTrue(py_mime["mime_type"].startswith("text/"))
        self.assertEqual(py_mime["mime_type_from_extension"], "text/x-python")

    def test_create_mime_record(self):
        """Test creating a MIME record from a file"""
        # Generate a test UUID
        test_uuid = uuid.uuid4()

        # Create a record
        record = self.mime_collector.create_mime_record(self.text_file, test_uuid)

        # Test record properties
        self.assertEqual(record.ObjectIdentifier, test_uuid)
        self.assertEqual(
            record.mime_type,
            self.mime_collector.detect_mime_type(self.text_file)["mime_type"],
        )
        self.assertGreaterEqual(
            len(record.SemanticAttributes), 3,
        )  # At least MIME type, confidence, and category

        # Serialize to verify it's valid
        serialized = record.model_dump()
        self.assertIn("mime_type", serialized)
        self.assertIn("confidence", serialized)
        self.assertIn("SemanticAttributes", serialized)

    def test_extension_matching(self):
        """Test confidence adjustment based on extension matching"""
        # Test match between extension and content
        html_result = self.mime_collector.detect_mime_type(self.html_file)

        # Test mismatch (binary file with .bin extension)
        bin_result = self.mime_collector.detect_mime_type(self.bin_file)

        # If extension and MIME match, confidence should be higher
        if (
            html_result["mime_type"] == "text/html"
            and html_result["mime_type_from_extension"] == "text/html"
        ):
            self.assertGreater(
                html_result["confidence"], 0.9,
            )  # High confidence when they match


def main():
    """Run the test suite"""
    unittest.main()


if __name__ == "__main__":
    main()
