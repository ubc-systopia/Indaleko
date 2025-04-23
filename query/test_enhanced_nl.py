"""
Test script for enhanced natural language query capabilities.

This script demonstrates how to use the enhanced NL parser and AQL translator
with improved natural language understanding.

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
import configparser
import json
import os
import sys

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db import IndalekoDBConfig
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from query.query_processing.data_models.translator_input import TranslatorInput
from query.query_processing.enhanced_nl_parser import EnhancedNLParser
from query.query_processing.query_translator.enhanced_aql_translator import (
    EnhancedAQLTranslator,
)
from query.search_execution.query_executor.aql_executor import AQLExecutor
from query.utils.llm_connector.openai_connector import OpenAIConnector

# pylint: enable=wrong-import-position


def get_api_key(api_key_file: str | None = None) -> str:
    """Get the OpenAI API key from the config file."""
    if api_key_file is None:
        config_dir = os.path.join(os.environ.get("INDALEKO_ROOT"), "config")
        api_key_file = os.path.join(config_dir, "openai-key.ini")

    assert os.path.exists(api_key_file), f"API key file ({api_key_file}) not found"
    config = configparser.ConfigParser()
    config.read(api_key_file, encoding="utf-8-sig")
    openai_key = config["openai"]["api_key"]

    if openai_key is None:
        raise ValueError("OpenAI API key not found in config file")
    if openai_key[0] == '"' or openai_key[0] == "'":
        openai_key = openai_key[1:]
    if openai_key[-1] == '"' or openai_key[-1] == "'":
        openai_key = openai_key[:-1]

    return openai_key


def print_section(title, content=None):
    """Helper function to print a formatted section."""
    print(f"\n{'-' * 5} {title} {'-' * 5}")
    if content is not None:
        print(content)


def print_color(text, color=None):
    """Print text in color if supported by terminal."""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "reset": "\033[0m",
    }

    if color and color in colors:
        print(f"{colors[color]}{text}{colors['reset']}")
    else:
        print(text)


def process_query(
    query: str,
    model: str = "gpt-4o",
    verbose: bool = False,
    execute: bool = False,
    json_output: bool = False,
    output_file: str | None = None,
):
    """
    Process a natural language query using the enhanced NL parser and AQL translator.

    Args:
        query: The natural language query to process
        model: The OpenAI model to use
        verbose: Whether to print detailed output
        execute: Whether to execute the generated AQL query
        json_output: Whether to output results as JSON
        output_file: File to write JSON output to
    """
    # Initialize database connection
    db_config = IndalekoDBConfig()
    collections_metadata = IndalekoDBCollectionsMetadata(db_config)

    # Initialize OpenAI connector
    openai_key = get_api_key()
    llm_connector = OpenAIConnector(api_key=openai_key, model=model)

    # Initialize enhanced NL parser and AQL translator
    nl_parser = EnhancedNLParser(llm_connector, collections_metadata)
    aql_translator = EnhancedAQLTranslator(collections_metadata)

    # Parse the query
    print_color("Parsing query with enhanced NL parser...", "blue")
    query_understanding = nl_parser.parse_enhanced(query)

    # Create structured query
    query_data = TranslatorInput(
        Query=query_understanding,
        Connector=llm_connector,
    )

    # Translate to AQL
    print_color("Translating to AQL with enhanced translator...", "blue")
    translated_query = aql_translator.translate_enhanced(
        query_understanding, query_data,
    )

    # Prepare result data
    result = {
        "original_query": query,
        "enhanced_understanding": query_understanding.model_dump(),
        "translated_query": translated_query.model_dump(),
    }

    # Execute the query if requested
    if execute:
        print_color("Executing generated AQL query...", "blue")
        executor = AQLExecutor()
        query_results = executor.execute(translated_query.aql_query, db_config)
        result["execution_results"] = query_results[:10]  # Limit to first 10 results

    # Output as JSON if requested
    if json_output:
        output = json.dumps(result, indent=2)
        if output_file:
            with open(output_file, "w") as f:
                f.write(output)
            print(f"Results saved to {output_file}")
        else:
            print(output)
        return

    # Format and display results
    print_color("\nNatural Language Query Processing Results", "blue")
    print_section("Original Query", query)

    # Display query understanding
    print_section("Enhanced Understanding")
    print(f"Primary Intent: {query_understanding.intent.primary_intent}")
    if query_understanding.intent.secondary_intents:
        print(
            f"Secondary Intents: {', '.join(query_understanding.intent.secondary_intents)}",
        )
    print(f"Description: {query_understanding.intent.description}")
    print(f"Overall Confidence: {query_understanding.confidence:.2f}")

    # Display entities
    if query_understanding.entities:
        print_section("Extracted Entities")
        for entity in query_understanding.entities:
            print_color(
                f"- {entity.original_text} → {entity.normalized_value} ({entity.entity_type})",
                "green",
            )

    # Display constraints
    if query_understanding.constraints:
        print_section("Query Constraints")
        for constraint in query_understanding.constraints:
            print_color(
                f"- {constraint.field} {constraint.operation} {constraint.value}",
                "yellow",
            )

    # Display generated AQL
    print_section("Generated AQL Query")
    print_color(translated_query.aql_query, "cyan")

    # Display bind variables
    if translated_query.bind_vars:
        print_section("Bind Variables")
        for key, value in translated_query.bind_vars.items():
            print(f"- {key}: {value}")

    # Display confidence and explanation
    print_section("Translation Confidence", f"{translated_query.confidence:.2f}")
    print_section("Explanation", translated_query.explanation)

    # Display performance hints
    if (
        hasattr(aql_translator, "performance_hints")
        and aql_translator.performance_hints
    ):
        print_section("Performance Hints")
        for hint in aql_translator.performance_hints:
            if hint.severity == "warning":
                print_color(
                    f"- {hint.description} ({hint.affected_component})", "yellow",
                )
            elif hint.severity == "error" or hint.severity == "critical":
                print_color(f"- {hint.description} ({hint.affected_component})", "red")
            else:
                print_color(f"- {hint.description}", "green")

            if hint.recommendation:
                print(f"  Recommendation: {hint.recommendation}")

    # Display context information
    if query_understanding.context:
        print_section("Context Information")
        print(f"Collections: {', '.join(query_understanding.context.collections)}")
        if query_understanding.context.temporal_context:
            temp = query_understanding.context.temporal_context
            print(
                f"Temporal Context: {temp.time_field} {temp.start_time or ''} - {temp.end_time or ''}",
            )

    # Display suggested facets
    if query_understanding.suggested_facets:
        print_section("Suggested Facets")
        for facet in query_understanding.suggested_facets:
            print_color(f"- {facet.facet_name}: {facet.facet_description}", "magenta")
            if facet.example_values:
                print(f"  Example values: {', '.join(facet.example_values)}")

    # Display conversational response
    print_section("Conversational Response")
    print_color(query_understanding.conversational_response, "cyan")

    # Display execution results if available
    if execute and "execution_results" in result:
        print_section("Query Results")
        for i, res in enumerate(result["execution_results"]):
            print(f"Result {i+1}:")
            if isinstance(res, dict) and "Label" in res:
                print(f"  - {res['Label']}")
            elif isinstance(res, dict) and "Path" in res:
                print(f"  - {res['Path']}")
            elif isinstance(res, dict):
                for j, (k, v) in enumerate(res.items()):
                    if j < 3:  # Limit to first 3 fields
                        print(f"  - {k}: {v}")
                if len(res) > 3:
                    print(f"  - ... and {len(res) - 3} more fields")
            else:
                print(f"  - {res}")


def main():
    """Main function to run the test."""
    # Initialize argument parser
    parser = argparse.ArgumentParser(
        description="Test enhanced natural language query capabilities",
        epilog="Example: python -m query.test_enhanced_nl --query 'Find PDF files created last week'",
    )

    # Add arguments
    parser.add_argument("--query", type=str, help="Natural language query to process")
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o",
        help="OpenAI model to use (default: gpt-4o)",
    )
    parser.add_argument("--verbose", action="store_true", help="Print detailed output")
    parser.add_argument(
        "--execute", action="store_true", help="Execute the generated AQL query",
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--output", type=str, help="Output file for JSON results")
    parser.add_argument("--debug", action="store_true", help="Show debug output")

    # Parse arguments
    args = parser.parse_args()

    # Enable debug output if requested
    if args.debug:
        from icecream import ic

        ic.enable()
    else:
        from icecream import ic

        ic.disable()

    # Get query from arguments or prompt
    query = args.query
    if not query:
        query = input("Enter your query: ")

    # Process the query
    process_query(
        query=query,
        model=args.model,
        verbose=args.verbose,
        execute=args.execute,
        json_output=args.json,
        output_file=args.output,
    )


if __name__ == "__main__":
    main()
