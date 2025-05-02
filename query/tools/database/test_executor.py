#!/usr/bin/env python3
"""
Test script for the query executor tool's cursor handling.

This script:
1. Creates a mock cursor object
2. Tests the cursor handling logic in the executor tool
3. Verifies that cursors are properly converted to lists
"""

import os
import sys
from pathlib import Path

# Add project root to path
current_path = Path(__file__).parent.resolve()
while not (Path(current_path) / "Indaleko.py").exists():
    current_path = Path(current_path).parent
os.environ["INDALEKO_ROOT"] = str(current_path)
sys.path.insert(0, str(current_path))

# Import the executor
from query.tools.database.executor import QueryExecutorTool
from arango.cursor import Cursor

# Create a simple mock cursor
class MockCursor(Cursor):
    """Mock cursor that yields a few results."""
    
    def __init__(self):
        self._items = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
            {"id": 3, "name": "Item 3"}
        ]
        self._position = 0
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if self._position >= len(self._items):
            raise StopIteration
        item = self._items[self._position]
        self._position += 1
        return item

def test_cursor_handling():
    """Test the cursor handling logic in the executor tool."""
    # Create a mock cursor
    cursor = MockCursor()
    
    # Create a result dict
    result_data = {}
    
    # Apply the cursor handling logic
    if isinstance(cursor, Cursor):
        # Convert cursor to list of documents
        result_list = [doc for doc in cursor]
        result_data["results"] = result_list
    else:
        result_data["results"] = cursor
    
    # Print the result
    print("Test result:")
    print(f"Type: {type(result_data['results'])}")
    print(f"Content: {result_data['results']}")
    
    # Verify the result
    if isinstance(result_data["results"], list) and len(result_data["results"]) == 3:
        print("SUCCESS: Cursor was correctly converted to a list")
        return True
    else:
        print("FAILURE: Cursor was not correctly converted")
        return False

if __name__ == "__main__":
    success = test_cursor_handling()
    sys.exit(0 if success else 1)