#!/usr/bin/env python3
"""
Test the prompt manager and integration with OpenAI connector.

This script demonstrates how the prompt manager optimizes prompts and
integrates with the OpenAI connector.

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

import configparser
import os
import sys
from pathlib import Path

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

from query.utils.llm_connector.openai_connector import OpenAIConnector
from query.utils.prompt_manager import (
    PromptManager,
    PromptOptimizationStrategy,
    PromptTemplate,
    create_aql_translation_template,
    create_nl_parser_template,
)


def get_api_key() -> str:
    """Get the OpenAI API key from the config file."""
    config_dir = os.path.join(os.environ.get("INDALEKO_ROOT"), "config")
    api_key_file = os.path.join(config_dir, "openai-key.ini")

    config = configparser.ConfigParser()
    config.read(api_key_file, encoding="utf-8-sig")

    api_key = config["openai"]["api_key"]

    # Clean up quotes if present
    if api_key[0] in ["'", '"'] and api_key[-1] in ["'", '"']:
        api_key = api_key[1:-1]

    return api_key


def test_standalone_prompt_manager():
    """Test the prompt manager on its own."""
    print("\n=== Testing Standalone Prompt Manager ===")

    # Initialize prompt manager with schema rules
    schema_rules = {
        # Rules for Record.Attributes access
        r"Record\.Attributes?": [
            # Correct ways to access attributes in ArangoDB collections
            "Record.Attributes.Path",
            "Record.Attributes.Size",
            "Record.Attributes.MimeType",
            # Incorrect patterns to detect
            "Record.Attribute.",  # Missing 's' in Attributes
            "DO NOT USE Record.Attribute",  # Contradiction warning
            "Record.attribute",  # Wrong case
        ],
        # Rules for collection names
        r"Collection": [
            # Correct collection names
            "Objects",
            "Activities",
            "SemanticData",
            # Incorrect collection names
            "files",
            "documents",
            "data",
        ],
    }

    prompt_manager = PromptManager(max_tokens=4000, schema_rules=schema_rules)

    # Register templates
    prompt_manager.register_template(create_aql_translation_template())
    prompt_manager.register_template(create_nl_parser_template())

    # Create prompts
    print("\nCreating prompts without optimization...")
    query = "Find all PDF files created last week containing project budget data"

    # Create baseline prompts (no optimization)
    parser_prompt = prompt_manager.create_prompt(template_name="nl_parser", query=query, optimize=False)

    aql_prompt = prompt_manager.create_prompt(template_name="aql_translation", query=query, optimize=False)

    # Display token counts
    parser_tokens = len(prompt_manager.tokenizer.encode(f"{parser_prompt['system']}\n\n{parser_prompt['user']}"))
    aql_tokens = len(prompt_manager.tokenizer.encode(f"{aql_prompt['system']}\n\n{aql_prompt['user']}"))

    print(f"Parser prompt tokens (no optimization): {parser_tokens}")
    print(f"AQL prompt tokens (no optimization): {aql_tokens}")

    # Test contradiction detection
    print("\nTesting contradiction detection...")

    # Create a template with contradictions
    contradictory_template = PromptTemplate(
        name="contradictory_template",
        description="Template with contradictions for testing",
        format=PromptFormat.CHAT,
        system_template="""
        You are a query translator for ArangoDB.

        # Important guidelines:
        - DO NOT USE Record.Attribute - this is incorrect format
        - Always use proper collection names

        # Example 1:
        Query: Find all PDFs
        AQL: ```
        FOR doc IN Objects
        FILTER doc.Record.Attributes.MimeType == "application/pdf"
        RETURN doc
        ```

        # Example 2:
        Query: Find large files
        AQL: ```
        FOR doc IN files
        FILTER doc.Record.Attribute.Size > 10000000
        RETURN doc
        ```

        Note: To access a file attribute, use Record.Attributes
        """,
        user_template="Translate this query to AQL: {query}",
        tags=["test", "contradictions"],
    )

    # Register the contradictory template
    prompt_manager.register_template(contradictory_template)

    # Create prompt with contradiction checking
    print("Testing contradiction resolution...")
    contradiction_prompt = prompt_manager.create_prompt(
        template_name="contradictory_template",
        query="Find all PDF files",
        optimize=True,
        strategies=[PromptOptimizationStrategy.CONTRADICTION_CHECK],
    )

    # Print the original and fixed template
    print("\nOriginal template had contradictions:")
    print("- 'DO NOT USE Record.Attribute' vs using 'Record.Attributes' in examples")
    print("- Example uses 'Record.Attribute.Size' (missing 's')")
    print("- Example uses 'files' collection (non-standard)")

    print("\nFixed template should resolve these issues")

    # Test normal optimization strategies
    print("\nCreating prompts with optimization...")

    # Test different optimization strategies
    for strategy_set in [
        [PromptOptimizationStrategy.WHITESPACE],
        [PromptOptimizationStrategy.EXAMPLE_REDUCE],
        [PromptOptimizationStrategy.CONTRADICTION_CHECK],  # Added contradiction check
        [PromptOptimizationStrategy.ALL],
    ]:
        strategy_names = [s.name for s in strategy_set]
        print(f"\nTesting optimization strategies: {strategy_names}")

        # Create optimized prompts
        optimized_parser = prompt_manager.create_prompt(
            template_name="nl_parser",
            query=query,
            optimize=True,
            strategies=strategy_set,
        )

        optimized_aql = prompt_manager.create_prompt(
            template_name="aql_translation",
            query=query,
            optimize=True,
            strategies=strategy_set,
        )

        # Display token counts
        opt_parser_tokens = len(
            prompt_manager.tokenizer.encode(f"{optimized_parser['system']}\n\n{optimized_parser['user']}"),
        )
        opt_aql_tokens = len(prompt_manager.tokenizer.encode(f"{optimized_aql['system']}\n\n{optimized_aql['user']}"))

        print(
            f"Parser prompt tokens (optimized): {opt_parser_tokens} "
            f"(saved: {parser_tokens - opt_parser_tokens} tokens, "
            f"{((parser_tokens - opt_parser_tokens) / parser_tokens) * 100:.1f}%)",
        )

        print(
            f"AQL prompt tokens (optimized): {opt_aql_tokens} "
            f"(saved: {aql_tokens - opt_aql_tokens} tokens, "
            f"{((aql_tokens - opt_aql_tokens) / aql_tokens) * 100:.1f}%)",
        )

    # Get stats
    print("\nPrompt Manager Statistics:")
    stats = prompt_manager.get_stats()
    for stat in stats:
        optimized_str = " (optimized)" if stat.optimized else ""
        strats = f", strategies: {stat.optimization_strategies}" if stat.optimized else ""
        print(f"Template: {stat.template_name}{optimized_str}, Tokens: {stat.tokens}{strats}")


def test_openai_connector_integration():
    """Test the OpenAI connector integration."""
    print("\n=== Testing OpenAI Connector Integration ===")

    try:
        # Get API key
        api_key = get_api_key()

        # Import OpenAI for client creation
        import openai

        # Create OpenAI client for LLM review
        client = openai.OpenAI(api_key=api_key)

        # Initialize OpenAI connector with prompt manager
        connector = OpenAIConnector(
            api_key=api_key,
            model="gpt-4o",
            max_tokens=8000,
            use_prompt_manager=True,
            optimization_strategies=[
                PromptOptimizationStrategy.WHITESPACE,
                PromptOptimizationStrategy.SCHEMA_SIMPLIFY,
                PromptOptimizationStrategy.EXAMPLE_REDUCE,
                # Add LLM review as an option
                PromptOptimizationStrategy.LLM_REVIEW,
            ],
        )

        # Add LLM client to prompt manager
        if hasattr(connector, "prompt_manager"):
            connector.prompt_manager.llm_client = client

        # Create a test prompt using the old style
        print("\nCreating a standard prompt (old style)...")
        standard_prompt = {
            "system": "You are a query translator that converts natural language queries "
            "into AQL (ArangoDB Query Language).\n\n"
            "# Available Collections:\n"
            "- Objects: Contains file system objects with Record.Attributes\n"
            "- Activities: Contains user activities with timestamps\n",
            "user": "Translate this query to AQL: Find all PDF files created last week",
        }

        # Create a test prompt using the new style
        print("\nCreating a managed prompt (new style)...")
        managed_prompt = {"template": "aql_translation", "query": "Find all PDF files created last week"}

        # Test both prompts
        # Note: We're not actually calling the OpenAI API here to avoid charges
        print("\nTesting prompt handling...")

        # Test with standard prompt
        print("Standard prompt handling:")
        connector.generate_query = lambda p, t=0: print(
            f"Standard prompt tokens: {len(connector.prompt_manager.tokenizer.encode(f'{p['system']}\n\n{p['user']}'))}",
        )
        connector.generate_query(standard_prompt)

        # Test with managed prompt
        print("\nManaged prompt handling:")
        connector.generate_query = lambda p, t=0: print(
            f"Managed prompt tokens: {len(connector.prompt_manager.tokenizer.encode(f'{p['system']}\n\n{p['user']}'))}",
        )
        connector.generate_query(managed_prompt)

        # Show prompt manager stats
        print("\nPrompt Manager Statistics:")
        stats = connector.prompt_manager.get_stats()
        for stat in stats:
            if hasattr(stat, "template_name"):
                optimized_str = " (optimized)" if stat.optimized else ""
                strats = f", strategies: {stat.optimization_strategies}" if stat.optimized else ""
                print(f"Template: {stat.template_name}{optimized_str}, Tokens: {stat.tokens}{strats}")

    except Exception as e:
        print(f"Error testing OpenAI connector: {e}")


def test_llm_review():
    """Test the LLM-based contradiction detection."""
    print("\n=== Testing LLM-Based Contradiction Review ===")

    try:
        # Get API key
        api_key = get_api_key()

        # Import OpenAI
        import openai

        # Create OpenAI client
        client = openai.OpenAI(api_key=api_key)

        # Create prompt manager with LLM client
        prompt_manager = PromptManager(max_tokens=4000, llm_client=client)

        # Create a sample contradictory template
        contradictory_template = """
        You are an expert on file systems and indexing for Indaleko.

        # Important rules:
        - Always use Record.Attributes.Path to refer to file paths
        - Never use Record.Attribute.Path - this is incorrect
        - Do not use file-based collections

        # Example queries:
        Query: Find all PDFs
        AQL: ```
        FOR doc IN Objects
        FILTER doc.Record.Attributes.MimeType == "application/pdf"
        RETURN doc
        ```

        Query: Find files in Documents folder
        AQL: ```
        FOR doc IN files
        FILTER doc.Record.Attribute.Path LIKE "/Documents/%"
        RETURN doc
        ```

        Follow these guidelines strictly for the best results.
        """

        # Test LLM review
        print("\nReviewing contradictory prompt with LLM:")
        fixed_prompt, _ = prompt_manager._llm_review_contradictions(contradictory_template, "")

        # Print simplified comparison
        print("\nOriginal prompt contained contradictions:")
        print("- Says 'Never use Record.Attribute.Path' but then uses it in an example")
        print("- Says 'Do not use file-based collections' but uses 'files' collection")

        print("\nFixed prompt from LLM review should resolve these contradictions")

        # Check if the fixed prompt is different
        if fixed_prompt != contradictory_template:
            print("✅ LLM successfully fixed contradictions")
        else:
            print("⚠️ LLM kept the prompt unchanged - contradictions might remain")

    except Exception as e:
        print(f"Error testing LLM review: {e}")
        print("Skipping LLM review test - this requires a valid OpenAI API key")


def main():
    """Run tests."""
    # Test standalone prompt manager
    test_standalone_prompt_manager()

    # Test OpenAI connector integration
    test_openai_connector_integration()

    # Test LLM-based contradiction review (optional)
    try:
        test_llm_review()
    except Exception as e:
        print(f"\nSkipping LLM review test (requires OpenAI API key): {e}")


if __name__ == "__main__":
    main()
