"""
Test script for the IndalekoSemanticChecksums collector.

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
import uuid
import tempfile
import json
from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Indaleko imports
from semantic.collectors.checksum.checksum import IndalekoSemanticChecksums, compute_checksums


def create_test_file(content):
    """Create a temporary test file with the given content."""
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.write(content.encode('utf-8'))
    temp_file.close()
    return temp_file.name


def test_checksum_collector():
    """Test the IndalekoSemanticChecksums collector."""
    # Create a test file
    test_content = "This is a test file for the checksum collector."
    test_file_path = create_test_file(test_content)
    
    try:
        # Create a unique identifier for this test file
        object_id = uuid.uuid4()
        
        # Initialize the collector
        collector = IndalekoSemanticChecksums()
        
        # Print collector information
        ic("Collector Name:", collector.get_collector_name())
        ic("Collector ID:", collector.get_collector_id())
        ic("Collector Description:", collector.get_collector_description())
        ic("Collector Characteristics:", [str(c) for c in collector.get_collector_characteristics()])
        
        # Compute checksums directly
        checksums = compute_checksums(test_file_path)
        ic("Computed Checksums:", checksums)
        
        # Get checksums using the collector
        checksum_record = collector.get_checksums_for_file(test_file_path, object_id)
        ic("Checksum Record:")
        
        # Format and print the checksum record JSON
        formatted_json = json.dumps(checksum_record, indent=2, default=str)
        print(formatted_json)
        
        # Verify that checksums match
        assert checksums["MD5"] == checksum_record["md5_checksum"]
        assert checksums["SHA1"] == checksum_record["sha1_checksum"]
        assert checksums["SHA256"] == checksum_record["sha256_checksum"]
        assert checksums["SHA512"] == checksum_record["sha512_checksum"]
        assert checksums["Dropbox"] == checksum_record["dropbox_checksum"]
        
        ic("All checksums verified successfully!")
        
    finally:
        # Clean up the test file
        os.unlink(test_file_path)


if __name__ == "__main__":
    test_checksum_collector()