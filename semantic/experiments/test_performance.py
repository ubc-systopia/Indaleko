"""
Test script for the semantic extractor performance monitoring framework.

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

import logging
import os
import sys
import tempfile
import time
import unittest

# Import path setup
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from semantic.collectors.mime.mime_collector import IndalekoSemanticMimeType
from semantic.performance_monitor import (
    SemanticExtractorPerformance,
    monitor_semantic_extraction,
)

# pylint: enable=wrong-import-position


class TestPerformanceMonitor(unittest.TestCase):
    """Test cases for performance monitoring."""

    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()

        # Create test files
        self.test_files = []
        for i in range(5):
            file_path = os.path.join(self.test_dir, f"test_{i}.txt")
            with open(file_path, "w") as f:
                # Create files of increasing size
                f.write("A" * (1024 * (i + 1)))
            self.test_files.append(file_path)

        # Create binary file
        self.binary_file = os.path.join(self.test_dir, "test.bin")
        with open(self.binary_file, "wb") as f:
            f.write(os.urandom(1024))
        self.test_files.append(self.binary_file)

        # Reset monitor
        self.monitor = SemanticExtractorPerformance(record_to_db=False)
        self.monitor.reset_stats()

    def tearDown(self):
        """Clean up test environment."""
        # Remove test files
        for file_path in self.test_files:
            if os.path.exists(file_path):
                os.remove(file_path)

        if os.path.exists(self.test_dir):
            os.rmdir(self.test_dir)

    def test_monitor_init(self):
        """Test monitor initialization."""
        self.assertTrue(self.monitor.is_enabled())
        self.assertEqual(self.monitor._stats["total_files"], 0)
        self.assertEqual(self.monitor._stats["total_bytes"], 0)
        self.assertEqual(self.monitor._stats["total_processing_time"], 0.0)

    def test_monitor_disable(self):
        """Test disabling the monitor."""
        self.monitor.disable()
        self.assertFalse(self.monitor.is_enabled())

        # Start monitoring
        context = self.monitor.start_monitoring("test", file_path=self.test_files[0])
        self.assertFalse(context.get("enabled", True))

        # Stop monitoring
        metrics = self.monitor.stop_monitoring(context)
        self.assertEqual(metrics, {})

        # Re-enable
        self.monitor.enable()
        self.assertTrue(self.monitor.is_enabled())

    def test_manual_monitoring(self):
        """Test manually using the monitor."""
        file_path = self.test_files[0]
        file_size = os.path.getsize(file_path)

        # Start monitoring
        context = self.monitor.start_monitoring(
            "test_manual", file_path=file_path, file_size=file_size,
        )

        # Do some work
        time.sleep(0.1)

        # Stop monitoring
        metrics = self.monitor.stop_monitoring(context, success=True)

        # Check metrics
        self.assertGreater(metrics["elapsed_time"], 0.0)
        self.assertEqual(metrics["file_path"], file_path)
        self.assertEqual(metrics["file_size"], file_size)
        self.assertTrue(metrics["success"])

    def test_decorator(self):
        """Test the monitoring decorator."""

        @monitor_semantic_extraction(extractor_name="TestDecorator")
        def test_function(file_path):
            """Test function for the decorator."""
            time.sleep(0.1)
            return {"result": "test", "file_path": file_path}

        # Call the function
        result = test_function(self.test_files[0])

        # Check result
        self.assertEqual(result["result"], "test")

        # Check stats
        stats = self.monitor.get_stats()
        self.assertEqual(stats["total_files"], 1)
        self.assertGreater(stats["total_processing_time"], 0.0)
        self.assertIn("TestDecorator", stats["extractor_stats"])

    def test_mime_detector_integration(self):
        """Test integration with MIME detector."""
        mime_detector = IndalekoSemanticMimeType()

        # Start monitoring
        context = self.monitor.start_monitoring(
            "mime_detector", file_path=self.test_files[0],
        )

        # Detect MIME type
        mime_data = mime_detector.detect_mime_type(self.test_files[0])

        # Stop monitoring
        metrics = self.monitor.stop_monitoring(
            context, success=True, additional_data=mime_data,
        )

        # Check metrics
        self.assertGreater(metrics["elapsed_time"], 0.0)
        self.assertEqual(metrics["file_path"], self.test_files[0])

        # Check stats
        stats = self.monitor.get_stats()
        self.assertEqual(stats["total_files"], 1)
        self.assertGreater(stats["total_processing_time"], 0.0)
        self.assertIn("mime_detector", stats["extractor_stats"])

    def test_multiple_files(self):
        """Test processing multiple files."""
        mime_detector = IndalekoSemanticMimeType()

        # Process all test files
        for file_path in self.test_files:
            context = self.monitor.start_monitoring(
                "mime_detector",
                file_path=file_path,
                file_size=os.path.getsize(file_path),
            )

            mime_data = mime_detector.detect_mime_type(file_path)

            self.monitor.stop_monitoring(
                context, success=True, additional_data=mime_data,
            )

        # Check stats
        stats = self.monitor.get_stats()
        self.assertEqual(stats["total_files"], len(self.test_files))
        self.assertGreater(stats["total_processing_time"], 0.0)
        self.assertGreater(stats["total_bytes"], 0)

        # Check derived metrics
        self.assertGreater(stats["files_per_second"], 0.0)
        self.assertGreater(stats["bytes_per_second"], 0.0)

    def test_failure_handling(self):
        """Test handling of failures."""
        # Start monitoring
        context = self.monitor.start_monitoring(
            "test_failure", file_path="nonexistent_file.txt",
        )

        # Stop monitoring with failure
        metrics = self.monitor.stop_monitoring(context, success=False)

        # Check metrics
        self.assertGreater(metrics["elapsed_time"], 0.0)
        self.assertEqual(metrics["file_path"], "nonexistent_file.txt")
        self.assertFalse(metrics["success"])

        # Check stats
        stats = self.monitor.get_stats()
        self.assertEqual(stats["total_files"], 1)
        self.assertIn("test_failure", stats["extractor_stats"])
        self.assertEqual(stats["extractor_stats"]["test_failure"]["success_count"], 0)
        self.assertEqual(stats["extractor_stats"]["test_failure"]["error_count"], 1)

    def test_decorated_exception(self):
        """Test decorator with function that raises exception."""

        @monitor_semantic_extraction(extractor_name="TestException")
        def failing_function(file_path):
            """Test function that raises an exception."""
            time.sleep(0.1)
            raise ValueError("Test exception")

        # Call the function and expect exception
        with self.assertRaises(ValueError):
            failing_function(self.test_files[0])

        # Check stats
        stats = self.monitor.get_stats()
        self.assertEqual(stats["total_files"], 1)
        self.assertIn("TestException", stats["extractor_stats"])
        self.assertEqual(stats["extractor_stats"]["TestException"]["success_count"], 0)
        self.assertEqual(stats["extractor_stats"]["TestException"]["error_count"], 1)


def main():
    """Run the tests."""
    unittest.main()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run tests
    main()
