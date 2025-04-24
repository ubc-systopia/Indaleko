"""
Test script for Indaleko tools.

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
import datetime
import json
import os
import sys
from typing import Any

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.tools.base import ToolInput, ToolOutput
from query.tools.database.executor import QueryExecutorTool
from query.tools.registry import get_registry
from query.tools.translation.aql_translator import AQLTranslatorTool
from query.tools.translation.nl_parser import NLParserTool


def json_serializable(obj):
    """Convert object to JSON serializable format."""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    return str(obj)


def test_nl_parser(query: str, debug: bool = False) -> ToolOutput:
    """
    Test the NL parser tool.

    Args:
        query (str): The query to parse.
        debug (bool): Whether to print debug information.

    Returns:
        ToolOutput: The result of the tool execution.
    """
    registry = get_registry()

    # Register the NL parser tool
    registry.register_tool(NLParserTool)

    # Create the tool input
    tool_input = ToolInput(
        tool_name="nl_parser",
        parameters={"query": query},
        invocation_id="test-1",
    )

    # Execute the tool
    result = registry.execute_tool(tool_input)

    # Print the result if debug is enabled
    if debug:
        # Convert to dict and handle datetime objects
        result_dict = result.model_dump()
        print(
            f"NL Parser Result: {json.dumps(result_dict, indent=2, default=json_serializable)}",
        )

    return result


def test_aql_translator(
    structured_query: dict[str, Any],
    debug: bool = False,
) -> ToolOutput:
    """
    Test the AQL translator tool.

    Args:
        structured_query (Dict[str, Any]): The structured query to translate.
        debug (bool): Whether to print debug information.

    Returns:
        ToolOutput: The result of the tool execution.
    """
    registry = get_registry()

    # Register the AQL translator tool
    registry.register_tool(AQLTranslatorTool)

    # Create the tool input
    tool_input = ToolInput(
        tool_name="aql_translator",
        parameters={"structured_query": structured_query},
        invocation_id="test-2",
    )

    # Execute the tool
    result = registry.execute_tool(tool_input)

    # Print the result if debug is enabled
    if debug:
        result_dict = result.model_dump()
        print(
            f"AQL Translator Result: {json.dumps(result_dict, indent=2, default=json_serializable)}",
        )

    return result


def test_query_executor(
    query: str,
    bind_vars: dict[str, Any] = None,
    debug: bool = False,
) -> ToolOutput:
    """
    Test the query executor tool.

    Args:
        query (str): The AQL query to execute.
        bind_vars (Dict[str, Any]): The bind variables for the query.
        debug (bool): Whether to print debug information.

    Returns:
        ToolOutput: The result of the tool execution.
    """
    registry = get_registry()

    # Register the query executor tool
    registry.register_tool(QueryExecutorTool)

    # Create parameters with default values
    parameters = {
        "query": query,
        "explain_only": True,  # Only explain the query, don't execute it
        "include_plan": True,
        "all_plans": False,
        "max_plans": 5,
    }

    # Add bind variables if provided
    if bind_vars:
        parameters["bind_vars"] = bind_vars

    # Create the tool input
    tool_input = ToolInput(
        tool_name="query_executor",
        parameters=parameters,
        invocation_id="test-3",
    )

    # Execute the tool
    result = registry.execute_tool(tool_input)

    # Print the result if debug is enabled
    if debug:
        result_dict = result.model_dump()
        print(
            f"Query Executor Result: {json.dumps(result_dict, indent=2, default=json_serializable)}",
        )

    return result


def test_full_pipeline(query: str, debug: bool = False) -> dict[str, Any]:
    """
    Test the full query pipeline.

    Args:
        query (str): The query to test.
        debug (bool): Whether to print debug information.

    Returns:
        Dict[str, Any]: The combined results of all tools.
    """
    # Step 1: Parse the query
    nl_result = test_nl_parser(query, debug)

    if not nl_result.success:
        print(f"Error parsing query: {nl_result.error}")
        return {"error": nl_result.error}

    # Step 2: Translate to AQL
    # Need to convert entities to a format the translator can understand
    from data_models.named_entity import (
        IndalekoNamedEntityDataModel,
        IndalekoNamedEntityType,
        NamedEntityCollection,
    )

    entities = []
    for entity in nl_result.result["entities"]:
        # Convert entity type string to valid IndalekoNamedEntityType
        entity_type = entity["type"]
        try:
            # Try to map the entity type to a valid enum value
            entity_category = IndalekoNamedEntityType(entity_type.lower())
        except ValueError:
            # If not a valid type, default to "item"
            entity_category = IndalekoNamedEntityType.item

        entities.append(
            IndalekoNamedEntityDataModel(
                name=entity["name"],
                category=entity_category,
                description=entity.get("value", entity["name"]),
            ),
        )

    # Create a properly formatted NamedEntityCollection
    entity_collection = NamedEntityCollection(entities=entities)

    structured_query = {
        "original_query": query,
        "intent": nl_result.result["intent"],
        "entities": entity_collection,
    }

    aql_result = test_aql_translator(structured_query, debug)

    if not aql_result.success:
        print(f"Error translating query: {aql_result.error}")
        return {"error": aql_result.error}

    # Step 3: Execute the query
    aql_query = aql_result.result["aql_query"]
    bind_vars = aql_result.result["bind_vars"]

    executor_result = test_query_executor(aql_query, bind_vars, debug)

    if not executor_result.success:
        print(f"Error executing query: {executor_result.error}")
        return {"error": executor_result.error}

    # Combine results
    return {
        "query": query,
        "structured_query": structured_query,
        "aql_query": aql_query,
        "bind_vars": bind_vars,
        "execution_plan": executor_result.result.get("execution_plan", {}),
        "nl_parser_time": nl_result.elapsed_time,
        "aql_translator_time": aql_result.elapsed_time,
        "query_executor_time": executor_result.elapsed_time,
        "total_time": nl_result.elapsed_time + aql_result.elapsed_time + executor_result.elapsed_time,
    }


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test Indaleko tools")
    parser.add_argument("--query", help="The query to test")
    parser.add_argument("--batch", help="Path to a file containing queries to test")
    parser.add_argument("--debug", action="store_true", help="Print debug information")
    parser.add_argument("--output", help="Output file for results")

    args = parser.parse_args()

    # Register all tools
    registry = get_registry()
    registry.register_tool(NLParserTool)
    registry.register_tool(AQLTranslatorTool)
    registry.register_tool(QueryExecutorTool)

    # Run tests
    results = []

    if args.query:
        # Test a single query
        result = test_full_pipeline(args.query, args.debug)
        results.append(result)

    elif args.batch:
        # Test multiple queries from a file
        try:
            with open(args.batch) as f:
                queries = f.readlines()

            for query in queries:
                query = query.strip()
                if not query or query.startswith("#"):
                    continue

                print(f"Testing query: {query}")
                result = test_full_pipeline(query, args.debug)
                results.append(result)

        except FileNotFoundError:
            print(f"Error: Batch file not found: {args.batch}")
            return

    else:
        # Use default exemplar queries
        default_queries = [
            "Show me documents with 'report' in their titles.",
            "Find files I edited on my phone while traveling last month.",
            "Get documents I exchanged with Dr. Jones regarding the conference paper.",
            "Show me files I created while on vacation in Hawaii last June.",
            "Show me photos taken within 16 kilometers of my house.",
            "Find PDFs I opened in the last week.",
        ]

        for query in default_queries:
            print(f"Testing query: {query}")
            result = test_full_pipeline(query, args.debug)
            results.append(result)

    # Write results to output file if specified
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)

    print(f"Tested {len(results)} queries.")

    # Print summary of results
    success_count = sum(1 for r in results if "error" not in r)
    print(f"Success: {success_count}/{len(results)}")

    if success_count < len(results):
        print("Errors:")
        for i, result in enumerate(results):
            if "error" in result:
                query = result.get("query", f"Query {i+1}")
                print(f"  {query}: {result['error']}")


if __name__ == "__main__":
    main()
