#!/usr/bin/env python3
"""
Test script for OpenAI connector.

This script:
1. Loads the OpenAI API key
2. Creates an instance of the OpenAI connector
3. Makes a simple API call to test connectivity
4. Reports the result
"""

import configparser
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

# Import the OpenAI connector
from query.utils.llm_connector.openai_connector import OpenAIConnector

def get_api_key(api_key_file: str) -> str:
    """Get the OpenAI API key from the config file."""
    if not os.path.exists(api_key_file):
        print(f"API key file not found: {api_key_file}")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(api_key_file, encoding="utf-8-sig")

    if "openai" not in config or "api_key" not in config["openai"]:
        print("OpenAI API key not found in config file")
        sys.exit(1)

    openai_key = config["openai"]["api_key"]

    # Clean up the key if it has quotes
    if openai_key[0] in ["'", '"'] and openai_key[-1] in ["'", '"']:
        openai_key = openai_key[1:-1]

    return openai_key

def test_openai_connection():
    """Test the OpenAI connection with a simple API call."""
    try:
        # Load the API key
        config_dir = os.path.join(os.environ.get("INDALEKO_ROOT"), "config")
        api_key_file = os.path.join(config_dir, "openai-key.ini")
        api_key = get_api_key(api_key_file)
        print(f"API key loaded from {api_key_file}")

        # Create the OpenAI connector
        model = "gpt-4o-mini"  # Use a smaller model for testing
        print(f"Creating OpenAI connector with model: {model}")
        connector = OpenAIConnector(api_key=api_key, model=model)

        # Make a simple API call
        print("Making a simple text generation API call...")
        start_time = time.time()
        response = connector.generate_text(
            prompt="Hello, this is a test message. Please respond with a short greeting.",
            max_tokens=20,
            temperature=0.0
        )
        elapsed_time = time.time() - start_time

        # Report result
        print(f"API call successful! Time taken: {elapsed_time:.2f} seconds")
        print(f"Response: {response}")

        return True
    except (GeneratorExit , RecursionError , MemoryError , NotImplementedError ) as e:
        print(f"Error testing OpenAI connection: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    success = test_openai_connection()
    sys.exit(0 if success else 1)
