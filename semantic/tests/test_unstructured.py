#!/usr/bin/env python3
"""
Indaleko Project - Tests for Unstructured Semantic Processor

This module contains unit tests for the unstructured semantic processor.

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
import shutil
import sys
import tempfile
import unittest
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from semantic.collectors.unstructured.data_models.input import (
    UnstructuredInputDataModel,
)
from semantic.collectors.unstructured.unstructured_collector import (
    UnstructuredCollector,
)
from semantic.processors.unstructured_processor import UnstructuredProcessor
from semantic.recorders.unstructured.unstructured_recorder import UnstructuredRecorder


class TestUnstructuredCollector(unittest.TestCase):
    """Test cases for the UnstructuredCollector class."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory
        self.temp_dir = tempfile.mkdtemp()

        # Create some test files
        self.create_test_files()

        # Configure the collector to skip Docker
        self.collector = UnstructuredCollector(
            skip_docker_pull=True,
            enable_performance_monitoring=False,
        )

    def tearDown(self):
        """Tear down test environment."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)

    def create_test_files(self):
        """Create test files in the temporary directory."""
        # Create a text file
        self.text_file = os.path.join(self.temp_dir, "test.txt")
        with open(self.text_file, "w") as f:
            f.write(
                "This is a test file.\nIt has multiple lines.\nFor testing purposes.",
            )

        # Create a PDF-like file (not a real PDF, just for testing)
        self.pdf_file = os.path.join(self.temp_dir, "test.pdf")
        with open(self.pdf_file, "w") as f:
            f.write("%PDF-1.7\nThis is a fake PDF file for testing purposes.\n%EOF")

    @patch("semantic.collectors.unstructured.unstructured_collector.subprocess.run")
    def test_get_collector_characteristics(self, mock_run):
        """Test get_collector_characteristics method."""
        # Set up mock to fake Docker availability
        mock_run.return_value = MagicMock(returncode=0)

        # Call the method
        characteristics = self.collector.get_collector_characteristics()

        # Verify the result
        self.assertEqual(characteristics.get_name(), self.collector.COLLECTOR_NAME)
        self.assertEqual(characteristics.get_provider_id(), self.collector.PROVIDER_ID)
        self.assertTrue(len(characteristics.get_supported_file_types()) > 0)

    @patch("semantic.collectors.unstructured.unstructured_collector.subprocess.run")
    def test_filter_files(self, mock_run):
        """Test _filter_files method."""
        # Set up mock to fake Docker availability
        mock_run.return_value = MagicMock(returncode=0)

        # Create input models
        input_models = [
            UnstructuredInputDataModel(
                ObjectIdentifier=uuid.uuid4(),
                LocalPath=self.text_file,
                ModificationTimestamp=datetime.fromtimestamp(
                    os.path.getmtime(self.text_file),
                    UTC,
                ),
                Length=os.path.getsize(self.text_file),
                Checksum=None,
            ),
            UnstructuredInputDataModel(
                ObjectIdentifier=uuid.uuid4(),
                LocalPath=self.pdf_file,
                ModificationTimestamp=datetime.fromtimestamp(
                    os.path.getmtime(self.pdf_file),
                    UTC,
                ),
                Length=os.path.getsize(self.pdf_file),
                Checksum=None,
            ),
            # Add a non-existent file
            UnstructuredInputDataModel(
                ObjectIdentifier=uuid.uuid4(),
                LocalPath=os.path.join(self.temp_dir, "nonexistent.txt"),
                ModificationTimestamp=datetime.now(UTC),
                Length=1024,
                Checksum=None,
            ),
            # Add a file that's too large
            UnstructuredInputDataModel(
                ObjectIdentifier=uuid.uuid4(),
                LocalPath=self.text_file,
                ModificationTimestamp=datetime.fromtimestamp(
                    os.path.getmtime(self.text_file),
                    UTC,
                ),
                Length=self.collector._max_file_size_mb * 1024 * 1024 + 1,  # Exceed the limit
                Checksum=None,
            ),
        ]

        # Mock _get_file_mime_type to return valid types
        with patch.object(self.collector, "_get_file_mime_type") as mock_mime:
            mock_mime.side_effect = lambda path: ("text/plain" if path.endswith(".txt") else "application/pdf")

            # Call the method
            filtered_files = self.collector._filter_files(input_models)

            # Verify the result
            self.assertEqual(len(filtered_files), 2)  # Only valid files should remain
            self.assertEqual(filtered_files[0].LocalPath, self.text_file)
            self.assertEqual(filtered_files[1].LocalPath, self.pdf_file)


class TestUnstructuredRecorder(unittest.TestCase):
    """Test cases for the UnstructuredRecorder class."""

    def setUp(self):
        """Set up test environment."""
        # Configure the recorder to skip database connection
        self.recorder = UnstructuredRecorder(
            skip_db_connection=True,
            enable_performance_monitoring=False,
        )

    def test_get_recorder_characteristics(self):
        """Test get_recorder_characteristics method."""
        # Call the method
        characteristics = self.recorder.get_recorder_characteristics()

        # Verify the result
        self.assertEqual(characteristics.get_name(), self.recorder.RECORDER_NAME)
        self.assertEqual(characteristics.get_provider_id(), self.recorder.RECORDER_ID)

    def test_get_collector_class_model(self):
        """Test get_collector_class_model method."""
        # Call the method
        collector_class = self.recorder.get_collector_class_model()

        # Verify the result
        self.assertEqual(collector_class, UnstructuredCollector)

    def test_create_attribute(self):
        """Test _create_attribute method."""
        # Call the method with various attribute types
        title_attr = self.recorder._create_attribute("Title", "Test Title")
        filename_attr = self.recorder._create_attribute("filename", "test.pdf")
        unknown_attr = self.recorder._create_attribute("unknown", "test value")

        # Verify the results
        self.assertEqual(
            title_attr.Identifier.Identifier,
            self.recorder.attribute_map["Title"],
        )
        self.assertEqual(title_attr.Value, "Test Title")

        self.assertEqual(
            filename_attr.Identifier.Identifier,
            self.recorder.attribute_map["filename"],
        )
        self.assertEqual(filename_attr.Value, "test.pdf")

        # Unknown attribute should use the SEM_UNUSED UUID
        self.assertEqual(
            unknown_attr.Identifier.Identifier,
            self.recorder.attribute_map.get(
                "unknown",
                "5cc55605-64f2-4491-9ff1-ddfe23e964b8",
            ),
        )
        self.assertEqual(unknown_attr.Value, "test value")


class TestUnstructuredProcessor(unittest.TestCase):
    """Test cases for the UnstructuredProcessor class."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory
        self.temp_dir = tempfile.mkdtemp()

        # Create some test files
        self.create_test_files()

        # Configure the processor to skip database and Docker
        self.processor = UnstructuredProcessor(
            skip_db_connection=True,
            skip_docker_pull=True,
            enable_performance_monitoring=False,
        )

        # Mock the collector's collect_data method
        self.mock_collector_collect = patch.object(
            self.processor._collector,
            "collect_data",
        ).start()

        # Mock the recorder's store_data method
        self.mock_recorder_store = patch.object(
            self.processor._recorder,
            "store_data",
        ).start()

    def tearDown(self):
        """Tear down test environment."""
        # Stop all patches
        patch.stopall()

        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)

    def create_test_files(self):
        """Create test files in the temporary directory."""
        # Create a text file
        self.text_file = os.path.join(self.temp_dir, "test.txt")
        with open(self.text_file, "w") as f:
            f.write(
                "This is a test file.\nIt has multiple lines.\nFor testing purposes.",
            )

        # Create a PDF-like file (not a real PDF, just for testing)
        self.pdf_file = os.path.join(self.temp_dir, "test.pdf")
        with open(self.pdf_file, "w") as f:
            f.write("%PDF-1.7\nThis is a fake PDF file for testing purposes.\n%EOF")

        # Create a subdirectory with more files
        self.sub_dir = os.path.join(self.temp_dir, "subdir")
        os.makedirs(self.sub_dir, exist_ok=True)

        self.sub_text_file = os.path.join(self.sub_dir, "subdir_test.txt")
        with open(self.sub_text_file, "w") as f:
            f.write("This is a test file in a subdirectory.")

    def test_process_pdf(self):
        """Test process_pdf method."""
        # Set up mock collector to return sample data
        sample_data = {
            "ObjectIdentifier": str(uuid.uuid4()),
            "LocalPath": self.pdf_file,
            "ModificationTimestamp": datetime.now(UTC).isoformat(),
            "Length": 100,
            "Unstructured": [
                {
                    "type": "Title",
                    "text": "Test Title",
                    "metadata": {
                        "filetype": "application/pdf",
                        "languages": ["eng"],
                        "page_number": 1,
                    },
                },
                {
                    "type": "NarrativeText",
                    "text": "This is the content of the PDF.",
                    "metadata": {
                        "filetype": "application/pdf",
                        "languages": ["eng"],
                        "page_number": 1,
                    },
                },
            ],
        }
        self.mock_collector_collect.return_value = [sample_data]

        # Set up mock recorder to return success
        self.mock_recorder_store.return_value = True

        # Mock mimetypes.guess_type to return PDF type
        with patch("mimetypes.guess_type") as mock_mime:
            mock_mime.return_value = ("application/pdf", None)

            # Call the method
            result = self.processor.process_pdf(self.pdf_file)

            # Verify the result
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["file"], self.pdf_file)

            # Check content extraction
            content = result.get("content", {})
            self.assertEqual(content.get("title"), "Test Title")
            self.assertEqual(len(content.get("text", [])), 2)
            self.assertEqual(content.get("text")[0], "Test Title")
            self.assertEqual(content.get("text")[1], "This is the content of the PDF.")

            # Verify mocks were called correctly
            mock_mime.assert_called_once_with(self.pdf_file)
            self.mock_collector_collect.assert_called_once()
            self.mock_recorder_store.assert_called_once_with([sample_data])

    def test_process_directory(self):
        """Test process_directory method."""
        # Set up mock collector to return sample data
        sample_data = [
            {
                "ObjectIdentifier": str(uuid.uuid4()),
                "LocalPath": self.pdf_file,
                "ModificationTimestamp": datetime.now(UTC).isoformat(),
                "Length": 100,
                "Unstructured": [
                    {
                        "type": "Title",
                        "text": "Test Title",
                        "metadata": {
                            "filetype": "application/pdf",
                            "languages": ["eng"],
                        },
                    },
                ],
            },
        ]
        self.mock_collector_collect.return_value = sample_data

        # Set up mock recorder to return success
        self.mock_recorder_store.return_value = True

        # Mock _find_files to return test files
        with patch.object(self.processor, "_find_files") as mock_find_files:
            mock_find_files.return_value = [self.pdf_file, self.text_file]

            # Call the method
            result = self.processor.process_directory(self.temp_dir)

            # Verify the result
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["files_found"], 2)
            self.assertEqual(result["files_processed"], 1)

            # Verify mocks were called correctly
            mock_find_files.assert_called_once_with(self.temp_dir, True, None, None)
            self.mock_collector_collect.assert_called_once()
            self.mock_recorder_store.assert_called_once_with(sample_data)

    def test_find_files(self):
        """Test _find_files method."""
        # Mock _is_valid_file to control which files are valid
        with patch.object(self.processor, "_is_valid_file") as mock_is_valid:
            # Make only PDF files valid
            mock_is_valid.side_effect = lambda path, exts, size: path.endswith(".pdf")

            # Call the method with recursive=True
            files = self.processor._find_files(self.temp_dir, True, [".pdf"], None)

            # Verify the result
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0], self.pdf_file)

            # Call the method with recursive=False
            files = self.processor._find_files(self.temp_dir, False, [".pdf"], None)

            # Verify the result (should not include files in subdirectories)
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0], self.pdf_file)


if __name__ == "__main__":
    unittest.main()
