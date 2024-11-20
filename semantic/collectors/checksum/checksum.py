'''
This implements a prototype example of semantic extraction: checksums

Project Indaleko
Copyright (C) 2024 Tony Mason

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
'''

# standard imports
import hashlib
import mmap
import os
import sys
import unittest
import uuid

# third-party imports

# explicit imports
from typing import List, Dict, Union
from icecream import ic


if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# Indaleko imports
# pylint: disable=wrong-import-position
from IndalekoObject import IndalekoObject

from semantic.collectors.semantic_collector import SemanticCollector
from semantic.characteristics import SemanticDataCharacteristics
import semantic.recorders.checksum.characteristics as ChecksumDataCharacteristics
from semantic.collectors.checksum.data_model import SemanticChecksumDataModel
# pylint: enable=wrong-import-position


class IndalkeoSemanticChecksums(SemanticCollector):
    '''This class defines the semantic file checksums for the Indaleko project.'''

    def __init__(self, **kwargs):
        '''Initialize the semantic file checksums collector'''
        self._name = 'Semantic File Checksums'
        self._provider_id = uuid.UUID('de7ff1c7-2550-4cb3-9538-775f9464746e')
        self._checksum_data = None # SemanticChecksumDataModel(**SemanticChecksumDataModel.Config.json_schema_extra['example'])
        for key, values in kwargs.items():
            setattr(self, key, values)
        assert hasattr(self, 'name') or hasattr(self, 'provider_id'), \
            'The name or provider_id must be provided for the semantic file checksums collector.'
        
    def lookup_file(self) -> Union[IndalekoObject, None]:
        '''Lookup the file for the collector'''
        raise NotImplementedError('This method is not implemented yet.')
    
    def get_checksums_for_file(self) -> None:
        '''Get the checksums for the file'''
        # this is just a placeholder for now
        self._checksum_data = SemanticChecksumDataModel(**SemanticChecksumDataModel.Config.json_schema_extra['example'])
        raise NotImplementedError('This method is not implemented yet.')

    def get_collector_characteristics(self) -> List[SemanticDataCharacteristics]:
        '''Get the characteristics of the collector'''
        return [
            SemanticDataCharacteristics.SEMANTIC_DATA_CHECKSUMS,
            ChecksumDataCharacteristics.SEMANTIC_CHECKSUM_MD5,
            ChecksumDataCharacteristics.SEMANTIC_CHECKSUM_SHA1,
            ChecksumDataCharacteristics.SEMANTIC_CHECKSUM_SHA256,
            ChecksumDataCharacteristics.SEMANTIC_CHECKSUM_DROPBOX_SHA2,
        ]

    def get_collector_name(self) -> str:
        '''Get the name of the collector'''
        return self._name

    def get_collector_id(self) -> str:
        '''Get the ID of the collector'''
        return self._provider_id


    def retrieve_data(self, data_id: str) -> Dict:
        '''Retrieve the data for the collector'''
        raise NotImplementedError('This method is not implemented yet.')

    def get_collector_description(self) -> str:
        '''Get the description of the collector'''
        return '''This collector provides semantic checksums for files.'''

    def get_json_schema(self) -> dict:
        '''Get the JSON schema for the collector'''
        return {
            "type": "object",
            "properties": {
                "MD5": {"type": "string"},
                "SHA1": {"type": "string"},
                "SHA256": {"type": "string"},
                "Dropbox": {"type": "string"},
            },
            "required": ["MD5", "SHA1", "SHA256", "Dropbox"],
        }



# Define Dropbox checksum
class DropboxChecksum:
    def __init__(self):
        self.block_hashes = []

    def update(self, data):
        # Compute SHA256 hash of each 4MB block
        sha256 = hashlib.sha256()
        sha256.update(data)
        self.block_hashes.append(sha256.digest())

    def digest(self):
        # Concatenate all block hashes and compute final SHA256 hash
        final_sha256 = hashlib.sha256()
        final_sha256.update(b"".join(self.block_hashes))
        return final_sha256.hexdigest()

# Define chunk size and threshold for mmap usage
CHUNK_SIZE = 4 * 1024 * 1024  # 4MB per chunk
MMAP_THRESHOLD = 16 * 1024 * 1024  # 16MB file size threshold

def compute_checksums(file_path):
    # Initialize checksum calculators
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    dropbox = DropboxChecksum()

    file_size = os.path.getsize(file_path)

    if file_size < MMAP_THRESHOLD:
        # For small files, read the entire file at once
        with open(file_path, 'rb') as f:
            data = f.read()
            md5.update(data)
            sha1.update(data)
            sha256.update(data)
            dropbox.update(data)
    else:
        # For large files, use memory mapping and process chunks
        with open(file_path, 'rb') as f:
            with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                for offset in range(0, file_size, CHUNK_SIZE):
                    chunk = mmapped_file[offset:offset + min(CHUNK_SIZE, file_size - offset)]
                    md5.update(chunk)
                    sha1.update(chunk)
                    sha256.update(chunk)
                    dropbox.update(chunk)

    # Get digests for each checksum
    md5_hash = md5.hexdigest()
    sha1_hash = sha1.hexdigest()
    sha256_hash = sha256.hexdigest()
    dropbox_hash = dropbox.digest()

    return {
        'MD5': md5_hash,
        'SHA1': sha1_hash,
        'SHA256': sha256_hash,
        'Dropbox': dropbox_hash,
    }

# Unit tests
class TestChecksum(unittest.TestCase):
    def setUp(self):
        # Create test files
        with open("test_file_1.txt", "w", encoding='utf-8-sig') as f:
            f.write("Hello World!")
        with open("test_file_2.txt", "wb") as f:
            f.write(b"A" * 4 * 1024 * 1024)  # 4MB of 'A'

    def tearDown(self):
        # Clean up test files
        os.remove("test_file_1.txt")
        os.remove("test_file_2.txt")

    def test_small_file_checksums(self):
        '''Test small file operations'''
        expected_md5 = "65a8e27d8879283831b664bd8b7f0ad4"
        expected_sha1 = "2ef7bde608ce5404e97d5f042f95f89f1c232871"
        expected_sha256 = "a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b53a72f2bd90d5e33"
        expected_dropbox = "4bfe31fa6076540f83efcaf8b9f96a303ec40b9fdb10a9c0ff18b75e5f6b9b5e"

        checksums = compute_checksums("test_file_1.txt")
        self.assertEqual(checksums['MD5'], expected_md5)
        self.assertEqual(checksums['SHA1'], expected_sha1)
        self.assertEqual(checksums['SHA256'], expected_sha256)
        self.assertEqual(checksums['Dropbox'], expected_dropbox)

    def test_large_file_checksums(self):
        '''Test large file operations'''
        checksums = compute_checksums("test_file_2.txt")
        self.assertEqual(len(checksums['Dropbox']), 64)  # SHA-256 hash length in hex is 64 characters

if __name__ == "__main__":
    unittest.main()

# Example usage
if __name__ == "__main__":
    test_file_path = "example_file.txt"  # Replace with your file path
    for algo, checksum in compute_checksums(test_file_path).items():
        ic(f"{algo}: {checksum}")
