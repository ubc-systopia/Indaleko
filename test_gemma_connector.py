"""
Test script for the Gemma LLM connector.

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

import argparse
import sys
import time

from icecream import ic

from query.utils.llm_connector.factory import LLMConnectorFactory
from query.utils.llm_connector.gemma_connector import GemmaConnector


def main():
    """Main function."""
    # Parse arguments
    parser = argparse.ArgumentParser(description="Test Gemma LLM connector")
    parser.add_argument(
        "--llm",
        default="gemma",
        choices=["openai", "gemma", "random"],
        help="The LLM connector to use",
    )
    parser.add_argument("--base-url", default="http://localhost:1234/v1", help="The base URL for the LM Studio API")
    parser.add_argument("--model", default="Gemma", help="The model to use")
    parser.add_argument("--prompt", default="What is Indaleko used for?", help="The prompt to test with")

    args = parser.parse_args()

    # Create connector
    if args.llm == "gemma":
        # Create directly
        connector = GemmaConnector(base_url=args.base_url, model=args.model)
    else:
        # Create using factory
        connector = LLMConnectorFactory.create_connector(connector_type=args.llm)

    ic(f"Using LLM connector: {connector.get_llm_name()}")

    # Test basic text generation
    print("\n--- Testing generate_text ---")
    start_time = time.time()
    response = connector.generate_text(args.prompt)
    elapsed = time.time() - start_time
    print(f"Response ({elapsed:.2f}s):")
    print(response)

    # Test extract_keywords
    print("\n--- Testing extract_keywords ---")
    start_time = time.time()
    keywords = connector.extract_keywords(args.prompt)
    elapsed = time.time() - start_time
    print(f"Keywords ({elapsed:.2f}s):")
    print(keywords)

    # Test summarize_text
    print("\n--- Testing summarize_text ---")
    sample_text = """
    Indaleko is a unified personal index system that helps users find,
    understand, and manage their data across multiple storage services and devices.
    It collects metadata from various sources like file systems, cloud storage,
    and collaborative tools, then provides a unified interface for searching and
    analyzing this data.
    """
    start_time = time.time()
    summary = connector.summarize_text(sample_text, max_length=25)
    elapsed = time.time() - start_time
    print(f"Summary ({elapsed:.2f}s):")
    print(summary)

    # Test classify_text
    print("\n--- Testing classify_text ---")
    categories = ["search", "analysis", "organization", "storage"]
    start_time = time.time()
    classification = connector.classify_text(args.prompt, categories)
    elapsed = time.time() - start_time
    print(f"Classification ({elapsed:.2f}s):")
    print(classification)

    print("\nAll tests completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
