"""
Test script for relationship query capabilities.

This script demonstrates how to use the relationship parser and query engine
to find connections between entities in Indaleko.

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
from typing import Dict, List, Any, Optional

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db import IndalekoDBConfig
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from query.query_processing.data_models.relationship_query_model import (
    RelationshipDirection,
    RelationshipEntity,
    RelationshipQuery,
    RelationshipType,
)
from query.query_processing.enhanced_nl_parser import EnhancedNLParser
from query.query_processing.relationship_parser import RelationshipParser
from query.utils.llm_connector.openai_connector import OpenAIConnector
# pylint: enable=wrong-import-position


def get_api_key(api_key_file: Optional[str] = None) -> str:
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
        "reset": "\033[0m"
    }
    
    if color and color in colors:
        print(f"{colors[color]}{text}{colors['reset']}")
    else:
        print(text)


def generate_aql_for_relationship(relationship_query: RelationshipQuery) -> str:
    """
    Generate AQL for a relationship query.
    
    This is a simplified implementation that generates basic AQL for common relationship types.
    A full implementation would need to handle more complex queries and traverse the graph.
    
    Args:
        relationship_query: The relationship query to generate AQL for
        
    Returns:
        str: AQL query for the relationship
    """
    relationship_type = relationship_query.relationship_type
    source_entity = relationship_query.source_entity
    target_entity = relationship_query.target_entity
    direction = relationship_query.direction
    time_constraint = relationship_query.time_constraint or {}
    additional_filters = relationship_query.additional_filters or {}
    
    # Build the AQL based on relationship type
    if relationship_type == RelationshipType.CREATED:
        # User created file relationship
        if source_entity.entity_type == "user" and (target_entity is None or target_entity.entity_type == "file"):
            # Start with the Activities collection to find creation events
            aql = """
            FOR activity IN ActivityContext
                FILTER activity.Action == "create"
            """
            
            # Add user filter if we have a specific user
            if source_entity.identifier and source_entity.identifier != "current_user":
                aql += f"""
                FILTER activity.User.Id == "{source_entity.identifier}"
                """
                
            # Add time constraints if available
            if time_constraint.get("start_time"):
                aql += f"""
                FILTER activity.Timestamp >= "{time_constraint['start_time']}"
                """
                
            if time_constraint.get("end_time"):
                aql += f"""
                FILTER activity.Timestamp <= "{time_constraint['end_time']}"
                """
                
            # Join with Objects to get the file details
            aql += """
            LET object = DOCUMENT(activity.ObjectId)
            FILTER object != null
            
            RETURN {
                "activity": activity,
                "object": object
            }
            """
            
            return aql
            
    elif relationship_type == RelationshipType.MODIFIED:
        # User modified file relationship
        if source_entity.entity_type == "user" and (target_entity is None or target_entity.entity_type == "file"):
            # Start with the Activities collection to find modification events
            aql = """
            FOR activity IN ActivityContext
                FILTER activity.Action == "modify"
            """
            
            # Add user filter if we have a specific user
            if source_entity.identifier and source_entity.identifier != "current_user":
                aql += f"""
                FILTER activity.User.Id == "{source_entity.identifier}"
                """
                
            # Add time constraints if available
            if time_constraint.get("start_time"):
                aql += f"""
                FILTER activity.Timestamp >= "{time_constraint['start_time']}"
                """
                
            if time_constraint.get("end_time"):
                aql += f"""
                FILTER activity.Timestamp <= "{time_constraint['end_time']}"
                """
                
            # Join with Objects to get the file details
            aql += """
            LET object = DOCUMENT(activity.ObjectId)
            FILTER object != null
            
            RETURN {
                "activity": activity,
                "object": object
            }
            """
            
            return aql
            
    elif relationship_type == RelationshipType.SHARED_WITH:
        # User shared file with another user
        if source_entity.entity_type == "user" and target_entity and target_entity.entity_type == "user":
            # Start with the SharingActivity collection
            aql = """
            FOR sharing IN SharingActivity
                FILTER sharing.Action == "share"
            """
            
            # Add source user filter
            if source_entity.identifier and source_entity.identifier != "current_user":
                aql += f"""
                FILTER sharing.SourceUser.Id == "{source_entity.identifier}"
                """
                
            # Add target user filter
            if target_entity.identifier:
                aql += f"""
                FILTER sharing.TargetUser.Id == "{target_entity.identifier}"
                """
                
            # Add time constraints if available
            if time_constraint.get("start_time"):
                aql += f"""
                FILTER sharing.Timestamp >= "{time_constraint['start_time']}"
                """
                
            if time_constraint.get("end_time"):
                aql += f"""
                FILTER sharing.Timestamp <= "{time_constraint['end_time']}"
                """
                
            # Join with Objects to get the file details
            aql += """
            LET object = DOCUMENT(sharing.ObjectId)
            FILTER object != null
            
            RETURN {
                "sharing": sharing,
                "object": object
            }
            """
            
            return aql
            
    elif relationship_type == RelationshipType.SAME_FOLDER:
        # Find files in the same folder
        if source_entity.entity_type == "file":
            # First find the folder of the source file
            aql = """
            LET sourceFile = (
                FOR file IN Objects
            """
            
            # Add source file filter if we have an identifier
            if source_entity.identifier:
                aql += f"""
                FILTER file.Label == "{source_entity.identifier}" OR 
                       file.Path LIKE "%{source_entity.identifier}"
                """
                
            aql += """
                LIMIT 1
                RETURN file
            )[0]
            
            LET sourceFolder = REGEX_REPLACE(sourceFile.Record.Attributes.Path, "/[^/]+$", "")
            
            FOR file IN Objects
                FILTER file._id != sourceFile._id
                FILTER REGEX_REPLACE(file.Record.Attributes.Path, "/[^/]+$", "") == sourceFolder
            """
            
            # Add additional filters if available
            for field, filter_info in additional_filters.items():
                if field == "file_type" and filter_info.get("value"):
                    extensions = filter_info.get("value")
                    if isinstance(extensions, str):
                        extensions = [extensions]
                    
                    aql += """
                    FILTER (
                    """
                    for i, ext in enumerate(extensions):
                        if i > 0:
                            aql += " OR "
                        aql += f"""
                        LOWER(file.Label) LIKE "%.{ext.lower()}"
                        """
                    aql += """
                    )
                    """
                    
            aql += """
            RETURN file
            """
            
            return aql
    
    # Default to a simple query if we don't have a specific pattern
    return """
    // This is a placeholder query for an unsupported relationship type
    // In a full implementation, we would handle all relationship types
    FOR doc IN Objects
        LIMIT 10
        RETURN doc
    """


def process_relationship_query(
    query: str,
    model: str = "gpt-4o",
    verbose: bool = False,
    execute: bool = False,
    json_output: bool = False,
):
    """
    Process a natural language query for relationships using the relationship parser.
    
    Args:
        query: Natural language query for relationships
        model: OpenAI model to use
        verbose: Whether to print detailed output
        execute: Whether to execute the generated AQL query
        json_output: Whether to output results as JSON
    """
    # Initialize database connection
    db_config = IndalekoDBConfig()
    collections_metadata = IndalekoDBCollectionsMetadata(db_config)
    
    # Initialize OpenAI connector
    openai_key = get_api_key()
    llm_connector = OpenAIConnector(api_key=openai_key, model=model)
    
    # Initialize enhanced NL parser and relationship parser
    enhanced_parser = EnhancedNLParser(llm_connector, collections_metadata)
    relationship_parser = RelationshipParser(
        llm_connector=llm_connector,
        collections_metadata=collections_metadata,
        enhanced_parser=enhanced_parser
    )
    
    # Parse the relationship query
    print_color("Parsing relationship query...", "blue")
    relationship_query = relationship_parser.parse_relationship_query(query)
    
    # Generate AQL for the relationship query
    aql_query = generate_aql_for_relationship(relationship_query)
    
    # Prepare result data
    result = {
        "original_query": query,
        "relationship_query": relationship_query.model_dump(),
        "aql_query": aql_query,
    }
    
    # Execute the query if requested
    if execute:
        print_color("Executing AQL query...", "blue")
        try:
            cursor = db_config.db.aql.execute(aql_query)
            query_results = [doc for doc in cursor]
            result["execution_results"] = query_results[:10]  # Limit to first 10 results
            result["result_count"] = len(query_results)
        except Exception as e:
            print_color(f"Error executing query: {e}", "red")
            result["error"] = str(e)
    
    # Output as JSON if requested
    if json_output:
        print(json.dumps(result, indent=2, default=lambda o: str(o)))
        return
    
    # Format and display results
    print_color("\nRelationship Query Results", "blue")
    print_section("Original Query", query)
    
    # Display relationship information
    print_section("Relationship Type", relationship_query.relationship_type)
    print_section("Direction", relationship_query.direction)
    
    # Display source entity
    print_section("Source Entity")
    print(f"Type: {relationship_query.source_entity.entity_type}")
    if relationship_query.source_entity.identifier:
        print(f"Identifier: {relationship_query.source_entity.identifier}")
    for key, value in relationship_query.source_entity.attributes.items():
        print(f"{key}: {value}")
    
    # Display target entity if available
    if relationship_query.target_entity:
        print_section("Target Entity")
        print(f"Type: {relationship_query.target_entity.entity_type}")
        if relationship_query.target_entity.identifier:
            print(f"Identifier: {relationship_query.target_entity.identifier}")
        for key, value in relationship_query.target_entity.attributes.items():
            print(f"{key}: {value}")
    
    # Display time constraints if available
    if relationship_query.time_constraint:
        print_section("Time Constraints")
        for key, value in relationship_query.time_constraint.items():
            print(f"{key}: {value}")
    
    # Display additional filters if available
    if relationship_query.additional_filters:
        print_section("Additional Filters")
        for key, value in relationship_query.additional_filters.items():
            print(f"{key}: {value}")
    
    # Display confidence
    print_section("Confidence", f"{relationship_query.confidence:.2f}")
    
    # Display generated AQL
    print_section("Generated AQL Query")
    print_color(aql_query, "cyan")
    
    # Display execution results if available
    if execute and "execution_results" in result:
        print_section("Query Results")
        if "error" in result:
            print_color(f"Error: {result['error']}", "red")
        elif result["result_count"] == 0:
            print("No results found.")
        else:
            print(f"Found {result['result_count']} results:")
            for i, res in enumerate(result["execution_results"]):
                print(f"\nResult {i+1}:")
                if isinstance(res, dict):
                    for key, value in res.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"  {res}")


def main():
    """Main function to run the relationship query test."""
    parser = argparse.ArgumentParser(
        description="Test relationship query capabilities in Indaleko",
        epilog="Example: python -m query.test_relationship_query --query 'Show files I shared with Bob last week'"
    )
    
    # Add arguments
    parser.add_argument("--query", type=str, help="Natural language query to process")
    parser.add_argument("--model", type=str, default="gpt-4o", help="OpenAI model to use (default: gpt-4o)")
    parser.add_argument("--verbose", action="store_true", help="Print detailed output")
    parser.add_argument("--execute", action="store_true", help="Execute the generated AQL query")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--debug", action="store_true", help="Show debug output")
    
    # Add examples to help users understand the capabilities
    parser.add_argument("--examples", action="store_true", help="Show example relationship queries")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Enable debug output if requested
    if args.debug:
        from icecream import ic
        ic.enable()
    else:
        from icecream import ic
        ic.disable()
    
    # Show examples if requested
    if args.examples:
        print_color("Example Relationship Queries:", "blue")
        print_color("\nUser-File Relationships:", "green")
        print("1. Show files I created last week")
        print("2. Find documents modified by Alice")
        print("3. What files have I viewed today?")
        
        print_color("\nFile-File Relationships:", "green")
        print("1. Find other files in the same folder as report.docx")
        print("2. Show files derived from source.txt")
        print("3. What files contain references to budget.xlsx?")
        
        print_color("\nUser-User Relationships:", "green")
        print("1. What files did I share with Bob?")
        print("2. Show documents that Alice and I both edited")
        print("3. Find files that Bob recommended to me last month")
        
        print_color("\nComplex Relationships:", "green")
        print("1. Find PDF files I created last week and shared with the marketing team")
        print("2. Show me documents related to the project that Alice and I both worked on")
        print("3. What spreadsheets in the Finance folder have been modified by both me and Bob?")
        
        return
    
    # Get query from arguments or prompt
    query = args.query
    if not query:
        query = input("Enter your relationship query: ")
    
    # Process the query
    process_relationship_query(
        query=query,
        model=args.model,
        verbose=args.verbose,
        execute=args.execute,
        json_output=args.json,
    )


if __name__ == "__main__":
    main()