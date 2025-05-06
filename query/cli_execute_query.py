"""
CLI utility for executing queries directly.

This standalone script provides a convenient way to execute Indaleko
queries both interactively and programmatically, making it suitable for
ablation testing and other integration tests.

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
import json
import logging
import os
import sys
from typing import Dict, List, Any, Optional

# Add the Indaleko root to the path
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.cli import execute_query
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from db.db_collections import IndalekoDBCollections


def setup_logging(log_level: str = "INFO") -> None:
    """Set up logging for the application."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def ablate_collection(collection_name: str) -> bool:
    """
    Ablate a collection to make it invisible to queries.

    Args:
        collection_name: Name of the collection to ablate

    Returns:
        True if successful, False otherwise
    """
    try:
        metadata_manager = IndalekoDBCollectionsMetadata()
        metadata_manager.ablate_collection(collection_name)
        logging.info(f"Ablated collection: {collection_name}")
        return True
    except Exception as e:
        logging.error(f"Failed to ablate collection {collection_name}: {e}")
        return False


def restore_collection(collection_name: str) -> bool:
    """
    Restore a previously ablated collection.

    Args:
        collection_name: Name of the collection to restore

    Returns:
        True if successful, False otherwise
    """
    try:
        metadata_manager = IndalekoDBCollectionsMetadata()
        result = metadata_manager.restore_collection(collection_name)
        if result:
            logging.info(f"Restored collection: {collection_name}")
        else:
            logging.warning(f"Collection {collection_name} was not ablated")
        return result
    except Exception as e:
        logging.error(f"Failed to restore collection {collection_name}: {e}")
        return False


def run_query(query_text: str, capture_aql: bool = True) -> Dict[str, Any]:
    """
    Execute a natural language query and return the results.

    Args:
        query_text: Natural language query to execute
        capture_aql: Whether to capture the AQL query

    Returns:
        Dictionary with query results and metadata
    """
    try:
        logging.info(f"Executing query: {query_text}")
        results = execute_query(query_text, capture_aql=capture_aql)

        # Extract AQL if available
        aql = ""
        if results and "_debug" in results[0]:
            aql = results[0]["_debug"].get("aql", "")

            # Clean up results by removing _debug field
            for result in results:
                if "_debug" in result:
                    del result["_debug"]

        return {
            "query": query_text,
            "results": results,
            "result_count": len(results),
            "aql": aql,
            "success": True
        }
    except Exception as e:
        logging.error(f"Error executing query: {e}")
        return {
            "query": query_text,
            "results": [],
            "result_count": 0,
            "aql": "",
            "success": False,
            "error": str(e)
        }


def main() -> int:
    """
    Main entry point for the CLI utility.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = argparse.ArgumentParser(description="Execute Indaleko queries directly")
    parser.add_argument("--query", type=str, help="Query to execute")
    parser.add_argument("--ablate", type=str, nargs="+", help="Collections to ablate")
    parser.add_argument("--restore", type=str, nargs="+", help="Collections to restore")
    parser.add_argument("--list-collections", action="store_true", help="List available collections")
    parser.add_argument("--output", type=str, help="Save results to file")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO",
                      help="Set logging level (default: INFO)")

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.log_level)

    # List collections if requested
    if args.list_collections:
        metadata_manager = IndalekoDBCollectionsMetadata()
        collections = metadata_manager.get_all_collections_metadata()

        print("\nAvailable collections:")
        for name in sorted(collections.keys()):
            print(f"  - {name}")

        return 0

    # Ablate collections if requested
    if args.ablate:
        for collection in args.ablate:
            ablate_collection(collection)

    # Restore collections if requested
    if args.restore:
        for collection in args.restore:
            restore_collection(collection)

    # Execute query if provided
    if args.query:
        result = run_query(args.query)

        # Print results
        print(f"\nQuery: {result['query']}")
        print(f"Result count: {result['result_count']}")

        if result['aql']:
            print(f"\nGenerated AQL:")
            print(result['aql'])

        print("\nResults:")
        for i, item in enumerate(result['results'][:10], 1):
            print(f"{i}. {json.dumps(item, indent=2)}")

        if len(result['results']) > 10:
            print(f"... and {len(result['results']) - 10} more results")

        # Save to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            logging.info(f"Results saved to: {args.output}")

    # Interactive mode
    if args.interactive:
        print("\nIndaleko Query CLI Interactive Mode")
        print("Type 'exit' or 'quit' to end the session")
        print("Type 'ablate <collection>' to ablate a collection")
        print("Type 'restore <collection>' to restore a collection")
        print("Type 'list' to list available collections")
        print("Type 'help' for this message\n")

        while True:
            try:
                command = input("Query> ").strip()

                if command.lower() in ['exit', 'quit']:
                    break
                elif command.lower() == 'help':
                    print("\nIndaleko Query CLI Help:")
                    print("  <query text>           - Execute a natural language query")
                    print("  ablate <collection>    - Ablate a collection")
                    print("  restore <collection>   - Restore a collection")
                    print("  list                   - List available collections")
                    print("  help                   - Show this help message")
                    print("  exit, quit             - End the session\n")
                elif command.lower() == 'list':
                    metadata_manager = IndalekoDBCollectionsMetadata()
                    collections = metadata_manager.get_all_collections_metadata()

                    print("\nAvailable collections:")
                    for name in sorted(collections.keys()):
                        print(f"  - {name}")
                    print()
                elif command.lower().startswith('ablate '):
                    collection = command[7:].strip()
                    if ablate_collection(collection):
                        print(f"Collection '{collection}' ablated\n")
                    else:
                        print(f"Failed to ablate collection '{collection}'\n")
                elif command.lower().startswith('restore '):
                    collection = command[8:].strip()
                    if restore_collection(collection):
                        print(f"Collection '{collection}' restored\n")
                    else:
                        print(f"Failed to restore collection '{collection}'\n")
                elif command:
                    # Treat as a query
                    result = run_query(command)

                    # Print results
                    print(f"Result count: {result['result_count']}")

                    if result['aql']:
                        print(f"\nGenerated AQL:")
                        print(result['aql'])

                    print("\nResults:")
                    for i, item in enumerate(result['results'][:5], 1):
                        print(f"{i}. {json.dumps(item, indent=2)}")

                    if len(result['results']) > 5:
                        print(f"... and {len(result['results']) - 5} more results\n")
            except KeyboardInterrupt:
                print("\nSession terminated by user")
                break
            except Exception as e:
                print(f"Error: {e}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
