#!/usr/bin/env python3
"""
Test script for the NL parser tool.

This script:
1. Creates an instance of the NL parser tool
2. Calls it with a simple query 
3. Reports detailed output and any errors
"""

import os
import sys
import time
from pathlib import Path

# Add the root directory to the Python path
current_path = Path(__file__).parent.resolve()
while not (Path(current_path) / "Indaleko.py").exists():
    current_path = Path(current_path).parent
os.environ["INDALEKO_ROOT"] = str(current_path)
sys.path.insert(0, str(current_path))

# Import the necessary components
from query.tools.translation.nl_parser import NLParserTool
from query.tools.base import ToolInput

def test_nl_parser():
    """Test the NL parser tool with a simple query."""
    try:
        print("Creating NL parser tool...")
        parser_tool = NLParserTool()
        
        # Create a simple query
        query = "Show me PDF files"
        print(f"Testing with query: '{query}'")
        
        # Create input data
        input_data = ToolInput(
            tool_name="nl_parser",
            parameters={"query": query},
            conversation_id="test-conversation",
            invocation_id="test-invocation"
        )
        
        # Execute the parser
        print("Executing NL parser...")
        start_time = time.time()
        result = parser_tool.execute(input_data)
        elapsed_time = time.time() - start_time
        
        # Report result
        print(f"Execution completed in {elapsed_time:.2f} seconds")
        print(f"Success: {result.success}")
        
        if result.success:
            print("\nParser output:")
            print(f"Intent: {result.result['intent']}")
            print(f"Entities: {result.result['entities']}")
            print(f"Categories: {result.result['categories']}")
        else:
            print(f"Error: {result.error}")
        
        return result.success
    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    success = test_nl_parser()
    sys.exit(0 if success else 1)